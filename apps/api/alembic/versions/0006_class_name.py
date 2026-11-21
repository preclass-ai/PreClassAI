"""class.name: display name of a class (nullable). Additive.

Revision ID: 0006
Revises: 0005
"""

from pathlib import Path

from alembic import op

revision = "0006"
down_revision = "0005"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0006_class_name.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE class DROP COLUMN name")
