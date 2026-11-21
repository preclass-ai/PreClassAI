"""Which model wrote a Habit reply (main or fallback). Additive only.

Revision ID: 0011
Revises: 0010
"""

from pathlib import Path

from alembic import op

revision = "0011"
down_revision = "0010"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0011_chat_model.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE chat_message DROP COLUMN IF EXISTS model")
