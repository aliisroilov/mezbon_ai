import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.payment import PaymentMethod, PaymentTransactionStatus


class PaymentInitiate(BaseModel):
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    method: PaymentMethod


class PaymentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None
    amount: Decimal
    method: PaymentMethod
    transaction_id: str | None
    status: PaymentTransactionStatus
    provider_response: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class PaymentInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    transaction_id: str | None
    payment_url: str | None
    qr_code_data: str | None
    status: PaymentTransactionStatus


class PaymentWebhook(BaseModel):
    transaction_id: str
    status: str
    provider: str
    payload: dict[str, Any] = Field(default_factory=dict)
