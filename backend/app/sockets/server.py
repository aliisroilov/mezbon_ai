"""Async Socket.IO server with JWT auth, room management, and ASGI mounting."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import socketio
from loguru import logger

from app.config import settings
from app.core.security import decode_token

# ---------------------------------------------------------------------------
# Module-level Socket.IO instance (imported by main.py and event modules)
# ---------------------------------------------------------------------------

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*" if settings.is_development else settings.cors_origins_list,
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)

# ---------------------------------------------------------------------------
# Session data store (sid → metadata)
# ---------------------------------------------------------------------------
# python-socketio has a built-in session per sid, but we keep a thin dict
# here for O(1) reverse lookups (device_id → sid, etc.).

_sid_meta: dict[str, dict[str, Any]] = {}


def get_sid_meta(sid: str) -> dict[str, Any] | None:
    """Return metadata dict for a connected socket, or None."""
    return _sid_meta.get(sid)


def find_sid_by_device(device_id: str) -> str | None:
    """Find the socket ID connected with a given device_id."""
    for sid, meta in _sid_meta.items():
        if meta.get("device_id") == device_id:
            return sid
    return None


# ---------------------------------------------------------------------------
# JWT authentication on connect
# ---------------------------------------------------------------------------

@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> bool | None:
    """Authenticate incoming connections via JWT or device token.

    Kiosks connect with:  auth = {"token": "<jwt>", "device_id": "..."}
    Admin connects with:  auth = {"token": "<jwt>"}

    On success the socket joins:
      - "clinic_{clinic_id}"             (all connections)
      - "device_{device_id}"            (kiosks only)
      - "admin_{clinic_id}"             (admin users only)
    """
    if auth is None:
        auth = {}

    token = auth.get("token") or _extract_token_from_headers(environ)
    if not token:
        logger.warning("Socket.IO connection rejected: no token", extra={"sid": sid})
        return False  # reject connection

    try:
        payload = decode_token(token)
    except ValueError as exc:
        logger.warning(
            "Socket.IO connection rejected: invalid token",
            extra={"sid": sid, "error": str(exc)},
        )
        return False

    clinic_id = payload.get("clinic_id")
    user_id = payload.get("sub")
    role = payload.get("role", "")

    if not clinic_id:
        logger.warning("Socket.IO connection rejected: no clinic_id in token", extra={"sid": sid})
        return False

    device_id = auth.get("device_id")

    # Persist metadata
    meta: dict[str, Any] = {
        "clinic_id": str(clinic_id),
        "user_id": str(user_id) if user_id else None,
        "role": role,
        "device_id": device_id,
    }
    _sid_meta[sid] = meta

    # Join rooms
    clinic_room = f"clinic_{clinic_id}"
    await sio.enter_room(sid, clinic_room)

    if device_id:
        device_room = f"device_{device_id}"
        await sio.enter_room(sid, device_room)
        logger.info(
            "Kiosk connected",
            extra={"sid": sid, "clinic_id": clinic_id, "device_id": device_id},
        )
    else:
        admin_room = f"admin_{clinic_id}"
        await sio.enter_room(sid, admin_room)
        logger.info(
            "Admin connected",
            extra={"sid": sid, "clinic_id": clinic_id, "role": role},
        )

    return True  # accept


@sio.event
async def disconnect(sid: str) -> None:
    meta = _sid_meta.pop(sid, None)
    if meta:
        logger.info(
            "Socket.IO client disconnected",
            extra={
                "sid": sid,
                "clinic_id": meta.get("clinic_id"),
                "device_id": meta.get("device_id"),
            },
        )
    else:
        logger.info("Socket.IO client disconnected", extra={"sid": sid})


# ---------------------------------------------------------------------------
# Emit helpers — used by kiosk_events / admin_events / services
# ---------------------------------------------------------------------------

async def emit_to_device(event: str, data: Any, device_id: str) -> None:
    """Emit an event to a specific kiosk device room."""
    room = f"device_{device_id}"
    text_preview = ""
    if isinstance(data, dict) and "text" in data:
        text_preview = str(data["text"])[:80]
    logger.info(
        f"emit_to_device: event={event}, room={room}",
        extra={"text_preview": text_preview, "device_id": device_id},
    )
    await sio.emit(event, data, room=room)


async def emit_to_clinic(event: str, data: Any, clinic_id: str | UUID) -> None:
    """Emit an event to everyone in a clinic."""
    await sio.emit(event, data, room=f"clinic_{clinic_id}")


async def emit_to_admin(event: str, data: Any, clinic_id: str | UUID) -> None:
    """Emit an event to all admin users of a clinic."""
    await sio.emit(event, data, room=f"admin_{clinic_id}")


# ---------------------------------------------------------------------------
# ASGI app factory
# ---------------------------------------------------------------------------

def create_sio_app(fastapi_app: Any) -> socketio.ASGIApp:
    """Wrap FastAPI app with Socket.IO ASGI app.

    Socket.IO will handle requests on ``/ws/socket.io`` and delegate the
    rest to FastAPI.
    """
    return socketio.ASGIApp(sio, fastapi_app, socketio_path="/ws/socket.io")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_token_from_headers(environ: dict) -> str | None:
    """Try to extract a Bearer token from the ASGI environ headers."""
    headers: dict[bytes, bytes] = dict(environ.get("asgi.scope", {}).get("headers", []))
    auth_header = headers.get(b"authorization", b"").decode()
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None
