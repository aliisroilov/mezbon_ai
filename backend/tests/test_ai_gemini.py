"""Tests for the Gemini service — mocked Gemini API, real Redis + service routing."""

import json
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from app.ai.gemini_service import GeminiService, _SESSION_TTL_S
from app.ai.prompts.functions import CLINIC_TOOLS, FUNCTION_DECLARATIONS
from app.ai.prompts.system_prompt import build_system_prompt
from app.core.exceptions import AIServiceError
from app.schemas.ai import ChatResponse, IntentClassification


# ---------------------------------------------------------------------------
# Helpers to build mock Gemini responses
# ---------------------------------------------------------------------------
def _make_text_response(text: str) -> MagicMock:
    """Build a mock Gemini response that contains a text part."""
    part = MagicMock()
    part.text = text
    part.function_call = MagicMock()
    part.function_call.name = ""
    candidate = MagicMock()
    candidate.content.parts = [part]
    response = MagicMock()
    response.candidates = [candidate]
    response.text = text
    return response


def _make_function_call_response(fn_name: str, fn_args: dict) -> MagicMock:
    """Build a mock Gemini response that contains a function call."""
    part = MagicMock()
    part.text = ""
    part.function_call = MagicMock()
    part.function_call.name = fn_name
    part.function_call.args = fn_args
    candidate = MagicMock()
    candidate.content.parts = [part]
    response = MagicMock()
    response.candidates = [candidate]
    response.text = ""
    return response


def _clinic_data() -> dict:
    return {
        "clinic_name": "Test Clinic",
        "clinic_address": "Test Address 123",
        "device_location": "Main entrance",
        "departments": [{"name": "Terapiya", "id": "dept-1"}],
        "doctors_on_duty": [{"name": "Dr. Karimov", "specialty": "Terapevt"}],
        "queue_status": [],
    }


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------
class TestSystemPrompt:
    def test_build_system_prompt_fills_template(self) -> None:
        prompt = build_system_prompt(_clinic_data())
        assert "Test Clinic" in prompt
        assert "Test Address 123" in prompt
        assert "Main entrance" in prompt
        assert "Terapiya" in prompt
        assert "Dr. Karimov" in prompt
        assert "NEVER diagnose" in prompt

    def test_build_system_prompt_with_patient_context(self) -> None:
        data = _clinic_data()
        data["patient_context"] = {
            "full_name": "Alisher Usmanov",
            "language_preference": "uz",
            "visit_count": 5,
        }
        prompt = build_system_prompt(data)
        assert "Alisher Usmanov" in prompt
        assert "RECOGNIZED PATIENT" in prompt

    def test_build_system_prompt_without_patient_context(self) -> None:
        prompt = build_system_prompt(_clinic_data())
        assert "RECOGNIZED PATIENT" not in prompt

    def test_build_system_prompt_empty_clinic_data(self) -> None:
        prompt = build_system_prompt({})
        assert "Clinic" in prompt  # default clinic name


# ---------------------------------------------------------------------------
# Function declarations tests
# ---------------------------------------------------------------------------
class TestFunctionDeclarations:
    def test_all_functions_declared(self) -> None:
        names = {fd.name for fd in FUNCTION_DECLARATIONS}
        expected = {
            "book_appointment", "check_in", "lookup_patient", "register_patient",
            "get_available_slots", "get_department_info", "get_doctor_info",
            "process_payment", "get_queue_status", "issue_queue_ticket",
            "search_faq", "escalate_to_human",
        }
        assert names == expected

    def test_clinic_tools_wraps_declarations(self) -> None:
        assert CLINIC_TOOLS is not None
        assert len(CLINIC_TOOLS.function_declarations) == 12


