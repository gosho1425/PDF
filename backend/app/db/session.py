"""
Async database session management for FastAPI request handlers.
"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_async_engine = None
_AsyncSessionLocal = None


def _get_async_engine():
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        from sqlalchemy.ext.asyncio import create_async_engine
        _async_engine = create_async_engine(
            settings.ASYNC_DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _async_engine


def _get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            bind=_get_async_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session."""
    SessionLocal = _get_async_session_factory()
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
