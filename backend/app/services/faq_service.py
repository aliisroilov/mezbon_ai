import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.faq import FAQ
from app.schemas.faq import FAQCreate, FAQUpdate


async def list_faqs(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    language: str | None = None,
    department_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[FAQ]:
    stmt = select(FAQ).where(FAQ.clinic_id == clinic_id)
    if language:
        stmt = stmt.where(FAQ.language == language)
    if department_id:
        stmt = stmt.where(FAQ.department_id == department_id)
    if not include_inactive:
        stmt = stmt.where(FAQ.is_active.is_(True))
    stmt = stmt.order_by(FAQ.sort_order, FAQ.created_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_faq(
    db: AsyncSession, clinic_id: uuid.UUID, faq_id: uuid.UUID
) -> FAQ:
    result = await db.execute(
        select(FAQ).where(FAQ.clinic_id == clinic_id, FAQ.id == faq_id)
    )
    faq = result.scalar_one_or_none()
    if faq is None:
        raise NotFoundError("FAQ not found")
    return faq


async def create_faq(
    db: AsyncSession, clinic_id: uuid.UUID, data: FAQCreate
) -> FAQ:
    faq = FAQ(clinic_id=clinic_id, **data.model_dump())
    db.add(faq)
    await db.flush()
    logger.info("FAQ created", extra={"faq_id": str(faq.id), "clinic_id": str(clinic_id)})
    return faq


async def update_faq(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    faq_id: uuid.UUID,
    data: FAQUpdate,
) -> FAQ:
    faq = await get_faq(db, clinic_id, faq_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(faq, key, value)
    await db.flush()
    logger.info("FAQ updated", extra={"faq_id": str(faq_id)})
    return faq


async def delete_faq(
    db: AsyncSession, clinic_id: uuid.UUID, faq_id: uuid.UUID
) -> None:
    faq = await get_faq(db, clinic_id, faq_id)
    faq.is_active = False
    await db.flush()
    logger.info("FAQ soft-deleted", extra={"faq_id": str(faq_id)})
