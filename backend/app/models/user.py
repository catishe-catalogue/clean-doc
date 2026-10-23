from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.job import ConversionJob
    from app.models.token import AppToken, RefreshToken
    from app.models.usage import DailyUsage


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, index=True, nullable=True
    )
    telegram_username: Mapped[str | None] = mapped_column(String, nullable=True)
    plan: Mapped[str] = mapped_column(String, default="free", nullable=False)

    # Magic Link / Email OTP (хеш SHA-256 кода, TTL 15 минут)
    magic_code_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    magic_code_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Защита от брутфорса и административная блокировка
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    magic_code_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    app_tokens: Mapped[list["AppToken"]] = relationship(
        "AppToken", back_populates="user", cascade="all, delete-orphan"
    )
    daily_usages: Mapped[list["DailyUsage"]] = relationship(
        "DailyUsage", back_populates="user", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ConversionJob"]] = relationship(
        "ConversionJob", back_populates="user", cascade="all, delete-orphan"
    )
