"""content_block.remediation_draft. Additive only.

Revision ID: 0009
Revises: 0008
"""

from pathlib import Path

from alembic import op

revision = "0009"
down_revision = "0008"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0009_remediation.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE content_block DROP COLUMN IF EXISTS remediation_draft")
