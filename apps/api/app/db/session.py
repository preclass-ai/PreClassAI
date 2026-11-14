from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    s = get_settings()
    return create_async_engine(s.database_url, poolclass=NullPool if s.db_null_pool else None)


async def get_db() -> AsyncIterator[AsyncSession]:
    """One session per request; handlers commit explicitly."""
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as session:
        yield session
