"""
scripts/migrate.py
------------------
Creates all MySQL tables defined in models/orm.py.

Safe to re-run: uses ``CREATE TABLE IF NOT EXISTS`` semantics via
SQLAlchemy's ``create_all(checkfirst=True)``.

Usage:
    python scripts/migrate.py
"""

import sys
from pathlib import Path

# Allow running from the project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging

from core.database import Base, engine
from models import orm  # noqa: F401 — registers ORM classes with Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate() -> None:
    """Apply all pending table migrations."""
    logger.info("Running database migration against: %s", engine.url)
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("Migration complete. Tables: %s", list(Base.metadata.tables.keys()))


if __name__ == "__main__":
    migrate()
