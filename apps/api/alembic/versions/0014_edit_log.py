"""transformation_event.before_payload / after_payload: content before and after a teacher edit. Additive.

Revision ID: 0014
Revises: 0013
"""

from pathlib import Path

from alembic import op

revision = "0014"
down_revision = "0013"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0014_edit_log.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE transformation_event DROP COLUMN IF EXISTS before_payload, DROP COLUMN IF EXISTS after_payload")
