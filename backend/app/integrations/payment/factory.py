from app.config import Settings
from app.models.payment import PaymentMethod
from app.integrations.payment.base import PaymentGateway
from app.integrations.payment.mock import MockGateway


def get_gateway(method: PaymentMethod, config: Settings) -> PaymentGateway:
    """Return the appropriate payment gateway for the given method.

    When PAYMENT_MOCK is enabled in config, always returns MockGateway
    regardless of the payment method (for dev/demo use).
    """
    if config.PAYMENT_MOCK:
        webhook_base = f"http://{config.APP_HOST}:{config.APP_PORT}"
        if config.APP_HOST == "0.0.0.0":
            webhook_base = f"http://localhost:{config.APP_PORT}"
        return MockGateway(webhook_base_url=webhook_base)

    # Lazy imports to avoid loading unused gateway dependencies
    match method:
        case PaymentMethod.UZCARD:
            from app.integrations.payment.uzcard import UzcardGateway
            return UzcardGateway(config)
        case PaymentMethod.HUMO:
            from app.integrations.payment.humo import HumoGateway
            return HumoGateway(config)
        case PaymentMethod.CLICK:
            from app.integrations.payment.click import ClickGateway
            return ClickGateway(config)
        case PaymentMethod.PAYME:
            from app.integrations.payment.payme import PaymeGateway
            return PaymeGateway(config)
        case PaymentMethod.CASH:
            # Cash payments don't go through a gateway
            raise ValueError("Cash payments do not use a payment gateway")
        case _:
            raise ValueError(f"Unsupported payment method: {method}")
