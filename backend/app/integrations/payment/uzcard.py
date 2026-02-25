from decimal import Decimal

import httpx
from loguru import logger

from app.config import Settings
from app.integrations.payment.base import (
    GatewayPaymentStatus,
    PaymentGateway,
    PaymentInitResult,
    PaymentStatusResult,
    RefundResult,
)


class UzcardGateway(PaymentGateway):
    """Uzcard merchant API integration.

    Docs: https://developer.uzcard.uz (requires merchant agreement)
    """

    def __init__(self, config: Settings) -> None:
        self._merchant_id = config.UZCARD_MERCHANT_ID
        # TODO: Add UZCARD_API_URL and UZCARD_SECRET to Settings when integrating
        self._api_url = "https://api.uzcard.uz/merchant"
        self._client = httpx.AsyncClient(
            base_url=self._api_url,
            timeout=30.0,
            headers={
                "X-Merchant-Id": self._merchant_id,
                "Content-Type": "application/json",
            },
        )

    async def initiate(
        self,
        amount: Decimal,
        order_id: str,
        description: str,
    ) -> PaymentInitResult:
        # TODO: Implement Uzcard payment initiation
        # 1. POST /create-transaction with amount (in tiyin), order_id, return_url
        # 2. Parse response for transaction_id and redirect URL
        # 3. Return PaymentInitResult
        logger.warning("UzcardGateway.initiate() not yet implemented")
        raise NotImplementedError("Uzcard integration pending merchant agreement")

    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        # TODO: Implement Uzcard status check
        # GET /transaction/{transaction_id}/status
        logger.warning("UzcardGateway.check_status() not yet implemented")
        raise NotImplementedError("Uzcard integration pending merchant agreement")

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> RefundResult:
        # TODO: Implement Uzcard refund
        # POST /refund with transaction_id, amount (in tiyin)
        logger.warning("UzcardGateway.refund() not yet implemented")
        raise NotImplementedError("Uzcard integration pending merchant agreement")

    async def verify_webhook(self, payload: dict, headers: dict) -> bool:
        # TODO: Verify Uzcard webhook signature
        # Extract signature from headers, compute HMAC-SHA256, compare
        logger.warning("UzcardGateway.verify_webhook() not yet implemented")
        return False
