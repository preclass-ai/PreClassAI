"""assignment.display_title, lesson.lesson_plan_id, rename_log. Additive.

Revision ID: 0015
Revises: 0014
"""

from pathlib import Path

from alembic import op

revision = "0015"
down_revision = "0014"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0015_lesson_title.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    for sql in ("DROP TABLE IF EXISTS rename_log", "ALTER TABLE lesson DROP COLUMN IF EXISTS lesson_plan_id",
                "ALTER TABLE assignment DROP COLUMN IF EXISTS display_title"):
        bind.exec_driver_sql(sql)
