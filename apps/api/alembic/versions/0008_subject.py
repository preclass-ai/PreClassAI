"""Subject catalogue (GDPT 2018). Additive only; only geography is active.

Revision ID: 0008
Revises: 0007
"""

from pathlib import Path

from alembic import op

revision = "0008"
down_revision = "0007"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0008_subject.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS subject")
