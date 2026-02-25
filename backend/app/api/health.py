from fastapi import APIRouter
from loguru import logger

from app.config import settings
from app.core.response import success_response

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:  # type: ignore[type-arg]
    """Health check with AI service status."""
    services: dict[str, str] = {"api": "ok"}

    # Gemini
    if settings.GEMINI_API_KEY:
        services["gemini"] = "ok"
    else:
        services["gemini"] = "no_api_key"

    # InsightFace
    try:
        from app.ai.face_service import face_service
        services["insightface"] = "ok" if face_service._initialized else "not_initialized"
    except Exception:
        services["insightface"] = "unavailable"

    # Muxlisa
    if settings.MUXLISA_MOCK:
        services["muxlisa"] = "mock"
    elif settings.MUXLISA_API_KEY:
        services["muxlisa"] = "ok"
    else:
        services["muxlisa"] = "no_api_key"

    # Database
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception:
        services["database"] = "unavailable"

    # Redis
    try:
        from app.core.redis import get_redis
        redis = get_redis()
        await redis.ping()
        services["redis"] = "ok"
    except Exception:
        services["redis"] = "unavailable"

    return success_response(services)
