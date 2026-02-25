import uuid
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.device import Device, DeviceHeartbeat, DeviceStatus
from app.schemas.device import DeviceRegister, DeviceUpdate, HeartbeatData


async def list_devices(
    db: AsyncSession, clinic_id: uuid.UUID
) -> list[dict]:
    result = await db.execute(
        select(Device).where(Device.clinic_id == clinic_id).order_by(Device.name)
    )
    devices = result.scalars().all()
    now = datetime.now(timezone.utc)
    return [
        {
            **{k: v for k, v in d.__dict__.items() if not k.startswith("_")},
            "is_healthy": d.last_heartbeat is not None
            and (now - d.last_heartbeat) < timedelta(minutes=5),
        }
        for d in devices
    ]


async def get_device(
    db: AsyncSession, clinic_id: uuid.UUID, device_id: uuid.UUID
) -> dict:
    result = await db.execute(
        select(Device).where(Device.clinic_id == clinic_id, Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if device is None:
        raise NotFoundError("Device not found")
    now = datetime.now(timezone.utc)
    return {
        **{k: v for k, v in device.__dict__.items() if not k.startswith("_")},
        "is_healthy": device.last_heartbeat is not None
        and (now - device.last_heartbeat) < timedelta(minutes=5),
    }


async def register_device(
    db: AsyncSession, clinic_id: uuid.UUID, data: DeviceRegister
) -> Device:
    existing = await db.execute(
        select(Device).where(Device.serial_number == data.serial_number)
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Device with this serial number already exists")

    device = Device(
        clinic_id=clinic_id,
        serial_number=data.serial_number,
        name=data.name,
        location_description=data.location_description,
        config=data.config,
    )
    db.add(device)
    await db.flush()
    logger.info("Device registered", extra={"device_id": str(device.id), "serial": data.serial_number})
    return device


async def update_device(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    device_id: uuid.UUID,
    data: DeviceUpdate,
) -> Device:
    result = await db.execute(
        select(Device).where(Device.clinic_id == clinic_id, Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if device is None:
        raise NotFoundError("Device not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(device, key, value)
    await db.flush()
    logger.info("Device updated", extra={"device_id": str(device_id)})
    return device


async def record_heartbeat(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    device_id: uuid.UUID,
    data: HeartbeatData,
) -> DeviceHeartbeat:
    result = await db.execute(
        select(Device).where(Device.clinic_id == clinic_id, Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if device is None:
        raise NotFoundError("Device not found")

    now = datetime.now(timezone.utc)
    device.last_heartbeat = now
    device.status = DeviceStatus.ONLINE

    heartbeat = DeviceHeartbeat(
        clinic_id=clinic_id,
        device_id=device_id,
        timestamp=now,
        uptime_seconds=data.uptime_seconds,
        cpu_usage=data.cpu_usage,
        memory_usage=data.memory_usage,
        errors=data.errors,
    )
    db.add(heartbeat)
    await db.flush()
    return heartbeat
