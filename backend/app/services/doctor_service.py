import uuid
from datetime import date, datetime, time, timedelta, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor, DoctorSchedule
from app.schemas.doctor import DoctorCreate, DoctorUpdate, ScheduleCreate, TimeSlot


async def list_doctors(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    department_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[Doctor]:
    from sqlalchemy.orm import selectinload

    stmt = select(Doctor).where(Doctor.clinic_id == clinic_id)
    if department_id:
        stmt = stmt.where(Doctor.department_id == department_id)
    if not include_inactive:
        stmt = stmt.where(Doctor.is_active.is_(True))
    stmt = stmt.options(selectinload(Doctor.department), selectinload(Doctor.schedules))
    stmt = stmt.order_by(Doctor.full_name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_doctor(
    db: AsyncSession, clinic_id: uuid.UUID, doctor_id: uuid.UUID
) -> Doctor:
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Doctor)
        .where(Doctor.clinic_id == clinic_id, Doctor.id == doctor_id)
        .options(selectinload(Doctor.department), selectinload(Doctor.schedules))
    )
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise NotFoundError("Doctor not found")
    return doctor


async def create_doctor(
    db: AsyncSession, clinic_id: uuid.UUID, data: DoctorCreate
) -> Doctor:
    doctor = Doctor(clinic_id=clinic_id, **data.model_dump())
    db.add(doctor)
    await db.flush()
    logger.info("Doctor created", extra={"doctor_id": str(doctor.id), "clinic_id": str(clinic_id)})
    return doctor


async def update_doctor(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    doctor_id: uuid.UUID,
    data: DoctorUpdate,
) -> Doctor:
    doctor = await get_doctor(db, clinic_id, doctor_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(doctor, key, value)
    await db.flush()
    logger.info("Doctor updated", extra={"doctor_id": str(doctor_id)})
    return doctor


async def set_schedule(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    doctor_id: uuid.UUID,
    schedules: list[ScheduleCreate],
) -> list[DoctorSchedule]:
    await get_doctor(db, clinic_id, doctor_id)

    # Remove existing schedules
    existing = await db.execute(
        select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor_id)
    )
    for sched in existing.scalars().all():
        await db.delete(sched)

    # Create new schedules
    new_schedules = []
    for s in schedules:
        sched = DoctorSchedule(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            **s.model_dump(),
        )
        db.add(sched)
        new_schedules.append(sched)

    await db.flush()
    logger.info("Doctor schedule updated", extra={"doctor_id": str(doctor_id), "count": len(new_schedules)})
    return new_schedules


async def get_available_slots(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    doctor_id: uuid.UUID,
    target_date: date,
    slot_duration: int = 30,
) -> list[TimeSlot]:
    doctor = await get_doctor(db, clinic_id, doctor_id)

    weekday = target_date.weekday()  # 0=Monday
    result = await db.execute(
        select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor.id,
            DoctorSchedule.day_of_week == weekday,
            DoctorSchedule.is_active.is_(True),
        )
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        return []

    # Load existing appointments for that date (non-cancelled)
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    appt_result = await db.execute(
        select(Appointment).where(
            Appointment.clinic_id == clinic_id,
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_at >= day_start,
            Appointment.scheduled_at <= day_end,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
    )
    appointments = appt_result.scalars().all()

    # Build booked intervals
    booked: list[tuple[time, time]] = []
    for appt in appointments:
        appt_start = appt.scheduled_at.time()
        appt_end_dt = appt.scheduled_at + timedelta(minutes=appt.duration_minutes)
        booked.append((appt_start, appt_end_dt.time()))

    # Generate slots
    slots: list[TimeSlot] = []
    current = schedule.start_time
    slot_delta = timedelta(minutes=slot_duration)

    while True:
        slot_end_dt = datetime.combine(target_date, current) + slot_delta
        slot_end = slot_end_dt.time()

        if slot_end > schedule.end_time:
            break

        # Check break overlap
        in_break = False
        if schedule.break_start and schedule.break_end:
            if current < schedule.break_end and slot_end > schedule.break_start:
                in_break = True

        # Check appointment overlap
        is_booked = False
        for b_start, b_end in booked:
            if current < b_end and slot_end > b_start:
                is_booked = True
                break

        slots.append(TimeSlot(
            start_time=current,
            end_time=slot_end,
            is_available=not in_break and not is_booked,
        ))

        current = slot_end

    return slots
