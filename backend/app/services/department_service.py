import uuid

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.department import Department
from app.models.doctor import Doctor
from app.schemas.department import DepartmentCreate, DepartmentUpdate


async def list_departments(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    include_inactive: bool = False,
) -> list[dict]:
    stmt = (
        select(
            Department,
            func.count(Doctor.id).label("doctor_count"),
        )
        .outerjoin(Doctor, (Doctor.department_id == Department.id) & (Doctor.is_active.is_(True)))
        .where(Department.clinic_id == clinic_id)
        .group_by(Department.id)
        .order_by(Department.sort_order, Department.name)
    )
    if not include_inactive:
        stmt = stmt.where(Department.is_active.is_(True))

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {**row[0].__dict__, "doctor_count": row[1]}
        for row in rows
    ]


async def get_department(
    db: AsyncSession, clinic_id: uuid.UUID, department_id: uuid.UUID
) -> dict:
    stmt = (
        select(
            Department,
            func.count(Doctor.id).label("doctor_count"),
        )
        .outerjoin(Doctor, (Doctor.department_id == Department.id) & (Doctor.is_active.is_(True)))
        .where(Department.clinic_id == clinic_id, Department.id == department_id)
        .group_by(Department.id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        raise NotFoundError("Department not found")
    return {**row[0].__dict__, "doctor_count": row[1]}


async def create_department(
    db: AsyncSession, clinic_id: uuid.UUID, data: DepartmentCreate
) -> Department:
    dept = Department(clinic_id=clinic_id, **data.model_dump())
    db.add(dept)
    await db.flush()
    logger.info("Department created", extra={"department_id": str(dept.id), "clinic_id": str(clinic_id)})
    return dept


async def update_department(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    department_id: uuid.UUID,
    data: DepartmentUpdate,
) -> Department:
    result = await db.execute(
        select(Department).where(
            Department.clinic_id == clinic_id, Department.id == department_id
        )
    )
    dept = result.scalar_one_or_none()
    if dept is None:
        raise NotFoundError("Department not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(dept, key, value)
    await db.flush()
    await db.refresh(dept)
    logger.info("Department updated", extra={"department_id": str(department_id)})
    return dept


async def soft_delete_department(
    db: AsyncSession, clinic_id: uuid.UUID, department_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Department).where(
            Department.clinic_id == clinic_id, Department.id == department_id
        )
    )
    dept = result.scalar_one_or_none()
    if dept is None:
        raise NotFoundError("Department not found")
    dept.is_active = False
    await db.flush()
    logger.info("Department soft-deleted", extra={"department_id": str(department_id)})
