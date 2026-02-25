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


class ClickGateway(PaymentGateway):
    """Click.uz merchant API integration.

    Docs: https://docs.click.uz/
    Flow: SHOP-API — merchant creates invoice, user pays via Click app.
    """

    def __init__(self, config: Settings) -> None:
        self._service_id = config.CLICK_SERVICE_ID
        # TODO: Add CLICK_MERCHANT_ID, CLICK_SECRET_KEY to Settings
        self._api_url = "https://api.click.uz/v2/merchant"
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
        # TODO: Implement Click invoice creation
        # 1. POST /invoice/create with service_id, amount, merchant_trans_id (order_id)
        # 2. Response contains invoice_id
        # 3. Build payment_url: https://my.click.uz/services/pay?service_id=...&merchant_id=...&amount=...&transaction_param=...
        # 4. Return PaymentInitResult with payment_url
        logger.warning("ClickGateway.initiate() not yet implemented")
        raise NotImplementedError("Click integration pending service agreement")

    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        # TODO: Implement Click status check
        # GET /invoice/status/{service_id}/{invoice_id}
        logger.warning("ClickGateway.check_status() not yet implemented")
        raise NotImplementedError("Click integration pending service agreement")

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> RefundResult:
        # TODO: Implement Click refund
        # Click refunds are handled via the merchant cabinet or support API
        logger.warning("ClickGateway.refund() not yet implemented")
        raise NotImplementedError("Click integration pending service agreement")

    async def verify_webhook(self, payload: dict, headers: dict) -> bool:
        # TODO: Verify Click webhook
        # Click sends prepare + complete requests with sign_string
        # sign_string = md5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
        logger.warning("ClickGateway.verify_webhook() not yet implemented")
        return False
