import asyncpg
import pytest

from tests.conftest import PG_URL, _run, reset_db

pytestmark = pytest.mark.db


async def _tables() -> set[str]:
    c = await asyncpg.connect(PG_URL)
    try:
        rows = await c.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        return {r["table_name"] for r in rows}
    finally:
        await c.close()


async def test_migration_up_down_up(db_ready: None) -> None:
    assert {"content_block", "published_version", "review_event"} <= await _tables()
    _run("-m", "alembic", "downgrade", "base")
    assert await _tables() <= {"alembic_version"}  # clean down
    reset_db()  # up again + seed
    assert "content_block" in await _tables()
