"""VAL-10: widen the validation rule-name CHECK. Existing rows stay valid.

Revision ID: 0005
Revises: 0004
"""

from pathlib import Path

from alembic import op

revision = "0005"
down_revision = "0004"

_DIR = Path(__file__).parent


def upgrade() -> None:
    for stmt in (_DIR / "0005_val10.sql").read_text(encoding="utf-8").split("-- split"):
        if stmt.strip():
            op.get_bind().exec_driver_sql(stmt)


def downgrade() -> None:
    # validation_result is append-only: keep the VAL-10 rows and only constrain new ones (NOT VALID)
    op.get_bind().exec_driver_sql("ALTER TABLE validation_result DROP CONSTRAINT ck_validation_rule")
    op.get_bind().exec_driver_sql(
        "ALTER TABLE validation_result ADD CONSTRAINT ck_validation_rule CHECK (rule ~ '^VAL-0[1-9]$') NOT VALID")
