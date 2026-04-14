"""
SQLAlchemy declarative base and session factory.
Uses synchronous driver for Celery workers, async for FastAPI request handlers.
"""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def get_engine(async_: bool = False):
    settings = get_settings()
    if async_:
        from sqlalchemy.ext.asyncio import create_async_engine
        return create_async_engine(
            settings.ASYNC_DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Synchronous session (used by Celery workers)
_sync_engine = None
_SyncSessionLocal = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = get_engine(async_=False)
    return _sync_engine


def get_sync_session_factory():
    global _SyncSessionLocal
    if _SyncSessionLocal is None:
        _SyncSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_sync_engine(),
        )
    return _SyncSessionLocal


def get_sync_db():
    """Dependency / context manager for synchronous DB sessions."""
    SessionLocal = get_sync_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
