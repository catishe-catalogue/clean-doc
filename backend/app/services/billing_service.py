import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from uuid import UUID, uuid4

import fitz
import httpx
import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.invoice import B2BInvoice
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing import CheckoutResponse
from app.services.dadata_service import dadata_service
from app.services.storage_service import storage_service

logger = structlog.get_logger()
settings = get_settings()

PRICE_MONTH_RUB = 1490
PRICE_YEAR_RUB = 11900


class BillingService:
    YUKASSA_PAYMENTS_URL = "https://api.yookassa.ru/v3/payments"

    async def create_checkout(
        self, user: User, billing_period: Literal["month", "year"]
    ) -> CheckoutResponse:
        """Создает платеж в ЮKassa (карты, СБП, рекуррентные списания)."""
        amount = PRICE_YEAR_RUB if billing_period == "year" else PRICE_MONTH_RUB
        period_text = "1 год" if billing_period == "year" else "1 месяц"
        desc = f"Подписка «Чистый документ» PRO на {period_text}"

        # shortcut: эмуляция оплаты ЮKassa при тестовых ключах мерчанта
        if (
            not settings.YUKASSA_SHOP_ID
            or not settings.YUKASSA_SECRET_KEY
            or settings.YUKASSA_SHOP_ID.startswith(("mock_", "test_"))
        ):
            mock_payment_id = f"mock_{secrets.token_hex(12)}"
            confirmation_url = (
                f"{settings.YUKASSA_RETURN_URL}?payment_id={mock_payment_id}&status=success"
            )
            return CheckoutResponse(
                payment_id=mock_payment_id,
                confirmation_url=confirmation_url,
                amount_rub=amount,
            )

        idempotence_key = str(uuid4())
        payload = {
            "amount": {"value": f"{amount}.00", "currency": "RUB"},
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": settings.YUKASSA_RETURN_URL,
            },
            "description": desc,
            "metadata": {
                "user_id": str(user.id),
                "billing_period": billing_period,
            },
            "save_payment_method": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.YUKASSA_PAYMENTS_URL,
                    json=payload,
                    auth=(settings.YUKASSA_SHOP_ID, settings.YUKASSA_SECRET_KEY),
                    headers={"Idempotence-Key": idempotence_key},
                )
            if resp.status_code not in (200, 201):
                logger.error("yukassa_error", status=resp.status_code, body=resp.text)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "error": "Ошибка платежного шлюза ЮKassa",
                        "code": "PAYMENT_GATEWAY_ERROR",
                    },
                )
            data = resp.json()
            payment_id = data["id"]
            confirmation_url = data.get("confirmation", {}).get(
                "confirmation_url", settings.YUKASSA_RETURN_URL
            )
            return CheckoutResponse(
                payment_id=payment_id,
                confirmation_url=confirmation_url,
                amount_rub=amount,
            )
        except httpx.RequestError as exc:
            logger.error("yukassa_network_error", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "Платежный шлюз временно недоступен",
                    "code": "PAYMENT_GATEWAY_UNAVAILABLE",
                },
            ) from exc

    async def handle_yukassa_webhook(self, db: AsyncSession, payload: dict[str, Any]) -> bool:
        """Идемпотентная обработка вебхука payment.succeeded от ЮKassa."""
        event = payload.get("event")
        if event != "payment.succeeded":
            return False

        obj = payload.get("object", {})
        payment_id = obj.get("id")
        payment_method_id = obj.get("payment_method", {}).get("id")
        metadata = obj.get("metadata", {})
        user_id_str = metadata.get("user_id")
        billing_period = metadata.get("billing_period", "month")

        if not user_id_str:
            logger.warning("yukassa_webhook_missing_user_id", payment_id=payment_id)
            return False

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            return False

        user = await db.scalar(select(User).where(User.id == user_id))
        if not user:
            logger.error("yukassa_webhook_user_not_found", user_id=user_id_str)
            return False

        # Проверка идемпотентности
        existing_sub = await db.scalar(
            select(Subscription).where(Subscription.yukassa_payment_id == payment_id)
        )
        if existing_sub:
            logger.info("yukassa_webhook_already_processed", payment_id=payment_id)
            return True

        now = datetime.now(UTC)
        days = 365 if billing_period == "year" else 30
        end_date = now + timedelta(days=days)
        next_billing = end_date - timedelta(hours=1)
        amount = PRICE_YEAR_RUB if billing_period == "year" else PRICE_MONTH_RUB

        new_sub = Subscription(
            user_id=user.id,
            plan="pro",
            billing_period=billing_period,
            status="active",
            yukassa_payment_id=payment_id,
            yukassa_payment_method_id=payment_method_id,
            amount_rub=amount,
            current_period_start=now,
            current_period_end=end_date,
            next_billing_at=next_billing,
            retry_count=0,
        )
        db.add(new_sub)
        user.plan = "pro"
        await db.commit()
        logger.info("subscription_activated", user_id=str(user.id), payment_id=payment_id)
        return True

    async def create_b2b_invoice(
        self, db: AsyncSession, user: User, inn: str, billing_period: Literal["year"] = "year"
    ) -> B2BInvoice:
        """Поиск реквизитов в DaData, генерация PDF-счета и сохранение в S3."""
        _ = billing_period
        company = await dadata_service.find_by_inn(inn)
        amount = PRICE_YEAR_RUB

        today_str = datetime.now(UTC).strftime("%Y%m%d")
        seq = secrets.randbelow(9000) + 1000
        invoice_number = f"CD-{today_str}-{seq}"

        # Генерация PDF-документа счета через PyMuPDF
        pdf_bytes = self._generate_invoice_pdf(
            invoice_number=invoice_number,
            company_name=company.name,
            inn=company.inn,
            kpp=company.kpp,
            address=company.address,
            amount=amount,
        )

        s3_key = f"invoices/{invoice_number}.pdf"
        await storage_service.upload_bytes(pdf_bytes, s3_key, content_type="application/pdf")

        invoice = B2BInvoice(
            user_id=user.id,
            invoice_number=invoice_number,
            inn=company.inn,
            kpp=company.kpp,
            company_name=company.name,
            company_address=company.address,
            amount_rub=amount,
            status="pending",
            pdf_s3_key=s3_key,
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
        logger.info(
            "b2b_invoice_created", invoice_id=str(invoice.id), invoice_number=invoice_number
        )
        return invoice

    def _generate_invoice_pdf(
        self,
        invoice_number: str,
        company_name: str,
        inn: str,
        kpp: str | None,
        address: str,
        amount: int,
    ) -> bytes:
        """Формирует типовой PDF-счет на оплату услуг сервиса."""
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4

        # Заголовок и реквизиты поставщика
        text_lines = [
            f"Счет на оплату № {invoice_number} от {datetime.now(UTC).strftime('%d.%m.%Y')} г.",
            "",
            'Поставщик: ООО "Чистый документ", ИНН 7701234567, КПП 770101001',
            "Адрес: 125009, г. Москва, Тверская ул., д. 7",
            'Банк: АО "ТИНЬКОФФ БАНК", БИК 044525974, Р/с 40702810100000123456',
            "Корр. счет: 30101810145250000974",
            "--------------------------------------------------------------------------------",
            f"Покупатель: {company_name}",
            f"ИНН: {inn}" + (f", КПП: {kpp}" if kpp else ""),
            f"Адрес: {address}",
            "--------------------------------------------------------------------------------",
            "Наименование товара / услуги: Доступ к сервису «Чистый документ» (тариф PRO на 1 год)",
            "Кол-во: 1 усл. ед.",
            f"Сумма к оплате: {amount:,} руб. 00 коп. (НДС не облагается в связи с применением УСН)".replace(
                ",", " "
            ),
            "--------------------------------------------------------------------------------",
            "В назначении платежа обязательно указывайте номер и дату счета.",
            "Счет действителен к оплате в течение 5 рабочих дней.",
        ]

        y_offset = 72
        for line in text_lines:
            page.insert_text((50, y_offset), line, fontsize=10, fontname="helv")
            y_offset += 20

        pdf_bytes = cast(bytes, doc.tobytes())
        doc.close()
        return pdf_bytes

    async def cancel_subscription(self, db: AsyncSession, user: User) -> None:
        """Отмена автопродления подписки."""
        sub = await db.scalar(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status == "active")
        )
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Активная подписка не найдена", "code": "SUBSCRIPTION_NOT_FOUND"},
            )
        sub.status = "cancelled"
        await db.commit()
        logger.info("subscription_cancelled", user_id=str(user.id))


billing_service = BillingService()
