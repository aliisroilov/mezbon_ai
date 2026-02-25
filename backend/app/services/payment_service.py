import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError, PaymentError
from app.integrations.crm.operations import sync_deal_update
from app.integrations.payment.base import GatewayPaymentStatus, PaymentInitResult
from app.integrations.payment.factory import get_gateway
from app.models.audit_log import AuditLog
from app.models.clinic import Clinic
from app.models.payment import Payment, PaymentMethod, PaymentTransactionStatus
from app.schemas.payment import PaymentInitiate


async def _get_clinic_settings(db: AsyncSession, clinic_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(Clinic.settings).where(Clinic.id == clinic_id))
    return result.scalar_one_or_none()


async def _sync_crm_deal_won(db: AsyncSession, payment: Payment) -> None:
    """Mark the CRM deal as won when payment completes. Fire-and-forget."""
    if not payment.appointment_id:
        return

    clinic_settings = await _get_clinic_settings(db, payment.clinic_id)
    if not clinic_settings or not clinic_settings.get("crm_enabled"):
        return

    # Find CRM deal ID from audit logs
    audit_result = await db.execute(
        select(AuditLog).where(
            AuditLog.clinic_id == payment.clinic_id,
            AuditLog.action == "crm.deal.create",
            AuditLog.entity_type == "appointment",
            AuditLog.entity_id == payment.appointment_id,
        ).order_by(AuditLog.created_at.desc()).limit(1)
    )
    audit_entry = audit_result.scalar_one_or_none()
    crm_deal_id = (
        audit_entry.new_value.get("crm_deal_id")
        if audit_entry and audit_entry.new_value
        else None
    )

    if crm_deal_id:
        await sync_deal_update(
            db,
            payment.clinic_id,
            clinic_settings,
            crm_deal_id,
            payment.id,
            {"status": "won", "amount": str(payment.amount)},
        )


