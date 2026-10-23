"""conversion_jobs

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Создание таблицы conversion_jobs
    op.create_table(
        "conversion_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_token_hash", sa.Text(), nullable=True),
        sa.Column("target_format", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_checksum", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "usage_date",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("s3_input_key", sa.Text(), nullable=False),
        sa.Column("s3_output_key", sa.Text(), nullable=True),
        sa.Column(
            "s3_preview_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "is_preview_only",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("processing_seconds", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(now() + INTERVAL '2 hours')"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "target_format IN ('docx', 'xlsx')",
            name="check_conversion_jobs_format",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'processing', 'completed', 'failed')",
            name="check_conversion_jobs_status",
        ),
    )

    # 2. Индексы производительности и фильтрации
    op.create_index(
        "idx_jobs_user_status",
        "conversion_jobs",
        ["user_id", "status"],
    )

    op.create_index(
        "idx_jobs_expires",
        "conversion_jobs",
        ["expires_at"],
        postgresql_where=sa.text("status = 'completed'"),
    )

    # 3. Составной частичный индекс дедупликации (user_id, sha256_checksum, usage_date)
    # Исключает повторный расход CPU/RAM при повторной отправке идентичного файла в те же сутки
    op.create_index(
        "idx_jobs_dedup",
        "conversion_jobs",
        ["user_id", "sha256_checksum", "usage_date"],
        postgresql_where=sa.text(
            "sha256_checksum IS NOT NULL AND status IN ('processing', 'completed')"
        ),
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_dedup", table_name="conversion_jobs")
    op.drop_index("idx_jobs_expires", table_name="conversion_jobs")
    op.drop_index("idx_jobs_user_status", table_name="conversion_jobs")
    op.drop_table("conversion_jobs")
