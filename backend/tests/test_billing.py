from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.subscription import Subscription
from app.models.user import User
from app.services.auth_service import auth_service

settings = get_settings()


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    user = User(
        email=f"billing_user_{uuid4().hex[:6]}@example.com",
        plan="free",
        is_blocked=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(sample_user: User) -> dict[str, str]:
    token = auth_service.create_access_token(sample_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_plans_pricing(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/billing/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["price_month_rub"] == 1490
    assert data["price_year_rub"] == 11900


@pytest.mark.asyncio
async def test_create_checkout_unauthorized(async_client: AsyncClient) -> None:
    # При выключенном DEV_FAST_MODE неавторизованный запрос возвращает 401
    with patch.object(settings, "DEV_FAST_MODE", False):
        resp = await async_client.post(
            "/api/v1/billing/create-checkout", json={"billing_period": "month"}
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_checkout_success(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    with patch.object(settings, "DEV_FAST_MODE", False):
        resp = await async_client.post(
            "/api/v1/billing/create-checkout",
            json={"billing_period": "year"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "payment_id" in data
        assert "confirmation_url" in data
        assert data["amount_rub"] == 11900


@pytest.mark.asyncio
async def test_yukassa_webhook_success_and_idempotency(
    async_client: AsyncClient, sample_user: User, db_session: AsyncSession
) -> None:
    payment_id = f"test_pay_{uuid4().hex}"
    payload: dict[str, Any] = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": payment_id,
            "status": "succeeded",
            "amount": {"value": "11900.00", "currency": "RUB"},
            "payment_method": {"id": "pm_test_123"},
            "metadata": {
                "user_id": str(sample_user.id),
                "billing_period": "year",
            },
        },
    }

    # Первая отправка вебхука
    resp1 = await async_client.post("/api/v1/billing/webhook/yukassa", json=payload)
    assert resp1.status_code == 200

    # Проверка активации PRO
    await db_session.refresh(sample_user)
    assert sample_user.plan == "pro"

    sub = await db_session.scalar(
        select(Subscription).where(Subscription.yukassa_payment_id == payment_id)
    )
    assert sub is not None
    assert sub.status == "active"
    assert sub.amount_rub == 11900

    # Повторная отправка того же вебхука (идемпотентность)
    resp2 = await async_client.post("/api/v1/billing/webhook/yukassa", json=payload)
    assert resp2.status_code == 200

    subs_count = len(
        (
            await db_session.scalars(
                select(Subscription).where(Subscription.yukassa_payment_id == payment_id)
            )
        ).all()
    )
    assert subs_count == 1


@pytest.mark.asyncio
async def test_create_b2b_invoice_validation(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    with patch.object(settings, "DEV_FAST_MODE", False):
        # Некорректная длина ИНН
        resp_bad = await async_client.post(
            "/api/v1/billing/invoices/create",
            json={"inn": "12345", "billing_period": "year"},
            headers=auth_headers,
        )
        assert resp_bad.status_code == 422  # Pydantic validation error

        # Несуществующий ИНН
        resp_not_found = await async_client.post(
            "/api/v1/billing/invoices/create",
            json={"inn": "0000000000", "billing_period": "year"},
            headers=auth_headers,
        )
        assert resp_not_found.status_code == 422
        assert resp_not_found.json()["detail"]["code"] == "DADATA_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_and_download_b2b_invoice(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    with patch.object(settings, "DEV_FAST_MODE", False):
        resp = await async_client.post(
            "/api/v1/billing/invoices/create",
            json={"inn": "7707083893", "billing_period": "year"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company_name"] == "ПАО СБЕРБАНК"
        assert data["amount_rub"] == 11900
        assert data["status"] == "pending"
        invoice_id = data["id"]

        # Скачивание счета владельцем
        dl_resp = await async_client.get(
            f"/api/v1/billing/invoices/{invoice_id}/pdf",
            headers=auth_headers,
            follow_redirects=False,
        )
        assert dl_resp.status_code == 307
        assert "cleandoc" in dl_resp.headers["location"]


@pytest.mark.asyncio
async def test_cancel_subscription(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    sample_user: User,
    db_session: AsyncSession,
) -> None:
    with patch.object(settings, "DEV_FAST_MODE", False):
        # Попытка отмены без активной подписки -> 404
        resp_404 = await async_client.post(
            "/api/v1/billing/cancel-subscription", headers=auth_headers
        )
        assert resp_404.status_code == 404

        # Создаем активную подписку
        now = datetime.now(UTC)
        sub = Subscription(
            user_id=sample_user.id,
            plan="pro",
            billing_period="month",
            status="active",
            amount_rub=1490,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(sub)
        await db_session.commit()

        # Успешная отмена
        resp_ok = await async_client.post(
            "/api/v1/billing/cancel-subscription", headers=auth_headers
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json()["status"] == "cancelled"

        await db_session.refresh(sub)
        assert sub.status == "cancelled"