# ---------------------------------------------------------------------------
# GeminiService unit tests (mocked Gemini + Redis)
# ---------------------------------------------------------------------------
class TestGeminiServiceInit:
    @patch("app.ai.gemini_service.genai")
    async def test_initialize_configures_model(self, mock_genai: MagicMock) -> None:
        svc = GeminiService()
        with patch("app.ai.gemini_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "test-key"
            mock_settings.GEMINI_MODEL = "gemini-2.0-flash"
            await svc.initialize(_clinic_data())

        mock_genai.configure.assert_called_once_with(api_key="test-key")
        assert svc._initialized is True
        assert svc.model is not None
        assert svc._intent_model is not None

    async def test_chat_raises_if_not_initialized(self) -> None:
        svc = GeminiService()
        with pytest.raises(AIServiceError, match="not initialized"):
            await svc.chat("session-1", "hello")


class TestGeminiChat:
    @pytest_asyncio.fixture
    async def svc(self) -> GeminiService:
        """Create an initialized GeminiService with mocked model."""
        service = GeminiService()
        service.model = MagicMock()
        service._intent_model = MagicMock()
        service._initialized = True
        return service

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        redis = AsyncMock(spec=Redis)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        redis.delete = AsyncMock()
        return redis

    async def test_chat_text_response(self, svc: GeminiService, mock_redis: AsyncMock) -> None:
        """Test basic text response from Gemini."""
        text_resp = _make_text_response("Salom! Qanday yordam bera olaman?")

        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(return_value=text_resp)
        mock_chat.history = []
        svc.model.start_chat = MagicMock(return_value=mock_chat)

        with patch("app.ai.gemini_service.get_redis", return_value=mock_redis):
            result = await svc.chat("session-1", "Salom")

        assert isinstance(result, ChatResponse)
        assert result.text == "Salom! Qanday yordam bera olaman?"
        assert result.function_calls == []
        assert result.ui_action is None

        # History should be saved to Redis
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "chat:session-1"
        assert call_args[1]["ex"] == _SESSION_TTL_S

    async def test_chat_with_patient_context(self, svc: GeminiService, mock_redis: AsyncMock) -> None:
        """Test that patient context is prepended to the message."""
        text_resp = _make_text_response("Salom, Alisher!")

        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(return_value=text_resp)
        mock_chat.history = []
        svc.model.start_chat = MagicMock(return_value=mock_chat)

        with patch("app.ai.gemini_service.get_redis", return_value=mock_redis):
            result = await svc.chat(
                "session-1",
                "Hello",
                patient_context={"full_name": "Alisher", "id": "p-123", "language_preference": "uz"},
            )

        # Verify the message sent to Gemini includes patient context
        sent_msg = mock_chat.send_message_async.call_args[0][0]
        assert "Alisher" in sent_msg
        assert "p-123" in sent_msg
        assert result.text == "Salom, Alisher!"

    async def test_chat_function_call_then_text(self, svc: GeminiService, mock_redis: AsyncMock) -> None:
        """Test function call → result → final text chain."""
        fn_resp = _make_function_call_response("search_faq", {"query": "ish vaqti"})
        final_resp = _make_text_response("Klinika har kuni 08:00 dan 20:00 gacha ishlaydi.")

        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(side_effect=[fn_resp, final_resp])
        mock_chat.history = []
        svc.model.start_chat = MagicMock(return_value=mock_chat)

        clinic_id = uuid.uuid4()
        db = AsyncMock()

        with (
            patch("app.ai.gemini_service.get_redis", return_value=mock_redis),
            patch.object(svc, "_execute_function_call", return_value={"results": [{"answer": "08:00-17:00"}]}),
        ):
            result = await svc.chat("session-1", "Ish vaqtlari qanday?", clinic_id=clinic_id, db=db)

        assert result.text == "Klinika har kuni 08:00 dan 20:00 gacha ishlaydi."
        assert len(result.function_calls) == 1
        assert result.function_calls[0]["name"] == "search_faq"
        assert result.ui_action == "show_faq_results"

    async def test_chat_multi_step_function_calls(self, svc: GeminiService, mock_redis: AsyncMock) -> None:
        """Test chained function calls: lookup_patient → get_available_slots → text."""
        resp1 = _make_function_call_response("lookup_patient", {"phone": "+998901112233"})
        resp2 = _make_function_call_response("get_available_slots", {"doctor_id": "d-1", "date": "2026-02-17"})
        resp3 = _make_text_response("Dr. Karimov ertaga 10:00 va 14:00 da bo'sh.")

        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(side_effect=[resp1, resp2, resp3])
        mock_chat.history = []
        svc.model.start_chat = MagicMock(return_value=mock_chat)

        clinic_id = uuid.uuid4()
        db = AsyncMock()

        with (
            patch("app.ai.gemini_service.get_redis", return_value=mock_redis),
            patch.object(
                svc,
                "_execute_function_call",
                side_effect=[
                    {"found": True, "patient_id": "p-1", "full_name": "Alisher"},
                    {"available_slots": [{"start": "10:00"}, {"start": "14:00"}]},
                ],
            ),
        ):
            result = await svc.chat("session-1", "Ertaga Dr. Karimovga yozilmoqchiman", clinic_id=clinic_id, db=db)

        assert len(result.function_calls) == 2
        assert result.function_calls[0]["name"] == "lookup_patient"
        assert result.function_calls[1]["name"] == "get_available_slots"
        assert result.ui_action == "show_time_slots"

    async def test_chat_loads_existing_history(self, svc: GeminiService) -> None:
        """Test that existing Redis history is loaded and passed to Gemini."""
        stored_history = json.dumps([
            {"role": "user", "parts": [{"text": "Salom"}]},
            {"role": "model", "parts": [{"text": "Salom! Qanday yordam?"}]},
        ])

        mock_redis = AsyncMock(spec=Redis)
        mock_redis.get = AsyncMock(return_value=stored_history)
        mock_redis.set = AsyncMock()

        text_resp = _make_text_response("Ha, albatta!")
        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(return_value=text_resp)
        mock_chat.history = []
        svc.model.start_chat = MagicMock(return_value=mock_chat)

        with patch("app.ai.gemini_service.get_redis", return_value=mock_redis):
            await svc.chat("session-1", "Shifokorlar haqida aytib bering")

        # Verify start_chat was called with history
        call_args = svc.model.start_chat.call_args
        assert len(call_args[1]["history"]) == 2

    async def test_reset_session(self, svc: GeminiService) -> None:
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.delete = AsyncMock()

        with patch("app.ai.gemini_service.get_redis", return_value=mock_redis):
            await svc.reset_session("session-42")

        mock_redis.delete.assert_called_once_with("chat:session-42")


class TestIntentClassification:
    @pytest_asyncio.fixture
    async def svc(self) -> GeminiService:
        service = GeminiService()
        service._intent_model = MagicMock()
        service._initialized = True
        return service

    async def test_classify_appointment_booking_uz(self, svc: GeminiService) -> None:
        """Uzbek: 'Shifokorga yozilmoqchiman' → APPOINTMENT_BOOKING."""
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "intent": "APPOINTMENT_BOOKING",
            "confidence": 0.95,
            "entities": {"service": "konsultatsiya"},
        })
        svc._intent_model.generate_content_async = AsyncMock(return_value=mock_resp)

        result = await svc.classify_intent("Shifokorga yozilmoqchiman")

        assert isinstance(result, IntentClassification)
        assert result.intent == "APPOINTMENT_BOOKING"
        assert result.confidence == 0.95
        assert result.entities.get("service") == "konsultatsiya"

    async def test_classify_greeting_uz(self, svc: GeminiService) -> None:
        """Uzbek greeting → GREETING."""
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "intent": "GREETING",
            "confidence": 0.99,
            "entities": {},
        })
        svc._intent_model.generate_content_async = AsyncMock(return_value=mock_resp)

        result = await svc.classify_intent("Assalomu alaykum")
        assert result.intent == "GREETING"
        assert result.confidence == 0.99

    async def test_classify_check_in_ru(self, svc: GeminiService) -> None:
        """Russian: 'У меня запись на сегодня' → CHECK_IN."""
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "intent": "CHECK_IN",
            "confidence": 0.88,
            "entities": {"date": "today"},
        })
        svc._intent_model.generate_content_async = AsyncMock(return_value=mock_resp)

        result = await svc.classify_intent("У меня запись на сегодня")
        assert result.intent == "CHECK_IN"

    async def test_classify_information_en(self, svc: GeminiService) -> None:
        """English: 'What are your working hours?' → INFORMATION."""
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "intent": "INFORMATION",
            "confidence": 0.92,
            "entities": {"topic": "working_hours"},
        })
        svc._intent_model.generate_content_async = AsyncMock(return_value=mock_resp)

        result = await svc.classify_intent("What are your working hours?")
        assert result.intent == "INFORMATION"

    async def test_classify_payment_uz(self, svc: GeminiService) -> None:
        """Uzbek: 'Tolov qilmoqchiman' → PAYMENT."""
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "intent": "PAYMENT",
            "confidence": 0.90,
            "entities": {},
        })
        svc._intent_model.generate_content_async = AsyncMock(return_value=mock_resp)

        result = await svc.classify_intent("To'lov qilmoqchiman")
        assert result.intent == "PAYMENT"

    async def test_classify_handles_invalid_json(self, svc: GeminiService) -> None:
        """Gracefully handle malformed JSON from Gemini."""
        mock_resp = MagicMock()
        mock_resp.text = "not valid json at all"
        svc._intent_model.generate_content_async = AsyncMock(return_value=mock_resp)

        result = await svc.classify_intent("random text")
        assert result.intent == "UNKNOWN"
        assert result.confidence == 0.0

    async def test_classify_clamps_confidence(self, svc: GeminiService) -> None:
        """Confidence values above 1.0 should be clamped."""
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({"intent": "GREETING", "confidence": 1.5, "entities": {}})
        svc._intent_model.generate_content_async = AsyncMock(return_value=mock_resp)

        result = await svc.classify_intent("Salom")
        assert result.confidence == 1.0


