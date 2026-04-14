"""FastAPI shared dependencies."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_async_db

async def get_db() -> AsyncSession:
    async for session in get_async_db():
        yield session
