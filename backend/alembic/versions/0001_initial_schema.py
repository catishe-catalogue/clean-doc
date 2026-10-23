"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-10-15 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # 1. users
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_username", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), server_default="free", nullable=False),
        sa.Column("magic_code_hash", sa.Text(), nullable=True),
        sa.Column("magic_code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_blocked", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "magic_code_attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("plan IN ('free', 'pro')", name="check_users_plan"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_telegram", "users", ["telegram_id"])

    # 2. refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
    )
    op.create_index(
        "idx_refresh_tokens_hash",
        "refresh_tokens",
        ["token_hash"],
        postgresql_where=sa.text("revoked = FALSE"),
    )

    # 3. daily_usage
    op.create_table(
        "daily_usage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("fingerprint", sa.Text(), nullable=True),
        sa.Column("ip_subnet", sa.Text(), nullable=False),
        sa.Column(
            "usage_date",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=False,
        ),
        sa.Column(
            "conversion_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_daily_user"),
    )
    op.create_index("idx_daily_usage_date", "daily_usage", ["usage_date"])
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

    # 4. subscriptions
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("billing_period", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("yukassa_payment_id", sa.Text(), nullable=True),
        sa.Column("yukassa_payment_method_id", sa.Text(), nullable=True),
        sa.Column("amount_rub", sa.Integer(), nullable=False),
        sa.Column(
            "current_period_start",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_billing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("plan IN ('pro')", name="check_subscriptions_plan"),
        sa.CheckConstraint(
            "billing_period IN ('month', 'year')", name="check_subscriptions_period"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'past_due', 'cancelled')",
            name="check_subscriptions_status",
        ),
        sa.UniqueConstraint("yukassa_payment_id", name="uq_subscriptions_payment_id"),
    )
    op.create_index("idx_subscriptions_user", "subscriptions", ["user_id", "status"])
    op.create_index(
        "idx_subscriptions_billing",
        "subscriptions",
        ["next_billing_at"],
        postgresql_where=sa.text("status IN ('active', 'past_due')"),
    )

    # 5. b2b_invoices
    op.create_table(
        "b2b_invoices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("inn", sa.Text(), nullable=False),
        sa.Column("kpp", sa.Text(), nullable=True),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("company_address", sa.Text(), nullable=False),
        sa.Column("amount_rub", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("pdf_s3_key", sa.Text(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'paid', 'cancelled')", name="check_invoices_status"
        ),
        sa.UniqueConstraint("invoice_number", name="uq_invoices_number"),
    )
    op.create_index("idx_invoices_user", "b2b_invoices", ["user_id", "status"])

    # 6. app_tokens
    op.create_table(
        "app_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{convert}'"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("token_hash", name="uq_app_tokens_hash"),
    )
    op.create_index(
        "idx_app_tokens_hash",
        "app_tokens",
        ["token_hash"],
        postgresql_where=sa.text("revoked = FALSE"),
    )


def downgrade() -> None:
    op.drop_table("app_tokens")
    op.drop_table("b2b_invoices")
    op.drop_table("subscriptions")
    op.drop_table("daily_usage")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
