from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.response import success_response
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RefreshRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tokens = await auth_service.authenticate(db, body.email, body.password)
    return success_response(tokens)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tokens = await auth_service.refresh_tokens(db, body.refresh_token)
    return success_response(tokens)


@router.post("/logout")
async def logout() -> dict:
    # Stateless JWT — client discards tokens.
    # Future: add token to Redis blocklist.
    return success_response({"message": "Logged out"})


# ---------------------------------------------------------------------------
# Device (kiosk) authentication — issues a JWT for kiosk devices
# ---------------------------------------------------------------------------


class DeviceAuthRequest(BaseModel):
    device_id: str
    clinic_id: str


@router.post("/device")
async def device_auth(body: DeviceAuthRequest) -> dict:
    """Issue a JWT for a kiosk device.

    In production this should verify the device against the DB (serial number,
    pre-registered devices list, etc.).  For dev/demo we issue a token for any
    device_id + clinic_id pair.
    """
    token = create_access_token({
        "sub": f"device:{body.device_id}",
        "clinic_id": body.clinic_id,
        "role": "kiosk",
        "device_id": body.device_id,
    })
    return success_response({"access_token": token, "token_type": "bearer"})
