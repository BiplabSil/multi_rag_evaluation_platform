"""
api/main.py
-----------
FastAPI application factory.

Creates the app instance, configures middleware, mounts the router,
and sets up structured logging.

Run with:
    uvicorn api.main:app --reload --port 8000
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from core.config import get_settings

_settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, _settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Multi-Agent RAG Evaluation Platform",
    description=(
        "Ingest documents, query them with a multi-agent RAG pipeline, "
        "and get automatic RAGAS quality metrics per response."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow local frontends / Swagger UI during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _settings.app_env == "development" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
