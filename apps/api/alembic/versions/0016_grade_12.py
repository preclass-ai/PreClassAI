"""Grade 12: widen ck_class_grade and ck_lesson_grade to (10, 11, 12). Only loosens: no row changes.

Revision ID: 0016
Revises: 0015
"""

from pathlib import Path

from alembic import op

revision = "0016"
down_revision = "0015"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0016_grade_12.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    for t in ("class", "lesson"):  # NOT VALID: existing grade-12 rows stay, new ones are refused again
        bind.exec_driver_sql(f"ALTER TABLE {t} DROP CONSTRAINT ck_{t}_grade")
        bind.exec_driver_sql(f"ALTER TABLE {t} ADD CONSTRAINT ck_{t}_grade CHECK (grade IN (10, 11)) NOT VALID")
