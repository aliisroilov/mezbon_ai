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


class PaymeGateway(PaymentGateway):
    """Payme merchant API integration.

    Docs: https://developer.help.paycom.uz/
    Flow: Merchant API (subscribe) — kiosk initiates, user confirms via Payme.
    """

    def __init__(self, config: Settings) -> None:
        self._merchant_id = config.PAYME_MERCHANT_ID
        # TODO: Add PAYME_SECRET_KEY to Settings
        self._api_url = "https://checkout.paycom.uz/api"
        self._client = httpx.AsyncClient(
            base_url=self._api_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    async def initiate(
        self,
        amount: Decimal,
        order_id: str,
        description: str,
    ) -> PaymentInitResult:
        # TODO: Implement Payme transaction creation
        # 1. JSON-RPC call: method "receipts.create"
        #    params: { amount (tiyin), account: { order_id } }
        # 2. Response contains receipt._id (transaction_id)
        # 3. Build checkout URL: https://checkout.paycom.uz/{base64_encoded_params}
        # 4. Return PaymentInitResult with payment_url + QR data
        logger.warning("PaymeGateway.initiate() not yet implemented")
        raise NotImplementedError("Payme integration pending merchant agreement")

    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        # TODO: Implement Payme status check
        # JSON-RPC: method "receipts.check" with id
        # Map Payme states (0=input, 1=waiting, 2=paid, 3=cancelled, 4=delivered)
        logger.warning("PaymeGateway.check_status() not yet implemented")
        raise NotImplementedError("Payme integration pending merchant agreement")

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> RefundResult:
        # TODO: Implement Payme refund
        # JSON-RPC: method "receipts.cancel" with id, reason
        logger.warning("PaymeGateway.refund() not yet implemented")
        raise NotImplementedError("Payme integration pending merchant agreement")

    async def verify_webhook(self, payload: dict, headers: dict) -> bool:
        # TODO: Verify Payme webhook
        # Payme sends JSON-RPC requests with Basic Auth (merchant_id:secret_key)
        # Verify Authorization header matches configured credentials
        logger.warning("PaymeGateway.verify_webhook() not yet implemented")
        return False
