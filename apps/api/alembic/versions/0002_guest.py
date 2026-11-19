"""Guest accounts for the anonymous survey: app_user.is_guest, survey_code, last_seen_at.

Revision ID: 0002
Revises: 0001
"""

from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0002_guest.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "ALTER TABLE app_user DROP COLUMN last_seen_at, DROP COLUMN survey_code, DROP COLUMN is_guest")
