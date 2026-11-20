"""Habit: chat_session, chat_message (append-only), study_activity. Additive.

Revision ID: 0003
Revises: 0002
"""

from pathlib import Path

from alembic import op

revision = "0003"
down_revision = "0002"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0003_habit.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    for t in ("study_activity", "chat_message", "chat_session"):
        op.get_bind().exec_driver_sql(f"DROP TABLE {t}")
