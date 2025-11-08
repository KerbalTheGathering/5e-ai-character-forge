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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
from requests_cache import CachedSession

from typing import Dict, List
from .schemas import (
    AbilitySet, GenerateInput, CharacterDraft, AbilityBlock, Proficiency,
    BackstoryInput, BackstoryResult, ExportInput, SaveInput, ExportPDFInput,
    MagicItemInput, MagicItem, MagicItemExport
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

load_dotenv()

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
      portrait_png BLOB
    )
    """)
    # ensure portrait column exists for older DBs
    try:
        con.execute("ALTER TABLE library ADD COLUMN portrait_png BLOB")
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
    con.close()

init_db()


PORT = int(os.getenv("PORT_API", "8000"))
RULES_BASE = os.getenv("RULES_BASE_URL", "https://www.dnd5eapi.co")
RULES_API_PREFIX = os.getenv("RULES_API_PREFIX", "api/2014")
RULES_API_PREFIX = os.getenv("RULES_API_PREFIX", "api/2014")
GEMINI_MODEL_TEXT = os.getenv("GEMINI_MODEL_TEXT", "gemini-2.5-pro")
GEMINI_MODEL_IMAGE = os.getenv("GEMINI_MODEL_IMAGE", "gemini-2.5-flash-image")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI(title="5e-ai-character-forge API", version="0.1.0")

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

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/api/rules/{path:path}")
async def rules_proxy(path: str):
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
    return roll_ability_set(seed)

BACKSTORY_SYS = (
 "You are an expert tabletop RPG writer. Write backstories consistent with D&D 5e SRD, "
 "avoiding copyrighted setting names. Use clear, evocative prose suitable for a character handout."
)

@app.post("/api/backstory", response_model=BackstoryResult)
async def backstory_route(payload: BackstoryInput):
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
async def items_generate(payload: MagicItemInput):
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
    con = db(); row = con.execute("SELECT id, name, created_at, item_json FROM item_library WHERE id = ?", (item_id,)).fetchone(); con.close()
    if not row: raise HTTPException(404, "Not found")
    import json
    item = json.loads(row["item_json"])
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "item": item}

@app.delete("/api/items/delete/{item_id}")
async def items_delete(item_id: int):
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
async def generate_portrait(payload: ExportInput):
    logging.info("Generating portrait image via Gemini...")
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
            f"Equipment hints: {', '.join(d.equipment[:8])}. Features: {', '.join((d.features or [])[:6])}.\n"
            f"Style: painterly, dramatic lighting, half-body portrait, fantasy, high-quality.\n"
            f"Backstory context (optional): {bs_text}"
        )
    except Exception as e:
        raise HTTPException(400, f"portrait prompt construction failed: {e}")
    try:
        logging.info("Generating portrait image...")
        client = genai_new.Client(api_key=GOOGLE_API_KEY)
        # normalize common aliases
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
                # PIL Image from SDK helper
                img = part.as_image()
                buf = BytesIO()
                img.save(buf, format="PNG")
                image_bytes = buf.getvalue()
                break
        if not image_bytes:
            raise ValueError("No image returned by model")
    except Exception as e:
        logging.error(f"Image generation failed: {e}")
        raise HTTPException(502, f"image generation failed: {e}")
    filename = f"{(d.name or d.race + ' ' + d.cls).replace(' ','_')}_portrait.png"
    return StreamingResponse(BytesIO(image_bytes), media_type="image/png", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@app.post("/api/export/json")
async def export_json(payload: ExportInput):
    data = {"draft": payload.draft.model_dump(), "backstory": payload.backstory.model_dump() if payload.backstory else None}
    filename = f"{payload.draft.race}_{payload.draft.cls}_lvl{payload.draft.level}.json".replace(" ", "_")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return JSONResponse(content=data, headers=headers)

@app.post("/api/export/md")
async def export_md(payload: ExportInput):
    md = markdown_from_draft(payload.draft, payload.backstory)
    filename = f"{payload.draft.race}_{payload.draft.cls}_lvl{payload.draft.level}.md".replace(" ", "_")
    return PlainTextResponse(content=md, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

from .schemas import ExportInput  # already imported earlier

@app.post("/api/library/save")
async def library_save(payload: SaveInput):
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
    cur.execute(
        "INSERT INTO library (name, created_at, draft_json, backstory_json, portrait_png) VALUES (?, ?, ?, ?, ?)",
        (name, created_at, payload.draft.model_dump_json(), payload.backstory.model_dump_json() if payload.backstory else None, portrait_blob)
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

@app.get("/api/library/list")
async def library_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
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
    con = db()
    row = con.execute("SELECT id, name, created_at, draft_json, backstory_json, portrait_png FROM library WHERE id = ?", (item_id,)).fetchone()
    con.close()
    if not row:
        raise HTTPException(404, "Not found")
    import json
    draft = json.loads(row["draft_json"])
    backstory = json.loads(row["backstory_json"]) if row["backstory_json"] else None
    portrait_b64 = None
    if row["portrait_png"] is not None:
        try:
            portrait_b64 = base64.b64encode(row["portrait_png"]).decode("ascii")
        except Exception:
            portrait_b64 = None
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "draft": draft, "backstory": backstory, "portrait_base64": portrait_b64}

@app.post("/api/export/pdf")
async def export_pdf(payload: ExportPDFInput):
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
