import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.redis import get_redis


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    RATE_LIMIT = 100
    WINDOW_SECONDS = 60

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}"

        redis = get_redis()
        try:
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, self.WINDOW_SECONDS)

            if current > self.RATE_LIMIT:
                return Response(
                    content='{"success":false,"data":null,"error":{"code":"RATE_LIMITED","message":"Too many requests"}}',
                    status_code=429,
                    media_type="application/json",
                )
        except Exception:
            pass  # fail open — don't block requests if Redis is down
        finally:
            await redis.aclose()

        return await call_next(request)
