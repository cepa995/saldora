"""Sync database access for Celery worker.

Uses psycopg2 (sync) since Celery tasks run synchronously.
Keeps worker decoupled from API's ORM models — uses raw SQL via text().
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

_engine = None
_SessionLocal = None


def get_session() -> Session:
    """Get a sync database session."""
    global _engine, _SessionLocal

    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable not set")

        _engine = create_engine(database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine)

    return _SessionLocal()


__all__ = ["get_session", "text"]
