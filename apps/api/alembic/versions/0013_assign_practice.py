"""assignment.cancelled_at and practice_attempt (practice runs of an item after the first attempt). Additive.

Revision ID: 0013
Revises: 0012
"""

from pathlib import Path

from alembic import op

revision = "0013"
down_revision = "0012"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0013_assign_practice.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS practice_attempt")
    bind.exec_driver_sql("ALTER TABLE assignment DROP COLUMN IF EXISTS cancelled_at")
