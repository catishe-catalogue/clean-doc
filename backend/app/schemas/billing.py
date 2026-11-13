from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateCheckoutRequest(BaseModel):
    billing_period: Literal["month", "year"] = "month"


class CheckoutResponse(BaseModel):
    payment_id: str
    confirmation_url: str
    amount_rub: int


class CreateInvoiceRequest(BaseModel):
    inn: str = Field(..., min_length=10, max_length=12, pattern=r"^\d{10}(\d{2})?$")
    billing_period: Literal["year"] = "year"


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    company_name: str
    amount_rub: int
    pdf_download_url: str
    status: Literal["pending", "paid", "cancelled"]
    created_at: datetime


class YukassaWebhookPayload(BaseModel):
    type: str = "notification"
    event: str
    object: dict[str, Any]


class SubscriptionStatusResponse(BaseModel):
    status: Literal["active", "past_due", "cancelled"]
    plan: str
    billing_period: str
    current_period_end: datetime


class PlanPriceResponse(BaseModel):
    plan: str = "pro"
    price_month_rub: int = 1490
    price_year_rub: int = 11900