class TestFunctionCallExecution:
    @pytest_asyncio.fixture
    async def svc(self) -> GeminiService:
        service = GeminiService()
        service._initialized = True
        return service

    def _make_fc(self, name: str, args: dict) -> MagicMock:
        fc = MagicMock()
        fc.name = name
        fc.args = args
        return fc

    async def test_lookup_patient_found(self, svc: GeminiService) -> None:
        db = AsyncMock()
        clinic_id = uuid.uuid4()
        patient_data = {
            "id": uuid.uuid4(),
            "full_name": "Alisher Usmanov",
            "language_preference": "uz",
        }

        with patch("app.ai.gemini_service.patient_service") as mock_ps:
            mock_ps.lookup_by_phone = AsyncMock(return_value=patient_data)
            # Import to use the actual method
            from app.services import patient_service
            with patch("app.services.patient_service.lookup_by_phone", new=AsyncMock(return_value=patient_data)):
                result = await svc._execute_function_call(
                    self._make_fc("lookup_patient", {"phone": "+998901112233"}),
                    clinic_id,
                    db,
                )

        assert result["found"] is True
        assert result["full_name"] == "Alisher Usmanov"

    async def test_lookup_patient_not_found(self, svc: GeminiService) -> None:
        db = AsyncMock()
        clinic_id = uuid.uuid4()

        with patch("app.services.patient_service.lookup_by_phone", new=AsyncMock(return_value=None)):
            result = await svc._execute_function_call(
                self._make_fc("lookup_patient", {"phone": "+998900000000"}),
                clinic_id,
                db,
            )

        assert result["found"] is False

    async def test_escalate_to_human(self, svc: GeminiService) -> None:
        db = AsyncMock()
        clinic_id = uuid.uuid4()

        result = await svc._execute_function_call(
            self._make_fc("escalate_to_human", {"reason": "Patient is upset"}),
            clinic_id,
            db,
        )

        assert result["escalated"] is True
        assert "Patient is upset" in result["reason"]

    async def test_unknown_function(self, svc: GeminiService) -> None:
        db = AsyncMock()
        clinic_id = uuid.uuid4()

        result = await svc._execute_function_call(
            self._make_fc("nonexistent_function", {}),
            clinic_id,
            db,
        )

        assert "error" in result
        assert "Unknown function" in result["error"]

    async def test_function_error_handling(self, svc: GeminiService) -> None:
        """Service exceptions are caught and returned as error dicts."""
        db = AsyncMock()
        clinic_id = uuid.uuid4()

        with patch(
            "app.services.patient_service.lookup_by_phone",
            new=AsyncMock(side_effect=Exception("DB connection lost")),
        ):
            result = await svc._execute_function_call(
                self._make_fc("lookup_patient", {"phone": "+998901112233"}),
                clinic_id,
                db,
            )

        assert "error" in result
        assert "DB connection lost" in result["error"]

    async def test_search_faq_with_matches(self, svc: GeminiService) -> None:
        db = AsyncMock()
        clinic_id = uuid.uuid4()

        mock_faq = MagicMock()
        mock_faq.question = "Ish vaqtlari qanday?"
        mock_faq.answer = "Dushanba-Shanba 08:00-17:00"
        mock_faq.language = "uz"

        with patch("app.services.faq_service.list_faqs", new=AsyncMock(return_value=[mock_faq])):
            result = await svc._execute_function_call(
                self._make_fc("search_faq", {"query": "ish vaqt"}),
                clinic_id,
                db,
            )

        assert result["count"] == 1
        assert result["results"][0]["answer"] == "Dushanba-Shanba 08:00-17:00"

    async def test_get_department_info(self, svc: GeminiService) -> None:
        db = AsyncMock()
        clinic_id = uuid.uuid4()
        dept_id = uuid.uuid4()

        dept = {"id": dept_id, "name": "Kardiologiya", "description": "Heart care", "floor": 2, "room_number": "201", "doctor_count": 3}

        with patch("app.services.department_service.list_departments", new=AsyncMock(return_value=[dept])):
            result = await svc._execute_function_call(
                self._make_fc("get_department_info", {"department_name": "Kardio"}),
                clinic_id,
                db,
            )

        assert result["name"] == "Kardiologiya"
        assert result["doctor_count"] == 3

    async def test_get_department_info_not_found(self, svc: GeminiService) -> None:
        db = AsyncMock()
        clinic_id = uuid.uuid4()

        with patch("app.services.department_service.list_departments", new=AsyncMock(return_value=[])):
            result = await svc._execute_function_call(
                self._make_fc("get_department_info", {"department_name": "Nonexistent"}),
                clinic_id,
                db,
            )

        assert "error" in result


