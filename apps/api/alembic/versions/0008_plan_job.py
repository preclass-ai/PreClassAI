"""Plan reading job, competency on extracted_mcq and content_block. Additive only.

Revision ID: 0008
Revises: 0007
"""

from pathlib import Path

from alembic import op

revision = "0008"
down_revision = "0007"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0008_plan_job.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    c = op.get_bind()
    c.exec_driver_sql("ALTER TABLE lesson DROP COLUMN IF EXISTS teach_date")
    c.exec_driver_sql("ALTER TABLE content_block DROP COLUMN IF EXISTS objective_id")
    c.exec_driver_sql("ALTER TABLE content_block DROP COLUMN IF EXISTS competency_code")
    c.exec_driver_sql("ALTER TABLE extracted_mcq DROP COLUMN IF EXISTS competency_code")
    c.exec_driver_sql("DROP TABLE IF EXISTS lesson_plan_job")
