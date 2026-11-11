"""fix daily guest partial unique indexes

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-11 20:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_daily_guest_fp", table_name="daily_usage")
    op.drop_index("uq_daily_guest_ip", table_name="daily_usage")
    op.create_index(
        "uq_daily_guest_fp",
        "daily_usage",
        ["fingerprint", "ip_subnet", "usage_date"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL AND fingerprint IS NOT NULL"),
    )
    op.create_index(
        "uq_daily_guest_ip",
        "daily_usage",
        ["ip_subnet", "usage_date"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL AND fingerprint IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_daily_guest_fp", table_name="daily_usage")
    op.drop_index("uq_daily_guest_ip", table_name="daily_usage")
    op.create_index(
        "uq_daily_guest_fp",
        "daily_usage",
        ["fingerprint", "ip_subnet", "usage_date"],
        unique=True,
        postgresql_where=sa.text("fingerprint IS NOT NULL"),
    )
    op.create_index(
        "uq_daily_guest_ip",
        "daily_usage",
        ["ip_subnet", "usage_date"],
        unique=True,
        postgresql_where=sa.text("fingerprint IS NULL"),
    )

