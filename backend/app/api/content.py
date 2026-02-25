import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.services import content_service

router = APIRouter(prefix="/content", tags=["content"])


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    language: str = Field(default="uz", pattern=r"^(uz|ru|en)$")
    active_from: datetime
    active_to: datetime


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    body: str | None = None
    language: str | None = Field(default=None, pattern=r"^(uz|ru|en)$")
    active_from: datetime | None = None
    active_to: datetime | None = None
    is_active: bool | None = None


def _serialize(ann) -> dict:
    return {k: v for k, v in ann.__dict__.items() if not k.startswith("_")}


@router.get("/")
async def list_announcements(
    active_only: bool = False,
    language: str | None = None,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    anns = await content_service.list_announcements(
        db, clinic_id, active_only=active_only, language=language
    )
    return success_response([_serialize(a) for a in anns])


@router.post("/", status_code=201)
async def create_announcement(
    body: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    ann = await content_service.create_announcement(
        db, clinic_id,
        title=body.title,
        body=body.body,
        language=body.language,
        active_from=body.active_from,
        active_to=body.active_to,
    )
    return success_response(_serialize(ann))


@router.patch("/{announcement_id}")
async def update_announcement(
    announcement_id: uuid.UUID,
    body: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    ann = await content_service.update_announcement(
        db, clinic_id, announcement_id, body.model_dump(exclude_unset=True)
    )
    return success_response(_serialize(ann))


@router.delete("/{announcement_id}", status_code=204)
async def delete_announcement(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> None:
    await content_service.delete_announcement(db, clinic_id, announcement_id)
