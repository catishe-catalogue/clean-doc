#!/usr/bin/env python3
"""Скрипт наполнения dev-базы тестовыми пользователями и данными."""
import asyncio
import sys
from datetime import date, datetime, timezone

import structlog

sys.path.insert(0, "backend")

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.subscription import Subscription  # noqa: E402
from app.models.usage import DailyUsage  # noqa: E402
from app.models.user import User  # noqa: E402

logger = structlog.get_logger()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
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
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc),
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
