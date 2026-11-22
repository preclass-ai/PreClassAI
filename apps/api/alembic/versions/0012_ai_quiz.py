"""AI-drafted quiz questions, quick-review cards and review progress. Additive only.

Revision ID: 0012
Revises: 0011
"""

from pathlib import Path

from alembic import op

revision = "0012"
down_revision = "0011"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0012_ai_quiz.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS review_progress")
    bind.exec_driver_sql("DROP TABLE IF EXISTS plan_ai_item")
    bind.exec_driver_sql("ALTER TABLE chat_message DROP CONSTRAINT IF EXISTS ck_chat_hint")
    bind.exec_driver_sql("ALTER TABLE chat_message ADD CONSTRAINT ck_chat_hint CHECK (hint_level BETWEEN 0 AND 3) NOT VALID")
    for col in ("ai_at", "ai_tokens", "ai_stats", "ai_state"):
        bind.exec_driver_sql(f"ALTER TABLE lesson_plan DROP COLUMN IF EXISTS {col}")
