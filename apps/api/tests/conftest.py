"""Shared fixtures. Tests marked `db` need Postgres at TEST_DATABASE_URL and are skipped otherwise."""

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest

API_DIR = Path(__file__).resolve().parents[1]
TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://preclass:preclass@localhost:5432/preclass_test"
)
PG_URL = TEST_URL.replace("+asyncpg", "")


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
