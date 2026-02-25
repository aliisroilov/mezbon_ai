import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("")
async def list_departments(
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    departments = await department_service.list_departments(db, clinic_id)
    return success_response([DepartmentRead(**d).model_dump(mode="json") for d in departments])


@router.get("/{department_id}")
async def get_department(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    dept = await department_service.get_department(db, clinic_id, department_id)
    return success_response(DepartmentRead(**dept).model_dump(mode="json"))


@router.post("", status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    dept = await department_service.create_department(db, clinic_id, body)
    data = {**dept.__dict__, "doctor_count": 0}
    return success_response(DepartmentRead(**data).model_dump(mode="json"))


@router.patch("/{department_id}")
async def update_department(
    department_id: uuid.UUID,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    dept = await department_service.update_department(db, clinic_id, department_id, body)
    data = {**dept.__dict__, "doctor_count": 0}
    return success_response(DepartmentRead(**data).model_dump(mode="json"))


@router.delete("/{department_id}", status_code=204)
async def delete_department(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> None:
    await department_service.soft_delete_department(db, clinic_id, department_id)
