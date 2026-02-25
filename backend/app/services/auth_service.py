import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User


async def authenticate(
    db: AsyncSession, email: str, password: str
) -> dict[str, str]:
    result = await db.execute(
        select(User).where(User.email == email, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise ForbiddenError("Invalid email or password")

    token_data = {"sub": str(user.id), "clinic_id": str(user.clinic_id), "role": user.role.value}
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)

    logger.info("User authenticated", extra={"user_id": str(user.id), "clinic_id": str(user.clinic_id)})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def refresh_tokens(
    db: AsyncSession, refresh_token: str
) -> dict[str, str]:
    try:
        payload = decode_token(refresh_token, refresh=True)
    except ValueError as e:
        raise ForbiddenError(str(e)) from e

    token_type = payload.get("type")
    if token_type != "refresh":
        raise ForbiddenError("Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise ForbiddenError("Invalid token payload")

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(str(user_id)), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    token_data = {"sub": str(user.id), "clinic_id": str(user.clinic_id), "role": user.role.value}
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)

    logger.info("Tokens refreshed", extra={"user_id": str(user.id)})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def create_user(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    email: str,
    password: str,
    full_name: str,
    role: str,
) -> User:
    user = User(
        clinic_id=clinic_id,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    await db.flush()
    logger.info("User created", extra={"user_id": str(user.id), "clinic_id": str(clinic_id)})
    return user
