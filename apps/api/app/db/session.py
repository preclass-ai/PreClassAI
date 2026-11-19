from collections.abc import AsyncIterator
from functools import lru_cache
from uuid import uuid4

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
    # PgBouncer (Neon "-pooler" host) in transaction mode cannot keep asyncpg prepared statements.
    pooler = "-pooler" in s.database_url
    args = {"statement_cache_size": 0, "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__"} if pooler else {}
    return create_async_engine(s.database_url, pool_size=s.db_pool_size, max_overflow=s.db_max_overflow,
                               pool_timeout=10, pool_pre_ping=True, pool_recycle=s.db_pool_recycle, connect_args=args)


async def get_db() -> AsyncIterator[AsyncSession]:
    """One session per request; handlers commit explicitly."""
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as session:
        yield session
