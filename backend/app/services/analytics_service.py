import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.payment import Payment, PaymentTransactionStatus
from app.models.queue import QueueStatus, QueueTicket
from app.models.visit_log import VisitLog


async def dashboard_stats(
    db: AsyncSession, clinic_id: uuid.UUID, target_date: date
) -> dict:
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    visitors = await db.execute(
        select(func.count(VisitLog.id)).where(
            VisitLog.clinic_id == clinic_id,
            VisitLog.started_at >= day_start,
            VisitLog.started_at <= day_end,
        )
    )

    appointments = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_at >= day_start,
            Appointment.scheduled_at <= day_end,
        )
    )

    payments = await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.clinic_id == clinic_id,
            Payment.created_at >= day_start,
            Payment.created_at <= day_end,
            Payment.status == PaymentTransactionStatus.COMPLETED,
        )
    )

    avg_wait = await db.execute(
        select(func.avg(QueueTicket.estimated_wait_minutes)).where(
            QueueTicket.clinic_id == clinic_id,
            QueueTicket.created_at >= day_start,
            QueueTicket.created_at <= day_end,
            QueueTicket.status == QueueStatus.COMPLETED,
        )
    )

    return {
        "date": target_date.isoformat(),
        "visitors_count": visitors.scalar() or 0,
        "appointments_count": appointments.scalar() or 0,
        "revenue": float(payments.scalar() or 0),
        "avg_wait_minutes": float(avg_wait.scalar() or 0),
    }


async def visitor_trends(
    db: AsyncSession, clinic_id: uuid.UUID, days: int = 30
) -> list[dict]:
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", VisitLog.started_at).label("day"),
            func.count(VisitLog.id).label("count"),
        )
        .where(
            VisitLog.clinic_id == clinic_id,
            VisitLog.started_at >= start_date,
        )
        .group_by("day")
        .order_by("day")
    )
    return [{"date": str(row[0].date()), "count": row[1]} for row in result.all()]


async def intent_distribution(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> list[dict]:
    start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)

    result = await db.execute(
        select(
            VisitLog.intent,
            func.count(VisitLog.id).label("count"),
        )
        .where(
            VisitLog.clinic_id == clinic_id,
            VisitLog.started_at >= start,
            VisitLog.started_at <= end,
            VisitLog.intent.isnot(None),
        )
        .group_by(VisitLog.intent)
        .order_by(func.count(VisitLog.id).desc())
    )
    return [{"intent": row[0], "count": row[1]} for row in result.all()]
