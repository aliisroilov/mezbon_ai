import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantModel


class DeviceStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


class Device(TenantModel):
    __tablename__ = "devices"
    __table_args__ = (
        Index(
            "ix_devices_clinic_serial",
            "clinic_id",
            "serial_number",
            unique=True,
        ),
    )

    serial_number: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    location_description: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, name="device_status_enum"),
        default=DeviceStatus.OFFLINE,
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    heartbeats: Mapped[list["DeviceHeartbeat"]] = relationship(
        back_populates="device", lazy="selectin", cascade="all, delete-orphan"
    )


class DeviceHeartbeat(TenantModel):
    __tablename__ = "device_heartbeats"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE")
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    cpu_usage: Mapped[float] = mapped_column(Float, default=0.0)
    memory_usage: Mapped[float] = mapped_column(Float, default=0.0)
    errors: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="heartbeats")
