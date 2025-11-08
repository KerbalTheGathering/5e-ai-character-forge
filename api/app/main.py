import logging
import os, asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Query
from .schemas import AbilitySet
from .rollers import roll_ability_set
from typing import Dict, List
from .schemas import AbilitySet, GenerateInput, CharacterDraft, AbilityBlock, Proficiency
import os, asyncio
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import time
import uuid
import httpx
from requests_cache import CachedSession

from typing import Dict, List
from .schemas import (
    AbilitySet, GenerateInput, CharacterDraft, AbilityBlock, Proficiency,
    BackstoryInput, BackstoryResult, ExportInput, SaveInput, ExportPDFInput,
    MagicItemInput, MagicItem, MagicItemExport,
    SpellInput, Spell, SpellExport,
    LevelPick, ProgressionInput, ProgressionPlan, ProgressionExport
)
import google.generativeai as genai  # for text backstory
# New SDK for image generation
try:
    from google import genai as genai_new
    from google.genai import types as genai_types  # noqa: F401  (kept for completeness)
except Exception:  # pragma: no cover
    genai_new = None  # type: ignore
from fastapi import Response
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
import base64
from io import BytesIO

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
from requests_cache import CachedSession

import sqlite3
from datetime import datetime

import io
import torch
from diffusers import FluxPipeline

load_dotenv()

# Configure application logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("5e-forge")

