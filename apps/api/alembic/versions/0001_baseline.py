"""Baseline schema: frozen DDL (0001_schema.sql) + triggers/roles (0001_triggers.sql).

Revision ID: 0001
Revises:
"""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None

_DIR = Path(__file__).parent


def _run(name: str) -> None:
    # asyncpg cannot run several statements in one call, so files are split on "-- split".
    for stmt in (_DIR / name).read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def upgrade() -> None:
    _run("0001_schema.sql")
    _run("0001_triggers.sql")


def downgrade() -> None:
    _run("0001_drop.sql")
