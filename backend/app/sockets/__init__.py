"""Socket.IO real-time layer.

Exports:
  - ``sio``              — the module-level AsyncServer instance
  - ``create_sio_app``   — ASGI app factory (wraps FastAPI)
  - ``setup_socket_events`` — call once at startup to register all handlers

Emit helpers (for use in services):
  - ``emit_to_device``
  - ``emit_to_admin``
  - ``emit_to_clinic``

Admin notification helpers:
  - ``notify_queue_update``
  - ``notify_device_status``
  - ``notify_payment_confirmed``
  - ``notify_appointment_updated``
  - ``notify_visitor_new``
"""

from app.sockets.server import (
    sio,
    create_sio_app,
    emit_to_admin,
    emit_to_clinic,
    emit_to_device,
)
from app.sockets.admin_events import (
    notify_appointment_updated,
    notify_device_status,
    notify_payment_confirmed,
    notify_queue_update,
    notify_visitor_new,
)
from app.sockets.kiosk_events import register_kiosk_events


def setup_socket_events(
    get_orchestrator: object,
    get_db_factory: object,
) -> None:
    """Register all Socket.IO event handlers.

    Call this once during application startup (in ``main.py`` lifespan).

    Parameters
    ----------
    get_orchestrator:
        A callable returning the ``Orchestrator`` instance.
    get_db_factory:
        A callable returning the ``async_sessionmaker``.
    """
    register_kiosk_events(
        get_orchestrator=get_orchestrator,
        get_db_factory=get_db_factory,
    )


__all__ = [
    "sio",
    "create_sio_app",
    "setup_socket_events",
    "emit_to_admin",
    "emit_to_clinic",
    "emit_to_device",
    "notify_appointment_updated",
    "notify_device_status",
    "notify_payment_confirmed",
    "notify_queue_update",
    "notify_visitor_new",
]
