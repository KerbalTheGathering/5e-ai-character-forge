from fastapi import APIRouter, HTTPException
from ..schemas import SaveInput
from ..database import create_item, get_item, list_items, delete_item
from ..config import logger
import json
import base64

router = APIRouter()

@router.post("/api/library/save")
async def library_save(payload: SaveInput):
    logger.debug("library: save name=%s class=%s race=%s", payload.draft.name, payload.draft.cls, payload.draft.race)
    name = payload.draft.name or f"{payload.draft.race} {payload.draft.cls} L{payload.draft.level}"
    portrait_blob = None
    if payload.portrait_base64:
        try:
            portrait_blob = base64.b64decode(payload.portrait_base64)
        except Exception:
            portrait_blob = None
    progression_json = None
    try:
        progression_json = payload.progression.model_dump_json() if getattr(payload, 'progression', None) else None
    except Exception:
        progression_json = None

    item_data = {
        "name": name,
        "draft_json": payload.draft.model_dump_json(),
        "backstory_json": payload.backstory.model_dump_json() if payload.backstory else None,
        "portrait_png": portrait_blob,
        "progression_json": progression_json
    }
    result = create_item("library", item_data)
    return {"id": result["id"], "name": name, "created_at": result["created_at"]}

@router.get("/api/library/list")
async def library_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    logger.debug("library: list limit=%s page=%s search=%s sort=%s", limit, page, search, sort)
    return list_items("library", limit, page, search, sort)

@router.get("/api/library/get/{item_id}")
async def library_get(item_id: int):
    logger.debug("library: get id=%s", item_id)
    row = get_item("library", item_id)
    if not row:
        raise HTTPException(404, "Not found")
    draft = json.loads(row["draft_json"])
    backstory = json.loads(row["backstory_json"]) if row["backstory_json"] else None
    progression = json.loads(row["progression_json"]) if row["progression_json"] else None
    portrait_b64 = None
    if row["portrait_png"] is not None:
        try:
            portrait_b64 = base64.b64encode(row["portrait_png"]).decode("ascii")
        except Exception:
            portrait_b64 = None
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"], "draft": draft, "backstory": backstory, "progression": progression, "portrait_base64": portrait_b64}

@router.delete("/api/library/delete/{item_id}")
async def library_delete(item_id: int):
    logger.debug("library: delete id=%s", item_id)
    deleted = delete_item("library", item_id)
    if not deleted:
        raise HTTPException(404, "Not found")
    return {"ok": True}
