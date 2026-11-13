from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    decode_access_token,
    get_current_user,
    get_optional_user,
    get_or_create_dev_user,
)
from app.models.invoice import B2BInvoice
from app.models.user import User
from app.schemas.billing import (
    CheckoutResponse,
    CreateCheckoutRequest,
    CreateInvoiceRequest,
    InvoiceResponse,
    PlanPriceResponse,
    YukassaWebhookPayload,
)
from app.services.billing_service import PRICE_MONTH_RUB, PRICE_YEAR_RUB, billing_service
from app.services.storage_service import storage_service

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter(prefix="/billing", tags=["Биллинг и B2B"])


@router.get("/plans", response_model=PlanPriceResponse)
async def get_plans_pricing() -> PlanPriceResponse:
    """Возвращает информацию о ценах тарифа PRO."""
    return PlanPriceResponse(
        plan="pro",
        price_month_rub=PRICE_MONTH_RUB,
        price_year_rub=PRICE_YEAR_RUB,
    )


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CreateCheckoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CheckoutResponse:
    """Создает платеж в ЮKassa для оформления подписки PRO."""
    return await billing_service.create_checkout(current_user, body.billing_period)


@router.post("/webhook/yukassa")
async def handle_yukassa_webhook(
    payload: YukassaWebhookPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Обрабатывает входящее уведомление от платежного шлюза ЮKassa."""
    await billing_service.handle_yukassa_webhook(db, payload.model_dump())
    return {"status": "ok"}


@router.post("/invoices/create", response_model=InvoiceResponse)
async def create_invoice(
    body: CreateInvoiceRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvoiceResponse:
    """Формирует B2B счет для оплаты юридическим лицом по ИНН."""
    invoice = await billing_service.create_b2b_invoice(
        db, current_user, body.inn, body.billing_period
    )
    pdf_download_url = f"/api/v1/billing/invoices/{invoice.id}/pdf"
    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        company_name=invoice.company_name,
        amount_rub=invoice.amount_rub,
        pdf_download_url=pdf_download_url,
        status="pending",
        created_at=invoice.created_at,
    )


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Query()] = None,
    current_user: Annotated[User | None, Depends(get_optional_user)] = None,
) -> RedirectResponse:
    """Выдает временную pre-signed ссылку на скачивание счета в формате PDF."""
    invoice = await db.get(B2BInvoice, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Счет не найден", "code": "INVOICE_NOT_FOUND"},
        )

    if not current_user and token:
        try:
            token_user_id = decode_access_token(token)
            if token_user_id == invoice.user_id:
                current_user = await db.get(User, token_user_id)
        except HTTPException:
            current_user = None

    if not current_user and settings.DEV_FAST_MODE:
        current_user = await get_or_create_dev_user(db)

    if not settings.DEV_FAST_MODE:
        if not current_user or current_user.id != invoice.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Доступ к счету запрещен", "code": "ACCESS_DENIED"},
            )

    presigned_url = await storage_service.generate_presigned_url(
        invoice.pdf_s3_key,
        expires_in_seconds=900,
        filename=f"invoice_{invoice.invoice_number}.pdf",
    )
    return RedirectResponse(url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Отменяет автопродление активной подписки пользователя."""
    await billing_service.cancel_subscription(db, current_user)
    return {"status": "cancelled"}
