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
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import AsyncSessionLocal
from app.models.invoice import B2BInvoice
from app.models.subscription import Subscription
from app.models.usage import DailyUsage
from app.models.user import User

logger = structlog.get_logger()


async def run_seed(session: AsyncSession) -> None:
    """Идемпотентная вставка сидовых данных для разработки и тестов."""
    now = datetime.now(timezone.utc)
    today = date.today()

    # 1. Пользователи (free, pro, catishe)
    users_data = [
        {"email": "free@clean-doc.local", "telegram_username": "test_free_user", "plan": "free"},
        {"email": "pro@clean-doc.local", "telegram_username": "test_pro_user", "plan": "pro"},
        {"email": "catishe@gmail.com", "telegram_username": "catishe", "plan": "pro"},
    ]

    for u_data in users_data:
        stmt = pg_insert(User).values(**u_data).on_conflict_do_nothing(index_elements=["email"])
        await session.execute(stmt)
    await session.flush()

    # Получаем id пользователей
    user_free = (
        await session.execute(select(User).filter_by(email="free@clean-doc.local"))
    ).scalar_one()
    user_pro = (
        await session.execute(select(User).filter_by(email="pro@clean-doc.local"))
    ).scalar_one()

    # 2. Подписка для user_pro (план строго 'pro')
    existing_sub = (
        await session.execute(select(Subscription).filter_by(user_id=user_pro.id))
    ).scalar_one_or_none()
    if not existing_sub:
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
        session.add(subscription)
        await session.flush()

    # 3. Daily Usage (uq_daily_user, uq_daily_guest_fp, uq_daily_guest_ip)
    # 3.1. Зарегистрированный пользователь (uq_daily_user)
    stmt_user_usage = (
        pg_insert(DailyUsage)
        .values(
            user_id=user_free.id,
            fingerprint=None,
            ip_subnet="127.0.0.0/24",
            usage_date=today,
            conversion_count=1,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "usage_date"])
    )
    await session.execute(stmt_user_usage)

    # 3.2. Гость с fingerprint (uq_daily_guest_fp)
    stmt_guest_fp = (
        pg_insert(DailyUsage)
        .values(
            user_id=None,
            fingerprint="fp_abc",
            ip_subnet="1.1.1.0/24",
            usage_date=today,
            conversion_count=1,
        )
        .on_conflict_do_nothing(
            index_elements=["fingerprint", "ip_subnet", "usage_date"],
            index_where=(DailyUsage.user_id.is_(None) & DailyUsage.fingerprint.isnot(None)),
        )
    )
    await session.execute(stmt_guest_fp)

    # 3.3. Гость по IP без fingerprint (uq_daily_guest_ip)
    stmt_guest_ip = (
        pg_insert(DailyUsage)
        .values(
            user_id=None,
            fingerprint=None,
            ip_subnet="2.2.2.0/24",
            usage_date=today,
            conversion_count=1,
        )
        .on_conflict_do_nothing(
            index_elements=["ip_subnet", "usage_date"],
            index_where=(DailyUsage.user_id.is_(None) & DailyUsage.fingerprint.is_(None)),
        )
    )
    await session.execute(stmt_guest_ip)

    # 4. B2B Инвойс (uq_invoices_number)
    stmt_invoice = (
        pg_insert(B2BInvoice)
        .values(
            user_id=user_pro.id,
            invoice_number="INV-2026-001",
            inn="7701234567",
            kpp="770101001",
            company_name="ООО Ромашка",
            company_address="г. Москва, ул. Ленина, д. 1",
            amount_rub=1490,
            status="paid",
            pdf_s3_key="invoices/INV-2026-001.pdf",
        )
        .on_conflict_do_nothing(index_elements=["invoice_number"])
    )
    await session.execute(stmt_invoice)

    await session.commit()
    logger.info("seed_completed")


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        await run_seed(session)


if __name__ == "__main__":
    asyncio.run(seed())
