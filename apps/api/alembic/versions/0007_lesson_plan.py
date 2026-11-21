"""Lesson plans (CV 5512): plan, sections, objectives, extracted MCQ, subject competencies. Additive only.

Revision ID: 0007
Revises: 0006
"""

from pathlib import Path

from alembic import op

revision = "0007"
down_revision = "0006"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0007_lesson_plan.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    for t in ("extracted_mcq", "objective", "lesson_section", "lesson_plan", "subject_competency"):
        op.get_bind().exec_driver_sql(f"DROP TABLE IF EXISTS {t}")
