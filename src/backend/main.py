"""
FastAPI application entrypoint.

Architecture:
  /health              — Liveness check (no auth required)
  /api/v1/rankings/... — Versioned API (current)
  /api/rankings/...    — Backwards-compatible alias → same handler
  /static/...          — Static file serving (if directory is populated)

CORS:
  Allowed origins are controlled entirely by the ALLOWED_ORIGINS env var.
  In development, defaults to localhost:5173. In production, set this
  to the deployed Vercel URL via the environment.
"""
import logging
import os
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from backend.core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# Ensure project root is on sys.path for consistent imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.ranking_routes import router as rankings_router
from backend.core.health import check_health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rate limiting is initialized in backend/core/limiter.py

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="NFL Stats Analyzer API",
    description="Historical NFL fantasy performance analytics.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5175,http://localhost:3000",
)
# Strip whitespace and trailing slashes for exact origin matching in CORSMiddleware
_allowed_origins: list[str] = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Print all incoming API calls and responses to the console for real-time visibility."""
    import time
    start_time = time.time()
    path = request.url.path
    
    if path.startswith("/api"):
        print(f"\n[API REQUEST] {request.method} {path}")
    
    response = await call_next(request)
    
    if path.startswith("/api"):
        duration = time.time() - start_time
        print(f"[API RESPONSE] {request.method} {path} | STATUS: {response.status_code} | TIME: {duration:.2f}s\n")
    return response

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"], summary="Service liveness check")
@limiter.limit("60/minute")
def health(request: Request):
    """
    Returns service health and available data state.
    Intended for use by monitoring systems (Render health check, UptimeRobot, etc.).
    Returns HTTP 200 even when degraded so the pod keeps running — monitor the
    `status` field in the response body, not just the HTTP code.
    """
    return check_health()


@app.get("/", include_in_schema=False)
@limiter.limit("30/minute")
def root(request: Request):
    return {"message": "NFL Stats Analyzer API", "version": "1.0.0", "docs": "/docs"}


# Versioned router — canonical path for all new clients
app.include_router(rankings_router, prefix="/api/v1", tags=["rankings"])

# Backwards-compatible alias — keeps existing frontend/consumers working
# while they migrate to /api/v1/
app.include_router(rankings_router, prefix="/api", tags=["rankings (legacy)"], include_in_schema=False)

# ── Static files ──────────────────────────────────────────────────────────────
_static_path = Path(__file__).parent / "static"
if _static_path.exists():
    app.mount("/static", StaticFiles(directory=_static_path), name="static")

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
