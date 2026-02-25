import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    floor: int | None = None
    room_number: str | None = Field(default=None, max_length=50)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    floor: int | None = None
    room_number: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
    sort_order: int | None = None


class DepartmentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    clinic_id: uuid.UUID
    name: str
    description: str
    floor: int | None
    room_number: str | None
    is_active: bool
    sort_order: int
    doctor_count: int = 0
    created_at: datetime
    updated_at: datetime
