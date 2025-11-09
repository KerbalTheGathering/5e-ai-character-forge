from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from ..schemas import ProgressionInput, ProgressionPlan, ProgressionExport, LevelPick
from ..helpers import fetch_json, markdown_from_progression
from ..database import create_item, get_item, list_items, delete_item
from ..pdf_export import export_progression_pdf_content
from ..config import RULES_BASE, RULES_API_PREFIX, logger
import json

router = APIRouter()

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

@router.post("/api/progression/generate", response_model=ProgressionPlan)
async def progression_generate(payload: ProgressionInput):
    ci = payload.class_index.lower().strip()
    if not ci:
        raise HTTPException(400, "class_index required")
    target = max(1, min(20, payload.target_level))
    d = payload.draft

    avg_hp = (d.hit_die // 2) + 1
    picks: list[LevelPick] = []

    try:
        cls_data = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/classes/{ci}")
        subclasses = [x.get("name") for x in cls_data.get("subclasses", []) or []]
    except Exception:
        subclasses = []
    chosen_subclass = subclasses[0] if subclasses else None
    subclass_level = SUBCLASS_LEVELS.get(ci, 3)

    asi_levels = ASI_LEVELS_OVERRIDES.get(ci, ASI_LEVELS_DEFAULT)

    for lvl in range(1, target + 1):
        try:
            lvl_data = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/classes/{ci}/levels/{lvl}")
            feat_names = [f.get("name") for f in lvl_data.get("features", []) or []]
        except Exception:
            feat_names = []

        if lvl == 1:
            hp_gain = d.hit_die + d.abilities.CON_mod
        else:
            hp_gain = avg_hp + d.abilities.CON_mod

        sc = chosen_subclass if (chosen_subclass and lvl == subclass_level) else None

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

@router.post("/api/progression/export/md")
async def progression_export_md(payload: ProgressionExport):
    md = markdown_from_progression(payload.plan)
    fname = (payload.plan.name or "progression").replace(" ", "_") + ".md"
    return PlainTextResponse(content=md, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="{fname}"'})

@router.post("/api/progression/export/pdf")
async def progression_export_pdf(payload: ProgressionExport):
    logger.debug("progression: export PDF name=%s", payload.plan.name)
    buffer = await export_progression_pdf_content(payload.plan)
    filename = (payload.plan.name or "progression").replace(' ','_') + ".pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@router.post("/api/progression/save")
async def progression_save(payload: ProgressionExport):
    name = payload.plan.name or "Progression Plan"
    progression_data = {"name": name, "plan_json": payload.plan.model_dump_json(), "prompt": payload.prompt}
    result = create_item("progression_library", progression_data)
    return result

@router.get("/api/progression/list")
async def progression_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    return list_items("progression_library", limit, page, search, sort)

@router.get("/api/progression/get/{plan_id}")
async def progression_get(plan_id: int):
    row = get_item("progression_library", plan_id)
    if not row: raise HTTPException(404, "Not found")
    plan = json.loads(row["plan_json"])
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "plan": plan}

@router.delete("/api/progression/delete/{plan_id}")
async def progression_delete(plan_id: int):
    ok = delete_item("progression_library", plan_id)
    if not ok: raise HTTPException(404, "Not found")
    return {"ok": True}
