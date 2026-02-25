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


class HumoGateway(PaymentGateway):
    """Humo card merchant API integration.

    Docs: https://developer.humocard.uz (requires merchant agreement)
    """

    def __init__(self, config: Settings) -> None:
        self._merchant_id = config.HUMO_MERCHANT_ID
        # TODO: Add HUMO_API_URL and HUMO_SECRET to Settings when integrating
        self._api_url = "https://api.humocard.uz/merchant"
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
        # TODO: Implement Humo payment initiation
        # 1. POST /payment/create with amount (tiyin), merchant_id, order_id
        # 2. Parse response for transaction_id and payment_url
        # 3. Return PaymentInitResult
        logger.warning("HumoGateway.initiate() not yet implemented")
        raise NotImplementedError("Humo integration pending merchant agreement")

    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        # TODO: Implement Humo status check
        # GET /payment/status/{transaction_id}
        logger.warning("HumoGateway.check_status() not yet implemented")
        raise NotImplementedError("Humo integration pending merchant agreement")

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> RefundResult:
        # TODO: Implement Humo refund
        # POST /payment/refund with transaction_id, amount
        logger.warning("HumoGateway.refund() not yet implemented")
        raise NotImplementedError("Humo integration pending merchant agreement")

    async def verify_webhook(self, payload: dict, headers: dict) -> bool:
        # TODO: Verify Humo webhook signature
        # Humo uses a shared secret for HMAC-SHA256 signature verification
        logger.warning("HumoGateway.verify_webhook() not yet implemented")
        return False
