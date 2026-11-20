"""Personalization: student_preference (student-chosen options only). Additive.

Revision ID: 0004
Revises: 0003
"""

from pathlib import Path

from alembic import op

revision = "0004"
down_revision = "0003"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0004_personalization.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE student_preference")
