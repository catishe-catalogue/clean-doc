from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class DailyUsage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_usage"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    fingerprint: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_subnet: Mapped[str] = mapped_column(String, nullable=False)
    usage_date: Mapped[date] = mapped_column(
        Date, server_default=func.current_date(), nullable=False
    )
    conversion_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    user: Mapped["User | None"] = relationship("User", back_populates="daily_usages")

    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_daily_user"),
        Index("idx_daily_usage_date", "usage_date"),
        Index(
            "uq_daily_guest_fp",
            "fingerprint",
            "ip_subnet",
            "usage_date",
            unique=True,
            postgresql_where=(fingerprint.isnot(None)),
        ),
        Index(
            "uq_daily_guest_ip",
            "ip_subnet",
            "usage_date",
            unique=True,
            postgresql_where=(fingerprint.is_(None)),
        ),
    )
