import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db, require_role
from app.core.response import success_response
from app.models.payment import PaymentTransactionStatus
from app.schemas.payment import (
    PaymentInitiate,
    PaymentInitiateResponse,
    PaymentRead,
    PaymentWebhook,
)
from app.services import payment_service
from app.sockets import notify_payment_confirmed

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/")
async def list_payments(
    patient_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    payments = await payment_service.list_payments(db, clinic_id, patient_id=patient_id)
    return success_response([
        PaymentRead.model_validate(p).model_dump(mode="json") for p in payments
    ])


@router.get("/{payment_id}")
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    payment = await payment_service.get_payment(db, clinic_id, payment_id)
    return success_response(PaymentRead.model_validate(payment).model_dump(mode="json"))


@router.post("/initiate", status_code=201)
async def initiate_payment(
    body: PaymentInitiate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    payment, gw_result = await payment_service.initiate_payment(db, clinic_id, body)
    response = PaymentInitiateResponse(
        payment_id=payment.id,
        transaction_id=payment.transaction_id,
        payment_url=gw_result.payment_url if gw_result else None,
        qr_code_data=gw_result.qr_code_data if gw_result else None,
        status=payment.status,
    )
    return success_response(response.model_dump(mode="json"))


@router.post("/webhook/{provider}")
async def payment_webhook(
    provider: str,
    body: PaymentWebhook,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Receive payment confirmation from provider. No auth required."""
    payment = await payment_service.handle_webhook(
        db, provider, body.transaction_id, body.status, body.payload
    )

    if payment.status == PaymentTransactionStatus.COMPLETED:
        await notify_payment_confirmed(
            clinic_id=payment.clinic_id,
            device_id=None,
            payment_data={
                "id": str(payment.id),
                "patient_id": str(payment.patient_id),
                "appointment_id": str(payment.appointment_id) if payment.appointment_id else None,
                "amount": str(payment.amount),
                "method": payment.method.value,
                "status": payment.status.value,
            },
        )

    return success_response({"payment_id": str(payment.id), "status": payment.status.value})


@router.get("/{payment_id}/status")
async def check_payment_status(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    payment = await payment_service.check_payment_status(db, clinic_id, payment_id)
    return success_response(PaymentRead.model_validate(payment).model_dump(mode="json"))


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _admin=Depends(require_role("SUPER_ADMIN", "CLINIC_ADMIN")),
) -> dict:
    payment = await payment_service.refund_payment(db, clinic_id, payment_id)
    return success_response(PaymentRead.model_validate(payment).model_dump(mode="json"))
