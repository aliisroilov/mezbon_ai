import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.schemas.faq import FAQCreate, FAQRead, FAQUpdate
from app.services import faq_service

router = APIRouter(prefix="/faq", tags=["faq"])


@router.get("/")
async def list_faqs(
    language: str | None = None,
    department_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    faqs = await faq_service.list_faqs(
        db, clinic_id, language=language, department_id=department_id
    )
    return success_response([FAQRead.model_validate(f).model_dump(mode="json") for f in faqs])


@router.get("/{faq_id}")
async def get_faq(
    faq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    faq = await faq_service.get_faq(db, clinic_id, faq_id)
    return success_response(FAQRead.model_validate(faq).model_dump(mode="json"))


@router.post("/", status_code=201)
async def create_faq(
    body: FAQCreate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    faq = await faq_service.create_faq(db, clinic_id, body)
    return success_response(FAQRead.model_validate(faq).model_dump(mode="json"))


@router.patch("/{faq_id}")
async def update_faq(
    faq_id: uuid.UUID,
    body: FAQUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    faq = await faq_service.update_faq(db, clinic_id, faq_id, body)
    return success_response(FAQRead.model_validate(faq).model_dump(mode="json"))


@router.delete("/{faq_id}", status_code=204)
async def delete_faq(
    faq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> None:
    await faq_service.delete_faq(db, clinic_id, faq_id)
