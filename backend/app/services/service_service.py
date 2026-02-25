import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.service import Service


async def list_services(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    department_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[Service]:
    stmt = select(Service).where(Service.clinic_id == clinic_id)
    if department_id:
        stmt = stmt.where(Service.department_id == department_id)
    if not include_inactive:
        stmt = stmt.where(Service.is_active.is_(True))
    stmt = stmt.order_by(Service.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_service(
    db: AsyncSession, clinic_id: uuid.UUID, service_id: uuid.UUID
) -> Service:
    result = await db.execute(
        select(Service).where(Service.clinic_id == clinic_id, Service.id == service_id)
    )
    svc = result.scalar_one_or_none()
    if svc is None:
        raise NotFoundError("Service not found")
    return svc


async def create_service(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    name: str,
    department_id: uuid.UUID,
    description: str = "",
    duration_minutes: int = 30,
    price_uzs: float = 0,
) -> Service:
    svc = Service(
        clinic_id=clinic_id,
        department_id=department_id,
        name=name,
        description=description,
        duration_minutes=duration_minutes,
        price_uzs=price_uzs,
    )
    db.add(svc)
    await db.flush()
    logger.info("Service created", extra={"service_id": str(svc.id), "clinic_id": str(clinic_id)})
    return svc


async def update_service(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    service_id: uuid.UUID,
    updates: dict,
) -> Service:
    svc = await get_service(db, clinic_id, service_id)
    for key, value in updates.items():
        setattr(svc, key, value)
    await db.flush()
    logger.info("Service updated", extra={"service_id": str(service_id)})
    return svc
