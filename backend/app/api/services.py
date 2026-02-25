import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.services import service_service

router = APIRouter(prefix="/services", tags=["services"])


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    department_id: uuid.UUID
    description: str = ""
    duration_minutes: int = Field(default=30, ge=5, le=480)
    price_uzs: Decimal = Field(default=Decimal("0"), ge=0)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    price_uzs: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


@router.get("/")
async def list_services(
    department_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    services = await service_service.list_services(db, clinic_id, department_id=department_id)
    return success_response([
        {k: v for k, v in s.__dict__.items() if not k.startswith("_")}
        for s in services
    ])


@router.get("/{service_id}")
async def get_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    svc = await service_service.get_service(db, clinic_id, service_id)
    return success_response({k: v for k, v in svc.__dict__.items() if not k.startswith("_")})


@router.post("/", status_code=201)
async def create_service(
    body: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    svc = await service_service.create_service(
        db, clinic_id,
        name=body.name,
        department_id=body.department_id,
        description=body.description,
        duration_minutes=body.duration_minutes,
        price_uzs=float(body.price_uzs),
    )
    return success_response({k: v for k, v in svc.__dict__.items() if not k.startswith("_")})


@router.patch("/{service_id}")
async def update_service(
    service_id: uuid.UUID,
    body: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    updates = body.model_dump(exclude_unset=True)
    if "price_uzs" in updates and updates["price_uzs"] is not None:
        updates["price_uzs"] = float(updates["price_uzs"])
    svc = await service_service.update_service(db, clinic_id, service_id, updates)
    return success_response({k: v for k, v in svc.__dict__.items() if not k.startswith("_")})
