"""Redis-backed visitor session state machine."""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from loguru import logger
from redis.asyncio import Redis

from app.core.redis import get_redis

# Session TTL in seconds (15 minutes)
_SESSION_TTL = 900


class SessionState(str, Enum):
    """All possible visitor states."""

    IDLE = "IDLE"
    DETECTED = "DETECTED"
    GREETING = "GREETING"
    INTENT_DISCOVERY = "INTENT_DISCOVERY"

    # Appointment booking flow
    APPOINTMENT_BOOKING = "APPOINTMENT_BOOKING"
    SELECT_DEPARTMENT = "SELECT_DEPARTMENT"
    SELECT_DOCTOR = "SELECT_DOCTOR"
    SELECT_TIMESLOT = "SELECT_TIMESLOT"
    CONFIRM_BOOKING = "CONFIRM_BOOKING"
    BOOKING_PAYMENT = "BOOKING_PAYMENT"
    BOOKING_COMPLETE = "BOOKING_COMPLETE"

    # Check-in flow
    CHECK_IN = "CHECK_IN"
    VERIFY_IDENTITY = "VERIFY_IDENTITY"
    CONFIRM_APPOINTMENT = "CONFIRM_APPOINTMENT"
    ISSUE_QUEUE_TICKET = "ISSUE_QUEUE_TICKET"
    ROUTE_TO_DEPARTMENT = "ROUTE_TO_DEPARTMENT"

    # Information flow
    INFORMATION_INQUIRY = "INFORMATION_INQUIRY"
    FAQ_RESPONSE = "FAQ_RESPONSE"
    SHOW_DEPARTMENT_INFO = "SHOW_DEPARTMENT_INFO"
    SHOW_DOCTOR_PROFILE = "SHOW_DOCTOR_PROFILE"

    # Payment flow
    PAYMENT = "PAYMENT"
    SELECT_PAYMENT_METHOD = "SELECT_PAYMENT_METHOD"
    PROCESS_PAYMENT = "PROCESS_PAYMENT"
    PAYMENT_RECEIPT = "PAYMENT_RECEIPT"

    # Complaint / handoff
    COMPLAINT = "COMPLAINT"
    RECORD_FEEDBACK = "RECORD_FEEDBACK"
    HAND_OFF = "HAND_OFF"

    # End
    FAREWELL = "FAREWELL"


# Valid transitions between states
VALID_TRANSITIONS: dict[SessionState, list[SessionState]] = {
    SessionState.IDLE: [SessionState.DETECTED],
    SessionState.DETECTED: [SessionState.GREETING],
    SessionState.GREETING: [SessionState.INTENT_DISCOVERY],
    SessionState.INTENT_DISCOVERY: [
        SessionState.APPOINTMENT_BOOKING,
        SessionState.CHECK_IN,
        SessionState.INFORMATION_INQUIRY,
        SessionState.PAYMENT,
        SessionState.COMPLAINT,
        SessionState.HAND_OFF,
        SessionState.FAREWELL,
    ],
    # Appointment booking flow
    SessionState.APPOINTMENT_BOOKING: [SessionState.SELECT_DEPARTMENT],
    SessionState.SELECT_DEPARTMENT: [SessionState.SELECT_DOCTOR],
    SessionState.SELECT_DOCTOR: [SessionState.SELECT_TIMESLOT],
    SessionState.SELECT_TIMESLOT: [SessionState.CONFIRM_BOOKING],
    SessionState.CONFIRM_BOOKING: [
        SessionState.BOOKING_PAYMENT,
        SessionState.BOOKING_COMPLETE,
    ],
    SessionState.BOOKING_PAYMENT: [SessionState.BOOKING_COMPLETE],
    SessionState.BOOKING_COMPLETE: [SessionState.FAREWELL, SessionState.INTENT_DISCOVERY],
    # Check-in flow
    SessionState.CHECK_IN: [SessionState.VERIFY_IDENTITY],
    SessionState.VERIFY_IDENTITY: [SessionState.CONFIRM_APPOINTMENT],
    SessionState.CONFIRM_APPOINTMENT: [SessionState.ISSUE_QUEUE_TICKET],
    SessionState.ISSUE_QUEUE_TICKET: [SessionState.ROUTE_TO_DEPARTMENT],
    SessionState.ROUTE_TO_DEPARTMENT: [SessionState.FAREWELL, SessionState.INTENT_DISCOVERY],
    # Information flow
    SessionState.INFORMATION_INQUIRY: [
        SessionState.FAQ_RESPONSE,
        SessionState.SHOW_DEPARTMENT_INFO,
        SessionState.SHOW_DOCTOR_PROFILE,
    ],
    SessionState.FAQ_RESPONSE: [SessionState.INTENT_DISCOVERY, SessionState.FAREWELL],
    SessionState.SHOW_DEPARTMENT_INFO: [
        SessionState.INTENT_DISCOVERY,
        SessionState.APPOINTMENT_BOOKING,
        SessionState.FAREWELL,
    ],
    SessionState.SHOW_DOCTOR_PROFILE: [
        SessionState.INTENT_DISCOVERY,
        SessionState.APPOINTMENT_BOOKING,
        SessionState.FAREWELL,
    ],
    # Payment flow
    SessionState.PAYMENT: [SessionState.SELECT_PAYMENT_METHOD],
    SessionState.SELECT_PAYMENT_METHOD: [SessionState.PROCESS_PAYMENT],
    SessionState.PROCESS_PAYMENT: [SessionState.PAYMENT_RECEIPT],
    SessionState.PAYMENT_RECEIPT: [SessionState.FAREWELL, SessionState.INTENT_DISCOVERY],
    # Complaint / handoff
    SessionState.COMPLAINT: [SessionState.RECORD_FEEDBACK],
    SessionState.RECORD_FEEDBACK: [SessionState.FAREWELL, SessionState.HAND_OFF],
    SessionState.HAND_OFF: [SessionState.FAREWELL],
    # Farewell loops back to idle
    SessionState.FAREWELL: [SessionState.IDLE],
}

