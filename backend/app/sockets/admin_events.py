"""Backend → admin dashboard Socket.IO event emitters.

These functions are called from the service layer (or directly from socket
handlers) to push real-time updates to admin dashboard clients.

Events emitted:
  - queue:update          — ticket created / called / completed
  - device:status         — heartbeat received or device went offline
  - payment:confirmed     — payment webhook processed
  - appointment:updated   — appointment status changed
  - visitor:new           — new visitor session started on a kiosk
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger

from app.sockets.server import emit_to_admin, emit_to_device


async def notify_queue_update(
    clinic_id: str | UUID,
    department_id: str | UUID,
    ticket_data: dict[str, Any],
    action: str = "update",
) -> None:
    """Emit ``queue:update`` to admin room when a queue ticket changes.

    Parameters
    ----------
    clinic_id:
        Clinic whose admin room should receive the event.
    department_id:
        Department the ticket belongs to.
    ticket_data:
        Serialised ticket (id, ticket_number, status, etc.).
    action:
        One of ``"created"`` | ``"called"`` | ``"completed"`` | ``"no_show"``.
    """
    await emit_to_admin("queue:update", {
        "action": action,
        "department_id": str(department_id),
        "ticket": ticket_data,
    }, clinic_id)
    logger.debug(
        "Emitted queue:update",
        extra={"clinic_id": str(clinic_id), "action": action},
    )


async def notify_device_status(
    clinic_id: str | UUID,
    device_id: str | UUID,
    status: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Emit ``device:status`` to admin room after heartbeat or offline detection.

    Parameters
    ----------
    status:
        ``"ONLINE"`` | ``"OFFLINE"`` | ``"MAINTENANCE"``
    details:
        Optional CPU/memory/uptime snapshot.
    """
    payload: dict[str, Any] = {
        "device_id": str(device_id),
        "status": status,
    }
    if details:
        payload.update(details)

    await emit_to_admin("device:status", payload, clinic_id)
    logger.debug(
        "Emitted device:status",
        extra={"clinic_id": str(clinic_id), "device_id": str(device_id), "status": status},
    )


async def notify_payment_confirmed(
    clinic_id: str | UUID,
    device_id: str | None,
    payment_data: dict[str, Any],
) -> None:
    """Emit ``payment:confirmed`` to both kiosk device and admin room.

    Called after a payment webhook marks a payment as COMPLETED.
    """
    await emit_to_admin("payment:confirmed", payment_data, clinic_id)

    if device_id:
        await emit_to_device("payment:confirmed", payment_data, device_id)

    logger.debug(
        "Emitted payment:confirmed",
        extra={"clinic_id": str(clinic_id), "payment_id": payment_data.get("id")},
    )


async def notify_appointment_updated(
    clinic_id: str | UUID,
    appointment_data: dict[str, Any],
) -> None:
    """Emit ``appointment:updated`` to admin room on status change."""
    await emit_to_admin("appointment:updated", appointment_data, clinic_id)
    logger.debug(
        "Emitted appointment:updated",
        extra={
            "clinic_id": str(clinic_id),
            "appointment_id": appointment_data.get("id"),
            "status": appointment_data.get("status"),
        },
    )


async def notify_visitor_new(
    clinic_id: str | UUID,
    device_id: str,
    session_id: str,
    patient: dict[str, Any] | None = None,
    state: str = "DETECTED",
) -> None:
    """Emit ``visitor:new`` to admin room when a visitor session starts."""
    await emit_to_admin("visitor:new", {
        "device_id": device_id,
        "session_id": session_id,
        "patient": patient,
        "state": state,
    }, clinic_id)
    logger.debug(
        "Emitted visitor:new",
        extra={"clinic_id": str(clinic_id), "session_id": session_id},
    )
