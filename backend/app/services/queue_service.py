import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.queue import QueueStatus, QueueTicket
from app.schemas.queue import QueueTicketCreate


async def list_tickets(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    department_id: uuid.UUID | None = None,
    status: QueueStatus | None = None,
) -> list[QueueTicket]:
    stmt = select(QueueTicket).where(QueueTicket.clinic_id == clinic_id)
    if department_id:
        stmt = stmt.where(QueueTicket.department_id == department_id)
    if status:
        stmt = stmt.where(QueueTicket.status == status)
    stmt = stmt.order_by(QueueTicket.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def issue_ticket(
    db: AsyncSession, clinic_id: uuid.UUID, data: QueueTicketCreate
) -> QueueTicket:
    # Get department for prefix
    dept_result = await db.execute(
        select(Department).where(
            Department.clinic_id == clinic_id, Department.id == data.department_id
        )
    )
    dept = dept_result.scalar_one_or_none()
    if dept is None:
        raise NotFoundError("Department not found")

    prefix = dept.name[0].upper() if dept.name else "X"

    # Count today's tickets for this department to generate number
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count(QueueTicket.id)).where(
            QueueTicket.clinic_id == clinic_id,
            QueueTicket.department_id == data.department_id,
            QueueTicket.created_at >= today_start,
        )
    )
    count = count_result.scalar() or 0
    ticket_number = f"{prefix}-{count + 1:03d}"

    # Estimate wait: count waiting tickets * avg 15 min
    waiting_result = await db.execute(
        select(func.count(QueueTicket.id)).where(
            QueueTicket.clinic_id == clinic_id,
            QueueTicket.department_id == data.department_id,
            QueueTicket.status == QueueStatus.WAITING,
        )
    )
    waiting_count = waiting_result.scalar() or 0
    estimated_wait = waiting_count * 15

    ticket = QueueTicket(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        department_id=data.department_id,
        doctor_id=data.doctor_id,
        ticket_number=ticket_number,
        estimated_wait_minutes=estimated_wait,
    )
    db.add(ticket)
    await db.flush()
    logger.info("Queue ticket issued", extra={"ticket": ticket_number, "clinic_id": str(clinic_id)})

    # Auto-print queue ticket
    try:
        from app.services.printer_service import get_printer_service

        printer = get_printer_service()

        patient_name = "Guest"
        if data.patient_id:
            patient_result = await db.execute(
                select(Patient).where(Patient.id == data.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient:
                patient_name = patient.full_name

        doctor_name = None
        if data.doctor_id:
            doctor_result = await db.execute(
                select(Doctor).where(Doctor.id == data.doctor_id)
            )
            doctor = doctor_result.scalar_one_or_none()
            if doctor:
                doctor_name = doctor.full_name

        printer.print_queue_ticket(
            ticket_number=ticket_number,
            patient_name=patient_name,
            department_name=dept.name,
            floor=dept.floor or 1,
            room=dept.room_number or "101",
            estimated_wait=estimated_wait,
            doctor_name=doctor_name,
        )
    except Exception as e:
        logger.warning(f"Failed to auto-print ticket: {e}")

    return ticket


async def call_next(
    db: AsyncSession, clinic_id: uuid.UUID, department_id: uuid.UUID
) -> QueueTicket:
    result = await db.execute(
        select(QueueTicket)
        .where(
            QueueTicket.clinic_id == clinic_id,
            QueueTicket.department_id == department_id,
            QueueTicket.status == QueueStatus.WAITING,
        )
        .order_by(QueueTicket.created_at.asc())
        .limit(1)
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise NotFoundError("No waiting tickets in this department")

    ticket.status = QueueStatus.IN_PROGRESS
    ticket.called_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ticket)
    logger.info("Queue ticket called", extra={"ticket": ticket.ticket_number})
    return ticket


async def complete_ticket(
    db: AsyncSession, clinic_id: uuid.UUID, ticket_id: uuid.UUID
) -> QueueTicket:
    result = await db.execute(
        select(QueueTicket).where(
            QueueTicket.clinic_id == clinic_id, QueueTicket.id == ticket_id
        )
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise NotFoundError("Ticket not found")

    if ticket.status != QueueStatus.IN_PROGRESS:
        raise ValidationError("Can only complete tickets that are IN_PROGRESS")

    ticket.status = QueueStatus.COMPLETED
    ticket.completed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ticket)
    logger.info("Queue ticket completed", extra={"ticket": ticket.ticket_number})
    return ticket


async def get_queue_stats(
    db: AsyncSession, clinic_id: uuid.UUID
) -> list[dict]:
    result = await db.execute(
        select(
            QueueTicket.department_id,
            func.count(QueueTicket.id).filter(QueueTicket.status == QueueStatus.WAITING).label("waiting_count"),
            func.avg(QueueTicket.estimated_wait_minutes).filter(
                QueueTicket.status == QueueStatus.WAITING
            ).label("avg_wait"),
        )
        .where(QueueTicket.clinic_id == clinic_id)
        .group_by(QueueTicket.department_id)
    )
    stats = []
    for row in result.all():
        dept_result = await db.execute(
            select(Department.name).where(Department.id == row[0])
        )
        dept_name = dept_result.scalar() or ""
        stats.append({
            "department_id": row[0],
            "department_name": dept_name,
            "waiting_count": row[1] or 0,
            "avg_wait_minutes": float(row[2] or 0),
        })
    return stats
