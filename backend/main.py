"""
PediCompass FastAPI application entry point.

Startup sequence:
  1. sys.path patched so that `common/` (sibling of `backend/`) is importable.
  2. All routers mounted under /api prefix.
  3. CORS configured for local frontend development.
  4. DynamoDB tables and Qdrant collection auto-created on startup.
"""

import os
import sys

# ── Make `common/` importable ─────────────────────────────────────────────────
# common/ lives at  code/common/  (one level above backend/)
# When uvicorn is invoked from code/backend/ the parent dir is NOT on sys.path.
_PARENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.abspath(_PARENT_DIR))

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.middleware.cors import configure_cors
from api.routes import auth, chat, profiles, analytics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("pedicompass")

app = FastAPI(
    title="PediCompass API",
    description="Agentic RAG system for paediatric triage (under-5s)",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
configure_cors(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])


@app.on_event("startup")
async def startup_event() -> None:
    """Auto-create DynamoDB tables and Qdrant collection if they don't exist."""
    logger.info("PediCompass starting up…")

    # Ensure DynamoDB tables exist
    from db.dynamodb_client import get_dynamodb_client
    db_client = get_dynamodb_client()
    await db_client.ensure_tables_exist()
    logger.info("DynamoDB tables ready.")

    # Ensure Qdrant collection exists
    from rag.qdrant_client import get_qdrant_manager
    qdrant = get_qdrant_manager()
    qdrant.ensure_collection()
    logger.info("Qdrant collection ready.")


@app.get("/api/health", tags=["health"])
async def health_check() -> dict:
    """Liveness probe endpoint."""
    return {"status": "ok", "service": "pedicompass-backend"}
