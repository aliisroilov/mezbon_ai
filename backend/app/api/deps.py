from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import decode_token


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@dataclass
class DeviceIdentity:
    """Lightweight identity for kiosk device tokens (no DB user)."""

    device_id: str
    clinic_id: UUID
    role: str = "kiosk"


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if not authorization.startswith("Bearer "):
        raise ForbiddenError("Invalid authorization header")

    token = authorization[7:]
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise ForbiddenError(str(e)) from e

    user_id = payload.get("sub")
    if user_id is None:
        raise ForbiddenError("Invalid token payload")

    # Device tokens have sub like "device:kiosk-001" — skip DB lookup
    if isinstance(user_id, str) and user_id.startswith("device:"):
        clinic_id = payload.get("clinic_id")
        if not clinic_id:
            raise ForbiddenError("Device token missing clinic_id")
        return DeviceIdentity(
            device_id=payload.get("device_id", user_id),
            clinic_id=UUID(str(clinic_id)),
        )

    # Regular user token — look up in DB
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    return user


async def get_clinic_id(current_user: Any = Depends(get_current_user)) -> UUID:
    return current_user.clinic_id  # type: ignore[no-any-return]


def require_role(*roles: str):  # type: ignore[no-untyped-def]
    async def _check(current_user: Any = Depends(get_current_user)) -> Any:
        if current_user.role not in roles:
            raise ForbiddenError(f"Role {current_user.role} not authorized")
        return current_user

    return _check
