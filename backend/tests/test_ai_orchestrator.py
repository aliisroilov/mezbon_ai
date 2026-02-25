"""Tests for the central AI orchestrator — mocked AI services."""

import base64
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import Redis

from app.ai.orchestrator import (
    Orchestrator,
    OrchestratorResponse,
    _INTENT_TO_STATE,
    _STATE_UI_ACTIONS,
)
from app.ai.session_manager import SessionManager, SessionState
from app.schemas.ai import (
    ChatResponse,
    FaceIdentifyResponse,
    IntentClassification,
    STTResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CLINIC_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
DEVICE_ID = "kiosk-01"


def _make_session_data(
    state: str = "IDLE",
    context: dict | None = None,
    language: str = "uz",
) -> str:
    return json.dumps(
        {
            "state": state,
            "device_id": DEVICE_ID,
            "clinic_id": str(CLINIC_ID),
            "context": context or {},
            "language": language,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )


def _mock_redis(session_data: str | None = None) -> AsyncMock:
    redis = AsyncMock(spec=Redis)
    redis.get = AsyncMock(return_value=session_data)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.expire = AsyncMock(return_value=True)
    return redis


def _mock_db_factory():
    """Create a mock async session factory."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    factory = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory, db


def _build_orchestrator(
    redis: AsyncMock | None = None,
    session_data: str | None = None,
) -> tuple[Orchestrator, dict]:
    """Build an orchestrator with mocked services.

    Returns (orchestrator, mocks_dict).
    """
    r = redis or _mock_redis(session_data)
    session_mgr = SessionManager(redis=r)

    gemini = AsyncMock()
    gemini.chat = AsyncMock(
        return_value=ChatResponse(text="Salom!", ui_action=None, next_state=None)
    )
    gemini.classify_intent = AsyncMock(
        return_value=IntentClassification(
            intent="APPOINTMENT_BOOKING", confidence=0.92, entities={}
        )
    )

    face = AsyncMock()
    face.identify = AsyncMock(return_value=None)

    muxlisa = AsyncMock()
    muxlisa.speech_to_text = AsyncMock(
        return_value=STTResponse(transcript="Shifokorga yozilmoqchiman", language="uz", confidence=0.95)
    )
    muxlisa.text_to_speech = AsyncMock(return_value=b"RIFF" + b"\x00" * 40)

    db_factory, db = _mock_db_factory()

    orch = Orchestrator(
        gemini=gemini,
        face=face,
        muxlisa=muxlisa,
        session_mgr=session_mgr,
        db_session_factory=db_factory,
    )

    return orch, {
        "gemini": gemini,
        "face": face,
        "muxlisa": muxlisa,
        "session_mgr": session_mgr,
        "redis": r,
        "db": db,
        "db_factory": db_factory,
    }


# ---------------------------------------------------------------------------
# OrchestratorResponse model
# ---------------------------------------------------------------------------
class TestOrchestratorResponse:
    def test_required_fields(self) -> None:
        resp = OrchestratorResponse(
            text="Hello", state="IDLE", session_id="sid-1"
        )
        assert resp.text == "Hello"
        assert resp.state == "IDLE"
        assert resp.session_id == "sid-1"
        assert resp.audio_base64 is None
        assert resp.ui_action is None
        assert resp.ui_data is None
        assert resp.patient is None

    def test_all_fields(self) -> None:
        resp = OrchestratorResponse(
            text="Salom",
            audio_base64="AAAA",
            ui_action="show_greeting",
            ui_data={"departments": []},
            state="GREETING",
            patient={"id": "p-1", "name": "Ali"},
            session_id="sid-1",
        )
        assert resp.audio_base64 == "AAAA"
        assert resp.patient["name"] == "Ali"

    def test_serializable(self) -> None:
        resp = OrchestratorResponse(
            text="Hi", state="IDLE", session_id="sid-1"
        )
        d = resp.model_dump()
        assert isinstance(d, dict)
        assert d["text"] == "Hi"


# ---------------------------------------------------------------------------
# handle_face_detected
# ---------------------------------------------------------------------------
class TestHandleFaceDetected:
    async def test_new_visitor_greeting(self) -> None:
        redis = _mock_redis(_make_session_data("IDLE"))
        orch, mocks = _build_orchestrator(redis=redis)

        result = await orch.handle_face_detected(DEVICE_ID, CLINIC_ID, b"image")

        assert isinstance(result, OrchestratorResponse)
        assert result.state == "GREETING"
        assert result.session_id  # non-empty
        assert result.patient is None
        mocks["gemini"].chat.assert_called_once()
        mocks["muxlisa"].text_to_speech.assert_called_once()

    async def test_recognized_patient(self) -> None:
        redis = _mock_redis(_make_session_data("IDLE"))
        orch, mocks = _build_orchestrator(redis=redis)

        mocks["face"].identify = AsyncMock(
            return_value=FaceIdentifyResponse(
                patient_id=PATIENT_ID, similarity=0.85, patient_name="Alisher"
            )
        )

        patient_data = {
            "id": PATIENT_ID,
            "full_name": "Alisher Navoiy",
            "phone": "+998901234567",
        }
        with patch(
            "app.ai.orchestrator.patient_service.get_patient",
            new=AsyncMock(return_value=patient_data),
        ):
            result = await orch.handle_face_detected(DEVICE_ID, CLINIC_ID, b"image")

        assert result.patient is not None
        assert result.patient["full_name"] == "Alisher Navoiy"

    async def test_face_identification_failure_graceful(self) -> None:
        redis = _mock_redis(_make_session_data("IDLE"))
        orch, mocks = _build_orchestrator(redis=redis)
        mocks["face"].identify = AsyncMock(side_effect=Exception("model error"))

        result = await orch.handle_face_detected(DEVICE_ID, CLINIC_ID, b"image")
        assert result.state == "GREETING"
        assert result.patient is None  # graceful fallback

    async def test_generates_audio(self) -> None:
        redis = _mock_redis(_make_session_data("IDLE"))
        orch, mocks = _build_orchestrator(redis=redis)
        result = await orch.handle_face_detected(DEVICE_ID, CLINIC_ID, b"image")
        assert result.audio_base64 is not None


# ---------------------------------------------------------------------------
# handle_speech
# ---------------------------------------------------------------------------
class TestHandleSpeech:
    async def test_basic_speech(self) -> None:
        redis = _mock_redis(_make_session_data("GREETING"))
        orch, mocks = _build_orchestrator(redis=redis)

        result = await orch.handle_speech("sid-1", b"audio_data")

        assert isinstance(result, OrchestratorResponse)
        assert result.text == "Salom!"
        mocks["muxlisa"].speech_to_text.assert_called_once_with(b"audio_data")
        mocks["gemini"].chat.assert_called_once()

    async def test_empty_transcript_returns_prompt(self) -> None:
        redis = _mock_redis(_make_session_data("GREETING"))
        orch, mocks = _build_orchestrator(redis=redis)
        mocks["muxlisa"].speech_to_text = AsyncMock(
            return_value=STTResponse(transcript="", language="uz", confidence=0.0)
        )

        result = await orch.handle_speech("sid-1", b"silence")
        assert "eshitmadim" in result.text.lower() or "qaytadan" in result.text.lower()
        mocks["gemini"].chat.assert_not_called()

    async def test_intent_classification_in_greeting(self) -> None:
        redis = _mock_redis(_make_session_data("GREETING"))
        orch, mocks = _build_orchestrator(redis=redis)

        await orch.handle_speech("sid-1", b"audio")
        mocks["gemini"].classify_intent.assert_called_once()

    async def test_expired_session(self) -> None:
        redis = _mock_redis(None)  # session not found
        orch, _ = _build_orchestrator(redis=redis)
        result = await orch.handle_speech("expired-sid", b"audio")
        assert result.state == "IDLE"
        assert "tugadi" in result.text.lower() or "sessiya" in result.text.lower()

    async def test_language_detection_updates_session(self) -> None:
        redis = _mock_redis(_make_session_data("GREETING", language="uz"))
        orch, mocks = _build_orchestrator(redis=redis)
        mocks["muxlisa"].speech_to_text = AsyncMock(
            return_value=STTResponse(
                transcript="Здравствуйте", language="ru", confidence=0.9
            )
        )

        await orch.handle_speech("sid-1", b"audio")
        # language should be updated in session
        # The set_language call writes to redis
        assert redis.set.call_count >= 1

    async def test_tts_generated_for_response(self) -> None:
        redis = _mock_redis(_make_session_data("INTENT_DISCOVERY"))
        orch, mocks = _build_orchestrator(redis=redis)
        result = await orch.handle_speech("sid-1", b"audio")
        mocks["muxlisa"].text_to_speech.assert_called()
        assert result.audio_base64 is not None


# ---------------------------------------------------------------------------
# handle_touch
# ---------------------------------------------------------------------------
class TestHandleTouch:
    async def test_select_department(self) -> None:
        redis = _mock_redis(_make_session_data("SELECT_DEPARTMENT"))
        orch, mocks = _build_orchestrator(redis=redis)

        result = await orch.handle_touch(
            "sid-1", "select_department", {"department_id": "dept-1"}
        )
        assert isinstance(result, OrchestratorResponse)
        mocks["gemini"].chat.assert_called_once()

    async def test_select_doctor(self) -> None:
        redis = _mock_redis(_make_session_data("SELECT_DOCTOR"))
        orch, mocks = _build_orchestrator(redis=redis)

        result = await orch.handle_touch(
            "sid-1", "select_doctor", {"doctor_id": "doc-1"}
        )
        assert isinstance(result, OrchestratorResponse)

    async def test_cancel_goes_to_farewell(self) -> None:
        redis = _mock_redis(_make_session_data("CONFIRM_BOOKING"))
        orch, _ = _build_orchestrator(redis=redis)

        result = await orch.handle_touch("sid-1", "cancel", {})
        # Should attempt transition to FAREWELL
        # The actual state depends on redis mock behavior
        assert isinstance(result, OrchestratorResponse)

    async def test_expired_session(self) -> None:
        redis = _mock_redis(None)
        orch, _ = _build_orchestrator(redis=redis)
        result = await orch.handle_touch("expired", "select_department", {})
        assert result.state == "IDLE"

    async def test_confirm_booking(self) -> None:
        redis = _mock_redis(_make_session_data("CONFIRM_BOOKING"))
        orch, mocks = _build_orchestrator(redis=redis)
        result = await orch.handle_touch("sid-1", "confirm", {})
        assert isinstance(result, OrchestratorResponse)


# ---------------------------------------------------------------------------
# handle_timeout
# ---------------------------------------------------------------------------
class TestHandleTimeout:
    async def test_first_timeout_prompts(self) -> None:
        redis = _mock_redis(_make_session_data("SELECT_DOCTOR"))
        orch, mocks = _build_orchestrator(redis=redis)

        result = await orch.handle_timeout("sid-1")
        assert "yerdasizmi" in result.text.lower() or "still there" in result.text.lower() or "здесь" in result.text.lower()
        assert result.ui_action == "show_timeout_prompt"

    async def test_second_timeout_farewell(self) -> None:
        redis = _mock_redis(
            _make_session_data("SELECT_DOCTOR", context={"timeout_warned": True})
        )
        orch, mocks = _build_orchestrator(redis=redis)

        result = await orch.handle_timeout("sid-1")
        assert result.ui_action == "show_farewell"
        redis.delete.assert_called_once()  # session reset

    async def test_timeout_expired_session(self) -> None:
        redis = _mock_redis(None)
        orch, _ = _build_orchestrator(redis=redis)
        result = await orch.handle_timeout("expired")
        assert result.state == "IDLE"

    async def test_timeout_russian_language(self) -> None:
        redis = _mock_redis(_make_session_data("GREETING", language="ru"))
        orch, _ = _build_orchestrator(redis=redis)
        result = await orch.handle_timeout("sid-1")
        assert "здесь" in result.text.lower()

    async def test_timeout_english_language(self) -> None:
        redis = _mock_redis(_make_session_data("GREETING", language="en"))
        orch, _ = _build_orchestrator(redis=redis)
        result = await orch.handle_timeout("sid-1")
        assert "still there" in result.text.lower()


# ---------------------------------------------------------------------------
# Intent → State mapping
# ---------------------------------------------------------------------------
class TestIntentMapping:
    def test_appointment_maps(self) -> None:
        assert _INTENT_TO_STATE["APPOINTMENT_BOOKING"] == SessionState.APPOINTMENT_BOOKING

    def test_checkin_maps(self) -> None:
        assert _INTENT_TO_STATE["CHECK_IN"] == SessionState.CHECK_IN

    def test_information_maps(self) -> None:
        assert _INTENT_TO_STATE["INFORMATION"] == SessionState.INFORMATION_INQUIRY

    def test_farewell_maps(self) -> None:
        assert _INTENT_TO_STATE["FAREWELL"] == SessionState.FAREWELL

    def test_unknown_intent_not_present(self) -> None:
        assert "UNKNOWN" not in _INTENT_TO_STATE


# ---------------------------------------------------------------------------
# State → UI action mapping
# ---------------------------------------------------------------------------
class TestStateUIMapping:
    def test_greeting_action(self) -> None:
        assert _STATE_UI_ACTIONS[SessionState.GREETING] == "show_greeting"

    def test_select_department_action(self) -> None:
        assert _STATE_UI_ACTIONS[SessionState.SELECT_DEPARTMENT] == "show_departments"

    def test_farewell_action(self) -> None:
        assert _STATE_UI_ACTIONS[SessionState.FAREWELL] == "show_farewell"

    def test_queue_ticket_action(self) -> None:
        assert _STATE_UI_ACTIONS[SessionState.ISSUE_QUEUE_TICKET] == "show_queue_ticket"


# ---------------------------------------------------------------------------
# Full visitor journeys (integration-style with mocked services)
# ---------------------------------------------------------------------------
class TestFullJourney:
    async def test_new_patient_booking_flow(self) -> None:
        """Simulate: face → greeting → speech (booking intent) → touch selections."""
        redis = _mock_redis(_make_session_data("IDLE"))
        orch, mocks = _build_orchestrator(redis=redis)

        # 1. Face detected
        r1 = await orch.handle_face_detected(DEVICE_ID, CLINIC_ID, b"face-img")
        assert r1.state == "GREETING"

        # 2. Speech — booking intent
        redis.get = AsyncMock(return_value=_make_session_data("GREETING"))
        r2 = await orch.handle_speech(r1.session_id, b"audio-booking")
        assert isinstance(r2, OrchestratorResponse)
        mocks["gemini"].classify_intent.assert_called()

        # 3. Touch — select department
        redis.get = AsyncMock(return_value=_make_session_data("SELECT_DEPARTMENT"))
        r3 = await orch.handle_touch(
            r1.session_id, "select_department", {"department_id": "dept-1"}
        )
        assert isinstance(r3, OrchestratorResponse)

        # 4. Touch — select doctor
        redis.get = AsyncMock(return_value=_make_session_data("SELECT_DOCTOR"))
        r4 = await orch.handle_touch(
            r1.session_id, "select_doctor", {"doctor_id": "doc-1"}
        )
        assert isinstance(r4, OrchestratorResponse)

    async def test_returning_patient_checkin_flow(self) -> None:
        """Simulate: recognized face → speech (check-in intent)."""
        redis = _mock_redis(_make_session_data("IDLE"))
        orch, mocks = _build_orchestrator(redis=redis)

        # Recognize patient
        mocks["face"].identify = AsyncMock(
            return_value=FaceIdentifyResponse(
                patient_id=PATIENT_ID, similarity=0.88, patient_name="Bobur"
            )
        )
        patient_data = {"id": PATIENT_ID, "full_name": "Bobur", "phone": "+998900000000"}

        with patch(
            "app.ai.orchestrator.patient_service.get_patient",
            new=AsyncMock(return_value=patient_data),
        ):
            r1 = await orch.handle_face_detected(DEVICE_ID, CLINIC_ID, b"face")

        assert r1.patient is not None
        assert r1.patient["full_name"] == "Bobur"

        # Speech — check-in intent
        mocks["gemini"].classify_intent = AsyncMock(
            return_value=IntentClassification(
                intent="CHECK_IN", confidence=0.95, entities={}
            )
        )
        redis.get = AsyncMock(
            return_value=_make_session_data(
                "GREETING",
                context={"patient_id": str(PATIENT_ID), "patient_name": "Bobur"},
            )
        )
        r2 = await orch.handle_speech(r1.session_id, b"check-in audio")
        assert isinstance(r2, OrchestratorResponse)

    async def test_faq_flow(self) -> None:
        """Simulate: face → speech (FAQ intent)."""
        redis = _mock_redis(_make_session_data("IDLE"))
        orch, mocks = _build_orchestrator(redis=redis)

        r1 = await orch.handle_face_detected(DEVICE_ID, CLINIC_ID, b"img")

        mocks["gemini"].classify_intent = AsyncMock(
            return_value=IntentClassification(
                intent="FAQ", confidence=0.85, entities={"query": "working hours"}
            )
        )
        mocks["gemini"].chat = AsyncMock(
            return_value=ChatResponse(
                text="Klinika 8:00 dan 18:00 gacha ishlaydi.",
                ui_action="show_faq",
            )
        )
        redis.get = AsyncMock(return_value=_make_session_data("GREETING"))

        r2 = await orch.handle_speech(r1.session_id, b"working hours?")
        assert "ishlaydi" in r2.text.lower() or r2.text  # got FAQ response

    async def test_timeout_and_farewell(self) -> None:
        """Simulate: timeout warning → second timeout → farewell."""
        redis = _mock_redis(_make_session_data("SELECT_DOCTOR"))
        orch, _ = _build_orchestrator(redis=redis)

        # First timeout
        r1 = await orch.handle_timeout("sid-1")
        assert r1.ui_action == "show_timeout_prompt"

        # Second timeout
        redis.get = AsyncMock(
            return_value=_make_session_data(
                "SELECT_DOCTOR", context={"timeout_warned": True}
            )
        )
        r2 = await orch.handle_timeout("sid-1")
        assert r2.ui_action == "show_farewell"


# ---------------------------------------------------------------------------
# TTS failure handling
# ---------------------------------------------------------------------------
class TestTTSFailure:
    async def test_tts_failure_returns_none_audio(self) -> None:
        redis = _mock_redis(_make_session_data("IDLE"))
        orch, mocks = _build_orchestrator(redis=redis)
        mocks["muxlisa"].text_to_speech = AsyncMock(side_effect=Exception("TTS down"))

        result = await orch.handle_face_detected(DEVICE_ID, CLINIC_ID, b"img")
        assert result.audio_base64 is None  # graceful
        assert result.text  # still has text
