import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.appointment import AppointmentStatus, PaymentStatus


class AppointmentCreate(BaseModel):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    service_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=5, le=480)
    notes: str = Field(default="", max_length=2000)


class AppointmentUpdate(BaseModel):
    status: AppointmentStatus | None = None
    payment_status: PaymentStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)
    scheduled_at: datetime | None = None


class AppointmentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    service_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    status: AppointmentStatus
    payment_status: PaymentStatus
    notes: str
    doctor_name: str = ""
    service_name: str = ""
    patient_name: str = ""
    created_at: datetime
    updated_at: datetime


class CheckInRequest(BaseModel):
    patient_id: uuid.UUID | None = None
    appointment_id: uuid.UUID | None = None