# States that are always reachable from any state
_ALWAYS_REACHABLE = {SessionState.FAREWELL, SessionState.HAND_OFF, SessionState.INTENT_DISCOVERY}


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


class SessionManager:
    """Manages visitor session state in Redis."""

    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis

    @property
    def redis(self) -> Redis:
        if self._redis is not None:
            return self._redis
        return get_redis()

    async def create_session(
        self, device_id: str, clinic_id: str | uuid.UUID
    ) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        data = {
            "state": SessionState.IDLE.value,
            "device_id": device_id,
            "clinic_id": str(clinic_id),
            "context": {},
            "language": "uz",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.redis.set(
            _session_key(session_id), json.dumps(data), ex=_SESSION_TTL
        )
        logger.info(
            "Session created",
            extra={"session_id": session_id, "device_id": device_id},
        )
        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Return the full session dict or None if expired / missing."""
        raw = await self.redis.get(_session_key(session_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def get_state(self, session_id: str) -> SessionState | None:
        """Return the current state or None if session does not exist."""
        session = await self.get_session(session_id)
        if session is None:
            return None
        return SessionState(session["state"])

    async def get_context(self, session_id: str) -> dict[str, Any]:
        """Return the session context dict (empty dict if missing)."""
        session = await self.get_session(session_id)
        if session is None:
            return {}
        return session.get("context", {})

    async def set_context(self, session_id: str, key: str, value: Any) -> None:
        """Set a single key in the session context."""
        session = await self.get_session(session_id)
        if session is None:
            return
        session.setdefault("context", {})[key] = value
        await self.redis.set(
            _session_key(session_id), json.dumps(session), ex=_SESSION_TTL
        )

    async def set_language(self, session_id: str, language: str) -> None:
        """Update the session language preference."""
        session = await self.get_session(session_id)
        if session is None:
            return
        session["language"] = language
        await self.redis.set(
            _session_key(session_id), json.dumps(session), ex=_SESSION_TTL
        )

    async def get_language(self, session_id: str) -> str:
        """Return the session language (defaults to 'uz')."""
        session = await self.get_session(session_id)
        if session is None:
            return "uz"
        return session.get("language", "uz")

    async def transition(
        self, session_id: str, new_state: SessionState
    ) -> bool:
        """Validate and execute a state transition.

        Returns True if the transition was valid and applied.
        """
        session = await self.get_session(session_id)
        if session is None:
            logger.warning(
                "Transition failed — session not found",
                extra={"session_id": session_id},
            )
            return False

        current = SessionState(session["state"])

        # Check if transition is valid
        if not self._is_valid_transition(current, new_state):
            logger.warning(
                "Invalid state transition",
                extra={
                    "session_id": session_id,
                    "from": current.value,
                    "to": new_state.value,
                },
            )
            return False

        session["state"] = new_state.value
        await self.redis.set(
            _session_key(session_id), json.dumps(session), ex=_SESSION_TTL
        )
        logger.info(
            "State transition",
            extra={
                "session_id": session_id,
                "from": current.value,
                "to": new_state.value,
            },
        )
        return True

    async def reset(self, session_id: str) -> None:
        """Delete a session from Redis."""
        await self.redis.delete(_session_key(session_id))
        logger.info("Session reset", extra={"session_id": session_id})

    async def touch(self, session_id: str) -> None:
        """Reset the TTL for a session (activity detected)."""
        key = _session_key(session_id)
        exists = await self.redis.expire(key, _SESSION_TTL)
        if not exists:
            logger.debug(
                "Touch failed — session not found",
                extra={"session_id": session_id},
            )

    @staticmethod
    def _is_valid_transition(
        current: SessionState, target: SessionState
    ) -> bool:
        """Check whether a transition from *current* to *target* is allowed."""
        # FAREWELL and HAND_OFF are always reachable
        if target in _ALWAYS_REACHABLE:
            return True
        allowed = VALID_TRANSITIONS.get(current, [])
        return target in allowed


# Module-level singleton
session_manager = SessionManager()
