import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.schemas.doctor import (
    AvailableSlotsResponse,
    DoctorCreate,
    DoctorRead,
    DoctorUpdate,
    ScheduleCreate,
    ScheduleRead,
)
from app.services import doctor_service

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("")
async def list_doctors(
    department_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    doctors = await doctor_service.list_doctors(db, clinic_id, department_id=department_id)
    result = []
    for d in doctors:
        dept_name = d.department.name if d.department else ""
        attrs = {k: v for k, v in d.__dict__.items() if not k.startswith("_") and k not in ("department", "schedules", "services")}
        result.append(DoctorRead(
            **attrs,
            department_name=dept_name,
            schedules=[ScheduleRead.model_validate(s) for s in d.schedules],
        ).model_dump(mode="json"))
    return success_response(result)


@router.get("/{doctor_id}")
async def get_doctor(
    doctor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    d = await doctor_service.get_doctor(db, clinic_id, doctor_id)
    dept_name = d.department.name if d.department else ""
    attrs = {k: v for k, v in d.__dict__.items() if not k.startswith("_") and k not in ("department", "schedules", "services")}
    data = DoctorRead(
        **attrs,
        department_name=dept_name,
        schedules=[ScheduleRead.model_validate(s) for s in d.schedules],
    ).model_dump(mode="json")
    return success_response(data)


@router.post("", status_code=201)
async def create_doctor(
    body: DoctorCreate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    d = await doctor_service.create_doctor(db, clinic_id, body)
    data = DoctorRead(
        **{k: v for k, v in d.__dict__.items() if not k.startswith("_")},
    ).model_dump(mode="json")
    return success_response(data)


@router.patch("/{doctor_id}")
async def update_doctor(
    doctor_id: uuid.UUID,
    body: DoctorUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    d = await doctor_service.update_doctor(db, clinic_id, doctor_id, body)
    data = DoctorRead(
        **{k: v for k, v in d.__dict__.items() if not k.startswith("_")},
    ).model_dump(mode="json")
    return success_response(data)


@router.get("/{doctor_id}/slots")
async def get_available_slots(
    doctor_id: uuid.UUID,
    target_date: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    slots = await doctor_service.get_available_slots(db, clinic_id, doctor_id, target_date)
    response = AvailableSlotsResponse(
        date=target_date,
        doctor_id=doctor_id,
        slots=slots,
    )
    return success_response(response.model_dump(mode="json"))


@router.put("/{doctor_id}/schedule")
async def set_schedule(
    doctor_id: uuid.UUID,
    body: list[ScheduleCreate],
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    schedules = await doctor_service.set_schedule(db, clinic_id, doctor_id, body)
    return success_response([ScheduleRead.model_validate(s).model_dump(mode="json") for s in schedules])
