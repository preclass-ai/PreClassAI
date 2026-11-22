"""Shared fixtures. Tests marked `db` need Postgres at TEST_DATABASE_URL and are skipped otherwise."""

import asyncio
import os
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

API_DIR = Path(__file__).resolve().parents[1]
TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://preclass:preclass@127.0.0.1:5432/preclass_test"
)
PG_URL = TEST_URL.replace("+asyncpg", "")

# The app under test uses the test database; must be set before `app.config.get_settings()` is first called.
os.environ.update(DATABASE_URL=TEST_URL, DB_NULL_POOL="1", COOKIE_SECURE="false",
                  UPLOAD_DIR=tempfile.mkdtemp(prefix="preclass-uploads-"))


async def _ping() -> None:
    conn = await asyncpg.connect(PG_URL, timeout=3)
    await conn.close()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    try:
        asyncio.run(_ping())
    except Exception:  # noqa: BLE001 any connection problem means "no DB"
        skip = pytest.mark.skip(reason="Postgres not reachable at TEST_DATABASE_URL")
        for item in items:
            if "db" in item.keywords:
                item.add_marker(skip)


def _run(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": TEST_URL, "PYTHONPATH": str(API_DIR), "PYTHONUTF8": "1"}
    subprocess.run([sys.executable, *args], cwd=API_DIR, env=env, check=True, capture_output=True)  # noqa: S603


def reset_db() -> None:
    """Drop everything, migrate to head, seed. Refuses to touch a non-test database."""
    assert PG_URL.rsplit("/", 1)[-1].endswith("_test"), "refusing to reset a non-test database"
    _run("-m", "alembic", "downgrade", "base")
    _run("-m", "alembic", "upgrade", "head")
    _run("-m", "seed.seed")


@pytest.fixture(scope="session")
def db_ready() -> None:
    reset_db()


@pytest.fixture
async def conn(db_ready: None) -> AsyncIterator[asyncpg.Connection]:
    """One connection per test inside a transaction that is always rolled back."""
    c = await asyncpg.connect(PG_URL)
    tr = c.transaction()
    await tr.start()
    yield c
    await tr.rollback()
    await c.close()


@pytest.fixture
async def db(db_ready: None) -> AsyncIterator[AsyncSession]:
    """Session bound to one connection inside a transaction that is rolled back after the test.
    Handler `commit()` calls only release a SAVEPOINT, so every test starts from the seeded state."""
    engine = create_async_engine(TEST_URL, poolclass=NullPool)
    async with engine.connect() as c:
        outer = await c.begin()
        session = AsyncSession(bind=c, join_transaction_mode="create_savepoint", expire_on_commit=False)
        yield session
        await session.close()
        await outer.rollback()
    await engine.dispose()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    from app.auth import admin_login_limiter, login_limiter
    from app.db.session import get_db
    from app.generation import background_runner, run_job
    from app.guest import guess_limiter
    from app.lessonplan.service import plan_runner
    from app.lessonplan.service import run_job as run_plan_job
    from app.main import app

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = _db

    async def _inline(job_id: object) -> None:  # run the generation job inside the test transaction
        await run_job(db, job_id)  # type: ignore[arg-type]

    app.dependency_overrides[background_runner] = lambda: _inline

    async def _plan_inline(job_id: object, data: bytes) -> None:  # the plan reading job runs inside the test transaction
        await run_plan_job(db, job_id, data)  # type: ignore[arg-type]

    app.dependency_overrides[plan_runner] = lambda: _plan_inline
    login_limiter.reset()
    guess_limiter.reset()
    admin_login_limiter.reset()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t", headers={"X-PreClass-CSRF": "1"}
    ) as c:
        yield c
    app.dependency_overrides.clear()


async def login(c: httpx.AsyncClient, identifier: str, password: str = "preclass-demo") -> httpx.Response:  # noqa: S107
    return await c.post("/v1/auth/login", json={"identifier": identifier, "password": password})
