import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.content import Announcement


async def list_announcements(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    active_only: bool = False,
    language: str | None = None,
) -> list[Announcement]:
    stmt = select(Announcement).where(Announcement.clinic_id == clinic_id)
    if language:
        stmt = stmt.where(Announcement.language == language)
    if active_only:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(
            Announcement.is_active.is_(True),
            Announcement.active_from <= now,
            Announcement.active_to >= now,
        )
    stmt = stmt.order_by(Announcement.active_from.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_announcement(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    title: str,
    body: str,
    language: str,
    active_from: datetime,
    active_to: datetime,
) -> Announcement:
    ann = Announcement(
        clinic_id=clinic_id,
        title=title,
        body=body,
        language=language,
        active_from=active_from,
        active_to=active_to,
    )
    db.add(ann)
    await db.flush()
    logger.info("Announcement created", extra={"announcement_id": str(ann.id)})
    return ann


async def update_announcement(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    announcement_id: uuid.UUID,
    updates: dict,
) -> Announcement:
    result = await db.execute(
        select(Announcement).where(
            Announcement.clinic_id == clinic_id, Announcement.id == announcement_id
        )
    )
    ann = result.scalar_one_or_none()
    if ann is None:
        raise NotFoundError("Announcement not found")
    for key, value in updates.items():
        setattr(ann, key, value)
    await db.flush()
    logger.info("Announcement updated", extra={"announcement_id": str(announcement_id)})
    return ann


async def delete_announcement(
    db: AsyncSession, clinic_id: uuid.UUID, announcement_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Announcement).where(
            Announcement.clinic_id == clinic_id, Announcement.id == announcement_id
        )
    )
    ann = result.scalar_one_or_none()
    if ann is None:
        raise NotFoundError("Announcement not found")
    ann.is_active = False
    await db.flush()
    logger.info("Announcement soft-deleted", extra={"announcement_id": str(announcement_id)})
