from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ConversionJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversion_jobs"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    target_format: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_date: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String,
        server_default="pending",
        nullable=False,
    )
    s3_input_key: Mapped[str] = mapped_column(Text, nullable=False)
    s3_output_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_preview_keys: Mapped[list[str]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_preview_only: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
    )
    processing_seconds: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=8, scale=3),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("(now() + INTERVAL '2 hours')"),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship("User", back_populates="jobs")

    __table_args__ = (
        CheckConstraint(
            "target_format IN ('docx', 'xlsx')",
            name="check_conversion_jobs_format",
        ),
        CheckConstraint(
            "status IN ('pending', 'queued', 'processing', 'completed', 'failed')",
            name="check_conversion_jobs_status",
        ),
        Index("idx_jobs_user_status", "user_id", "status"),
        Index(
            "idx_jobs_expires",
            "expires_at",
            postgresql_where=text("status = 'completed'"),
        ),
        Index(
            "idx_jobs_dedup",
            "user_id",
            "sha256_checksum",
            "usage_date",
            postgresql_where=text(
                "sha256_checksum IS NOT NULL AND status IN ('processing', 'completed')"
            ),
        ),
    )
