from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import B2BInvoice
from app.models.subscription import Subscription
from app.models.token import AppToken, RefreshToken
from app.models.usage import DailyUsage
from app.models.user import User


@pytest.mark.asyncio
async def test_user_creation_and_defaults(db_session: AsyncSession) -> None:
    """Проверяет создание пользователя, генерацию UUIDv4 и дефолтный тариф free."""
    user = User(
        email="client@clean-doc.local",
        telegram_id=987654321,
        telegram_username="test_client",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert isinstance(user.id, UUID)
    assert user.plan == "free"
    assert user.is_blocked is False
    assert user.magic_code_attempts == 0
    assert user.magic_code_hash is None
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


@pytest.mark.asyncio
async def test_cascade_delete_user_related_records(db_session: AsyncSession) -> None:
    """Проверяет каскадное удаление токенов и записей использования при удалении пользователя."""
    user = User(email="cascade@clean-doc.local")
    db_session.add(user)
    await db_session.flush()

    token = RefreshToken(
        user_id=user.id,
        token_hash="dummy_refresh_hash_12345",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    app_token = AppToken(
        user_id=user.id,
        name="1C-Integration",
        token_hash="dummy_app_hash_67890",
    )
    usage = DailyUsage(
        user_id=user.id,
        ip_subnet="192.168.1.0/24",
        usage_date=date.today(),
        conversion_count=1,
    )
    db_session.add_all([token, app_token, usage])
    await db_session.commit()

    # Удаляем пользователя
    await db_session.delete(user)
    await db_session.commit()

    # Проверяем каскадное удаление
    res_token = await db_session.scalar(select(RefreshToken).where(RefreshToken.user_id == user.id))
    res_app = await db_session.scalar(select(AppToken).where(AppToken.user_id == user.id))
    res_usage = await db_session.scalar(select(DailyUsage).where(DailyUsage.user_id == user.id))

    assert res_token is None
    assert res_app is None
    assert res_usage is None


@pytest.mark.asyncio
async def test_daily_usage_registered_user_constraint(db_session: AsyncSession) -> None:
    """Проверяет ограничение unique(user_id, usage_date) для авторизованных пользователей."""
    user = User(email="limit@clean-doc.local")
    db_session.add(user)
    await db_session.flush()

    today = date.today()
    usage1 = DailyUsage(
        user_id=user.id, ip_subnet="10.0.0.0/24", usage_date=today, conversion_count=1
    )
    db_session.add(usage1)
    await db_session.commit()

    usage2 = DailyUsage(
        user_id=user.id, ip_subnet="10.0.0.0/24", usage_date=today, conversion_count=2
    )
    db_session.add(usage2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_daily_usage_guest_partial_indexes(db_session: AsyncSession) -> None:
    """Проверяет работу частичных уникальных индексов для анонимных пользователей."""
    today = date.today()

    # 1. Гость с fingerprint
    u_fp1 = DailyUsage(user_id=None, fingerprint="fp_abc", ip_subnet="1.1.1.0/24", usage_date=today)
    db_session.add(u_fp1)
    await db_session.commit()

    u_fp2_duplicate = DailyUsage(
        user_id=None, fingerprint="fp_abc", ip_subnet="1.1.1.0/24", usage_date=today
    )
    db_session.add(u_fp2_duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # 2. Гость без fingerprint (фолбэк по ip_subnet)
    u_ip1 = DailyUsage(user_id=None, fingerprint=None, ip_subnet="2.2.2.0/24", usage_date=today)
    db_session.add(u_ip1)
    await db_session.commit()

    u_ip2_duplicate = DailyUsage(
        user_id=None, fingerprint=None, ip_subnet="2.2.2.0/24", usage_date=today
    )
    db_session.add(u_ip2_duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_subscription_check_constraints(db_session: AsyncSession) -> None:
    """Проверяет CHECK constraint на plan ('pro') и billing_period ('month', 'year')."""
    user = User(email="sub@clean-doc.local")
    db_session.add(user)
    await db_session.flush()

    # Валидная подписка
    sub_valid = Subscription(
        user_id=user.id,
        plan="pro",
        billing_period="month",
        status="active",
        amount_rub=1490,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(sub_valid)
    await db_session.commit()

    # Невалидный план
    sub_invalid = Subscription(
        user_id=user.id,
        plan="enterprise_invalid",
        billing_period="month",
        status="active",
        amount_rub=5000,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(sub_invalid)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_b2b_invoice_creation_and_unique_constraint(db_session: AsyncSession) -> None:
    """Проверяет создание B2B счета, генерацию UUID и ограничение уникальности invoice_number."""
    user = User(email="invoice@clean-doc.local")
    db_session.add(user)
    await db_session.flush()

    inv1 = B2BInvoice(
        user_id=user.id,
        invoice_number="INV-2026-001",
        inn="7707083893",
        company_name="ООО Ромашка",
        company_address="г. Москва, ул. Ленина, д. 1",
        amount_rub=11900,
        pdf_s3_key="invoices/INV-2026-001.pdf",
    )
    db_session.add(inv1)
    await db_session.commit()
    await db_session.refresh(inv1)

    assert isinstance(inv1.id, UUID)
    assert inv1.status == "pending"
    assert inv1.kpp is None
    assert inv1.paid_at is None
    assert isinstance(inv1.created_at, datetime)

    # Проверка уникальности номера счета
    inv2_dup = B2BInvoice(
        user_id=user.id,
        invoice_number="INV-2026-001",
        inn="7707083893",
        company_name="ООО Другая",
        company_address="г. Москва",
        amount_rub=11900,
        pdf_s3_key="invoices/INV-2026-002.pdf",
    )
    db_session.add(inv2_dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
