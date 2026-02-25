"""Tests for the Redis-backed visitor session state machine."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from redis.asyncio import Redis

from app.ai.session_manager import (
    VALID_TRANSITIONS,
    SessionManager,
    SessionState,
    _ALWAYS_REACHABLE,
    _SESSION_TTL,
    _session_key,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_session_data(
    state: str = "IDLE",
    device_id: str = "kiosk-01",
    clinic_id: str = "00000000-0000-0000-0000-000000000001",
    language: str = "uz",
    context: dict | None = None,
) -> str:
    return json.dumps(
        {
            "state": state,
            "device_id": device_id,
            "clinic_id": clinic_id,
            "context": context or {},
            "language": language,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )


def _mock_redis() -> AsyncMock:
    redis = AsyncMock(spec=Redis)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.expire = AsyncMock(return_value=True)
    return redis


# ---------------------------------------------------------------------------
# SessionState enum
# ---------------------------------------------------------------------------
class TestSessionStateEnum:
    def test_all_states_are_strings(self) -> None:
        for s in SessionState:
            assert isinstance(s, str)
            assert isinstance(s.value, str)

    def test_idle_exists(self) -> None:
        assert SessionState.IDLE == "IDLE"

    def test_farewell_exists(self) -> None:
        assert SessionState.FAREWELL == "FAREWELL"

    def test_booking_flow_states(self) -> None:
        flow = [
            SessionState.APPOINTMENT_BOOKING,
            SessionState.SELECT_DEPARTMENT,
            SessionState.SELECT_DOCTOR,
            SessionState.SELECT_TIMESLOT,
            SessionState.CONFIRM_BOOKING,
            SessionState.BOOKING_PAYMENT,
            SessionState.BOOKING_COMPLETE,
        ]
        for s in flow:
            assert s in SessionState

    def test_all_states_have_transitions(self) -> None:
        """Every state should appear as a key in VALID_TRANSITIONS."""
        for s in SessionState:
            assert s in VALID_TRANSITIONS, f"{s} missing from VALID_TRANSITIONS"


# ---------------------------------------------------------------------------
# Valid transitions table
# ---------------------------------------------------------------------------
class TestTransitionTable:
    def test_idle_only_goes_to_detected(self) -> None:
        assert VALID_TRANSITIONS[SessionState.IDLE] == [SessionState.DETECTED]

    def test_intent_discovery_branches(self) -> None:
        targets = VALID_TRANSITIONS[SessionState.INTENT_DISCOVERY]
        assert SessionState.APPOINTMENT_BOOKING in targets
        assert SessionState.CHECK_IN in targets
        assert SessionState.INFORMATION_INQUIRY in targets
        assert SessionState.PAYMENT in targets
        assert SessionState.COMPLAINT in targets

    def test_farewell_goes_to_idle(self) -> None:
        assert SessionState.IDLE in VALID_TRANSITIONS[SessionState.FAREWELL]

    def test_no_state_transitions_to_itself(self) -> None:
        for state, targets in VALID_TRANSITIONS.items():
            assert state not in targets, f"{state} has self-transition"


# ---------------------------------------------------------------------------
# _is_valid_transition
# ---------------------------------------------------------------------------
class TestIsValidTransition:
    def test_valid_forward(self) -> None:
        assert SessionManager._is_valid_transition(
            SessionState.IDLE, SessionState.DETECTED
        )

    def test_invalid_skip(self) -> None:
        assert not SessionManager._is_valid_transition(
            SessionState.IDLE, SessionState.GREETING
        )

    def test_farewell_always_reachable(self) -> None:
        for state in SessionState:
            assert SessionManager._is_valid_transition(
                state, SessionState.FAREWELL
            ), f"FAREWELL not reachable from {state}"

    def test_hand_off_always_reachable(self) -> None:
        for state in SessionState:
            assert SessionManager._is_valid_transition(
                state, SessionState.HAND_OFF
            ), f"HAND_OFF not reachable from {state}"

    def test_invalid_backward(self) -> None:
        assert not SessionManager._is_valid_transition(
            SessionState.GREETING, SessionState.IDLE
        )

    def test_booking_flow_valid(self) -> None:
        flow = [
            (SessionState.APPOINTMENT_BOOKING, SessionState.SELECT_DEPARTMENT),
            (SessionState.SELECT_DEPARTMENT, SessionState.SELECT_DOCTOR),
            (SessionState.SELECT_DOCTOR, SessionState.SELECT_TIMESLOT),
            (SessionState.SELECT_TIMESLOT, SessionState.CONFIRM_BOOKING),
            (SessionState.CONFIRM_BOOKING, SessionState.BOOKING_PAYMENT),
            (SessionState.BOOKING_PAYMENT, SessionState.BOOKING_COMPLETE),
        ]
        for src, dst in flow:
            assert SessionManager._is_valid_transition(src, dst), f"{src} → {dst}"


# ---------------------------------------------------------------------------
# SessionManager.create_session
# ---------------------------------------------------------------------------
class TestCreateSession:
    async def test_creates_session_with_uuid(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        sid = await mgr.create_session("kiosk-01", "clinic-uuid")
        assert len(sid) == 36  # UUID format
        redis.set.assert_called_once()

    async def test_session_stored_with_ttl(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        sid = await mgr.create_session("kiosk-01", "clinic-uuid")
        call_args = redis.set.call_args
        assert call_args.kwargs.get("ex") == _SESSION_TTL

    async def test_initial_state_is_idle(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        await mgr.create_session("kiosk-01", "clinic-uuid")
        stored = json.loads(redis.set.call_args.args[1])
        assert stored["state"] == "IDLE"

    async def test_initial_language_is_uz(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        await mgr.create_session("kiosk-01", "clinic-uuid")
        stored = json.loads(redis.set.call_args.args[1])
        assert stored["language"] == "uz"


# ---------------------------------------------------------------------------
# SessionManager.get_session / get_state
# ---------------------------------------------------------------------------
class TestGetSession:
    async def test_returns_none_for_missing(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        assert await mgr.get_session("nonexistent") is None

    async def test_returns_parsed_dict(self) -> None:
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=_make_session_data("GREETING"))
        mgr = SessionManager(redis=redis)
        session = await mgr.get_session("sid-1")
        assert session is not None
        assert session["state"] == "GREETING"

    async def test_get_state_returns_enum(self) -> None:
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=_make_session_data("DETECTED"))
        mgr = SessionManager(redis=redis)
        state = await mgr.get_state("sid-1")
        assert state == SessionState.DETECTED

    async def test_get_state_none_when_missing(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        assert await mgr.get_state("missing") is None


# ---------------------------------------------------------------------------
# SessionManager.set_context / get_context
# ---------------------------------------------------------------------------
class TestContext:
    async def test_set_and_get_context(self) -> None:
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=_make_session_data())
        mgr = SessionManager(redis=redis)

        await mgr.set_context("sid-1", "patient_id", "p-123")
        # set was called to persist
        redis.set.assert_called_once()
        stored = json.loads(redis.set.call_args.args[1])
        assert stored["context"]["patient_id"] == "p-123"

    async def test_get_context_empty_when_missing(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        ctx = await mgr.get_context("nonexistent")
        assert ctx == {}

    async def test_get_context_preserves_existing(self) -> None:
        data = _make_session_data(context={"foo": "bar"})
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=data)
        mgr = SessionManager(redis=redis)
        ctx = await mgr.get_context("sid-1")
        assert ctx == {"foo": "bar"}


# ---------------------------------------------------------------------------
# SessionManager.set_language / get_language
# ---------------------------------------------------------------------------
class TestLanguage:
    async def test_set_language(self) -> None:
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=_make_session_data())
        mgr = SessionManager(redis=redis)
        await mgr.set_language("sid-1", "ru")
        stored = json.loads(redis.set.call_args.args[1])
        assert stored["language"] == "ru"

    async def test_get_language_default(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        lang = await mgr.get_language("nonexistent")
        assert lang == "uz"

    async def test_get_language_from_session(self) -> None:
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=_make_session_data(language="en"))
        mgr = SessionManager(redis=redis)
        assert await mgr.get_language("sid-1") == "en"


# ---------------------------------------------------------------------------
# SessionManager.transition
# ---------------------------------------------------------------------------
class TestTransition:
    async def test_valid_transition_succeeds(self) -> None:
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=_make_session_data("IDLE"))
        mgr = SessionManager(redis=redis)
        result = await mgr.transition("sid-1", SessionState.DETECTED)
        assert result is True
        stored = json.loads(redis.set.call_args.args[1])
        assert stored["state"] == "DETECTED"

    async def test_invalid_transition_fails(self) -> None:
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=_make_session_data("IDLE"))
        mgr = SessionManager(redis=redis)
        result = await mgr.transition("sid-1", SessionState.GREETING)
        assert result is False
        redis.set.assert_not_called()

    async def test_transition_resets_ttl(self) -> None:
        redis = _mock_redis()
        redis.get = AsyncMock(return_value=_make_session_data("IDLE"))
        mgr = SessionManager(redis=redis)
        await mgr.transition("sid-1", SessionState.DETECTED)
        call_args = redis.set.call_args
        assert call_args.kwargs.get("ex") == _SESSION_TTL

    async def test_farewell_from_any_state(self) -> None:
        for state in SessionState:
            if state == SessionState.FAREWELL:
                continue
            redis = _mock_redis()
            redis.get = AsyncMock(return_value=_make_session_data(state.value))
            mgr = SessionManager(redis=redis)
            result = await mgr.transition("sid-1", SessionState.FAREWELL)
            assert result is True, f"FAREWELL failed from {state}"

    async def test_missing_session_returns_false(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        result = await mgr.transition("nonexistent", SessionState.DETECTED)
        assert result is False

    async def test_full_booking_flow(self) -> None:
        """Walk through the entire booking flow."""
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)

        flow = [
            ("IDLE", SessionState.DETECTED),
            ("DETECTED", SessionState.GREETING),
            ("GREETING", SessionState.INTENT_DISCOVERY),
            ("INTENT_DISCOVERY", SessionState.APPOINTMENT_BOOKING),
            ("APPOINTMENT_BOOKING", SessionState.SELECT_DEPARTMENT),
            ("SELECT_DEPARTMENT", SessionState.SELECT_DOCTOR),
            ("SELECT_DOCTOR", SessionState.SELECT_TIMESLOT),
            ("SELECT_TIMESLOT", SessionState.CONFIRM_BOOKING),
            ("CONFIRM_BOOKING", SessionState.BOOKING_PAYMENT),
            ("BOOKING_PAYMENT", SessionState.BOOKING_COMPLETE),
            ("BOOKING_COMPLETE", SessionState.FAREWELL),
            ("FAREWELL", SessionState.IDLE),
        ]
        for current, target in flow:
            redis.get = AsyncMock(return_value=_make_session_data(current))
            result = await mgr.transition("sid-1", target)
            assert result is True, f"{current} → {target.value} failed"

    async def test_full_checkin_flow(self) -> None:
        """Walk through the check-in flow."""
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)

        flow = [
            ("IDLE", SessionState.DETECTED),
            ("DETECTED", SessionState.GREETING),
            ("GREETING", SessionState.INTENT_DISCOVERY),
            ("INTENT_DISCOVERY", SessionState.CHECK_IN),
            ("CHECK_IN", SessionState.VERIFY_IDENTITY),
            ("VERIFY_IDENTITY", SessionState.CONFIRM_APPOINTMENT),
            ("CONFIRM_APPOINTMENT", SessionState.ISSUE_QUEUE_TICKET),
            ("ISSUE_QUEUE_TICKET", SessionState.ROUTE_TO_DEPARTMENT),
            ("ROUTE_TO_DEPARTMENT", SessionState.FAREWELL),
        ]
        for current, target in flow:
            redis.get = AsyncMock(return_value=_make_session_data(current))
            result = await mgr.transition("sid-1", target)
            assert result is True, f"{current} → {target.value} failed"


# ---------------------------------------------------------------------------
# SessionManager.reset
# ---------------------------------------------------------------------------
class TestReset:
    async def test_deletes_key(self) -> None:
        redis = _mock_redis()
        mgr = SessionManager(redis=redis)
        await mgr.reset("sid-1")
        redis.delete.assert_called_once_with(_session_key("sid-1"))


# ---------------------------------------------------------------------------
# SessionManager.touch
# ---------------------------------------------------------------------------
class TestTouch:
    async def test_resets_ttl(self) -> None:
        redis = _mock_redis()
        redis.expire = AsyncMock(return_value=True)
        mgr = SessionManager(redis=redis)
        await mgr.touch("sid-1")
        redis.expire.assert_called_once_with(_session_key("sid-1"), _SESSION_TTL)

    async def test_touch_missing_session(self) -> None:
        redis = _mock_redis()
        redis.expire = AsyncMock(return_value=False)
        mgr = SessionManager(redis=redis)
        await mgr.touch("nonexistent")  # Should not raise


# ---------------------------------------------------------------------------
# Session key format
# ---------------------------------------------------------------------------
class TestSessionKey:
    def test_key_format(self) -> None:
        assert _session_key("abc-123") == "session:abc-123"
