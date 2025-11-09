import os, asyncio
import httpx
import io
import base64
import torch
import google.generativeai as genai
from diffusers import FluxPipeline
from fastapi import HTTPException
from typing import Any, Dict
from io import BytesIO
from .config import (
    GOOGLE_API_KEY, GEMINI_MODEL_TEXT, GEMINI_MODEL_IMAGE, logger,
    USE_LOCAL, LOCAL_LLM_URL, LOCAL_LLM_MODEL, LOCAL_PORTRAIT_URL,
    LOCAL_IMAGE_BASE_MODEL, LOCAL_IMAGE_MODEL, LOCAL_IMAGE_STEPS, LOCAL_IMAGE_GUIDANCE,
    LOCAL_IMAGE_SEED, LOCAL_IMAGE_WIDTH, LOCAL_IMAGE_HEIGHT
)

# New SDK for image generation
try:
    from google import genai as genai_new
    from google.genai import types as genai_types  # noqa: F401  (kept for completeness)
except Exception:  # pragma: no cover
    genai_new = None  # type: ignore

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def use_local_inference(engine: str | None) -> bool:
    return (engine == 'local') or (engine is None and USE_LOCAL)

async def local_text_generate(prompt: str) -> str:
    """Generate text using Ollama.
    Ensures HTTP client resources are properly released after generation.
    """
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(LOCAL_LLM_URL, json={"model": LOCAL_LLM_MODEL, "prompt": prompt, "stream": False})
            r.raise_for_status()
            data = r.json()
            result = data.get("response") or data.get("text") or data.get("message") or ""
            # Client is automatically closed by async with context manager
            return result
    except Exception as e:
        raise HTTPException(502, f"local llm failed: {e}")

async def google_text_generate(prompt: str, system_instruction: str) -> str:
    if not GOOGLE_API_KEY:
        raise HTTPException(400, "Missing GOOGLE_API_KEY in environment.")
    model = genai.GenerativeModel(GEMINI_MODEL_TEXT, system_instruction=system_instruction)
    resp = await asyncio.to_thread(model.generate_content, prompt)
    text = resp.text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json\n", "").replace("\njson", "")
    return text

async def local_image_generate(prompt: str) -> bytes:
    """Generate an image locally.
    Diffusers pipeline (MPS preferred on macOS)
    Returns PNG bytes.
    Ensures pipeline resources are released after generation.
    """
    logger.info("Attempting local image generation via Diffusers (preferring MPS)...")
    pipe = None
    device = "cpu"
    cuda_ok = False
    mps_ok = False
    try:
        try:
            mps_ok = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
        except Exception:
            mps_ok = False
        try:
            cuda_ok = bool(getattr(torch.version, "cuda", None)) and bool(hasattr(torch, "cuda")) and bool(torch.cuda.is_available())
        except Exception:
            cuda_ok = False
        device = "mps" if mps_ok else ("cuda" if cuda_ok else "cpu")
        dtype = torch.float16 if device == "mps" else (torch.bfloat16 if device == "cuda" else torch.float32)
        logger.info("Diffusion device=%s dtype=%s model=%s", device, str(dtype).split(".")[-1], LOCAL_IMAGE_MODEL)

        pipe = FluxPipeline.from_pretrained(LOCAL_IMAGE_MODEL, dtype=dtype)

        try:
            logger.info("Moving diffusion pipeline to device %s...", device)
            pipe.to(device)
        except Exception:
            logger.info("Diffusion pipeline .to(%s) failed; continuing on default device", device)

        aspect_ratios = {
            "1:1": (512, 512),
            "16:9": (1664, 928),
            "9:16": (928, 1664),
            "4:3": (1472, 1140),
            "3:4": (1140, 1472),
            "3:2": (1584, 1056),
            "2:3": (1056, 1584),
        }
        width, height = aspect_ratios.get("1:1", (0, 0))
        seed = LOCAL_IMAGE_SEED if LOCAL_IMAGE_SEED >= 0 else 0
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
    finally:
        # Release pipeline resources
        if pipe is not None:
            try:
                # Move pipeline off device to free GPU/MPS memory
                pipe.to("cpu")
                # Clear CUDA cache if available
                if cuda_ok and hasattr(torch.cuda, "empty_cache"):
                    torch.cuda.empty_cache()
                # Clear MPS cache if available
                if mps_ok and hasattr(torch.backends.mps, "empty_cache"):
                    torch.backends.mps.empty_cache()
                # Delete the pipeline object
                del pipe
                logger.info("FluxPipeline resources released")
            except Exception as cleanup_e:
                logger.warning("Error during pipeline cleanup: %s", cleanup_e)

async def google_image_generate(prompt: str) -> bytes:
    if not GOOGLE_API_KEY:
        raise HTTPException(400, "Missing GOOGLE_API_KEY in environment.")
    if genai_new is None:
        raise HTTPException(500, "google-genai not installed. Please install google-genai >= 0.3.0")
    
    logger.info("Using Gemini image generation...")
    client = genai_new.Client(api_key=GOOGLE_API_KEY)
    model_name = GEMINI_MODEL_IMAGE
    if model_name in ("gemini-flash-2.5", "gemini-2.5-flash"):
        model_name = "gemini-2.5-flash-image"
    resp = await asyncio.to_thread(
        client.models.generate_content,
        model=model_name,
        contents=[prompt],
    )
    logger.info("Extracting image data from response...")
    image_bytes: bytes | None = None
    for part in getattr(resp, "parts", []) or []:
        if getattr(part, "inline_data", None) is not None:
            img = part.as_image(); buf = BytesIO(); img.save(buf, format="PNG"); image_bytes = buf.getvalue(); break
    if not image_bytes:
        raise ValueError("No image returned by model")
    return image_bytes

async def get_model_health() -> Dict[str, Any]:
    """Report local inference model/device info for image and text.
    Note: This does not load pipelines; it infers device/dtype from torch availability
    and optionally probes the local text endpoint with a fast OPTIONS request.
    """
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
