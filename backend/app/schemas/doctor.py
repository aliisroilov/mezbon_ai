import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday .. 6=Sunday")
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None


class ScheduleRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    doctor_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    break_start: time | None
    break_end: time | None
    is_active: bool


class DoctorCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    specialty: str = Field(default="", max_length=255)
    department_id: uuid.UUID
    bio: str = Field(default="", max_length=2000)
    photo_url: str | None = Field(default=None, max_length=500)


class DoctorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    specialty: str | None = Field(default=None, max_length=255)
    department_id: uuid.UUID | None = None
    bio: str | None = Field(default=None, max_length=2000)
    photo_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class DoctorRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    clinic_id: uuid.UUID
    department_id: uuid.UUID
    full_name: str
    specialty: str
    bio: str
    photo_url: str | None
    is_active: bool
    department_name: str = ""
    next_available_slot: datetime | None = None
    schedules: list[ScheduleRead] = []
    created_at: datetime
    updated_at: datetime


class TimeSlot(BaseModel):
    start_time: time
    end_time: time
    is_available: bool = True


class AvailableSlotsResponse(BaseModel):
    date: date
    doctor_id: uuid.UUID
    slots: list[TimeSlot]
