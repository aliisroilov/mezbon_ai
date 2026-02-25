import uuid
from datetime import date, datetime, time, timedelta, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.integrations.crm.operations import sync_deal_create
from app.models.appointment import Appointment, AppointmentStatus
from app.models.clinic import Clinic
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate


async def _get_clinic_settings(db: AsyncSession, clinic_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(Clinic.settings).where(Clinic.id == clinic_id))
    return result.scalar_one_or_none()


async def list_appointments(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    doctor_id: uuid.UUID | None = None,
    patient_id: uuid.UUID | None = None,
    status: AppointmentStatus | None = None,
) -> list[Appointment]:
    stmt = select(Appointment).where(Appointment.clinic_id == clinic_id)
    if date_from:
        stmt = stmt.where(
            Appointment.scheduled_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to:
        stmt = stmt.where(
            Appointment.scheduled_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        )
    if doctor_id:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if patient_id:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if status:
        stmt = stmt.where(Appointment.status == status)
    stmt = stmt.order_by(Appointment.scheduled_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_appointment(
    db: AsyncSession, clinic_id: uuid.UUID, appointment_id: uuid.UUID
) -> Appointment:
    result = await db.execute(
        select(Appointment).where(
            Appointment.clinic_id == clinic_id, Appointment.id == appointment_id
        )
    )
    appt = result.scalar_one_or_none()
    if appt is None:
        raise NotFoundError("Appointment not found")
    return appt


async def book_appointment(
    db: AsyncSession, clinic_id: uuid.UUID, data: AppointmentCreate
) -> Appointment:
    appt_end = data.scheduled_at + timedelta(minutes=data.duration_minutes)

    # Check date range for same-day conflict detection
    tz = data.scheduled_at.tzinfo or timezone.utc
    day_start = datetime.combine(data.scheduled_at.date(), time.min, tzinfo=tz)
    day_end = datetime.combine(data.scheduled_at.date(), time.max, tzinfo=tz)

    # Check no double-booking for the same doctor at that time
    existing = await db.execute(
        select(Appointment).where(
            Appointment.clinic_id == clinic_id,
            Appointment.doctor_id == data.doctor_id,
            Appointment.scheduled_at >= day_start,
            Appointment.scheduled_at <= day_end,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
    )
    for appt in existing.scalars().all():
        existing_end = appt.scheduled_at + timedelta(minutes=appt.duration_minutes)
        if data.scheduled_at < existing_end and appt_end > appt.scheduled_at:
            raise ConflictError("Time slot conflicts with existing appointment")

    # Check no double-booking for the same patient at that time
    patient_appts = await db.execute(
        select(Appointment).where(
            Appointment.clinic_id == clinic_id,
            Appointment.patient_id == data.patient_id,
            Appointment.scheduled_at >= day_start,
            Appointment.scheduled_at <= day_end,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
    )
    for appt in patient_appts.scalars().all():
        existing_end = appt.scheduled_at + timedelta(minutes=appt.duration_minutes)
        if data.scheduled_at < existing_end and appt_end > appt.scheduled_at:
            raise ConflictError("Patient already has an appointment at this time")

    appointment = Appointment(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        doctor_id=data.doctor_id,
        service_id=data.service_id,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        notes=data.notes,
    )
    db.add(appointment)
    await db.flush()
    logger.info("Appointment booked", extra={"appointment_id": str(appointment.id), "clinic_id": str(clinic_id)})

    # CRM sync — create deal if CRM is enabled and patient has a CRM contact
    # The crm_contact_id would be stored in clinic's patient metadata or audit logs
    # For now, we pass the patient_id as a reference; the CRM operations module
    # handles the case where no contact_id is available
    clinic_settings = await _get_clinic_settings(db, clinic_id)
    if clinic_settings and clinic_settings.get("crm_enabled"):
        # Look up CRM contact ID from audit logs (set during patient registration)
        from app.models.audit_log import AuditLog
        audit_result = await db.execute(
            select(AuditLog).where(
                AuditLog.clinic_id == clinic_id,
                AuditLog.action == "crm.contact.create",
                AuditLog.entity_type == "patient",
                AuditLog.entity_id == data.patient_id,
            ).order_by(AuditLog.created_at.desc()).limit(1)
        )
        audit_entry = audit_result.scalar_one_or_none()
        crm_contact_id = (
            audit_entry.new_value.get("crm_contact_id")
            if audit_entry and audit_entry.new_value
            else None
        )

        if crm_contact_id:
            await sync_deal_create(
                db,
                clinic_id,
                clinic_settings,
                crm_contact_id,
                appointment.id,
                {
                    "title": f"Appointment {appointment.id}",
                    "amount": 0,  # Amount set later when payment is made
                    "appointment_id": str(appointment.id),
                    "scheduled_at": str(data.scheduled_at),
                },
            )

    return appointment


async def check_in(
    db: AsyncSession, clinic_id: uuid.UUID, appointment_id: uuid.UUID
) -> Appointment:
    appt = await get_appointment(db, clinic_id, appointment_id)

    if appt.status != AppointmentStatus.SCHEDULED:
        raise ValidationError(f"Cannot check in: appointment status is {appt.status.value}")

    today = datetime.now(timezone.utc).date()
    if appt.scheduled_at.date() != today:
        raise ValidationError("Can only check in on the appointment day")

    appt.status = AppointmentStatus.CHECKED_IN
    await db.flush()
    await db.refresh(appt)
    logger.info("Appointment checked in", extra={"appointment_id": str(appointment_id)})
    return appt


async def cancel_appointment(
    db: AsyncSession, clinic_id: uuid.UUID, appointment_id: uuid.UUID
) -> Appointment:
    appt = await get_appointment(db, clinic_id, appointment_id)

    if appt.status in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED):
        raise ValidationError(f"Cannot cancel: appointment status is {appt.status.value}")

    appt.status = AppointmentStatus.CANCELLED
    await db.flush()
    await db.refresh(appt)
    logger.info("Appointment cancelled", extra={"appointment_id": str(appointment_id)})
    return appt


async def update_appointment_status(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    appointment_id: uuid.UUID,
    data: AppointmentUpdate,
) -> Appointment:
    appt = await get_appointment(db, clinic_id, appointment_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(appt, key, value)
    await db.flush()
    await db.refresh(appt)
    logger.info("Appointment updated", extra={"appointment_id": str(appointment_id)})
    return appt
