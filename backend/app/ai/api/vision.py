"""Vision API routes — face detection, identification, and registration."""

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.face_service import face_service
from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.schemas.ai import FaceDetectionResponse, FaceIdentifyResponse

router = APIRouter(prefix="/ai", tags=["AI Vision"])


@router.post("/detect")
async def detect_faces(
    image: UploadFile = File(..., description="Image file (JPEG/PNG)"),
    _user=Depends(get_current_user),
) -> dict:
    """Detect all faces in an uploaded image.

    Returns bounding boxes and confidence scores for each detected face.
    """
    image_bytes = await image.read()
    result = await face_service.detect_faces(image_bytes)
    return success_response(result.model_dump())


@router.post("/identify")
async def identify_face(
    image: UploadFile = File(..., description="Image file (JPEG/PNG)"),
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
) -> dict:
    """Detect face in image and match against registered patients.

    Returns the matched patient info or null if no match found.
    """
    image_bytes = await image.read()
    result = await face_service.identify(image_bytes, clinic_id, db)

    if result is None:
        return success_response(None)
    return success_response(result.model_dump())


@router.post("/register-face")
async def register_face(
    image: UploadFile = File(..., description="Image file with patient face"),
    patient_id: uuid.UUID = Form(..., description="UUID of the patient"),
    device_id: str = Form(..., description="Kiosk device identifier"),
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
) -> dict:
    """Register a face embedding for a patient.

    Requires active FACE_RECOGNITION consent for the patient.
    The consent must be granted before calling this endpoint.
    """
    image_bytes = await image.read()
    await face_service.register_face(
        image_bytes=image_bytes,
        patient_id=patient_id,
        clinic_id=clinic_id,
        device_id=device_id,
        db=db,
    )
    return success_response({"message": "Face registered successfully", "patient_id": str(patient_id)})
