"""
MoveScore — FastAPI Backend

Entry point for the Cloud Run backend service.
Dance first. Music second.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from routes import upload as upload_router
from routes import run_agent as run_agent_router
from schemas.api import HealthResponse
from utils.errors import AgenticCinemaError

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MoveScore API",
    description="Dance first. Music second. Choreography-first music generation for creators.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# In production: set FRONTEND_URL to the deployed Cloud Run frontend URL.
# In development: defaults to localhost:3000.
_allowed_origins = [settings.frontend_url]
if settings.frontend_url != "http://localhost:3000":
    # Also allow localhost during testing alongside the production origin
    _allowed_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Request-ID"],
)

# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(AgenticCinemaError)
async def agentic_cinema_error_handler(
    request: Request, exc: AgenticCinemaError
) -> JSONResponse:
    logger.error("AgenticCinemaError: %s", exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error("Unhandled error on %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred. Please try again."},
    )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(upload_router.router, tags=["Upload"])
app.include_router(run_agent_router.router, tags=["Agent"])


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Health check endpoint for Cloud Run."""
    return HealthResponse(status="ok")


@app.get("/", tags=["Health"])
async def root() -> dict:
    return {
        "service": "MoveScore API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ── Dev runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=True,
    )
