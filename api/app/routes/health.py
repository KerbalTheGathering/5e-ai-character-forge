from fastapi import APIRouter
from ..ai_inference import get_model_health

router = APIRouter()

@router.get("/health")
async def health():
    return {"ok": True}

@router.get("/health/model")
async def health_model():
    return await get_model_health()
