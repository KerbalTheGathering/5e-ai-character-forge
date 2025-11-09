import asyncio
import base64
from fastapi import APIRouter, HTTPException, Response, Query
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from ..schemas import ExportInput, ExportPDFInput
from ..ai_inference import use_local_inference, local_image_generate, google_image_generate
from ..helpers import markdown_from_draft, rules_cache
from ..pdf_export import export_character_pdf_content
from ..config import RULES_BASE, logger

router = APIRouter()

@router.get("/api/rules/{path:path}")
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

@router.post("/api/portrait")
async def generate_portrait(payload: ExportInput, engine: str | None = Query(default=None)):
    logger.info("Generating portrait image...")
    d = payload.draft  # Define d early so it's available for filename generation
    try:
        # Use custom prompt if provided, otherwise construct default prompt
        if payload.custom_prompt and payload.custom_prompt.strip():
            logger.info("Using custom portrait prompt...")
            prompt = payload.custom_prompt.strip()
        else:
            logger.info("Constructing portrait prompt...")
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
        if use_local_inference(engine):
            logger.info("Using local image generation...")
            image_bytes = await local_image_generate(prompt)
        else:
            logger.info("Using Gemini image generation...")
            image_bytes = await google_image_generate(prompt)
    except Exception as e:
        logger.exception("Image generation failed")
        raise HTTPException(502, f"image generation failed: {e}")
    try:
        logger.info("portrait bytes: %d bytes%s", len(image_bytes),
                    " (png)" if image_bytes.startswith(b"\x89PNG\r\n\x1a\n") else "")
    except Exception:
        pass
    filename = f"{(d.name or d.race + ' ' + d.cls).replace(' ','_')}_portrait.png"
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(image_bytes)),
            "Cache-Control": "no-store",
        },
    )

@router.post("/api/export/json")
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

@router.post("/api/export/md")
async def export_md(payload: ExportInput):
    logger.debug("export_md: name=%s class=%s race=%s", payload.draft.name, payload.draft.cls, payload.draft.race)
    parts: list[str] = [markdown_from_draft(payload.draft, payload.backstory)]
    plan = getattr(payload, 'progression', None)
    if plan is not None:
        try:
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

@router.post("/api/export/pdf")
async def export_pdf(payload: ExportPDFInput):
    logger.debug("export_pdf: name=%s class=%s race=%s portrait=%s", payload.draft.name, payload.draft.cls, payload.draft.race, bool(payload.portrait_base64))
    buffer = await export_character_pdf_content(payload.draft, payload.backstory, getattr(payload, 'progression', None), payload.portrait_base64)
    filename = f"{(payload.draft.name or payload.draft.race + ' ' + payload.draft.cls).replace(' ','_')}_Sheet.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
