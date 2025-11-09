import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configure application logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("5e-forge")

# Database configuration
DB_PATH = os.getenv("DB_PATH", "app.db")

# Server configuration
PORT = int(os.getenv("PORT_API", "8000"))

# D&D 5e API configuration
RULES_BASE = os.getenv("RULES_BASE_URL", "https://www.dnd5eapi.co")
RULES_API_PREFIX = os.getenv("RULES_API_PREFIX", "api/2014")

# AI/LLM configuration (Google Gemini)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL_TEXT = os.getenv("GEMINI_MODEL_TEXT", "gemini-2.5-pro")
GEMINI_MODEL_IMAGE = os.getenv("GEMINI_MODEL_IMAGE", "gemini-2.5-flash-image")

# Local inference toggles
USE_LOCAL = os.getenv("USE_LOCAL_INFERENCE", "false").lower() == "true"
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/generate")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "gpt-oss:120b")
LOCAL_PORTRAIT_URL = os.getenv("LOCAL_PORTRAIT_URL", "http://localhost:7860/generate")
LOCAL_IMAGE_BASE_MODEL = os.getenv("LOCAL_IMAGE_BASE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
LOCAL_IMAGE_MODEL = os.getenv("LOCAL_IMAGE_MODEL", "ByteDance/SDXL-Lightning")
LOCAL_IMAGE_STEPS = int(os.getenv("LOCAL_IMAGE_STEPS", "4"))
LOCAL_IMAGE_GUIDANCE = float(os.getenv("LOCAL_IMAGE_GUIDANCE", "0.0"))
LOCAL_IMAGE_SEED = int(os.getenv("LOCAL_IMAGE_SEED", "0"))
LOCAL_IMAGE_WIDTH = int(os.getenv("LOCAL_IMAGE_WIDTH", "0"))
LOCAL_IMAGE_HEIGHT = int(os.getenv("LOCAL_IMAGE_HEIGHT", "0"))

# External rules API caching
cache_dir = Path(".cache"); cache_dir.mkdir(exist_ok=True)