async def list_payments(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID | None = None,
) -> list[Payment]:
    stmt = select(Payment).where(Payment.clinic_id == clinic_id)
    if patient_id:
        stmt = stmt.where(Payment.patient_id == patient_id)
    stmt = stmt.order_by(Payment.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_payment(
    db: AsyncSession, clinic_id: uuid.UUID, payment_id: uuid.UUID
) -> Payment:
    result = await db.execute(
        select(Payment).where(Payment.clinic_id == clinic_id, Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise NotFoundError("Payment not found")
    return payment


async def initiate_payment(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    data: PaymentInitiate,
) -> tuple[Payment, PaymentInitResult | None]:
    """Create a Payment record and initiate it via the appropriate gateway.

    Returns (payment, gateway_result). For CASH payments, gateway_result is None.
    """
    payment = Payment(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        appointment_id=data.appointment_id,
        amount=data.amount,
        method=data.method,
    )
    db.add(payment)
    await db.flush()

    logger.info(
        "Payment record created",
        extra={
            "payment_id": str(payment.id),
            "amount": str(data.amount),
            "method": data.method.value,
        },
    )

    if data.method == PaymentMethod.CASH:
        payment.status = PaymentTransactionStatus.COMPLETED
        await db.flush()
        await _sync_crm_deal_won(db, payment)
        return payment, None

    try:
        gateway = get_gateway(data.method, settings)
        result = await gateway.initiate(
            amount=data.amount,
            order_id=str(payment.id),
            description=f"Payment {payment.id}",
        )
        payment.transaction_id = result.transaction_id
        await db.flush()

        logger.info(
            "Gateway payment initiated",
            extra={
                "payment_id": str(payment.id),
                "transaction_id": result.transaction_id,
            },
        )
        return payment, result

    except NotImplementedError as e:
        payment.status = PaymentTransactionStatus.FAILED
        payment.provider_response = {"error": str(e)}
        await db.flush()
        raise PaymentError(f"Payment method {data.method.value} not yet available") from e
    except Exception as e:
        payment.status = PaymentTransactionStatus.FAILED
        payment.provider_response = {"error": str(e)}
        await db.flush()
        logger.error(
            "Gateway initiation failed",
            extra={"payment_id": str(payment.id), "error": str(e)},
        )
        raise PaymentError("Payment gateway error") from e


async def handle_webhook(
    db: AsyncSession,
    provider: str,
    transaction_id: str,
    status: str,
    payload: dict,
) -> Payment:
    """Process an incoming webhook from a payment provider.

    Verifies the webhook, updates the Payment record, and returns it.
    The caller (API layer) is responsible for emitting socket events.
    """
    result = await db.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise NotFoundError("Payment not found for transaction")

    if not settings.PAYMENT_MOCK:
        gateway = get_gateway(payment.method, settings)
        if not await gateway.verify_webhook(payload, {}):
            raise PaymentError("Webhook signature verification failed")

    status_map = {
        "completed": PaymentTransactionStatus.COMPLETED,
        "failed": PaymentTransactionStatus.FAILED,
        "refunded": PaymentTransactionStatus.REFUNDED,
    }
    new_status = status_map.get(status.lower())
    if new_status:
        payment.status = new_status
    payment.provider_response = payload

    await db.flush()

    logger.info(
        "Payment webhook processed",
        extra={
            "payment_id": str(payment.id),
            "provider": provider,
            "status": status,
        },
    )

    # CRM sync — mark deal as won when payment completes
    if payment.status == PaymentTransactionStatus.COMPLETED:
        await _sync_crm_deal_won(db, payment)

    return payment


async def check_payment_status(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> Payment:
    """Check payment status by polling the gateway and updating the record."""
    payment = await get_payment(db, clinic_id, payment_id)

    if payment.status != PaymentTransactionStatus.PENDING:
        return payment

    if not payment.transaction_id or payment.method == PaymentMethod.CASH:
        return payment

    try:
        gateway = get_gateway(payment.method, settings)
        gw_result = await gateway.check_status(payment.transaction_id)

        gateway_to_db = {
            GatewayPaymentStatus.COMPLETED: PaymentTransactionStatus.COMPLETED,
            GatewayPaymentStatus.FAILED: PaymentTransactionStatus.FAILED,
            GatewayPaymentStatus.REFUNDED: PaymentTransactionStatus.REFUNDED,
            GatewayPaymentStatus.PENDING: PaymentTransactionStatus.PENDING,
        }
        new_status = gateway_to_db.get(gw_result.status)
        if new_status and new_status != payment.status:
            payment.status = new_status
            payment.provider_response = gw_result.extra or payment.provider_response
            await db.flush()

    except NotImplementedError:
        pass
    except Exception as e:
        logger.warning(
            "Gateway status check failed",
            extra={"payment_id": str(payment.id), "error": str(e)},
        )

    return payment


async def refund_payment(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> Payment:
    """Refund a completed payment via the gateway."""
    payment = await get_payment(db, clinic_id, payment_id)

    if payment.status != PaymentTransactionStatus.COMPLETED:
        raise PaymentError("Only completed payments can be refunded")

    if payment.method == PaymentMethod.CASH:
        payment.status = PaymentTransactionStatus.REFUNDED
        await db.flush()
        return payment

    if not payment.transaction_id:
        raise PaymentError("No transaction ID for refund")

    try:
        gateway = get_gateway(payment.method, settings)
        refund_result = await gateway.refund(payment.transaction_id, payment.amount)

        payment.status = PaymentTransactionStatus.REFUNDED
        payment.provider_response = {
            **(payment.provider_response or {}),
            "refund_id": refund_result.refund_id,
        }
        await db.flush()

        logger.info(
            "Payment refunded",
            extra={
                "payment_id": str(payment.id),
                "refund_id": refund_result.refund_id,
            },
        )

    except NotImplementedError as e:
        raise PaymentError(f"Refund not available for {payment.method.value}") from e
    except Exception as e:
        logger.error(
            "Refund failed",
            extra={"payment_id": str(payment.id), "error": str(e)},
        )
        raise PaymentError("Refund processing failed") from e

    return payment
