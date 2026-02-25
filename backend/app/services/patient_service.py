import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_field, encrypt_field
from app.core.exceptions import NotFoundError
from app.integrations.crm.operations import sync_contact_create
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


async def _get_clinic_settings(db: AsyncSession, clinic_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(Clinic.settings).where(Clinic.id == clinic_id))
    return result.scalar_one_or_none()


def _decrypt_patient(patient: Patient) -> dict:
    return {
        "id": patient.id,
        "clinic_id": patient.clinic_id,
        "full_name": decrypt_field(patient.full_name_enc),
        "phone": decrypt_field(patient.phone_enc),
        "date_of_birth": decrypt_field(patient.dob_enc) if patient.dob_enc else None,
        "language_preference": patient.language_preference,
        "has_face_embedding": patient.face_embedding_enc is not None,
        "created_at": patient.created_at,
        "updated_at": patient.updated_at,
    }


async def list_patients(
    db: AsyncSession, clinic_id: uuid.UUID
) -> list[dict]:
    result = await db.execute(
        select(Patient).where(Patient.clinic_id == clinic_id).order_by(Patient.created_at.desc())
    )
    return [_decrypt_patient(p) for p in result.scalars().all()]


async def get_patient(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> dict:
    result = await db.execute(
        select(Patient).where(Patient.clinic_id == clinic_id, Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found")
    return _decrypt_patient(patient)


async def register_patient(
    db: AsyncSession, clinic_id: uuid.UUID, data: PatientCreate
) -> dict:
    patient = Patient(
        clinic_id=clinic_id,
        full_name_enc=encrypt_field(data.full_name),
        phone_enc=encrypt_field(data.phone),
        dob_enc=encrypt_field(str(data.date_of_birth)) if data.date_of_birth else "",
        language_preference=data.language_preference,
    )
    db.add(patient)
    await db.flush()
    logger.info("Patient registered", extra={"patient_id": str(patient.id), "clinic_id": str(clinic_id)})

    # CRM sync — fire-and-forget, never crashes registration
    decrypted = _decrypt_patient(patient)
    clinic_settings = await _get_clinic_settings(db, clinic_id)
    await sync_contact_create(
        db,
        clinic_id,
        clinic_settings,
        patient.id,
        {
            "full_name": data.full_name,
            "phone": data.phone,
            "date_of_birth": str(data.date_of_birth) if data.date_of_birth else None,
            "language_preference": data.language_preference,
        },
    )

    return decrypted


async def update_patient(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PatientUpdate,
) -> dict:
    result = await db.execute(
        select(Patient).where(Patient.clinic_id == clinic_id, Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found")

    updates = data.model_dump(exclude_unset=True)
    if "full_name" in updates:
        patient.full_name_enc = encrypt_field(updates["full_name"])
    if "phone" in updates:
        patient.phone_enc = encrypt_field(updates["phone"])
    if "date_of_birth" in updates:
        patient.dob_enc = encrypt_field(str(updates["date_of_birth"])) if updates["date_of_birth"] else ""
    if "language_preference" in updates:
        patient.language_preference = updates["language_preference"]

    await db.flush()
    await db.refresh(patient)
    logger.info("Patient updated", extra={"patient_id": str(patient_id)})
    return _decrypt_patient(patient)


async def lookup_by_phone(
    db: AsyncSession, clinic_id: uuid.UUID, phone: str
) -> dict | None:
    # AES-GCM encryption is non-deterministic (random nonce), so we must scan and decrypt
    result = await db.execute(
        select(Patient).where(Patient.clinic_id == clinic_id)
    )
    for patient in result.scalars().all():
        try:
            decrypted = decrypt_field(patient.phone_enc)
            if decrypted == phone:
                return _decrypt_patient(patient)
        except Exception:
            continue
    return None
