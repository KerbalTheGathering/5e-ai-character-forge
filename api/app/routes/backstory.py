from fastapi import APIRouter, HTTPException, Query
from ..schemas import BackstoryInput, BackstoryResult
from ..ai_inference import use_local_inference, local_text_generate, google_text_generate
from ..config import logger
import json

router = APIRouter()

BACKSTORY_SYS = (
 "You are an expert tabletop RPG writer. Write backstories consistent with D&D 5e SRD, "
 "avoiding copyrighted setting names. Use clear, evocative prose suitable for a character handout."
)

@router.post("/api/backstory", response_model=BackstoryResult)
async def backstory_route(payload: BackstoryInput, engine: str | None = Query(default=None)):
    logger.debug("backstory: request received for %s/%s level %s", payload.draft.race, payload.draft.cls, payload.draft.level)

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
    )
    if payload.tone == "custom" and payload.custom_inspiration:
        prompt += f"Custom inspiration: {payload.custom_inspiration}\n"
    prompt += (
        f"Return JSON ONLY with keys: summary, traits (list), ideals (list), bonds (list), flaws (list), "
        f"hooks (list), prose_markdown. Avoid extra keys."
    )
    if not payload.include_hooks:
        prompt += " The 'hooks' array should be empty."

    if use_local_inference(engine):
        text = await local_text_generate(prompt)
    else:
        text = await google_text_generate(prompt, BACKSTORY_SYS)
    
    try:
        obj = json.loads(text)
    except Exception as e:
        raise HTTPException(502, f"LLM returned non-JSON: {e}")

    try:
        result = BackstoryResult(**obj)
    except Exception as e:
        raise HTTPException(502, f"Backstory schema validation failed: {e}")

    return result