DB_PATH = "app.db"

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""
    CREATE TABLE IF NOT EXISTS library (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT NOT NULL,
      draft_json TEXT NOT NULL,
      backstory_json TEXT,
      portrait_png BLOB,
      progression_json TEXT
    )
    """)
    # ensure portrait column exists for older DBs
    try:
        con.execute("ALTER TABLE library ADD COLUMN portrait_png BLOB")
        con.commit()
    except Exception:
        pass
    # ensure progression column exists for older DBs
    try:
        con.execute("ALTER TABLE library ADD COLUMN progression_json TEXT")
        con.commit()
    except Exception:
        pass
    con.commit()
    # Magic item library
    con.execute("""
    CREATE TABLE IF NOT EXISTS item_library (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT NOT NULL,
      item_json TEXT NOT NULL,
      prompt TEXT
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS spell_library (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT NOT NULL,
      spell_json TEXT NOT NULL,
      prompt TEXT
    )
    """)
    # Progression plans library
    con.execute("""
    CREATE TABLE IF NOT EXISTS progression_library (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT NOT NULL,
      plan_json TEXT NOT NULL,
      prompt TEXT
    )
    """)
    con.close()

init_db()


PORT = int(os.getenv("PORT_API", "8000"))
RULES_BASE = os.getenv("RULES_BASE_URL", "https://www.dnd5eapi.co")
RULES_API_PREFIX = os.getenv("RULES_API_PREFIX", "api/2014")
GEMINI_MODEL_TEXT = os.getenv("GEMINI_MODEL_TEXT", "gemini-2.5-pro")
GEMINI_MODEL_IMAGE = os.getenv("GEMINI_MODEL_IMAGE", "gemini-2.5-flash-image")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Local inference toggles
USE_LOCAL = os.getenv("USE_LOCAL_INFERENCE", "false").lower() == "true"
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/generate")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "gpt-oss:120b")
LOCAL_PORTRAIT_URL = os.getenv("LOCAL_PORTRAIT_URL", "http://localhost:7860/generate")
LOCAL_IMAGE_BASE_MODEL = os.getenv("LOCAL_IMAGE_BASE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
LOCAL_IMAGE_MODEL = os.getenv("LOCAL_IMAGE_MODEL", "ByteDance/SDXL-Lightning")
# Optional tuning for local image generation
LOCAL_IMAGE_STEPS = int(os.getenv("LOCAL_IMAGE_STEPS", "4"))
LOCAL_IMAGE_GUIDANCE = float(os.getenv("LOCAL_IMAGE_GUIDANCE", "0.0"))
LOCAL_IMAGE_SEED = int(os.getenv("LOCAL_IMAGE_SEED", "0"))
LOCAL_IMAGE_WIDTH = int(os.getenv("LOCAL_IMAGE_WIDTH", "0"))  # 0 = use model default
LOCAL_IMAGE_HEIGHT = int(os.getenv("LOCAL_IMAGE_HEIGHT", "0"))  # 0 = use model default

async def local_text_generate(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(LOCAL_LLM_URL, json={"model": LOCAL_LLM_MODEL, "prompt": prompt, "stream": False})
            r.raise_for_status(); data = r.json();
            return data.get("response") or data.get("text") or data.get("message") or ""
    except Exception as e:
        raise HTTPException(502, f"local llm failed: {e}")

async def local_image_generate(prompt: str) -> bytes:
    """Generate an image locally.
    Diffusers pipeline (MPS preferred on macOS)
    Returns PNG bytes.
    """
    logging.info("Attempting local image generation via Diffusers (preferring MPS)...")
    # 1) Diffusers path
    try:
        # Prefer MPS on macOS; then CUDA; else CPU. Guard CUDA probe to avoid errors on CPU-only builds.
        try:
            mps_ok = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
        except Exception:
            mps_ok = False
        cuda_ok = False
        try:
            cuda_ok = bool(getattr(torch.version, "cuda", None)) and bool(hasattr(torch, "cuda")) and bool(torch.cuda.is_available())
        except Exception:
            cuda_ok = False
        device = "mps" if mps_ok else ("cuda" if cuda_ok else "cpu")
        # MPS prefers float16; CUDA commonly uses bfloat16; CPU stays float32.
        dtype = torch.float16 if device == "mps" else (torch.bfloat16 if device == "cuda" else torch.float32)
        logger.info("Diffusion device=%s dtype=%s model=%s", device, str(dtype).split(".")[-1], LOCAL_IMAGE_MODEL)

        # Load the requested model repo (e.g., FLUX.1-schnell) with correct dtype.
        # Use new `dtype` arg (avoid deprecation warning). Do not force a variant.
        pipe = FluxPipeline.from_pretrained(LOCAL_IMAGE_MODEL, dtype=dtype)

        try:
            logger.info("Moving diffusion pipeline to device %s...", device)
            pipe.to(device)
        except Exception:
            logger.info("Diffusion pipeline .to(%s) failed; continuing on default device", device)

        aspect_ratios = {
            "1:1": (1328, 1328),
            "16:9": (1664, 928),
            "9:16": (928, 1664),
            "4:3": (1472, 1140),
            "3:4": (1140, 1472),
            "3:2": (1584, 1056),
            "2:3": (1056, 1584),
        }
        width, height = aspect_ratios.get("1:1", (0, 0))
        seed = LOCAL_IMAGE_SEED if LOCAL_IMAGE_SEED >= 0 else 0
        # Use CPU generator; MPS generators are unsupported and can cause runtime errors.
        #gen = torch.Generator(device=device).manual_seed(seed)
        #width = LOCAL_IMAGE_WIDTH if LOCAL_IMAGE_WIDTH > 0 else (512 if device in ("mps", "cuda") else 0)
        #height = LOCAL_IMAGE_HEIGHT if LOCAL_IMAGE_HEIGHT > 0 else (512 if device in ("mps", "cuda") else 0)
        # Use CPU generator on MPS to avoid known issues with MPS generators.
        gen_device = "cpu" if device == "mps" else device
        kwargs = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": LOCAL_IMAGE_STEPS,
            "guidance_scale": LOCAL_IMAGE_GUIDANCE,
            "max_sequence_length": 512,
            "generator": torch.Generator(device=gen_device).manual_seed(seed),
        }

        try:
            img = pipe(**kwargs).images[0]
        except Exception as inner_e:
            # If MPS path fails (common with certain PyTorch MPS edge cases), retry on CPU.
            if device == "mps":
                logger.warning("MPS generation failed (%s); retrying on CPU float32...", inner_e)
                pipe.to("cpu")
                kwargs_retry = dict(kwargs)
                kwargs_retry["generator"] = torch.Generator(device="cpu").manual_seed(seed)
                img = pipe(**kwargs_retry).images[0]
            else:
                raise
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.exception("Diffusers generation failed: %s", e)
        raise HTTPException(500, f"local Diffusers generation failed: {e}. Ensure torch with MPS support and diffusers are installed.")

def use_local(engine: str | None) -> bool:
    return (engine == 'local') or (engine is None and USE_LOCAL)

app = FastAPI(title="5e-ai-character-forge API", version="0.1.0")

# Request/response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    start = time.perf_counter()
    path = request.url.path
    method = request.method
    try:
        logger.info("%s %s start rid=%s", method, path, rid)
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("%s %s done status=%s rid=%s duration_ms=%s", method, path, getattr(response, 'status_code', 'NA'), rid, duration_ms)
        try:
            response.headers["X-Request-ID"] = rid
        except Exception:
            pass
        return response
    except HTTPException as he:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.warning("%s %s http_error status=%s detail=%s rid=%s duration_ms=%s", method, path, he.status_code, he.detail, rid, duration_ms)
        raise
    except Exception as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.exception("%s %s unhandled_error rid=%s duration_ms=%s", method, path, rid, duration_ms)
        raise

# CORS: allow local Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{os.getenv('PORT_WEB','5173')}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# simple on-disk cache for rules calls
cache_dir = Path(".cache"); cache_dir.mkdir(exist_ok=True)
rules_cache = CachedSession(cache_name=str(cache_dir / "rules_cache"), backend="sqlite", expire_after=60*60*24)

def mod(score: int) -> int:
    return (score - 10) // 2

def pb(level: int) -> int:
    # 5e proficiency progression
    if level <= 4: return 2
    if level <= 8: return 3
    if level <= 12: return 4
    if level <= 16: return 5
    return 6

async def fetch_json(url: str):
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()
    
def markdown_from_draft(d: CharacterDraft, bs: BackstoryResult | None = None) -> str:
    lines = []
    lines.append(f"# {d.race} {d.cls} — Level {d.level}")
    lines.append("")
    lines.append(f"- **Background:** {d.background}")
    lines.append(f"- **Proficiency Bonus:** +{d.proficiency_bonus}")
    lines.append(f"- **Hit Die:** d{d.hit_die}")
    lines.append(f"- **Speed:** {d.speed} ft")
    lines.append(f"- **AC (no armor):** {d.armor_class_basic}")
    a = d.abilities
    lines.append(
        f"- **Abilities:** STR {a.STR} ({a.STR_mod:+}), DEX {a.DEX} ({a.DEX_mod:+}), "
        f"CON {a.CON} ({a.CON_mod:+}), INT {a.INT} ({a.INT_mod:+}), "
        f"WIS {a.WIS} ({a.WIS_mod:+}), CHA {a.CHA} ({a.CHA_mod:+})"
    )
    if d.saving_throws:
        lines.append(f"- **Saving Throws:** {', '.join(d.saving_throws)}")
    if d.languages:
        lines.append(f"- **Languages:** {', '.join(d.languages)}")
    if d.proficiencies:
        lines.append(f"- **Proficiencies:** {', '.join(p.name for p in d.proficiencies)}")
    if d.equipment:
        lines.append(f"- **Equipment:** {', '.join(d.equipment)}")
    lines.append("")
    if bs:
        lines.append("## Backstory")
        lines.append("")
        lines.append(bs.prose_markdown.strip())
        lines.append("")
        lines.append("### Traits / Ideals / Bonds / Flaws")
        lines.append(f"- **Traits:** {', '.join(bs.traits) or '—'}")
        lines.append(f"- **Ideals:** {', '.join(bs.ideals) or '—'}")
        lines.append(f"- **Bonds:** {', '.join(bs.bonds) or '—'}")
        lines.append(f"- **Flaws:** {', '.join(bs.flaws) or '—'}")
        if bs.hooks:
            lines.append(f"- **Hooks:** {', '.join(bs.hooks)}")
    return "\n".join(lines)

def markdown_from_progression(plan: ProgressionPlan, draft: CharacterDraft | None = None) -> str:
    lines: list[str] = []
    title = plan.name or (draft.name if draft and draft.name else None) or "Progression Plan"
    lines.append(f"# {title}")
    cls_name = draft.cls if draft else plan.class_index.title()
    lines.append("")
    lines.append(f"- Class: {cls_name}")
    if draft:
        lines.append(f"- Ancestry/Background: {draft.race} · {draft.background}")
    lines.append(f"- Target Level: {plan.target_level}")
    lines.append("")
    lines.append("## Level-by-Level")
    for p in plan.picks:
        hdr = f"### Level {p.level}"
        if p.subclass:
            hdr += f" — Subclass: {p.subclass}"
        lines.append(hdr)
        feats = ", ".join(p.features) if p.features else "—"
        lines.append(f"- Features: {feats}")
        if p.asi:
            lines.append(f"- ASI/Feat: {p.asi}")
        if p.spells_known:
            lines.append(f"- Spells Known: {', '.join(p.spells_known)}")
        if p.prepared:
            lines.append(f"- Prepared: {', '.join(p.prepared)}")
        if p.hp_gain is not None:
            lines.append(f"- HP Gain: {p.hp_gain}")
        if p.notes:
            lines.append("")
            lines.append(p.notes)
        lines.append("")
    if plan.notes_markdown:
        lines.append("## Notes")
        lines.append(plan.notes_markdown)
    return "\n".join(lines)

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/health/model")
async def health_model():
    """Report local inference model/device info for image and text.
    Note: This does not load pipelines; it infers device/dtype from torch availability
    and optionally probes the local text endpoint with a fast OPTIONS request.
    """
    # device/dtype selection mirrors local_image_generate()
    try:
        try:
            cuda_ok = bool(hasattr(torch, "cuda")) and bool(torch.cuda.is_available())
        except Exception:
            cuda_ok = False
        try:
            mps_ok = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
        except Exception:
            mps_ok = False
        device = "cuda" if cuda_ok else ("mps" if mps_ok else "cpu")
        dtype = "bfloat16" if device == "cuda" else ("float16" if device == "mps" else "float32")
    except Exception:
        device = "cpu"; dtype = "float32"

    # Optional quick reachability probe for local text endpoint
    text_reachable = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.options(LOCAL_LLM_URL)
            text_reachable = resp.status_code < 500
    except Exception:
        text_reachable = False

    return {
        "mode_default": "local" if USE_LOCAL else "google",
        "image": {
            "model": LOCAL_IMAGE_MODEL,
            "base_model": LOCAL_IMAGE_BASE_MODEL,
            "device": device,
            "dtype": dtype,
        },
        "text": {
            "url": LOCAL_LLM_URL,
            "model": LOCAL_LLM_MODEL,
            "reachable": text_reachable,
        },
    }

@app.get("/api/rules/{path:path}")
async def rules_proxy(path: str):
    logger.debug("rules_proxy: path=%s", path)
    # Proxies dnd5eapi with caching + minimal normalization
    url = f"{RULES_BASE}/{path.lstrip('/')}"
    try:
        # CachedSession is sync; run in thread
        def _get():
            return rules_cache.get(url, timeout=20)
        resp = await asyncio.to_thread(_get)
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, f"dnd5eapi error: {resp.text[:200]}")
        return resp.json()
    except Exception as e:
        raise HTTPException(502, f"rules proxy failed: {e}")

@app.post("/api/generate", response_model=CharacterDraft)
async def generate_character(payload: GenerateInput):
    logger.debug("generate_character: class=%s race=%s background=%s level=%s", payload.class_index, payload.race_index, payload.background_index, payload.level)
    # fetch class / race / background
    cls = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/classes/{payload.class_index}")
    race = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/races/{payload.race_index}")
    bg   = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/backgrounds/{payload.background_index}")

    # scores -> abilities
    if len(payload.scores) != 6 or len(payload.assignment) != 6:
        raise HTTPException(400, "scores and assignment must each have length 6")
    ability_map: Dict[str,int] = {}
    for score, abil in zip(payload.scores, payload.assignment):
        ability_map[abil] = score
    for k in ["STR","DEX","CON","INT","WIS","CHA"]:
        if k not in ability_map: raise HTTPException(400, f"missing ability in assignment: {k}")

    ab = AbilityBlock(
        STR=ability_map["STR"], DEX=ability_map["DEX"], CON=ability_map["CON"],
        INT=ability_map["INT"], WIS=ability_map["WIS"], CHA=ability_map["CHA"],
        STR_mod=(ability_map["STR"]-10)//2, DEX_mod=(ability_map["DEX"]-10)//2, CON_mod=(ability_map["CON"]-10)//2,
        INT_mod=(ability_map["INT"]-10)//2, WIS_mod=(ability_map["WIS"]-10)//2, CHA_mod=(ability_map["CHA"]-10)//2,
    )
    def pb(level:int)->int:
        return 2 if level<=4 else 3 if level<=8 else 4 if level<=12 else 5 if level<=16 else 6
    level = max(1, min(payload.level, 20))
    hit_die = int(cls.get("hit_die", 8))
    saves = [st["name"] for st in cls.get("saving_throws", [])]

    # languages from race + background (options not chosen yet)
    langs = [l["name"] for l in race.get("languages", [])]
    langs += [l["name"] for l in bg.get("languages", [])] if bg.get("languages") else []

    # proficiencies
    profs: List[Proficiency] = []
    for p in cls.get("proficiencies", []):
        profs.append(Proficiency(type="proficiency", name=p["name"], source="class"))
    for p in race.get("starting_proficiencies", []):
        profs.append(Proficiency(type="proficiency", name=p["name"], source="race"))
    for p in bg.get("starting_proficiencies", []):
        profs.append(Proficiency(type="proficiency", name=p["name"], source="background"))

    # equipment: class starting_equipment + background starting_equipment
    equip: List[str] = []
    try:
        cls_eq = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/starting-equipment/{payload.class_index}")
        for item in cls_eq.get("starting_equipment", []):
            equip.append(f"{item.get('quantity','1')}x {item['equipment']['name']}")
    except Exception:
        pass
    for item in bg.get("starting_equipment", []) or []:
        equip.append(f"{item.get('quantity','1')}x {item['equipment']['name']}")

    # NEW: class features & spell slots at this level (compute BEFORE constructing draft)
    lvl = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/classes/{payload.class_index}/levels/{level}")
    feat_names = [f["name"] for f in lvl.get("features", [])]

    slots: dict[str, int] | None = None
    sc = lvl.get("spellcasting")
    if sc:
        slots = {}
        for k, v in sc.items():
            if k.startswith("spell_slots_level_"):
                n = k.split("_")[-1]
                try:
                    slots[n] = int(v or 0)
                except Exception:
                    pass

    # construct draft (now include features & spell_slots)
    draft = CharacterDraft(
        level=level,
        cls=cls.get("name", payload.class_index),
        race=race.get("name", payload.race_index),
        background=bg.get("name", payload.background_index),
        hit_die=hit_die,
        proficiency_bonus=pb(level),
        abilities=ab,
        speed=int(race.get("speed", 30)),
        saving_throws=saves,
        languages=sorted(list(dict.fromkeys(langs))),
        proficiencies=profs,
        equipment=equip,
        armor_class_basic=10 + ab.DEX_mod,
        features=feat_names,            # <-- added
        spell_slots=slots,              # <-- added
    )
    return draft


@app.get("/api/roll/abilities", response_model=AbilitySet)
async def roll_abilities(seed: int | None = Query(default=None, description="optional seed for reproducibility")):
    logger.debug("roll_abilities: seed=%s", seed)
    return roll_ability_set(seed)

BACKSTORY_SYS = (
 "You are an expert tabletop RPG writer. Write backstories consistent with D&D 5e SRD, "
 "avoiding copyrighted setting names. Use clear, evocative prose suitable for a character handout."
)

@app.post("/api/backstory", response_model=BackstoryResult)
async def backstory_route(payload: BackstoryInput, engine: str | None = Query(default=None)):
    logger.debug("backstory: request received for %s/%s level %s", payload.draft.race, payload.draft.cls, payload.draft.level)
    model = None
    if not use_local(engine):
        if not GOOGLE_API_KEY:
            raise HTTPException(400, "Missing GOOGLE_API_KEY in environment.")
        model = genai.GenerativeModel(GEMINI_MODEL_TEXT, system_instruction=BACKSTORY_SYS)

    d = payload.draft
    abil = d.abilities
    summary = (
        f"{d.race} {d.cls}, Level {d.level}. Background: {d.background}. "
        f"Abilities STR {abil.STR} ({abil.STR_mod:+}), DEX {abil.DEX} ({abil.DEX_mod:+}), "
        f"CON {abil.CON} ({abil.CON_mod:+}), INT {abil.INT} ({abil.INT_mod:+}), "
        f"WIS {abil.WIS} ({abil.WIS_mod:+}), CHA {abil.CHA} ({abil.CHA_mod:+}). "
        f"Languages: {', '.join(d.languages) or '—'}. "
        f"Saving Throws: {', '.join(d.saving_throws) or '—'}."
    )
    length_map = {"short":"~120-180 words","standard":"~250-350 words","long":"~500-700 words"}
    prompt = (
        f"Character summary: {summary}\n"
        f"Tone preset: {payload.tone}. Target length: {length_map[payload.length]}.\n"
        f"Return JSON ONLY with keys: summary, traits (list), ideals (list), bonds (list), flaws (list), "
        f"hooks (list), prose_markdown. Avoid extra keys."
    )
    if not payload.include_hooks:
        prompt += " The 'hooks' array should be empty."

    if use_local(engine):
        text = await local_text_generate(prompt)
    else:
        resp = await asyncio.to_thread(model.generate_content, prompt)
        text = resp.text.strip()
    # Some responses may include code fences; strip them.
    if text.startswith("```"):
        text = text.strip("`")
        # after stripping backticks, remove potential json\n prefix/suffix
        text = text.replace("json\n","").replace("\njson","")

    import json
    try:
        obj = json.loads(text)
    except Exception as e:
        raise HTTPException(502, f"LLM returned non-JSON: {e}")

    # Validate and coerce via Pydantic
    try:
        result = BackstoryResult(**obj)
    except Exception as e:
        raise HTTPException(502, f"Backstory schema validation failed: {e}")

    return result

# ---- Magic Items ----
MI_GUIDE = (
    "You are a D&D 5e SRD-friendly designer. Create balanced, flavorful magic items. "
    "Follow DMG-style format. Avoid copyrighted setting names."
)

@app.post("/api/items/generate", response_model=MagicItem)
async def items_generate(payload: MagicItemInput, engine: str | None = Query(default=None)):
    logger.debug("items: generate request name=%s rarity=%s type=%s", payload.name, payload.rarity, payload.item_type)
    model = None
    if not use_local(engine):
        if not GOOGLE_API_KEY:
            raise HTTPException(400, "Missing GOOGLE_API_KEY in environment.")
        model = genai.GenerativeModel(GEMINI_MODEL_TEXT, system_instruction=MI_GUIDE)
    rarity = (payload.rarity or "Uncommon").title()
    name = payload.name or "Unnamed Relic"
    itype = payload.item_type or "Wondrous item"
    attune = "requires Attunement" if payload.requires_attunement else "does not require Attunement"
    long_prompt = (
        "Using the following inputs, design a single magic item and return JSON ONLY with keys: "
        "name, item_type, rarity, requires_attunement, description, properties (array of strings), charges (optional int), bonus (optional int), damage (optional string).\n"
        f"Inputs: name={name}; type={itype}; rarity={rarity}; attunement={attune}.\n"
        "Guidelines: Keep power consistent with rarity. If properties grant spells, align with 'Magic Item Power by Rarity'.\n"
        + (payload.prompt or "")
    )
    try:
        if use_local(engine):
            text = await local_text_generate(long_prompt)
        else:
            resp = await asyncio.to_thread(model.generate_content, long_prompt)
            text = resp.text.strip()
        if text.startswith("```"):
            text = text.strip("`").replace("json\n","").replace("\njson","")
        import json
        data = json.loads(text)
        item = MagicItem(**data)
        return item
    except Exception as e:
        raise HTTPException(502, f"item generation failed: {e}")

@app.post("/api/items/save")
async def items_save(payload: MagicItemExport):
    logger.debug("items: save %s", payload.item.name)
    con = db()
    cur = con.cursor()
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    cur.execute(
        "INSERT INTO item_library (name, created_at, item_json, prompt) VALUES (?, ?, ?, ?)",
        (payload.item.name, created_at, payload.item.model_dump_json(), None)
    )
    con.commit(); new_id = cur.lastrowid; con.close()
    return {"id": new_id, "name": payload.item.name, "created_at": created_at}

@app.get("/api/items/list")
async def items_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    logger.debug("items: list limit=%s page=%s search=%s sort=%s", limit, page, search, sort)
    con = db()
    q_base = "FROM item_library"
    params: list[object] = []
    if search:
        q_base += " WHERE name LIKE ?"
        params.append(f"%{search}%")
    total = con.execute(f"SELECT COUNT(*) {q_base}", params).fetchone()[0]
    sort_map = {
        "name_asc": "name ASC",
        "name_desc": "name DESC",
        "created_asc": "created_at ASC",
        "created_desc": "created_at DESC",
    }
    order_sql = sort_map.get(sort, "created_at DESC")
    offset = max(0, (page-1) * limit)
    rows = con.execute(
        f"SELECT id, name, created_at {q_base} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        (*params, limit, offset)
    ).fetchall()
    con.close()
    return {"items": [dict(r) for r in rows], "total": total}

@app.get("/api/items/get/{item_id}")
async def items_get(item_id: int):
    logger.debug("items: get id=%s", item_id)
    con = db(); row = con.execute("SELECT id, name, created_at, item_json FROM item_library WHERE id = ?", (item_id,)).fetchone(); con.close()
    if not row: raise HTTPException(404, "Not found")
    import json
    item = json.loads(row["item_json"])
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "item": item}

@app.delete("/api/items/delete/{item_id}")
async def items_delete(item_id: int):
    logger.debug("items: delete id=%s", item_id)
    con = db(); cur = con.cursor(); cur.execute("DELETE FROM item_library WHERE id = ?", (item_id,)); con.commit(); ok = cur.rowcount; con.close()
    if not ok: raise HTTPException(404, "Not found")
    return {"ok": True}

def _extract_image_b64(resp) -> str:
    """Try to extract inline PNG base64 from a Gemini SDK response in a robust way."""
    try:
        # Preferred: candidates[0].content.parts[*].inline_data.data
        cands = getattr(resp, "candidates", []) or []
        for c in cands:
            content = getattr(c, "content", None)
            parts = getattr(content, "parts", []) if content else []
            for p in parts:
                inline = getattr(p, "inline_data", None)
                if inline and getattr(inline, "mime_type", "") in ("image/png", "image/jpeg", "image/webp"):
                    data = getattr(inline, "data", None)
                    if data:
                        return data
        # Fallback to raw result structure
        raw = getattr(resp, "_result", None)
        if raw:
            cands = getattr(raw, "candidates", []) or []
            for c in cands:
                content = getattr(c, "content", None)
                parts = getattr(content, "parts", []) if content else []
                for p in parts:
                    inline = getattr(p, "inline_data", None)
                    if inline and inline.get("mime_type"):
                        data = inline.get("data")
                        if data:
                            return data
    except Exception:
        pass
    raise ValueError("No inline image data found in model response")

@app.post("/api/portrait")
async def generate_portrait(payload: ExportInput, engine: str | None = Query(default=None)):
    logging.info("Generating portrait image...")
    if not use_local(engine):
        if not GOOGLE_API_KEY:
            raise HTTPException(400, "Missing GOOGLE_API_KEY in environment.")
        if genai_new is None:
            raise HTTPException(500, "google-genai not installed. Please install google-genai >= 0.3.0")
    # build a concise prompt from draft + backstory
    try:
        logging.info("Constructing portrait prompt...")
        d = payload.draft
        name = d.name or "Unnamed Adventurer"
        abilities = d.abilities
        bs_text = payload.backstory.prose_markdown[:1200] if payload.backstory else ""
        prompt = (
            f"Create a detailed fantasy portrait of a D&D 5e character.\n"
            f"Name: {name}. Race: {d.race}. Class: {d.cls}. Background: {d.background}. Level: {d.level}.\n"
            f"Key abilities: STR {abilities.STR}, DEX {abilities.DEX}, CON {abilities.CON}, INT {abilities.INT}, WIS {abilities.WIS}, CHA {abilities.CHA}.\n"
        )
    except Exception as e:
        raise HTTPException(400, f"portrait prompt construction failed: {e}")
    try:
        if use_local(engine):
            logging.info("Using local image generation...")
            image_bytes = await local_image_generate(prompt)
        else:
            logging.info("Using Gemini image generation...")
            client = genai_new.Client(api_key=GOOGLE_API_KEY)
            model_name = GEMINI_MODEL_IMAGE
            if model_name in ("gemini-flash-2.5", "gemini-2.5-flash"):
                model_name = "gemini-2.5-flash-image"
            resp = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=[prompt],
            )
            logging.info("Extracting image data from response...")
            image_bytes: bytes | None = None
            for part in getattr(resp, "parts", []) or []:
                if getattr(part, "inline_data", None) is not None:
                    img = part.as_image(); buf = BytesIO(); img.save(buf, format="PNG"); image_bytes = buf.getvalue(); break
            if not image_bytes:
                raise ValueError("No image returned by model")
    except Exception as e:
        logger.exception("Image generation failed")
        raise HTTPException(502, f"image generation failed: {e}")
    # Basic sanity log
    try:
        logger.info("portrait bytes: %d bytes%s", len(image_bytes),
                    " (png)" if image_bytes.startswith(b"\x89PNG\r\n\x1a\n") else "")
    except Exception:
        pass
    filename = f"{(d.name or d.race + ' ' + d.cls).replace(' ','_')}_portrait.png"
    # Return as a normal binary Response with explicit length
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(image_bytes)),
            "Cache-Control": "no-store",
        },
    )

@app.post("/api/export/json")
async def export_json(payload: ExportInput):
    logger.debug("export_json: name=%s class=%s race=%s", payload.draft.name, payload.draft.cls, payload.draft.race)
    data = {
        "draft": payload.draft.model_dump(),
        "backstory": payload.backstory.model_dump() if payload.backstory else None,
        "progression": payload.progression.model_dump() if getattr(payload, 'progression', None) else None,
    }
    filename = f"{payload.draft.race}_{payload.draft.cls}_lvl{payload.draft.level}.json".replace(" ", "_")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return JSONResponse(content=data, headers=headers)

@app.post("/api/export/md")
async def export_md(payload: ExportInput):
    logger.debug("export_md: name=%s class=%s race=%s", payload.draft.name, payload.draft.cls, payload.draft.race)
    # Base markdown for draft and optional backstory
    parts: list[str] = [markdown_from_draft(payload.draft, payload.backstory)]
    # Append progression section if provided
    plan = getattr(payload, 'progression', None)
    if plan is not None:
        try:
            # Render a section without an extra top-level title
            lines: list[str] = []
            title = plan.name or "Progression Plan"
            lines.append("")
            lines.append("## Progression Plan")
            lines.append("")
            lines.append(f"- Title: {title}")
            lines.append(f"- Class: {payload.draft.cls}")
            lines.append(f"- Target Level: {plan.target_level}")
            lines.append("")
            lines.append("### Level-by-Level")
            for p in plan.picks:
                hdr = f"#### Level {p.level}"
                if p.subclass:
                    hdr += f" — Subclass: {p.subclass}"
                lines.append(hdr)
                feats = ", ".join(p.features) if (p.features or []) else "—"
                lines.append(f"- Features: {feats}")
                if p.asi:
                    lines.append(f"- ASI/Feat: {p.asi}")
                if p.spells_known:
                    lines.append(f"- Spells Known: {', '.join(p.spells_known)}")
                if p.prepared:
                    lines.append(f"- Prepared: {', '.join(p.prepared)}")
                if p.hp_gain is not None:
                    lines.append(f"- HP Gain: {p.hp_gain}")
                if p.notes:
                    lines.append("")
                    lines.append(p.notes)
                lines.append("")
            if plan.notes_markdown:
                lines.append("### Notes")
                lines.append(plan.notes_markdown)
            parts.append("\n".join(lines))
        except Exception as e:
            logger.warning("progression md render failed: %s", e)
    md = "\n\n".join(parts)
    filename = f"{payload.draft.race}_{payload.draft.cls}_lvl{payload.draft.level}.md".replace(" ", "_")
    return PlainTextResponse(content=md, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

from .schemas import ExportInput  # already imported earlier

@app.post("/api/library/save")
async def library_save(payload: SaveInput):
    logger.debug("library: save name=%s class=%s race=%s", payload.draft.name, payload.draft.cls, payload.draft.race)
    # default a name if not provided in draft
    name = payload.draft.name or f"{payload.draft.race} {payload.draft.cls} L{payload.draft.level}"
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    con = db()
    cur = con.cursor()
    portrait_blob = None
    if payload.portrait_base64:
        try:
            portrait_blob = base64.b64decode(payload.portrait_base64)
        except Exception:
            portrait_blob = None
    # progression serialized (if provided)
    progression_json = None
    try:
      progression_json = payload.progression.model_dump_json() if getattr(payload, 'progression', None) else None
    except Exception:
      progression_json = None

    cur.execute(
        "INSERT INTO library (name, created_at, draft_json, backstory_json, portrait_png, progression_json) VALUES (?, ?, ?, ?, ?, ?)",
        (name, created_at, payload.draft.model_dump_json(), payload.backstory.model_dump_json() if payload.backstory else None, portrait_blob, progression_json)
    )
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return {"id": new_id, "name": name, "created_at": created_at}

@app.post("/api/items/export/pdf")
async def items_export_pdf(payload: MagicItemExport):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
    except Exception as e:
        raise HTTPException(500, f"PDF generation libs missing: {e}")

    item = payload.item
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    def draw_footer():
        try:
            now = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')
        except Exception:
            now = ''
        c.setFont("Helvetica", 9)
        c.drawRightString(width - 0.75*inch, 0.45*inch, f"Page {c.getPageNumber()}  •  Generated {now}")

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(0.75*inch, height - 0.9*inch, f"{item.name} — {item.item_type} · {item.rarity}")
    y = height - 1.25*inch
    c.setFont("Helvetica", 11)
    c.drawString(0.75*inch, y, f"Attunement: {'Required' if item.requires_attunement else 'No'}")
    y -= 16

    from textwrap import wrap
    for line in wrap(item.description or "", 98):
        c.drawString(0.75*inch, y, line); y -= 14
        if y < 1*inch: draw_footer(); c.showPage(); y = height - 0.9*inch

    if item.properties:
        y -= 8
        c.setFont("Helvetica-Bold", 12); c.drawString(0.75*inch, y, "Properties"); y -= 16; c.setFont("Helvetica", 11)
        for p in item.properties:
            for line in wrap(p, 95):
                c.drawString(0.9*inch, y, f"• {line}" if line == p else f"  {line}"); y -= 14
                if y < 1*inch: draw_footer(); c.showPage(); y = height - 0.9*inch

    draw_footer(); c.showPage(); c.save(); buffer.seek(0)
    filename = f"{item.name.replace(' ', '_')}_Item.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'})

# ---- Spells ----
SPELL_GUIDE = (
    "You are a D&D 5e SRD-friendly designer. Create balanced, flavorful spells. "
    "Use style similar to the Player's Handbook. Follow guidance: balance, identity, duration/range/area tradeoffs, utility; and the Spell Damage table guidelines." 
)

@app.post("/api/spells/generate", response_model=Spell)
async def spells_generate(payload: SpellInput, engine: str | None = Query(default=None)):
    logger.debug("spells: generate request name=%s level=%s school=%s classes=%s target=%s intent=%s", payload.name, payload.level, payload.school, payload.classes, payload.target, payload.intent)
    model = None
    if not use_local(engine):
        if not GOOGLE_API_KEY:
            raise HTTPException(400, "Missing GOOGLE_API_KEY in environment.")
        model = genai.GenerativeModel(GEMINI_MODEL_TEXT, system_instruction=SPELL_GUIDE)
    name = payload.name or "Unnamed Spell"
    level = 0 if payload.level is None else max(0, min(9, payload.level))
    school = payload.school or "Evocation"
    classes = ", ".join(payload.classes or ["Wizard"])
    target = payload.target or "one"
    intent = payload.intent or "damage"
    rules = (
        "Design a single spell and return JSON ONLY with keys: "
        "name, level (0-9), school, classes (array of strings), casting_time, range, duration, components, concentration (bool), ritual (bool), description, damage (optional), save (optional).\n"
        f"Inputs: name={name}; level={level}; school={school}; classes={classes}; target={target}; intent={intent}.\n"
        "Use the Spell Damage table (approximate dice by level, half on save). If healing, use same table as HP restoration. Cantrips should be weak and scale normally.\n"
        + (payload.prompt or "")
    )
    try:
        if use_local(engine):
            text = await local_text_generate(rules)
        else:
            resp = await asyncio.to_thread(model.generate_content, rules)
            text = resp.text.strip()
        if text.startswith("```"):
            text = text.strip("`").replace("json\n","").replace("\njson","")
        import json
        data = json.loads(text)

        # Normalize common LLM variations to avoid 502s
        def _to_bool(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(v)
            if isinstance(v, str):
                return v.strip().lower() in {"true","yes","y","1","required","requires","require"}
            return False

        norm: dict = {}
        norm["name"] = str(data.get("name") or name)
        try:
            lvl_raw = data.get("level", level)
            lvl = int(lvl_raw)
        except Exception:
            lvl = level
        norm["level"] = max(0, min(9, lvl))
        norm["school"] = str(data.get("school") or school)

        cls_raw = data.get("classes")
        if isinstance(cls_raw, str):
            cls_list = [c.strip() for c in cls_raw.split(",") if c.strip()]
        elif isinstance(cls_raw, list):
            cls_list = [str(c).strip() for c in cls_raw if str(c).strip()]
        else:
            cls_list = [c.strip() for c in classes.split(",") if c.strip()]
        norm["classes"] = cls_list

        norm["casting_time"] = str(data.get("casting_time") or "1 action")
        norm["range"] = str(data.get("range") or ("Self" if target == "self" else "60 feet"))
        norm["duration"] = str(data.get("duration") or "Instantaneous")

        comps = data.get("components")
        if isinstance(comps, list):
            comps_s = ", ".join([str(x) for x in comps])
        elif isinstance(comps, dict):
            v = comps.get("verbal") or comps.get("v") or comps.get("V")
            s = comps.get("somatic") or comps.get("s") or comps.get("S")
            m = comps.get("material") or comps.get("m") or comps.get("M")
            parts = []
            if v: parts.append("V")
            if s: parts.append("S")
            if m: parts.append("M" + (f" ({m})" if isinstance(m, str) and m else ""))
            comps_s = ", ".join(parts) if parts else "V, S"
        else:
            comps_s = str(comps or "V, S")
        norm["components"] = comps_s

        norm["concentration"] = _to_bool(data.get("concentration", False))
        norm["ritual"] = _to_bool(data.get("ritual", False))
        norm["description"] = str(data.get("description") or "")
        if not norm["description"].strip():
            norm["description"] = "No description provided."
        dmg = data.get("damage")
        norm["damage"] = None if dmg in ("", None) else str(dmg)
        sv = data.get("save")
        norm["save"] = None if sv in ("", None) else str(sv)

        logger.debug("spells: normalized payload=%s", {k: (v if k != 'description' else (v[:60]+'...')) for k,v in norm.items()})

        spell = Spell(**norm)
        return spell
    except Exception as e:
        logger.exception("spells: generation failed")
        raise HTTPException(502, f"spell generation failed: {e}")

@app.post("/api/spells/save")
async def spells_save(payload: SpellExport):
    logger.debug("spells: save %s", payload.spell.name)
    con = db(); cur = con.cursor(); created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    cur.execute("INSERT INTO spell_library (name, created_at, spell_json, prompt) VALUES (?, ?, ?, ?)", (payload.spell.name, created_at, payload.spell.model_dump_json(), None))
    con.commit(); new_id = cur.lastrowid; con.close(); return {"id": new_id, "name": payload.spell.name, "created_at": created_at}

@app.get("/api/spells/list")
async def spells_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    logger.debug("spells: list limit=%s page=%s search=%s sort=%s", limit, page, search, sort)
    con = db(); q_base = "FROM spell_library"; params: list[object] = []
    if search: q_base += " WHERE name LIKE ?"; params.append(f"%{search}%")
    total = con.execute(f"SELECT COUNT(*) {q_base}", params).fetchone()[0]
    sort_map = {"name_asc":"name ASC","name_desc":"name DESC","created_asc":"created_at ASC","created_desc":"created_at DESC"}
    order_sql = sort_map.get(sort, "created_at DESC"); offset = max(0, (page-1)*limit)
    rows = con.execute(f"SELECT id,name,created_at {q_base} ORDER BY {order_sql} LIMIT ? OFFSET ?", (*params, limit, offset)).fetchall(); con.close()
    return {"items":[dict(r) for r in rows], "total": total}

@app.get("/api/spells/get/{spell_id}")
async def spells_get(spell_id: int):
    logger.debug("spells: get id=%s", spell_id)
    con = db(); row = con.execute("SELECT id,name,created_at,spell_json FROM spell_library WHERE id=?", (spell_id,)).fetchone(); con.close()
    if not row: raise HTTPException(404, "Not found")
    import json
    spell = json.loads(row["spell_json"])
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "spell": spell}

@app.delete("/api/spells/delete/{spell_id}")
async def spells_delete(spell_id: int):
    logger.debug("spells: delete id=%s", spell_id)
    con = db(); cur = con.cursor(); cur.execute("DELETE FROM spell_library WHERE id=?", (spell_id,)); con.commit(); ok = cur.rowcount; con.close();
    if not ok: raise HTTPException(404, "Not found"); return {"ok": True}

# ---- Progression Planner ----

# Subclass unlock levels per 5e 2014 SRD core classes
SUBCLASS_LEVELS: dict[str, int] = {
    "barbarian": 3, "bard": 3, "cleric": 1, "druid": 2, "fighter": 3,
    "monk": 3, "paladin": 3, "ranger": 3, "rogue": 3, "sorcerer": 1,
    "warlock": 1, "wizard": 2,
}

# ASI levels per class (defaults; fighter/rogue have extras)
ASI_LEVELS_DEFAULT = [4, 8, 12, 16, 19]
ASI_LEVELS_OVERRIDES: dict[str, list[int]] = {
    "fighter": [4, 6, 8, 12, 14, 16, 19],
    "rogue": [4, 8, 10, 12, 16, 19],
}

@app.post("/api/progression/generate", response_model=ProgressionPlan)
async def progression_generate(payload: ProgressionInput):
    ci = payload.class_index.lower().strip()
    if not ci:
        raise HTTPException(400, "class_index required")
    target = max(1, min(20, payload.target_level))
    d = payload.draft

    # Hit points: level 1 = hit_die + CON_mod; later = avg (half+1) + CON_mod
    avg_hp = (d.hit_die // 2) + 1
    picks: list[LevelPick] = []

    # Determine subclass list and name choice
    try:
        cls_data = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/classes/{ci}")
        subclasses = [x.get("name") for x in cls_data.get("subclasses", []) or []]
    except Exception:
        subclasses = []
    chosen_subclass = subclasses[0] if subclasses else None
    subclass_level = SUBCLASS_LEVELS.get(ci, 3)

    # ASI schedule
    asi_levels = ASI_LEVELS_OVERRIDES.get(ci, ASI_LEVELS_DEFAULT)

    for lvl in range(1, target + 1):
        # Level features from SRD
        try:
            lvl_data = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/classes/{ci}/levels/{lvl}")
            feat_names = [f.get("name") for f in lvl_data.get("features", []) or []]
        except Exception:
            feat_names = []

        # hp gain this level
        if lvl == 1:
            hp_gain = d.hit_die + d.abilities.CON_mod
        else:
            hp_gain = avg_hp + d.abilities.CON_mod

        # subclass applied?
        sc = chosen_subclass if (chosen_subclass and lvl == subclass_level) else None

        # ASI placeholder
        asi = "+2 to primary ability" if lvl in asi_levels else None

        notes = None
        if sc:
            notes = f"Chose subclass: {sc}."
        pick = LevelPick(level=lvl, hp_gain=hp_gain, features=feat_names, subclass=sc, asi=asi, spells_known=[], prepared=[], notes=notes)
        picks.append(pick)

    plan = ProgressionPlan(
        name=d.name or f"{d.race} {d.cls} progression",
        class_index=ci,
        target_level=target,
        picks=picks,
        notes_markdown=(
            "This is an initial, rules-aware skeleton plan.\n\n"
            "• Features pulled from SRD per level.\n\n"
            "• Subclass chosen automatically if available; adjust as desired.\n\n"
            "• ASI/feat choices are placeholders.\n"
        ),
    )
    return plan

@app.post("/api/progression/export/md")
async def progression_export_md(payload: ProgressionExport):
    md = markdown_from_progression(payload.plan)
    fname = (payload.plan.name or "progression").replace(" ", "_") + ".md"
    return PlainTextResponse(content=md, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="{fname}"'})

@app.post("/api/progression/export/pdf")
async def progression_export_pdf(payload: ProgressionExport):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
    except Exception as e:
        raise HTTPException(500, f"PDF generation libs missing: {e}")

    plan = payload.plan
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    margin = 0.75*inch
    content_width = width - 2*margin

    def draw_footer():
        try:
            now = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')
        except Exception:
            now = ''
        c.setFont("Helvetica", 9)
        c.drawRightString(width - margin, margin * 0.6, f"Page {c.getPageNumber()}  •  Generated {now}")

    def wrap_text(text: str, max_width: float, font: str = "Helvetica", size: int = 10):
        c.setFont(font, size)
        words = text.split()
        lines: list[str] = []
        line = ""
        for w in words:
            test = (line + (" " if line else "") + w)
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines

    def draw_block(x: float, y_top: float, text_lines: list[str], width_avail: float, leading: float = 14, font: str = "Helvetica", size: int = 10):
        c.setFont(font, size)
        y = y_top
        for raw in text_lines:
            for ln in wrap_text(raw, width_avail, font, size):
                if y <= margin:
                    draw_footer(); c.showPage()
                    draw_title(title)
                    y = height - margin - 0.25*inch
                    c.setFont(font, size)
                c.drawString(x, y, ln)
                y -= leading
        return y

    def draw_title(text: str):
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, height - margin + 0.1*inch, text)

    title = (plan.name or "Progression Plan")
    draw_title(title)
    y = height - margin - 0.35*inch

    # Summary
    summary = [
        f"Class: {plan.class_index.title()}",
        f"Target Level: {plan.target_level}",
    ]
    y = draw_block(margin, y, summary, content_width, leading=13)

    # Level-by-level sections
    for p in plan.picks:
        y -= 8
        c.setFont("Helvetica-Bold", 12)
        hdr = f"Level {p.level}"
        if p.subclass:
            hdr += f" — Subclass: {p.subclass}"
        if y <= margin:
            draw_footer(); c.showPage(); draw_title(title); y = height - margin - 0.35*inch
        c.drawString(margin, y, hdr); y -= 14
        body: list[str] = []
        body.append(f"Features: {', '.join(p.features) if p.features else '—'}")
        if p.asi:
            body.append(f"ASI/Feat: {p.asi}")
        if p.spells_known:
            body.append(f"Spells Known: {', '.join(p.spells_known)}")
        if p.prepared:
            body.append(f"Prepared: {', '.join(p.prepared)}")
        if p.hp_gain is not None:
            body.append(f"HP Gain: {p.hp_gain}")
        if p.notes:
            body.append(p.notes)
        y = draw_block(margin, y, body, content_width, leading=13)

    if plan.notes_markdown:
        draw_footer(); c.showPage(); draw_title(title)
        y = height - margin - 0.35*inch
        c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Notes"); y -= 14
        y = draw_block(margin, y, [plan.notes_markdown], content_width, leading=13)

    draw_footer(); c.showPage(); c.save(); buffer.seek(0)
    filename = (plan.name or "progression").replace(' ','_') + ".pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
@app.post("/api/progression/save")
async def progression_save(payload: ProgressionExport):
    name = payload.plan.name or "Progression Plan"
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    con = db(); cur = con.cursor()
    cur.execute(
        "INSERT INTO progression_library (name, created_at, plan_json, prompt) VALUES (?, ?, ?, ?)",
        (name, created_at, payload.plan.model_dump_json(), None),
    )
    con.commit(); new_id = cur.lastrowid; con.close()
    return {"id": new_id, "name": name, "created_at": created_at}

@app.get("/api/progression/list")
async def progression_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    con = db(); q_base = "FROM progression_library"; params: list[object] = []
    if search: q_base += " WHERE name LIKE ?"; params.append(f"%{search}%")
    total = con.execute(f"SELECT COUNT(*) {q_base}", params).fetchone()[0]
    sort_map = {"name_asc":"name ASC","name_desc":"name DESC","created_asc":"created_at ASC","created_desc":"created_at DESC"}
    order_sql = sort_map.get(sort, "created_at DESC"); offset = max(0, (page-1)*limit)
    rows = con.execute(f"SELECT id,name,created_at {q_base} ORDER BY {order_sql} LIMIT ? OFFSET ?", (*params, limit, offset)).fetchall(); con.close()
    return {"items":[dict(r) for r in rows], "total": total}

@app.get("/api/progression/get/{plan_id}")
async def progression_get(plan_id: int):
    con = db(); row = con.execute("SELECT id,name,created_at,plan_json FROM progression_library WHERE id=?", (plan_id,)).fetchone(); con.close()
    if not row: raise HTTPException(404, "Not found")
    import json
    plan = json.loads(row["plan_json"])  # already matches ProgressionPlan shape
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "plan": plan}

@app.delete("/api/progression/delete/{plan_id}")
async def progression_delete(plan_id: int):
    con = db(); cur = con.cursor(); cur.execute("DELETE FROM progression_library WHERE id=?", (plan_id,)); con.commit(); ok = cur.rowcount; con.close()
    if not ok: raise HTTPException(404, "Not found"); return {"ok": True}

@app.get("/api/library/list")
async def library_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    logger.debug("library: list limit=%s page=%s search=%s sort=%s", limit, page, search, sort)
    con = db()
    q_base = "FROM library"
    params: list[object] = []
    if search:
        q_base += " WHERE name LIKE ?"
        params.append(f"%{search}%")
    total = con.execute(f"SELECT COUNT(*) {q_base}", params).fetchone()[0]
    sort_map = {
        "name_asc": "name ASC",
        "name_desc": "name DESC",
        "created_asc": "created_at ASC",
        "created_desc": "created_at DESC",
    }
    order_sql = sort_map.get(sort, "created_at DESC")
    offset = max(0, (page-1)*limit)
    rows = con.execute(
        f"SELECT id, name, created_at {q_base} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        (*params, limit, offset)
    ).fetchall()
    con.close()
    return {"items": [dict(r) for r in rows], "total": total}

@app.get("/api/library/get/{item_id}")
async def library_get(item_id: int):
    logger.debug("library: get id=%s", item_id)
    con = db()
    row = con.execute("SELECT id, name, created_at, draft_json, backstory_json, portrait_png, progression_json FROM library WHERE id = ?", (item_id,)).fetchone()
    con.close()
    if not row:
        raise HTTPException(404, "Not found")
    import json
    draft = json.loads(row["draft_json"])
    backstory = json.loads(row["backstory_json"]) if row["backstory_json"] else None
    try:
        progression_raw = row["progression_json"] if "progression_json" in row.keys() else None
    except Exception:
        progression_raw = None
    progression = json.loads(progression_raw) if progression_raw else None
    portrait_b64 = None
    if row["portrait_png"] is not None:
        try:
            portrait_b64 = base64.b64encode(row["portrait_png"]).decode("ascii")
        except Exception:
            portrait_b64 = None
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "draft": draft, "backstory": backstory, "progression": progression, "portrait_base64": portrait_b64}

@app.post("/api/export/pdf")
async def export_pdf(payload: ExportPDFInput):
    logger.debug("export_pdf: name=%s class=%s race=%s portrait=%s", payload.draft.name, payload.draft.cls, payload.draft.race, bool(payload.portrait_base64))
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
    except Exception as e:
        raise HTTPException(500, f"PDF generation libs missing: {e}")

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- helpers ---
    def draw_title(page_title: str):
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, height - margin + 0.1*inch, page_title)

    def draw_footer():
        try:
            now = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')
        except Exception:
            now = ''
        c.setFont("Helvetica", 9)
        page_text = f"Page {c.getPageNumber()}  •  Generated {now}"
        c.drawRightString(width - margin, margin * 0.6, page_text)

    def wrap_text(text: str, max_width: float, font: str = "Helvetica", size: int = 10):
        c.setFont(font, size)
        words = text.split()
        lines: list[str] = []
        line = ""
        for w in words:
            test = (line + (" " if line else "") + w)
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                # very long single word fallback
                if c.stringWidth(w, font, size) > max_width:
                    # hard chop
                    accum = ""
                    for ch in w:
                        if c.stringWidth(accum + ch, font, size) <= max_width:
                            accum += ch
                        else:
                            lines.append(accum)
                            accum = ch
                    line = accum
                else:
                    line = w
        if line:
            lines.append(line)
        return lines

    def draw_block(x: float, y_top: float, text_lines: list[str], width_avail: float, leading: float = 14, font: str = "Helvetica", size: int = 10):
        c.setFont(font, size)
        y = y_top
        for raw in text_lines:
            for ln in wrap_text(raw, width_avail, font, size):
                if y <= margin:
                    draw_footer(); c.showPage()
                    draw_title(title)
                    y = height - margin - 0.25*inch
                    c.setFont(font, size)
                c.drawString(x, y, ln)
                y -= leading
        return y

    # --- layout ---
    margin = 0.75*inch
    gutter = 0.4*inch
    content_width = width - 2*margin

    # Title
    title = (payload.draft.name or f"{payload.draft.race} {payload.draft.cls}") + f" — Level {payload.draft.level}"
    draw_title(title)

    # Top starting y
    y = height - margin - 0.35*inch

    # Portrait (if any) on the left column
    left_x = margin
    info_x = margin
    info_width = content_width
    img_h = 0
    if payload.portrait_base64:
        try:
            img_bytes = base64.b64decode(payload.portrait_base64)
            img = ImageReader(BytesIO(img_bytes))
            img_w = 2.3*inch
            img_h = 2.9*inch
            c.drawImage(img, left_x, y - img_h + 0.15*inch, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
            info_x = left_x + img_w + gutter
            info_width = content_width - (img_w + gutter)
        except Exception:
            pass

    # Section helpers
    def draw_section(x: float, y_top: float, title_text: str, body_lines: list[str], width_avail: float) -> float:
        # title
        c.setFont("Helvetica-Bold", 12)
        y_local = y_top
        c.drawString(x, y_local, title_text)
        y_local -= 14
        # body
        return draw_block(x, y_local, body_lines, width_avail, leading=13, font="Helvetica", size=10)

    # Stats block text
    d = payload.draft
    a = d.abilities
    stats_lines = [
        f"Background: {d.background}",
        f"Proficiency Bonus: +{d.proficiency_bonus}",
        f"Hit Die: d{d.hit_die} · Speed: {d.speed} ft · AC (no armor): {d.armor_class_basic}",
        f"Abilities: STR {a.STR} ({a.STR_mod:+}), DEX {a.DEX} ({a.DEX_mod:+}), CON {a.CON} ({a.CON_mod:+}), INT {a.INT} ({a.INT_mod:+}), WIS {a.WIS} ({a.WIS_mod:+}), CHA {a.CHA} ({a.CHA_mod:+})",
    ]
    y_after = draw_section(info_x, y - 0.1*inch, "Stats", stats_lines, info_width)

    if d.saving_throws:
        y_after = draw_section(info_x, y_after - 6, "Saving Throws", [", ".join(d.saving_throws)], info_width)
    if d.languages:
        y_after = draw_section(info_x, y_after - 6, "Languages", [", ".join(d.languages)], info_width)
    if d.proficiencies:
        y_after = draw_section(info_x, y_after - 6, "Proficiencies", [", ".join(p.name for p in d.proficiencies)], info_width)
    if d.equipment:
        y_after = draw_section(info_x, y_after - 6, "Equipment", [", ".join(d.equipment)], info_width)
    if d.features:
        y_after = draw_section(info_x, y_after - 6, f"Features @ Level {d.level}", [", ".join(d.features)], info_width)

    # ensure we leave space under portrait area too
    y = min(y_after, y - img_h - 0.2*inch)

    # Backstory
    if payload.backstory:
        draw_footer(); c.showPage()
        draw_title("Backstory")
        c.setFont("Helvetica", 11)
        prose = payload.backstory.prose_markdown
        y2 = height - margin - 0.35*inch
        para_leading = 15
        for paragraph in [p for p in prose.split("\n\n") if p.strip()]:
            for ln in wrap_text(paragraph, content_width, "Helvetica", 11):
                if y2 <= margin:
                    draw_footer(); c.showPage(); draw_title("Backstory"); y2 = height - margin - 0.35*inch; c.setFont("Helvetica", 11)
                c.drawString(margin, y2, ln)
                y2 -= para_leading

    # Progression Plan page (optional)
    if getattr(payload, 'progression', None):
        try:
            plan = payload.progression
            draw_footer(); c.showPage()
            draw_title("Progression Plan")
            y3 = height - margin - 0.35*inch
            # table header
            c.setFont("Helvetica-Bold", 11)
            cols = [
                ("Level", 0.9*inch),
                ("Features", 3.3*inch),
                ("Subclass", 1.4*inch),
                ("ASI/Feat", 1.2*inch),
                ("HP", 0.7*inch),
            ]
            x = margin
            for title_text, w in cols:
                c.drawString(x, y3, title_text)
                x += w
            y3 -= 14
            c.setFont("Helvetica", 10)
            # rows
            for p in plan.picks:
                if y3 <= margin:
                    draw_footer(); c.showPage(); draw_title("Progression Plan"); y3 = height - margin - 0.35*inch; c.setFont("Helvetica", 10)
                    x = margin
                    c.setFont("Helvetica-Bold", 11)
                    for title_text, w in cols:
                        c.drawString(x, y3, title_text); x += w
                    y3 -= 14; c.setFont("Helvetica", 10)
                x = margin
                col_vals = [
                    str(p.level),
                    ", ".join(p.features) if (p.features or []) else "—",
                    (p.subclass or "—"),
                    (p.asi or "—"),
                    (str(p.hp_gain) if (p.hp_gain is not None) else "—"),
                ]
                # simple draw; wrap features within its column
                widths = [w for _, w in cols]
                # compute wrapped lines for each col (features may wrap)
                lines_per_col: list[list[str]] = []
                for (val, w) in zip(col_vals, widths):
                    lines_per_col.append(wrap_text(val, w))
                row_height = max(len(col) for col in lines_per_col) * 13
                # draw row lines
                max_lines = max(len(col) for col in lines_per_col)
                for line_idx in range(max_lines):
                    x = margin
                    for col_idx, w in enumerate(widths):
                        text_line = lines_per_col[col_idx][line_idx] if line_idx < len(lines_per_col[col_idx]) else ""
                        c.drawString(x, y3, text_line)
                        x += w
                    y3 -= 13
            # optional notes
            if getattr(plan, 'notes_markdown', None):
                y3 -= 10
                c.setFont("Helvetica-Bold", 11); c.drawString(margin, y3, "Notes"); y3 -= 14; c.setFont("Helvetica", 10)
                y3 = draw_block(margin, y3, [plan.notes_markdown], content_width)
        except Exception:
            # If anything goes wrong drawing progression, still emit PDF
            pass

    draw_footer(); c.showPage(); c.save()
    buffer.seek(0)
    filename = f"{(d.name or d.race + ' ' + d.cls).replace(' ','_')}_Sheet.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@app.delete("/api/library/delete/{item_id}")
async def library_delete(item_id: int):
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM library WHERE id = ?", (item_id,))
    con.commit()
    deleted = cur.rowcount
    con.close()
    if not deleted:
        raise HTTPException(404, "Not found")
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
# ---- Magic Items ----
