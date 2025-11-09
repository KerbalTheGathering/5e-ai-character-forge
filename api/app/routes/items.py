from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from ..schemas import MagicItemInput, MagicItem, MagicItemExport
from ..ai_inference import use_local_inference, local_text_generate, google_text_generate
from ..database import create_item, get_item, list_items, delete_item, get_db_connection
from ..pdf_export import export_magic_item_pdf_content
from ..config import logger
import json

router = APIRouter()

MI_GUIDE = (
    "You are a D&D 5e SRD-friendly designer. Create balanced, flavorful magic items. "
    "Follow DMG-style format. Avoid copyrighted setting names."
)

@router.post("/api/items/generate", response_model=MagicItem)
async def items_generate(payload: MagicItemInput, engine: str | None = Query(default=None)):
    logger.debug("items: generate request name=%s rarity=%s type=%s", payload.name, payload.rarity, payload.item_type)
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
        if use_local_inference(engine):
            text = await local_text_generate(long_prompt)
        else:
            text = await google_text_generate(long_prompt, MI_GUIDE)
        if text.startswith("```"):
            text = text.strip("`").replace("json\n","").replace("\njson","")
        data = json.loads(text)
        item = MagicItem(**data)
        return item
    except Exception as e:
        raise HTTPException(502, f"item generation failed: {e}")

@router.post("/api/items/save")
async def items_save(payload: MagicItemExport):
    logger.debug("items: save %s", payload.item.name)
    item_data = {"name": payload.item.name, "item_json": payload.item.model_dump_json(), "prompt": payload.prompt}
    result = create_item("item_library", item_data)
    return result

@router.get("/api/items/list")
async def items_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    logger.debug("items: list limit=%s page=%s search=%s sort=%s", limit, page, search, sort)
    result = list_items("item_library", limit, page, search, sort)
    # Enrich items with item_type and rarity from item_json
    con = get_db_connection()
    for item in result["items"]:
        row = con.execute("SELECT item_json FROM item_library WHERE id = ?", (item["id"],)).fetchone()
        if row:
            try:
                item_data = json.loads(row["item_json"])
                item["item_type"] = item_data.get("item_type", "")
                item["rarity"] = item_data.get("rarity", "")
            except Exception:
                item["item_type"] = ""
                item["rarity"] = ""
    con.close()
    return result

@router.get("/api/items/get/{item_id}")
async def items_get(item_id: int):
    logger.debug("items: get id=%s", item_id)
    row = get_item("item_library", item_id)
    if not row: raise HTTPException(404, "Not found")
    item = json.loads(row["item_json"])
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "item": item}

@router.delete("/api/items/delete/{item_id}")
async def items_delete(item_id: int):
    logger.debug("items: delete id=%s", item_id)
    ok = delete_item("item_library", item_id)
    if not ok: raise HTTPException(404, "Not found")
    return {"ok": True}

@router.post("/api/items/export/pdf")
async def items_export_pdf(payload: MagicItemExport):
    logger.debug("items: export PDF name=%s", payload.item.name)
    buffer = await export_magic_item_pdf_content(payload.item)
    filename = f"{payload.item.name.replace(' ', '_')}_Item.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
