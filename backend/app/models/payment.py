import enum
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantModel


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    UZCARD = "UZCARD"
    HUMO = "HUMO"
    CLICK = "CLICK"
    PAYME = "PAYME"


class PaymentTransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Payment(TenantModel):
    __tablename__ = "payments"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum")
    )
    transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[PaymentTransactionStatus] = mapped_column(
        Enum(PaymentTransactionStatus, name="payment_transaction_status_enum"),
        default=PaymentTransactionStatus.PENDING,
    )
    provider_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
