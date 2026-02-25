import asyncio
import uuid
from decimal import Decimal

import httpx
from loguru import logger

from app.integrations.payment.base import (
    GatewayPaymentStatus,
    PaymentGateway,
    PaymentInitResult,
    PaymentStatusResult,
    RefundResult,
)


class MockGateway(PaymentGateway):
    """Mock payment gateway for development and demos.

    Auto-completes payments after a configurable delay by firing a
    webhook back to the local server.
    """

    def __init__(
        self,
        webhook_base_url: str = "http://localhost:8000",
        auto_complete_delay: float = 3.0,
    ) -> None:
        self._webhook_base_url = webhook_base_url
        self._auto_complete_delay = auto_complete_delay
        self._transactions: dict[str, GatewayPaymentStatus] = {}

    async def initiate(
        self,
        amount: Decimal,
        order_id: str,
        description: str,
    ) -> PaymentInitResult:
        transaction_id = f"mock_{uuid.uuid4().hex[:16]}"
        self._transactions[transaction_id] = GatewayPaymentStatus.PENDING

        qr_code_data = (
            f"mock://pay?tx={transaction_id}&amount={amount}&order={order_id}"
        )

        logger.info(
            "Mock payment initiated",
            extra={
                "transaction_id": transaction_id,
                "amount": str(amount),
                "order_id": order_id,
            },
        )

        # Schedule auto-completion in the background
        asyncio.create_task(
            self._auto_complete(transaction_id, order_id)
        )

        return PaymentInitResult(
            transaction_id=transaction_id,
            payment_url=f"{self._webhook_base_url}/mock-pay/{transaction_id}",
            qr_code_data=qr_code_data,
        )

    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        status = self._transactions.get(
            transaction_id, GatewayPaymentStatus.PENDING
        )
        return PaymentStatusResult(
            transaction_id=transaction_id,
            status=status,
        )

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> RefundResult:
        refund_id = f"mock_ref_{uuid.uuid4().hex[:12]}"
        self._transactions[transaction_id] = GatewayPaymentStatus.REFUNDED

        logger.info(
            "Mock refund processed",
            extra={
                "transaction_id": transaction_id,
                "refund_id": refund_id,
                "amount": str(amount),
            },
        )

        return RefundResult(
            transaction_id=transaction_id,
            refund_id=refund_id,
            status=GatewayPaymentStatus.REFUNDED,
        )

    async def verify_webhook(self, payload: dict, headers: dict) -> bool:
        # Mock gateway always trusts webhooks
        return True

    async def _auto_complete(self, transaction_id: str, order_id: str) -> None:
        """Wait, then fire a webhook to self to simulate provider callback."""
        await asyncio.sleep(self._auto_complete_delay)

        self._transactions[transaction_id] = GatewayPaymentStatus.COMPLETED

        webhook_url = (
            f"{self._webhook_base_url}/api/v1/payments/webhook/mock"
        )
        webhook_payload = {
            "transaction_id": transaction_id,
            "status": "completed",
            "provider": "mock",
            "payload": {
                "order_id": order_id,
                "message": "Mock payment auto-completed",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(webhook_url, json=webhook_payload)
                logger.info(
                    "Mock auto-complete webhook sent",
                    extra={
                        "transaction_id": transaction_id,
                        "webhook_status": resp.status_code,
                    },
                )
        except Exception as e:
            logger.warning(
                "Mock auto-complete webhook failed (non-fatal)",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
