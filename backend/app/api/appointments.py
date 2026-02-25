import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.models.appointment import AppointmentStatus
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentUpdate
from app.services import appointment_service
from app.sockets import notify_appointment_updated

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _serialize(appt) -> dict:
    return AppointmentRead(
        **{k: v for k, v in appt.__dict__.items() if not k.startswith("_")},
    ).model_dump(mode="json")


@router.get("/")
async def list_appointments(
    date_from: date | None = None,
    date_to: date | None = None,
    doctor_id: uuid.UUID | None = None,
    patient_id: uuid.UUID | None = None,
    status: AppointmentStatus | None = None,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    appts = await appointment_service.list_appointments(
        db, clinic_id,
        date_from=date_from,
        date_to=date_to,
        doctor_id=doctor_id,
        patient_id=patient_id,
        status=status,
    )
    return success_response([_serialize(a) for a in appts])


@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    appt = await appointment_service.get_appointment(db, clinic_id, appointment_id)
    return success_response(_serialize(appt))


@router.post("/", status_code=201)
async def book_appointment(
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    appt = await appointment_service.book_appointment(db, clinic_id, body)
    appt_data = _serialize(appt)
    await notify_appointment_updated(clinic_id, appt_data)
    return success_response(appt_data)


@router.patch("/{appointment_id}/status")
async def update_status(
    appointment_id: uuid.UUID,
    body: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    appt = await appointment_service.update_appointment_status(
        db, clinic_id, appointment_id, body
    )
    appt_data = _serialize(appt)
    await notify_appointment_updated(clinic_id, appt_data)
    return success_response(appt_data)


@router.post("/{appointment_id}/check-in")
async def check_in(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    appt = await appointment_service.check_in(db, clinic_id, appointment_id)
    appt_data = _serialize(appt)
    await notify_appointment_updated(clinic_id, appt_data)
    return success_response(appt_data)


@router.post("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    appt = await appointment_service.cancel_appointment(db, clinic_id, appointment_id)
    appt_data = _serialize(appt)
    await notify_appointment_updated(clinic_id, appt_data)
    return success_response(appt_data)
