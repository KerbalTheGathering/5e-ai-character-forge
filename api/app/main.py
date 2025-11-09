import os, asyncio
import time
import uuid
import uvicorn

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import PORT, logger
from . import database # Import the database module to ensure init_db() is called

# Import routers
from .routes import health, character, backstory, items, spells, progression, library, export, creature

app = FastAPI(title="5e-ai-character-forge API", version="0.1.0")

# Request/response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    start = time.perf_counter()
    path = request.url.path
    method = request.method
    try:
        logger.info("%s %s start rid=%s", method, path, rid)
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("%s %s done status=%s rid=%s duration_ms=%s", method, path, getattr(response, 'status_code', 'NA'), rid, duration_ms)
        try:
            response.headers["X-Request-ID"] = rid
        except Exception:
            pass
        return response
    except HTTPException as he:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.warning("%s %s http_error status=%s detail=%s rid=%s duration_ms=%s", method, path, he.status_code, he.detail, rid, duration_ms)
        raise
    except Exception as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.exception("%s %s unhandled_error rid=%s duration_ms=%s", method, path, rid, duration_ms)
        raise

# CORS: allow local Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{os.getenv('PORT_WEB','5173')}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(character.router)
app.include_router(backstory.router)
app.include_router(items.router)
app.include_router(spells.router)
app.include_router(progression.router)
app.include_router(library.router)
app.include_router(export.router)
app.include_router(creature.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
