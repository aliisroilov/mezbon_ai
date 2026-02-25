from redis.asyncio import ConnectionPool, Redis

from app.config import settings

pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
)


def get_redis() -> Redis:  # type: ignore[type-arg]
    return Redis(connection_pool=pool)
