"""
PaperLens v2 — Windows-first local research tool.
Runs directly on Windows with: python -m uvicorn app.main:app --reload
No Docker, no PostgreSQL, no Redis required.
"""
from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.database import init_db

# ── Bootstrap ──────────────────────────────────────────────────────────────────
settings = get_settings()
setup_logging(debug=settings.DEBUG)
log = get_logger(__name__)

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PaperLens",
    description=(
        "Local research paper extraction tool. "
        "Scans a Windows folder for PDFs, extracts structured data with AI, "
        "stores results locally. No cloud infrastructure required."
    ),
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# This is a local-only tool — allow all origins so the Next.js proxy,
# direct curl calls, and the Swagger UI all work without configuration.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    log.info(f"PaperLens v{settings.APP_VERSION} starting…")
    settings.ensure_dirs()
    init_db()
    log.info(f"Database: {settings.DB_PATH}")
    log.info(f"LLM: {settings.LLM_PROVIDER} / {settings.LLM_MODEL}")
    log.info("Ready — API docs at http://localhost:8000/api/docs")


# ── Request timing ─────────────────────────────────────────────────────────────
@app.middleware("http")
async def timing(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.time()-t0:.3f}s"
    return response


# ── Global error handler ───────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_error(request: Request, exc: Exception):
    log.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc) if settings.DEBUG else "Internal server error"},
    )


# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/api/docs"}
