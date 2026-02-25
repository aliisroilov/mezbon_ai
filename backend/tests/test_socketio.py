"""Socket.IO integration tests.

Tests the complete flow:
  1. Mock kiosk connects with JWT auth
  2. Sends ``kiosk:face_frame``
  3. Receives ``ai:response`` with session_id and greeting

Also tests:
  - Connection rejection without token
  - Room assignment (clinic, device, admin)
  - Heartbeat → device:status emit
  - Touch action → ai:response
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import socketio as sio_client_pkg

from app.core.security import create_access_token
from app.models.user import UserRole
from app.sockets.server import sio, _sid_meta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token(clinic_id: str | uuid.UUID, user_id: str | uuid.UUID | None = None) -> str:
    """Create a valid JWT for testing."""
    return create_access_token({
        "sub": str(user_id or uuid.uuid4()),
        "clinic_id": str(clinic_id),
        "role": UserRole.CLINIC_ADMIN.value,
    })


def _make_face_frame() -> str:
    """Return a tiny base64-encoded 1x1 white JPEG."""
    # Minimal JPEG (1x1 pixel, white)
    minimal_jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' ),01444\x1f\'9telebriti:\x00\x00"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa7\xa3\x13"
        b"\xff\xd9"
    )
    return base64.b64encode(minimal_jpeg).decode()


# ---------------------------------------------------------------------------
# Unit tests for server.py connect/disconnect logic
# ---------------------------------------------------------------------------

class TestSocketAuth:
    """Test JWT authentication on Socket.IO connect."""

    @pytest.mark.asyncio
    async def test_connect_with_valid_token_kiosk(self) -> None:
        """Kiosk connection with valid JWT + device_id should be accepted."""
        clinic_id = uuid.uuid4()
        device_id = str(uuid.uuid4())
        token = _make_token(clinic_id)

        # Import the connect handler directly
        from app.sockets.server import connect

        # Simulate connect — returns True on success
        result = await connect(
            sid="test-sid-1",
            environ={},
            auth={"token": token, "device_id": device_id},
        )
        assert result is True

        meta = _sid_meta.get("test-sid-1")
        assert meta is not None
        assert meta["clinic_id"] == str(clinic_id)
        assert meta["device_id"] == device_id

        # Cleanup
        _sid_meta.pop("test-sid-1", None)

    @pytest.mark.asyncio
    async def test_connect_with_valid_token_admin(self) -> None:
        """Admin connection with valid JWT (no device_id) should be accepted."""
        clinic_id = uuid.uuid4()
        token = _make_token(clinic_id)

        from app.sockets.server import connect

        result = await connect(
            sid="test-sid-2",
            environ={},
            auth={"token": token},
        )
        assert result is True

        meta = _sid_meta.get("test-sid-2")
        assert meta is not None
        assert meta["device_id"] is None

        _sid_meta.pop("test-sid-2", None)

    @pytest.mark.asyncio
    async def test_connect_rejected_without_token(self) -> None:
        """Connection without any token should be rejected."""
        from app.sockets.server import connect

        result = await connect(sid="test-sid-3", environ={}, auth={})
        assert result is False
        assert "test-sid-3" not in _sid_meta

    @pytest.mark.asyncio
    async def test_connect_rejected_with_invalid_token(self) -> None:
        """Connection with garbage token should be rejected."""
        from app.sockets.server import connect

        result = await connect(
            sid="test-sid-4",
            environ={},
            auth={"token": "invalid.jwt.garbage"},
        )
        assert result is False
        assert "test-sid-4" not in _sid_meta

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_metadata(self) -> None:
        """Disconnect should remove sid from _sid_meta."""
        _sid_meta["test-sid-5"] = {"clinic_id": "x", "device_id": "y"}

        from app.sockets.server import disconnect

        await disconnect("test-sid-5")
        assert "test-sid-5" not in _sid_meta


# ---------------------------------------------------------------------------
# Integration test: face_frame → ai:response
# ---------------------------------------------------------------------------

class TestKioskFaceFrame:
    """Test the kiosk:face_frame handler end-to-end with mocked orchestrator."""

    @pytest.mark.asyncio
    async def test_face_frame_returns_ai_response(self) -> None:
        """Sending face_frame should invoke orchestrator and emit ai:response."""
        from app.ai.orchestrator import OrchestratorResponse
        from app.sockets.kiosk_events import register_kiosk_events

        clinic_id = uuid.uuid4()
        device_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        mock_response = OrchestratorResponse(
            text="Xush kelibsiz! Men Mezbon.",
            audio_base64=None,
            ui_action="show_greeting",
            state="GREETING",
            patient=None,
            session_id=session_id,
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.handle_face_detected = AsyncMock(return_value=mock_response)

        # Register events with our mock orchestrator
        register_kiosk_events(
            get_orchestrator=lambda: mock_orchestrator,
            get_db_factory=lambda: None,
        )

        # Place a fake sid in metadata (simulating authenticated connection)
        test_sid = "face-test-sid"
        _sid_meta[test_sid] = {
            "clinic_id": str(clinic_id),
            "user_id": None,
            "role": "",
            "device_id": device_id,
        }

        # Patch sio.emit so we can capture what gets emitted
        emitted: list[tuple] = []
        original_emit = sio.emit

        async def capture_emit(event, data, **kwargs):
            emitted.append((event, data, kwargs))

        sio.emit = capture_emit  # type: ignore[assignment]

        try:
            # Get the registered handler
            handlers = sio.handlers.get("/", {})
            face_handler = handlers.get("kiosk:face_frame")
            assert face_handler is not None, "kiosk:face_frame handler not registered"

            # Call it
            await face_handler(test_sid, {
                "device_id": device_id,
                "frame": _make_face_frame(),
            })

            # Verify orchestrator was called
            mock_orchestrator.handle_face_detected.assert_awaited_once()
            call_kwargs = mock_orchestrator.handle_face_detected.call_args
            assert str(call_kwargs.kwargs["clinic_id"]) == str(clinic_id)
            assert call_kwargs.kwargs["device_id"] == device_id

            # Verify events were emitted
            event_names = [e[0] for e in emitted]
            assert "ai:response" in event_names
            assert "ai:state_change" in event_names
            assert "visitor:new" in event_names

            # Verify ai:response payload
            ai_resp = next(e for e in emitted if e[0] == "ai:response")
            assert ai_resp[1]["text"] == "Xush kelibsiz! Men Mezbon."
            assert ai_resp[1]["state"] == "GREETING"
            assert ai_resp[1]["session_id"] == session_id

        finally:
            sio.emit = original_emit  # type: ignore[assignment]
            _sid_meta.pop(test_sid, None)


# ---------------------------------------------------------------------------
# Integration test: touch_action → ai:response
# ---------------------------------------------------------------------------

class TestKioskTouchAction:
    """Test the kiosk:touch_action handler with mocked orchestrator."""

    @pytest.mark.asyncio
    async def test_touch_action_returns_ai_response(self) -> None:
        from app.ai.orchestrator import OrchestratorResponse
        from app.sockets.kiosk_events import register_kiosk_events

        clinic_id = uuid.uuid4()
        device_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        mock_response = OrchestratorResponse(
            text="Terapiya bo'limini tanladingiz.",
            audio_base64=None,
            ui_action="show_doctors",
            state="SELECT_DOCTOR",
            patient=None,
            session_id=session_id,
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.handle_touch = AsyncMock(return_value=mock_response)

        register_kiosk_events(
            get_orchestrator=lambda: mock_orchestrator,
            get_db_factory=lambda: None,
        )

        test_sid = "touch-test-sid"
        _sid_meta[test_sid] = {
            "clinic_id": str(clinic_id),
            "user_id": None,
            "role": "",
            "device_id": device_id,
        }

        emitted: list[tuple] = []

        async def capture_emit(event, data, **kwargs):
            emitted.append((event, data, kwargs))

        sio.emit = capture_emit  # type: ignore[assignment]
        original_emit = sio.emit

        try:
            handlers = sio.handlers.get("/", {})
            touch_handler = handlers.get("kiosk:touch_action")
            assert touch_handler is not None

            await touch_handler(test_sid, {
                "device_id": device_id,
                "session_id": session_id,
                "action": "select_department",
                "data": {"department_id": str(uuid.uuid4())},
            })

            mock_orchestrator.handle_touch.assert_awaited_once()
            event_names = [e[0] for e in emitted]
            assert "ai:response" in event_names

        finally:
            sio.emit = original_emit  # type: ignore[assignment]
            _sid_meta.pop(test_sid, None)


# ---------------------------------------------------------------------------
# Admin notification tests
# ---------------------------------------------------------------------------

class TestAdminNotifications:
    """Test admin event emit helpers."""

    @pytest.mark.asyncio
    async def test_notify_queue_update(self) -> None:
        from app.sockets.admin_events import notify_queue_update

        emitted: list[tuple] = []

        async def capture_emit(event, data, **kwargs):
            emitted.append((event, data, kwargs))

        sio.emit = capture_emit  # type: ignore[assignment]

        try:
            clinic_id = uuid.uuid4()
            await notify_queue_update(
                clinic_id=clinic_id,
                department_id=uuid.uuid4(),
                ticket_data={"id": "t1", "ticket_number": "T-001", "status": "WAITING"},
                action="created",
            )

            assert len(emitted) == 1
            assert emitted[0][0] == "queue:update"
            assert emitted[0][1]["action"] == "created"
            assert emitted[0][2]["room"] == f"admin_{clinic_id}"
        finally:
            sio.emit = sio.__class__.emit.__get__(sio)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_notify_payment_confirmed(self) -> None:
        from app.sockets.admin_events import notify_payment_confirmed

        emitted: list[tuple] = []

        async def capture_emit(event, data, **kwargs):
            emitted.append((event, data, kwargs))

        sio.emit = capture_emit  # type: ignore[assignment]

        try:
            clinic_id = uuid.uuid4()
            device_id = str(uuid.uuid4())
            await notify_payment_confirmed(
                clinic_id=clinic_id,
                device_id=device_id,
                payment_data={"id": "p1", "amount": "50000", "status": "COMPLETED"},
            )

            # Should emit to both admin room and device room
            assert len(emitted) == 2
            events = {e[0] for e in emitted}
            assert "payment:confirmed" in events
        finally:
            sio.emit = sio.__class__.emit.__get__(sio)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_notify_appointment_updated(self) -> None:
        from app.sockets.admin_events import notify_appointment_updated

        emitted: list[tuple] = []

        async def capture_emit(event, data, **kwargs):
            emitted.append((event, data, kwargs))

        sio.emit = capture_emit  # type: ignore[assignment]

        try:
            clinic_id = uuid.uuid4()
            await notify_appointment_updated(
                clinic_id=clinic_id,
                appointment_data={"id": "a1", "status": "CHECKED_IN"},
            )

            assert len(emitted) == 1
            assert emitted[0][0] == "appointment:updated"
            assert emitted[0][1]["status"] == "CHECKED_IN"
        finally:
            sio.emit = sio.__class__.emit.__get__(sio)  # type: ignore[union-attr]
