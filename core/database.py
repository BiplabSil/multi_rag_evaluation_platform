"""
core/database.py
----------------
SQLAlchemy engine + session factory for MySQL.

Usage (FastAPI dependency injection):

    from core.database import get_db

    @app.get("/example")
    def example(db: Session = Depends(get_db)):
        ...
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker #orm - Object Relational Mapper

from core.config import get_settings


# ── Engine ────────────────────────────────────────────────────────────────────

def _build_engine():
    """Create the SQLAlchemy engine with connection-pool settings suitable for FastAPI."""
    settings = get_settings()
    return create_engine(
        settings.mysql_url,      # WHERE to connect
        pool_pre_ping=True,      # CHECK connections are alive before using
        pool_size=10,            # KEEP 10 connections ready at all times
        max_overflow=20,         # ALLOW 20 extra during traffic spikes
        echo=(settings.app_env == "development"), # PRINT SQL queries (only in development)
    )


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Base model ────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Context manager (for scripts / tests) ─────────────────────────────────────

@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager version of get_db for use outside of FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
