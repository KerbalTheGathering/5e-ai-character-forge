from fastapi import APIRouter, HTTPException, Query
from ..schemas import SpellInput, Spell, SpellExport
from ..ai_inference import use_local_inference, local_text_generate, google_text_generate
from ..database import create_item, get_item, list_items, delete_item, get_db_connection
from ..config import logger
import json

router = APIRouter()

SPELL_GUIDE = (
    "You are a D&D 5e SRD-friendly designer. Create balanced, flavorful spells. "
    "Use style similar to the Player's Handbook. Follow guidance: balance, identity, duration/range/area tradeoffs, utility; and the Spell Damage table guidelines." 
)

@router.post("/api/spells/generate", response_model=Spell)
async def spells_generate(payload: SpellInput, engine: str | None = Query(default=None)):
    logger.debug("spells: generate request name=%s level=%s school=%s classes=%s target=%s intent=%s", payload.name, payload.level, payload.school, payload.classes, payload.target, payload.intent)
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
        if use_local_inference(engine):
            text = await local_text_generate(rules)
        else:
            text = await google_text_generate(rules, SPELL_GUIDE)
        if text.startswith("```"):
            text = text.strip("`").replace("json\n","").replace("\njson","")
        data = json.loads(text)

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

@router.post("/api/spells/save")
async def spells_save(payload: SpellExport):
    logger.debug("spells: save %s", payload.spell.name)
    spell_data = {"name": payload.spell.name, "spell_json": payload.spell.model_dump_json(), "prompt": payload.prompt}
    result = create_item("spell_library", spell_data)
    return result

@router.get("/api/spells/list")
async def spells_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    logger.debug("spells: list limit=%s page=%s search=%s sort=%s", limit, page, search, sort)
    result = list_items("spell_library", limit, page, search, sort)
    # Enrich items with level and school from spell_json
    con = get_db_connection()
    for item in result["items"]:
        row = con.execute("SELECT spell_json FROM spell_library WHERE id = ?", (item["id"],)).fetchone()
        if row:
            try:
                spell_data = json.loads(row["spell_json"])
                item["level"] = spell_data.get("level", 0)
                item["school"] = spell_data.get("school", "")
            except Exception:
                item["level"] = 0
                item["school"] = ""
    con.close()
    return result

@router.get("/api/spells/get/{spell_id}")
async def spells_get(spell_id: int):
    logger.debug("spells: get id=%s", spell_id)
    row = get_item("spell_library", spell_id)
    if not row: raise HTTPException(404, "Not found")
    spell = json.loads(row["spell_json"])
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "spell": spell}

@router.delete("/api/spells/delete/{spell_id}")
async def spells_delete(spell_id: int):
    logger.debug("spells: delete id=%s", spell_id)
    ok = delete_item("spell_library", spell_id)
    if not ok: raise HTTPException(404, "Not found")
    return {"ok": True}
