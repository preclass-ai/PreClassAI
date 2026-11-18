from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    s = get_settings()
    if s.db_null_pool:
        return create_async_engine(s.database_url, poolclass=NullPool)
    # Postgres max_connections is 30 in compose.dev.yml: 10 + 5 leaves room for psql, tests and the job worker.
    # Short pool_timeout so a stuck pool answers 500 in 10 s instead of 30 s.
    return create_async_engine(s.database_url, pool_size=10, max_overflow=5, pool_timeout=10,
                               pool_pre_ping=True, pool_recycle=1800)


async def get_db() -> AsyncIterator[AsyncSession]:
    """One session per request; handlers commit explicitly."""
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as session:
        yield session
