import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.schemas.patient import PatientCreate, PatientLookup, PatientRead, PatientUpdate
from app.services import patient_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/")
async def list_patients(
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    patients = await patient_service.list_patients(db, clinic_id)
    return success_response([PatientRead(**p).model_dump(mode="json") for p in patients])


@router.get("/{patient_id}")
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    patient = await patient_service.get_patient(db, clinic_id, patient_id)
    return success_response(PatientRead(**patient).model_dump(mode="json"))


@router.post("/", status_code=201)
async def register_patient(
    body: PatientCreate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    patient = await patient_service.register_patient(db, clinic_id, body)
    return success_response(PatientRead(**patient).model_dump(mode="json"))


@router.patch("/{patient_id}")
async def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    patient = await patient_service.update_patient(db, clinic_id, patient_id, body)
    return success_response(PatientRead(**patient).model_dump(mode="json"))


@router.post("/lookup")
async def lookup_patient(
    body: PatientLookup,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    patient = await patient_service.lookup_by_phone(db, clinic_id, body.phone)
    if patient is None:
        return success_response(None)
    return success_response(PatientRead(**patient).model_dump(mode="json"))
