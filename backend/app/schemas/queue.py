import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.queue import QueueStatus


class QueueTicketCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    department_id: uuid.UUID
    doctor_id: uuid.UUID | None = None


class QueueTicketRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID | None
    department_id: uuid.UUID
    doctor_id: uuid.UUID | None
    ticket_number: str
    status: QueueStatus
    estimated_wait_minutes: int
    called_at: datetime | None = None
    completed_at: datetime | None = None
    department_name: str = ""
    created_at: datetime
    updated_at: datetime


class QueueStats(BaseModel):
    department_id: uuid.UUID
    department_name: str = ""
    waiting_count: int = 0
    avg_wait_minutes: float = 0.0
