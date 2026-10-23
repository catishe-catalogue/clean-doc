from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan: Mapped[str] = mapped_column(String, nullable=False)
    billing_period: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    yukassa_payment_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    yukassa_payment_method_id: Mapped[str | None] = mapped_column(String, nullable=True)
    amount_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_billing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        CheckConstraint("plan IN ('pro')", name="check_subscriptions_plan"),
        CheckConstraint("billing_period IN ('month', 'year')", name="check_subscriptions_period"),
        CheckConstraint(
            "status IN ('active', 'past_due', 'cancelled')",
            name="check_subscriptions_status",
        ),
        Index("idx_subscriptions_user", "user_id", "status"),
        Index(
            "idx_subscriptions_billing",
            "next_billing_at",
            postgresql_where=(status.in_(["active", "past_due"])),
        ),
    )