class TestRetryLogic:
    @pytest_asyncio.fixture
    async def svc(self) -> GeminiService:
        service = GeminiService()
        service.model = MagicMock()
        service._initialized = True
        return service

    async def test_retry_on_timeout(self, svc: GeminiService) -> None:
        """Should retry on timeout and succeed on second attempt."""
        text_resp = _make_text_response("Success after retry")

        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(
            side_effect=[TimeoutError(), text_resp]
        )
        mock_chat.history = []

        # The _send_with_retry uses asyncio.wait_for which raises asyncio.TimeoutError
        import asyncio

        mock_chat.send_message_async = AsyncMock(
            side_effect=[asyncio.TimeoutError(), text_resp]
        )

        mock_redis = AsyncMock(spec=Redis)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()

        svc.model.start_chat = MagicMock(return_value=mock_chat)

        with patch("app.ai.gemini_service.get_redis", return_value=mock_redis):
            # Patch sleep to avoid real delays in tests
            with patch("asyncio.sleep", new=AsyncMock()):
                with patch("asyncio.wait_for", new=AsyncMock(side_effect=[asyncio.TimeoutError(), text_resp])):
                    # Directly test _send_with_retry
                    pass

        # Simpler: test _send_with_retry directly
        call_count = 0
        original_send = mock_chat.send_message_async

        async def side_effect_fn(msg):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError()
            return text_resp

        mock_chat.send_message_async = side_effect_fn

        with patch("asyncio.sleep", new=AsyncMock()):
            with patch("asyncio.wait_for", side_effect=lambda coro, timeout: coro):
                result = await svc._send_with_retry(mock_chat, "test", "s-1")

        assert result.text == "Success after retry"

    async def test_raises_after_max_retries(self, svc: GeminiService) -> None:
        """Should raise AIServiceError after exhausting retries."""
        import asyncio

        mock_chat = MagicMock()

        async def always_timeout(msg):
            raise asyncio.TimeoutError()

        mock_chat.send_message_async = always_timeout

        with patch("asyncio.sleep", new=AsyncMock()):
            with patch("asyncio.wait_for", side_effect=lambda coro, timeout: coro):
                with pytest.raises(AIServiceError, match="timed out"):
                    await svc._send_with_retry(mock_chat, "test", "s-1")


