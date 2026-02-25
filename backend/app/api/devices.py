import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.schemas.device import DeviceRead, DeviceRegister, DeviceUpdate, HeartbeatData
from app.services import device_service
from app.sockets import notify_device_status

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/")
async def list_devices(
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    devices = await device_service.list_devices(db, clinic_id)
    return success_response([DeviceRead(**d).model_dump(mode="json") for d in devices])


@router.get("/{device_id}")
async def get_device(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    device = await device_service.get_device(db, clinic_id, device_id)
    return success_response(DeviceRead(**device).model_dump(mode="json"))


@router.post("/", status_code=201)
async def register_device(
    body: DeviceRegister,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    device = await device_service.register_device(db, clinic_id, body)
    data = {
        **{k: v for k, v in device.__dict__.items() if not k.startswith("_")},
        "is_healthy": False,
    }
    return success_response(DeviceRead(**data).model_dump(mode="json"))


@router.patch("/{device_id}")
async def update_device(
    device_id: uuid.UUID,
    body: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    device = await device_service.update_device(db, clinic_id, device_id, body)
    data = {
        **{k: v for k, v in device.__dict__.items() if not k.startswith("_")},
        "is_healthy": False,
    }
    return success_response(DeviceRead(**data).model_dump(mode="json"))


@router.post("/{device_id}/heartbeat")
async def record_heartbeat(
    device_id: uuid.UUID,
    body: HeartbeatData,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    heartbeat = await device_service.record_heartbeat(db, clinic_id, device_id, body)
    await notify_device_status(
        clinic_id=clinic_id,
        device_id=device_id,
        status="ONLINE",
        details={
            "cpu_usage": body.cpu_usage,
            "memory_usage": body.memory_usage,
            "uptime_seconds": body.uptime_seconds,
        },
    )
    return success_response({"status": "ok"})
