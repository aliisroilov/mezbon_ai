import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


class GatewayPaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


@dataclass(frozen=True)
class PaymentInitResult:
    transaction_id: str
    payment_url: str | None = None
    qr_code_data: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentStatusResult:
    transaction_id: str
    status: GatewayPaymentStatus
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RefundResult:
    transaction_id: str
    refund_id: str
    status: GatewayPaymentStatus
    extra: dict = field(default_factory=dict)


class PaymentGateway(ABC):
    """Abstract base class for all payment gateway integrations."""

    @abstractmethod
    async def initiate(
        self,
        amount: Decimal,
        order_id: str,
        description: str,
    ) -> PaymentInitResult:
        """Initiate a payment and return transaction details + payment URL/QR."""
        ...

    @abstractmethod
    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        """Check the current status of a transaction."""
        ...

    @abstractmethod
    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> RefundResult:
        """Refund a completed transaction (full or partial)."""
        ...

    @abstractmethod
    async def verify_webhook(self, payload: dict, headers: dict) -> bool:
        """Verify the authenticity of an incoming webhook from the provider."""
        ...