class TestUIAction:
    def test_ui_action_mapping(self) -> None:
        svc = GeminiService()

        assert svc._determine_ui_action([]) is None
        assert svc._determine_ui_action([{"name": "book_appointment", "args": {}}]) == "show_booking_confirmation"
        assert svc._determine_ui_action([{"name": "search_faq", "args": {}}]) == "show_faq_results"
        assert svc._determine_ui_action([{"name": "issue_queue_ticket", "args": {}}]) == "show_queue_ticket"
        assert svc._determine_ui_action([{"name": "escalate_to_human", "args": {}}]) == "show_staff_notification"
        assert svc._determine_ui_action([{"name": "register_patient", "args": {}}]) is None

    def test_ui_action_uses_last_function(self) -> None:
        svc = GeminiService()
        calls = [
            {"name": "lookup_patient", "args": {}},
            {"name": "get_available_slots", "args": {}},
        ]
        assert svc._determine_ui_action(calls) == "show_time_slots"


class TestSessionHistory:
    async def test_save_and_load_roundtrip(self) -> None:
        """Test that history serialization/deserialization works."""
        import google.generativeai as genai

        svc = GeminiService()
        mock_redis = AsyncMock(spec=Redis)
        stored_value = None

        async def mock_set(key, value, ex=None):
            nonlocal stored_value
            stored_value = value

        async def mock_get(key):
            return stored_value

        mock_redis.set = mock_set
        mock_redis.get = mock_get

        # Build history
        history = [
            genai.protos.Content(
                role="user",
                parts=[genai.protos.Part(text="Salom")],
            ),
            genai.protos.Content(
                role="model",
                parts=[genai.protos.Part(text="Salom! Qanday yordam?")],
            ),
        ]

        await svc._save_history(mock_redis, "test-session", history)
        loaded = await svc._load_history(mock_redis, "test-session")

        assert len(loaded) == 2
        assert loaded[0].role == "user"
        assert loaded[1].role == "model"

    async def test_load_empty_history(self) -> None:
        svc = GeminiService()
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.get = AsyncMock(return_value=None)

        history = await svc._load_history(mock_redis, "nonexistent")
        assert history == []

    async def test_load_corrupted_history(self) -> None:
        svc = GeminiService()
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.get = AsyncMock(return_value="not valid json {{{")

        history = await svc._load_history(mock_redis, "corrupted")
        assert history == []
