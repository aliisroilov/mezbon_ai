import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.device import DeviceStatus


class DeviceRegister(BaseModel):
    serial_number: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    location_description: str = Field(default="", max_length=500)
    config: dict[str, Any] | None = None


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location_description: str | None = Field(default=None, max_length=500)
    config: dict[str, Any] | None = None
    status: DeviceStatus | None = None


class DeviceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    clinic_id: uuid.UUID
    serial_number: str
    name: str
    location_description: str
    status: DeviceStatus
    config: dict[str, Any] | None
    last_heartbeat: datetime | None
    is_healthy: bool = False
    created_at: datetime
    updated_at: datetime


class HeartbeatData(BaseModel):
    uptime_seconds: int = Field(default=0, ge=0)
    cpu_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    memory_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    errors: dict[str, Any] | None = None
