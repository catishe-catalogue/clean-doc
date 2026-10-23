#!/usr/bin/env python3
"""Скрипт наполнения dev-базы тестовыми пользователями и данными."""
import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

# Добавляем backend в sys.path независимо от рабочей директории запуска
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
import structlog

from app.core.database import AsyncSessionLocal  # pyright: ignore[reportMissingImports]
from app.models.subscription import Subscription  # pyright: ignore[reportMissingImports]
from app.models.usage import DailyUsage  # pyright: ignore[reportMissingImports]
from app.models.user import User  # pyright: ignore[reportMissingImports]

logger = structlog.get_logger()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # Проверяем на повторный запуск (идемпотентность)
        existing = await session.scalar(
            select(User).where(User.email == "free@clean-doc.local")
        )
        if existing:
            logger.info("seed_already_applied", free_user_id=str(existing.id))
            return

        now = datetime.now(timezone.utc)
        user_free = User(
            email="free@clean-doc.local",
            telegram_username="test_free_user",
            plan="free",
        )
        user_pro = User(
            email="pro@clean-doc.local",
            telegram_username="test_pro_user",
            plan="pro",
        )
        session.add_all([user_free, user_pro])
        await session.flush()

        subscription = Subscription(
            user_id=user_pro.id,
            plan="pro",
            billing_period="month",
            status="active",
            amount_rub=1490,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            next_billing_at=now + timedelta(days=29, hours=23),
        )
        usage = DailyUsage(
            user_id=user_free.id,
            ip_subnet="127.0.0.0/24",
            usage_date=date.today(),
            conversion_count=1,
        )
        session.add_all([subscription, usage])
        await session.commit()
        logger.info(
            "seed_completed",
            free_user_id=str(user_free.id),
            pro_user_id=str(user_pro.id),
        )


if __name__ == "__main__":
    asyncio.run(seed())
