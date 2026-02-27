"""Gemini 2.0 Flash service — the AI brain of Mezbon clinic receptionist.

Handles:
  - Multi-turn conversation with Redis-backed history (in-memory fallback)
  - Function calling with automatic execution + result feeding
  - Demo fallback data when DB services are unavailable
  - Response sanitisation (never returns JSON to visitor)
"""

import asyncio
import json
import random
import re
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from loguru import logger

from app.ai.prompts.functions import CLINIC_TOOLS
from app.ai.prompts.system_prompt import build_system_prompt
from app.config import settings
from app.core.exceptions import AIServiceError
from app.schemas.ai import ChatResponse, IntentClassification

# ── Constants ────────────────────────────────────────────────────────────────
_MAX_RETRIES = 2
_BASE_BACKOFF_S = 0.5
_GEMINI_TIMEOUT_S = 10.0

_SESSION_TTL_S = 600  # 10 minutes
_MAX_FUNCTION_CHAIN = 5

# Intent classification prompt
_INTENT_PROMPT = """\
Classify this clinic visitor's intent. Return JSON only, no markdown.
Schema: {{"intent": str, "confidence": float, "entities": dict}}

Valid intents:
- APPOINTMENT_BOOKING: wants to book or schedule a visit
- CHECK_IN: arrived for an existing appointment
- INFORMATION: asking about departments, doctors, services, hours
- PAYMENT: wants to pay for a service
- COMPLAINT: has a complaint or negative feedback
- GREETING: just greeting (salom, privet, hello)
- FAREWELL: saying goodbye
- UNKNOWN: cannot determine

Extract entities where applicable: names, dates, department names, doctor names, \
phone numbers, service names.

Visitor message: "{message}"
"""


class GeminiService:
    """Async wrapper around Google Gemini 2.0 Flash for clinic chat.

    Supports two modes:
      1. Full mode — Redis history + DB function execution (production)
      2. Demo mode — in-memory history + hardcoded demo data (testing)
    """

    def __init__(self) -> None:
        self.model: genai.GenerativeModel | None = None
        self._intent_model: genai.GenerativeModel | None = None
        self._initialized = False
        # In-memory history fallback (used when Redis is unavailable)
        self._memory_history: dict[str, list] = {}

    async def initialize(self, clinic_data: dict) -> None:
        """Configure Gemini with clinic context as system instruction.

        Args:
            clinic_data: Dict with clinic_name, clinic_address, departments,
                         doctors_on_duty, queue_status, etc.
        """
        genai.configure(api_key=settings.GEMINI_API_KEY)

        system_prompt = build_system_prompt(clinic_data)

        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_prompt,
            tools=[CLINIC_TOOLS],
            generation_config=genai.GenerationConfig(
                temperature=0.8,        # Warmer for natural, human-like conversation
                top_p=0.9,              # More diverse word choices
                top_k=40,               # Broader vocabulary selection
                max_output_tokens=200,  # Shorter = faster + more natural for kiosk
            ),
        )

        self._intent_model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=(
                "You are an intent classifier for a medical clinic reception kiosk. "
                "Classify visitor messages into one of these intents: "
                "GREETING, APPOINTMENT_BOOKING, CHECK_IN, INFORMATION, PAYMENT, "
                "COMPLAINT, HAND_OFF, FAREWELL, UNKNOWN. "
                "Visitors may speak in Uzbek, Russian, or English. "
                'Respond with JSON: {"intent": "...", "confidence": 0.0-1.0, "language": "uz|ru|en"}'
            ),
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=200,
                response_mime_type="application/json",
            ),
        )

        self._initialized = True
        logger.info(
            "GeminiService initialized",
            extra={
                "model": settings.GEMINI_MODEL,
                "clinic": clinic_data.get("clinic_name", "unknown"),
            },
        )

    async def chat(
        self,
        session_id: str,
        message: str,
        patient_context: dict | None = None,
        clinic_id: uuid.UUID | None = None,
        db: Any | None = None,
        language: str = "uz",
    ) -> ChatResponse:
        """Main conversation method with function-call handling.

        Args:
            session_id: Unique session identifier.
            message: Visitor's text message.
            patient_context: Optional recognized patient info to prepend.
            clinic_id: Tenant ID for service calls (None → demo mode).
            db: Database session for function execution (None → demo mode).

        Returns:
            ChatResponse with text, function_calls, and optional ui_action.
        """
        if not self._initialized or self.model is None:
            raise AIServiceError("GeminiService not initialized — call initialize() first")

        if not message or not message.strip():
            raise AIServiceError("Cannot send empty message to Gemini")

        start_ts = time.monotonic()

        # Load conversation history (Redis or in-memory fallback)
        # Trim to last 12 entries (6 turns) — faster Gemini responses, enough for booking flow
        history = await self._load_history(session_id)
        if len(history) > 12:
            history = history[-12:]

        # Preprocess time/date references and symptom hints
        processed_message = self._preprocess_time_references(message)
        processed_message = self._add_symptom_hints(processed_message)

        # Build the user message with STRONG language directive
        user_msg = processed_message

        # Language directive — this is the PRIMARY mechanism for language switching.
        # Must be BEFORE the message so Gemini processes it first.
        lang_directives = {
            "ru": "[ЯЗЫК: РУССКИЙ. Отвечай ТОЛЬКО на русском языке. НЕ используй узбекский.]",
            "uz": "",  # Default — system prompt is already in Uzbek, no extra directive needed
        }
        lang_prefix = lang_directives.get(language, "")

        # Patient name — only add if meaningful and not already in message
        name_prefix = ""
        if patient_context:
            name = patient_context.get("full_name", "")
            if name and name not in processed_message:
                # Check if name already in recent history
                name_in_history = False
                for entry in (history or [])[-4:]:
                    parts = getattr(entry, "parts", [])
                    for p in parts:
                        text_val = getattr(p, "text", "")
                        if isinstance(text_val, str) and name.lower() in text_val.lower():
                            name_in_history = True
                            break
                    if name_in_history:
                        break
                if not name_in_history:
                    name_prefix = f"(Bemor: {name}) " if language == "uz" else f"(Пациент: {name}) " if language == "ru" else ""

        # Assemble: [LANG DIRECTIVE] (Patient name) actual message
        parts_list = []
        if lang_prefix:
            parts_list.append(lang_prefix)
        user_msg = name_prefix + processed_message
        if parts_list:
            user_msg = "\n".join(parts_list) + "\n" + user_msg

        # Start or continue chat
        chat_session = self.model.start_chat(history=history)

        # Send message with retry
        response = await self._send_with_retry(chat_session, user_msg, session_id)

        # Process response — handle function calls in a chain
        all_function_calls: list[dict] = []
        chain_depth = 0

        while chain_depth < _MAX_FUNCTION_CHAIN:
            # Safely access response parts (may be empty after retries/errors)
            try:
                parts = response.candidates[0].content.parts
            except (IndexError, AttributeError):
                logger.warning(
                    "Gemini response has no candidates/parts",
                    extra={"session_id": session_id, "chain_depth": chain_depth},
                )
                break

            # Collect ALL function calls from this turn (Gemini may return
            # multiple in one response). We must execute all of them and
            # send all results back together.
            turn_calls: list[tuple[Any, str, dict]] = []  # (fc, name, args)
            for part in parts:
                if hasattr(part, "function_call") and part.function_call and part.function_call.name:
                    fc = part.function_call
                    fn_name = fc.name
                    fn_args = dict(fc.args) if fc.args else {}
                    turn_calls.append((fc, fn_name, fn_args))

            if not turn_calls:
                break

            # Execute all function calls for this turn
            turn_results: list[tuple[str, dict]] = []
            for fc, fn_name, fn_args in turn_calls:
                all_function_calls.append({"name": fn_name, "args": fn_args})
                logger.info(
                    "Gemini function call",
                    extra={
                        "session_id": session_id,
                        "function": fn_name,
                        "args": fn_args,
                        "chain_depth": chain_depth,
                    },
                )
                result = await self._execute_function_call(fc, clinic_id, db)
                all_function_calls[-1]["result"] = result
                turn_results.append((fn_name, result))

            # Send ALL function results back to Gemini in one message
            try:
                response = await self._send_multi_function_results(
                    chat_session, turn_results, session_id
                )
            except AIServiceError:
                # Function result feeding failed after retries — break out
                # of the chain and use whatever text we have so far.
                logger.warning(
                    "Failed to feed function results to Gemini, using fallback",
                    extra={"session_id": session_id, "functions": [r[0] for r in turn_results]},
                )
                break
            chain_depth += 1

        # Extract final text
        text = self._extract_text(response)

        # Sanitise — ensure it's natural language, not JSON
        text = self._sanitise_text(text)

        # Add variety — avoid repeating the same opening phrase
        text = self._add_variety(text, chat_session.history)

        # Fallback when Gemini returned no usable text
        if not text:
            _FALLBACK = {
                "uz": "Kechirasiz, tushunolmadim. Qayta urinib ko'ring.",
                "ru": "Извините, я не понял. Попробуйте ещё раз.",
            }
            text = _FALLBACK.get(language, _FALLBACK["uz"])

        # Final polish for natural Uzbek output
        text = self._polish_uzbek_response(text)

        # Determine UI action from function calls
        ui_action = self._determine_ui_action(all_function_calls)

        # Save updated history
        await self._save_history(session_id, chat_session.history)

        latency_ms = (time.monotonic() - start_ts) * 1000
        logger.info(
            "Gemini chat completed",
            extra={
                "session_id": session_id,
                "input_len": len(message),
                "output_len": len(text),
                "latency_ms": round(latency_ms, 1),
                "function_calls": [fc["name"] for fc in all_function_calls],
            },
        )

        return ChatResponse(
            text=text,
            function_calls=all_function_calls,
            ui_action=ui_action,
        )

    async def classify_intent(self, message: str) -> IntentClassification:
        """Classify visitor intent using structured JSON output."""
        if not self._intent_model:
            raise AIServiceError("GeminiService not initialized — call initialize() first")

        if not message or not message.strip():
            return IntentClassification(intent="UNKNOWN", confidence=0.0, entities={})

        start_ts = time.monotonic()
        prompt = _INTENT_PROMPT.format(message=message)

        response = await self._call_with_retry(
            self._intent_model.generate_content_async,
            prompt,
            "intent_classification",
        )

        latency_ms = (time.monotonic() - start_ts) * 1000
        logger.info(
            "Intent classification completed",
            extra={"input_len": len(message), "latency_ms": round(latency_ms, 1)},
        )

        try:
            result = json.loads(response.text)
            return IntentClassification(
                intent=result.get("intent", "UNKNOWN"),
                confidence=min(max(float(result.get("confidence", 0.0)), 0.0), 1.0),
                entities=result.get("entities", {}),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Failed to parse intent JSON",
                extra={"raw": response.text, "error": str(exc)},
            )
            return IntentClassification(intent="UNKNOWN", confidence=0.0, entities={})

    async def reset_session(self, session_id: str) -> None:
        """Clear conversation history from Redis and in-memory."""
        self._memory_history.pop(session_id, None)
        try:
            from app.core.redis import get_redis

            redis = get_redis()
            await redis.delete(f"chat:{session_id}")
        except Exception as e:
            logger.debug("Redis chat history clear failed", extra={"session_id": session_id, "error": str(e)})
        logger.info("Session reset", extra={"session_id": session_id})

    # ------------------------------------------------------------------
    # Text extraction & sanitisation
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract text from Gemini response, handling multiple parts.

        Safely handles empty candidates / parts to avoid IndexError.
        """
        parts = []
        try:
            candidates = getattr(response, "candidates", None)
            if not candidates:
                logger.warning("Gemini response has no candidates")
                return ""
            content = getattr(candidates[0], "content", None)
            if not content:
                return ""
            for part in content.parts:
                if hasattr(part, "text") and part.text:
                    parts.append(part.text)
        except (IndexError, AttributeError) as exc:
            logger.warning(
                "Failed to extract text from Gemini response",
                extra={"error": str(exc)},
            )
        return " ".join(parts).strip()

    @staticmethod
    def _sanitise_text(text: str) -> str:
        """Ensure response is natural language, not JSON/code.

        Less aggressive than before — only strips actual JSON objects,
        code blocks, and state tags. Preserves quoted strings and short text.
        """
        if not text:
            return ""

        cleaned = text.strip()

        # Strip tags that Gemini might echo back
        cleaned = re.sub(r'\[CURRENT_STATE:\s*[^\]]*\]\s*', '', cleaned).strip()
        cleaned = re.sub(r'\[USER_ACTION:\s*[^\]]*\]\s*', '', cleaned).strip()
        cleaned = re.sub(r'\[SYSTEM:\s*[^\]]*\]\s*', '', cleaned).strip()
        cleaned = re.sub(r'\[Context:\s*[^\]]*\]\s*', '', cleaned).strip()
        cleaned = re.sub(r'\(Bemor:\s*[^)]*\)\s*', '', cleaned).strip()
        cleaned = re.sub(r'\(Пациент:\s*[^)]*\)\s*', '', cleaned).strip()
        cleaned = re.sub(r'\[ЯЗЫК:\s*[^\]]*\]\s*', '', cleaned).strip()
        cleaned = re.sub(r'\[Called\s+[^\]]*\]\s*', '', cleaned).strip()

        # Strip markdown code fences
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        # Only strip if it's a pure JSON object/array (starts AND ends with braces)
        if cleaned.startswith(("{", "[")) and cleaned.endswith(("}", "]")):
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    for key in ("text", "message", "response", "reply", "answer", "javob"):
                        val = parsed.get(key)
                        if val and isinstance(val, str) and len(val) > 3:
                            return val
                return ""
            except (json.JSONDecodeError, ValueError):
                pass  # Not JSON, keep as-is

        # Strip surrounding quotes (but not internal quotes)
        if cleaned.startswith('"') and cleaned.endswith('"') and cleaned.count('"') == 2:
            cleaned = cleaned[1:-1]

        # Only strip code if it truly starts with code markers
        if cleaned.startswith(("```", "import ", "def ", "class ", "function ")):
            return ""

        return cleaned

    # ------------------------------------------------------------------
    # Function result summarisation for history
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize_function_result(fn_name: str, result: dict) -> str:
        """Summarise function results as human-readable text for conversation history.

        Instead of storing raw JSON in history (which wastes tokens and confuses
        Gemini), store a brief Uzbek summary so Gemini can reference it naturally.
        """
        if not result or not isinstance(result, dict):
            return f"[{fn_name}: natija yo'q]"

        if "error" in result:
            return f"[{fn_name}: xatolik — {result.get('message', result['error'])}]"

        if fn_name == "get_department_info":
            docs = result.get("doctors", [])
            if docs:
                names = ", ".join(d.get("name", d.get("full_name", "")) for d in docs[:3])
                return f"[Bo'lim: {result.get('name', '')}. Shifokorlar: {names}]"
            depts = result.get("departments", [])
            if depts:
                names = ", ".join(d.get("name", "") for d in depts[:4])
                return f"[Bo'limlar: {names}]"
            return f"[Bo'lim: {result.get('name', 'topildi')}]"

        if fn_name == "get_available_slots":
            slots = result.get("available_slots", [])
            if isinstance(slots, list) and slots:
                times = ", ".join(s if isinstance(s, str) else s.get("start", "") for s in slots[:5])
                return f"[{result.get('date', '')}: bo'sh vaqtlar — {times}]"
            return f"[{result.get('date', '')}: bo'sh vaqt yo'q]"

        if fn_name == "book_appointment":
            code = result.get("confirmation_code", "")
            return f"[Qabul yozildi. Kod: {code}]"

        if fn_name == "lookup_patient":
            if result.get("found"):
                return f"[Bemor topildi: {result.get('full_name', '')}]"
            return "[Bemor topilmadi]"

        if fn_name == "register_patient":
            return f"[Bemor ro'yxatdan o'tdi: {result.get('full_name', '')}]"

        if fn_name == "check_in":
            if result.get("success"):
                return f"[Check-in muvaffaqiyatli. Navbat: {result.get('queue_position', '?')}]"
            return f"[Check-in: {result.get('message', 'natija')}]"

        if fn_name == "get_queue_status":
            return f"[Navbat: {result.get('waiting_count', '?')} kishi, ~{result.get('estimated_wait_minutes', '?')} daqiqa]"

        if fn_name == "issue_queue_ticket":
            return f"[Chiptangiz: {result.get('ticket_number', '?')}]"

        if fn_name == "search_faq":
            results_list = result.get("results", [])
            if results_list:
                return f"[FAQ: {len(results_list)} ta javob topildi]"
            return "[FAQ: javob topilmadi]"

        if fn_name == "process_payment":
            return f"[To'lov: {result.get('status', result.get('message', 'jarayonda'))}]"

        if fn_name == "escalate_to_human":
            return "[Xodimga uzatildi]"

        # Fallback
        return f"[{fn_name}: bajarildi]"

    # ------------------------------------------------------------------
    # Anti-repetition
    # ------------------------------------------------------------------

    @staticmethod
    def _add_variety(text: str, history: list) -> str:
        """Add variety to responses by replacing repeated greeting patterns.

        Checks if the response starts with the same phrase as a recent model
        response. If so, swaps in an alternative to avoid robotic repetition.
        """
        if not text or not history:
            return text

        # Collect recent model responses
        recent_starts: list[str] = []
        for entry in history[-6:]:
            if getattr(entry, "role", "") == "model":
                for part in getattr(entry, "parts", []):
                    t = getattr(part, "text", "")
                    if t and not t.startswith("["):
                        # Take first ~40 chars as the "opening"
                        recent_starts.append(t[:40].lower().strip())

        if not recent_starts:
            return text

        text_start = text[:40].lower().strip()

        # Check if we're repeating ourselves
        repeating = any(text_start == rs for rs in recent_starts)
        if not repeating:
            return text

        # Swap opening phrases to add variety
        _ALTERNATIVES = {
            "albatta": ["Xo'p", "Bo'ldi", "Ha, hozir"],
            "xo'p": ["Albatta", "Yaxshi", "Bo'ldi"],
            "yaxshi": ["Xo'p", "Tushundim", "Bo'ldi"],
            "tushundim": ["Xo'p", "Yaxshi", "Bo'ldi"],
            "marhamat": ["Albatta", "Xo'p", "Ha"],
            "hozir": ["Bir lahza", "Ko'rib beraman", "Ha, hozir"],
        }

        for key, alts in _ALTERNATIVES.items():
            if text.lower().startswith(key):
                replacement = random.choice(alts)
                # Preserve the case pattern of the original
                return replacement + text[len(key):]

        return text

    # ------------------------------------------------------------------
    # Smart preprocessing — time, symptoms, polish
    # ------------------------------------------------------------------

    def _preprocess_time_references(self, text: str) -> str:
        """Normalize colloquial time references to help Gemini understand.

        Converts things like '2 ga' → '14:00 ga', 'ertaga' → actual date, etc.
        Does NOT modify the original text — adds a hidden hint for Gemini.
        """
        hints: list[str] = []
        text_lower = text.lower().strip()

        tz = timezone(timedelta(hours=5))  # Tashkent
        now = datetime.now(tz)
        today = now.date()
        tomorrow = today + timedelta(days=1)

        # Date references
        if any(w in text_lower for w in ['bugun', 'hozir', 'tezroq', 'сегодня', 'today']):
            hints.append(f"[sana: {today.isoformat()}]")
        elif any(w in text_lower for w in ['ertaga', 'завтра', 'tomorrow']):
            hints.append(f"[sana: {tomorrow.isoformat()}]")

        # Weekday references (Uzbek)
        weekdays_uz = {
            'dushanba': 0, 'seshanba': 1, 'chorshanba': 2, 'payshanba': 3,
            'juma': 4, 'shanba': 5, 'yakshanba': 6,
        }
        for day_name, day_num in weekdays_uz.items():
            if day_name in text_lower:
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target = today + timedelta(days=days_ahead)
                hints.append(f"[sana: {target.isoformat()}, {day_name}]")
                break

        # Colloquial time: "2 ga", "3 da", "10 ga"
        time_match = re.search(r'(\d{1,2})\s*(?:ga|da|ge|de)\b', text_lower)
        if time_match:
            hour = int(time_match.group(1))
            # Assume PM for hours 1-6 (clinic hours)
            if 1 <= hour <= 6:
                hour += 12
            if 7 <= hour <= 18:
                hints.append(f"[vaqt: {hour:02d}:00]")

        # "ertalab" = morning, "peshin"/"tushdan keyin" = afternoon
        if any(w in text_lower for w in ['ertalab', 'утром', 'morning']):
            hints.append("[vaqt oralig'i: 08:00-12:00]")
        elif any(w in text_lower for w in ['peshin', 'tushdan keyin', 'kechqurun', 'после обеда', 'afternoon']):
            hints.append("[vaqt oralig'i: 14:00-18:00]")

        # "yarim" = :30
        if 'yarim' in text_lower:
            hints.append("[yarim soat = :30]")

        # Phone number normalization hint
        phone_match = re.search(r'(\d[\d\s\-]{6,})', text_lower)
        if phone_match:
            digits = re.sub(r'\D', '', phone_match.group(1))
            if len(digits) >= 9:
                if not digits.startswith('998'):
                    digits = '998' + digits[-9:]
                hints.append(f"[telefon: +{digits}]")

        if hints:
            return text + " " + " ".join(hints)

        return text

    # Symptom → Department mapping for hint injection
    _SYMPTOM_DEPT_MAP: dict[str, str] = {
        # Uzbek symptoms
        "bosh og'riq": 'nevrologiya', "boshim og'riydi": 'nevrologiya',
        'bosh aylan': 'nevrologiya', 'uyqu': 'nevrologiya', 'asab': 'nevrologiya',
        'tish': 'stomatologiya', 'tishim': 'stomatologiya', 'milk tish': 'stomatologiya',
        "ko'z": 'oftalmologiya', "ko'zim": 'oftalmologiya', "ko'r": 'oftalmologiya',
        'yurak': 'kardiologiya', 'yuragim': 'kardiologiya', 'bosim': 'kardiologiya',
        'qon bosim': 'kardiologiya',
        'qorin': 'gastroenterologiya', 'oshqozon': 'gastroenterologiya',
        'ich ket': 'gastroenterologiya', 'qayt': 'gastroenterologiya', 'qornim': 'gastroenterologiya',
        'quloq': 'lor', 'burun': 'lor', 'tomoq': 'lor', 'tomoqim': 'lor',
        'teri': 'dermatologiya', 'toshma': 'dermatologiya', 'qichish': 'dermatologiya',
        'allergiya': 'dermatologiya',
        'bola': 'pediatriya', 'bolam': 'pediatriya',
        'homilador': 'ginekologiya', 'ayollar': 'ginekologiya', 'ginekolog': 'ginekologiya',
        'suyak': 'ortopediya', "bo'g'im": 'ortopediya', 'belim': 'ortopediya',
        "bel og'riq": 'ortopediya', 'orqa': 'ortopediya',
        'operatsiya': 'xirurgiya', 'jarroh': 'xirurgiya', 'xirurg': 'xirurgiya',
        'tekshiruv': 'terapiya', 'analiz': 'terapiya', 'check-up': 'terapiya',
        'umumiy': 'terapiya', 'shamollash': 'terapiya', 'isitma': 'terapiya',
        'stress': 'psixologiya', 'depressiya': 'psixologiya', 'ruhiy': 'psixologiya',
        # Russian symptoms
        'голова': 'nevrologiya', 'головная': 'nevrologiya',
        'зуб': 'stomatologiya', 'зубы': 'stomatologiya',
        'глаз': 'oftalmologiya', 'зрение': 'oftalmologiya',
        'сердце': 'kardiologiya', 'давление': 'kardiologiya',
        'живот': 'gastroenterologiya', 'желудок': 'gastroenterologiya',
        'ухо': 'lor', 'нос': 'lor', 'горло': 'lor',
        'кожа': 'dermatologiya', 'сыпь': 'dermatologiya',
        'ребенок': 'pediatriya', 'ребёнок': 'pediatriya',
        'спина': 'ortopediya', 'поясница': 'ortopediya',
        # Common no-apostrophe variants (kiosk keyboard input)
        'boshim ogriydi': 'nevrologiya', 'bosh ogriq': 'nevrologiya',
        'tishim ogriydi': 'stomatologiya',
        'kozim': 'oftalmologiya', 'koz': 'oftalmologiya',
        'yuragim ogriydi': 'kardiologiya',
        'qornim ogriydi': 'gastroenterologiya',
        'qulogim ogriydi': 'lor',
        'belim ogriydi': 'ortopediya', 'bel ogriq': 'ortopediya',
        'bogim': 'ortopediya',
    }

    def _add_symptom_hints(self, text: str) -> str:
        """Detect symptoms in text and add department hints for Gemini."""
        text_lower = text.lower()
        detected: set[str] = set()

        for symptom, dept in self._SYMPTOM_DEPT_MAP.items():
            if symptom in text_lower:
                detected.add(dept)

        if detected:
            dept_hint = ", ".join(detected)
            return text + f" [mos bo'lim: {dept_hint}]"
        return text

    def _polish_uzbek_response(self, text: str) -> str:
        """Final polish for natural Uzbek output."""
        if not text:
            return text

        result = text

        # Fix double spaces
        result = re.sub(r' {2,}', ' ', result)

        # Fix common Gemini Uzbek mistakes
        _REPLACEMENTS = {
            'Sizga qanday yordam bera olaman?': 'Nima qilib beray?',
            'Sizga qanday yordam bera olaman': 'Nima qilib beray',
            'Men sizga yordam berishga tayyorman': 'Yordam beraman',
            'Hurmatli bemor': '',
            'hurmatli bemor': '',
            'null': '',
            'undefined': '',
            'None': '',
            'Error': 'muammo',
            'error': 'muammo',
        }

        for old, new in _REPLACEMENTS.items():
            if old in result:
                result = result.replace(old, new)

        # Remove trailing punctuation weirdness
        result = result.strip()
        result = re.sub(r'[.]{2,}', '.', result)   # Fix multiple dots
        result = re.sub(r'[!]{2,}', '!', result)   # Fix multiple exclamation marks

        result = result.strip()

        # Ensure response doesn't start with a lowercase letter (looks broken)
        if result and result[0].islower() and not result.startswith(('va ', 'yoki ', 'ham ')):
            result = result[0].upper() + result[1:]

        return result

    # ------------------------------------------------------------------
    # Retry logic
    # ------------------------------------------------------------------

    async def _send_with_retry(
        self, chat_session: Any, message: Any, session_id: str
    ) -> Any:
        """Send a message via chat session with retry and timeout."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    chat_session.send_message_async(message),
                    timeout=_GEMINI_TIMEOUT_S,
                )
                return response
            except IndexError:
                # The SDK's _check_response crashes with IndexError when
                # Gemini returns empty candidates (safety filter, overload,
                # or malformed function response).  The response was still
                # appended to history by the SDK — we just need to retry
                # or recover gracefully.
                logger.warning(
                    "Gemini returned empty candidates (IndexError in SDK)",
                    extra={"session_id": session_id, "attempt": attempt},
                )
                if attempt == _MAX_RETRIES:
                    raise AIServiceError(
                        "Gemini returned empty response after retries"
                    )
                # Remove the last two history entries (our message + empty
                # model response) so the retry starts clean.
                try:
                    if len(chat_session.history) >= 2:
                        chat_session.history.pop()  # empty model response
                        chat_session.history.pop()  # our message
                except Exception as e:
                    logger.debug("Failed to trim Gemini history after IndexError", extra={"error": str(e)})
            except asyncio.TimeoutError:
                logger.warning(
                    "Gemini timeout",
                    extra={"session_id": session_id, "attempt": attempt},
                )
                if attempt == _MAX_RETRIES:
                    raise AIServiceError("Gemini API timed out after retries")
            except (
                google_exceptions.ResourceExhausted,
                google_exceptions.ServiceUnavailable,
                google_exceptions.InternalServerError,
            ) as exc:
                logger.warning(
                    "Gemini API error (retryable)",
                    extra={"session_id": session_id, "attempt": attempt, "error": str(exc)},
                )
                if attempt == _MAX_RETRIES:
                    raise AIServiceError(f"Gemini API failed after {_MAX_RETRIES} retries: {exc}")
            except google_exceptions.GoogleAPIError as exc:
                logger.error("Gemini API error (non-retryable)", extra={"error": str(exc)})
                raise AIServiceError(f"Gemini API error: {exc}")

            backoff = _BASE_BACKOFF_S * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)

        raise AIServiceError("Gemini API call failed")

    async def _call_with_retry(
        self, async_fn: Any, content: Any, label: str
    ) -> Any:
        """Call an async Gemini function with retry and timeout."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    async_fn(content),
                    timeout=_GEMINI_TIMEOUT_S,
                )
                return response
            except asyncio.TimeoutError:
                logger.warning(f"Gemini {label} timeout", extra={"attempt": attempt})
                if attempt == _MAX_RETRIES:
                    raise AIServiceError(f"Gemini {label} timed out after retries")
            except (
                google_exceptions.ResourceExhausted,
                google_exceptions.ServiceUnavailable,
                google_exceptions.InternalServerError,
            ) as exc:
                logger.warning(
                    f"Gemini {label} error (retryable)",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                if attempt == _MAX_RETRIES:
                    raise AIServiceError(
                        f"Gemini {label} failed after {_MAX_RETRIES} retries: {exc}"
                    )
            except google_exceptions.GoogleAPIError as exc:
                logger.error(f"Gemini {label} error (non-retryable)", extra={"error": str(exc)})
                raise AIServiceError(f"Gemini {label} error: {exc}")

            backoff = _BASE_BACKOFF_S * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)

        raise AIServiceError(f"Gemini {label} call failed")

    # ------------------------------------------------------------------
    # Function result feeding
    # ------------------------------------------------------------------

    async def _send_function_result(
        self, chat_session: Any, fn_name: str, result: dict, session_id: str
    ) -> Any:
        """Send function execution result back to Gemini for natural language response."""
        from google.protobuf import json_format, struct_pb2

        # Convert result to Protobuf Struct preserving types (lists, nested dicts)
        s = struct_pb2.Struct()
        try:
            safe_result = result if isinstance(result, dict) else {"result": str(result)}
            # json_format handles nested structures properly
            json_format.ParseDict(safe_result, s)
        except Exception:
            # Fallback: flatten to strings if protobuf conversion fails
            clean: dict[str, Any] = {}
            for k, v in (result if isinstance(result, dict) else {"result": str(result)}).items():
                if isinstance(v, (dict, list)):
                    clean[k] = json.dumps(v, ensure_ascii=False, default=str)
                elif v is not None:
                    clean[k] = str(v)
                else:
                    clean[k] = ""
            s.update(clean)

        part = genai.protos.Part(
            function_response=genai.protos.FunctionResponse(
                name=fn_name,
                response=s,
            )
        )

        return await self._send_with_retry(chat_session, part, session_id)

    async def _send_multi_function_results(
        self,
        chat_session: Any,
        results: list[tuple[str, dict]],
        session_id: str,
    ) -> Any:
        """Send multiple function results back to Gemini in one message.

        Gemini requires that ALL function_response parts match ALL
        function_call parts from the previous turn.  We wrap them in
        a single Content with role="function" so the SDK sends them
        as one atomic message.
        """
        if len(results) == 1:
            return await self._send_function_result(
                chat_session, results[0][0], results[0][1], session_id
            )

        from google.protobuf import json_format, struct_pb2

        parts = []
        for fn_name, result in results:
            s = struct_pb2.Struct()
            try:
                safe_result = result if isinstance(result, dict) else {"result": str(result)}
                json_format.ParseDict(safe_result, s)
            except Exception:
                clean: dict[str, Any] = {}
                for k, v in (result if isinstance(result, dict) else {"result": str(result)}).items():
                    if isinstance(v, (dict, list)):
                        clean[k] = json.dumps(v, ensure_ascii=False, default=str)
                    elif v is not None:
                        clean[k] = str(v)
                    else:
                        clean[k] = ""
                s.update(clean)

            parts.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fn_name,
                        response=s,
                    )
                )
            )

        # Wrap all parts in a single Content with role="user".  The SDK
        # assigns role="user" when you pass a single Part, so we must do the
        # same for multi-part.  The function_response data is in the Parts
        # themselves — the Content role is just "user".
        content = genai.protos.Content(role="user", parts=parts)
        return await self._send_with_retry(chat_session, content, session_id)

    # ------------------------------------------------------------------
    # History: Redis with in-memory fallback
    # ------------------------------------------------------------------

    async def _load_history(self, session_id: str) -> list:
        """Load conversation history from Redis, falling back to in-memory."""
        # Try Redis first
        try:
            from app.core.redis import get_redis

            redis = get_redis()
            raw = await redis.get(f"chat:{session_id}")
            if raw:
                return self._deserialise_history(json.loads(raw))
        except Exception as exc:
            logger.debug(f"Redis history unavailable, using memory: {exc}")

        # In-memory fallback
        return self._memory_history.get(session_id, [])

    async def _save_history(self, session_id: str, history: list) -> None:
        """Save conversation history to Redis and in-memory."""
        serialised = self._serialise_history(history)

        # Always save in memory (as Gemini Content objects for direct reuse)
        self._memory_history[session_id] = self._deserialise_history(serialised)

        # Try Redis
        try:
            from app.core.redis import get_redis

            redis = get_redis()
            await redis.set(
                f"chat:{session_id}",
                json.dumps(serialised, default=str),
                ex=_SESSION_TTL_S,
            )
        except Exception as exc:
            logger.debug(f"Redis history save failed, memory only: {exc}")

    @staticmethod
    def _serialise_history(history: list) -> list[dict]:
        """Convert Gemini Content objects to JSON-serialisable dicts.

        Function calls/responses are stored with metadata so _deserialise_history
        can reconstruct human-readable summaries.
        """
        entries = []
        for content in history:
            parts = []
            for part in content.parts:
                if hasattr(part, "text") and part.text:
                    parts.append({"text": part.text})
                elif (
                    hasattr(part, "function_call")
                    and part.function_call
                    and part.function_call.name
                ):
                    parts.append({
                        "function_call": {
                            "name": part.function_call.name,
                            "args": dict(part.function_call.args)
                            if part.function_call.args
                            else {},
                        }
                    })
                elif (
                    hasattr(part, "function_response")
                    and part.function_response
                    and part.function_response.name
                ):
                    # Store response name + result summary for history
                    fr = part.function_response
                    resp_data = {}
                    try:
                        resp_data = dict(fr.response) if fr.response else {}
                    except Exception:
                        pass
                    parts.append({
                        "function_response": {
                            "name": fr.name,
                            "result": resp_data,
                        }
                    })
            if parts:
                entries.append({"role": content.role, "parts": parts})
        return entries

    @staticmethod
    def _deserialise_history(entries: list[dict]) -> list:
        """Convert stored dicts back to Gemini Content format.

        Uses _summarize_function_result for human-readable function summaries
        instead of raw JSON — saves tokens and helps Gemini reference past actions.
        """
        history = []
        for entry in entries:
            text_parts = []
            for p in entry.get("parts", []):
                if "text" in p and p["text"]:
                    text_parts.append(genai.protos.Part(text=p["text"]))
                elif "function_call" in p:
                    # Brief note that a function was called
                    fc = p["function_call"]
                    text_parts.append(genai.protos.Part(text=f"[{fc['name']} chaqirildi]"))
                elif "function_response" in p:
                    # Human-readable summary of function result
                    fr = p["function_response"]
                    result = fr.get("result", {})
                    summary = GeminiService._summarize_function_result(fr["name"], result)
                    text_parts.append(genai.protos.Part(text=summary))
            if text_parts:
                # Avoid consecutive same-role entries (Gemini rejects them)
                if history and history[-1].role == entry["role"]:
                    history[-1].parts.extend(text_parts)
                else:
                    history.append(
                        genai.protos.Content(role=entry["role"], parts=text_parts)
                    )
        return history

    # ------------------------------------------------------------------
    # Function execution — real DB or demo fallback
    # ------------------------------------------------------------------

    async def _execute_function_call(
        self,
        function_call: Any,
        clinic_id: uuid.UUID | None,
        db: Any | None,
    ) -> dict:
        """Execute a Gemini function call.

        Tries the real DB implementation first; falls back to demo data
        if clinic_id/db are missing or the DB call fails.
        """
        fn_name = function_call.name
        args = dict(function_call.args) if function_call.args else {}

        # Try real DB implementation if we have a database context
        if clinic_id and db:
            try:
                result = await self._execute_real(fn_name, args, clinic_id, db)
                if result and "error" not in result:
                    return result
                logger.debug(
                    f"Real function returned error, trying demo: {result}",
                    extra={"function": fn_name},
                )
            except Exception as exc:
                logger.warning(
                    f"Real function failed, using demo fallback: {exc}",
                    extra={"function": fn_name},
                )

        # Demo fallback
        return await self._execute_demo(fn_name, args)

    async def _execute_real(
        self, fn_name: str, args: dict, clinic_id: uuid.UUID, db: Any
    ) -> dict:
        """Execute function against real database services."""
        from sqlalchemy.ext.asyncio import AsyncSession

        if not isinstance(db, AsyncSession):
            return {"error": "Invalid database session"}

        if fn_name == "book_appointment":
            # Validate required fields before attempting booking
            missing = []
            if not args.get("doctor_id"):
                missing.append("shifokor")
            if not args.get("date"):
                missing.append("sana")
            if not args.get("time"):
                missing.append("vaqt")
            if missing:
                return {
                    "status": "incomplete",
                    "message": f"Qabulni yakunlash uchun kerak: {', '.join(missing)}",
                    "missing_fields": missing,
                }
            return await self._fn_real_book_appointment(db, clinic_id, args)
        elif fn_name == "check_in":
            return await self._fn_real_check_in(db, clinic_id, args)
        elif fn_name == "lookup_patient":
            return await self._fn_real_lookup_patient(db, clinic_id, args)
        elif fn_name == "register_patient":
            return await self._fn_real_register_patient(db, clinic_id, args)
        elif fn_name == "get_available_slots":
            return await self._fn_real_get_available_slots(db, clinic_id, args)
        elif fn_name == "get_department_info":
            return await self._fn_real_get_department_info(db, clinic_id, args)
        elif fn_name == "get_doctor_info":
            return await self._fn_real_get_doctor_info(db, clinic_id, args)
        elif fn_name == "process_payment":
            return await self._fn_real_process_payment(db, clinic_id, args)
        elif fn_name == "get_queue_status":
            return await self._fn_real_get_queue_status(db, clinic_id, args)
        elif fn_name == "issue_queue_ticket":
            return await self._fn_real_issue_queue_ticket(db, clinic_id, args)
        elif fn_name == "search_faq":
            return await self._fn_real_search_faq(db, clinic_id, args)
        elif fn_name == "escalate_to_human":
            return await self._fn_escalate_to_human(args)
        else:
            return {"error": f"Unknown function: {fn_name}"}

    async def _execute_demo(self, fn_name: str, args: dict) -> dict:
        """Execute function with demo/hardcoded data (no DB needed)."""
        handler = getattr(self, f"_fn_demo_{fn_name}", None)
        if handler:
            return await handler(**args)
        # Generic handlers that work without DB
        if fn_name == "escalate_to_human":
            return await self._fn_escalate_to_human(args)
        logger.warning(f"No demo handler for function: {fn_name}")
        return {"error": f"Function {fn_name} mavjud emas"}

    # ------------------------------------------------------------------
    # UI action resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_ui_action(function_calls: list[dict]) -> str | None:
        """Determine a UI navigation hint based on executed data functions.

        Derives the UI action automatically from which data function was
        called — no explicit navigate_screen needed.  Scans backwards so
        the most recent function takes priority.
        """
        if not function_calls:
            return None

        # Derive UI action from data functions
        for fc in reversed(function_calls):
            name = fc["name"]
            result = fc.get("result") or {}

            if name == "get_department_info":
                # If returned doctors for a specific dept → show doctors
                if isinstance(result.get("doctors"), list) and result["doctors"]:
                    return "show_doctors"
                if result.get("department_id") or result.get("name"):
                    return "show_departments"
                if result.get("departments"):
                    return "show_departments"

            elif name == "get_doctor_info":
                return "show_doctors"

            elif name == "get_available_slots":
                return "show_slots"

            elif name == "book_appointment":
                return "show_queue_ticket"

            elif name == "check_in":
                return "show_checkin"

            elif name == "issue_queue_ticket":
                return "show_queue_ticket"

            elif name == "process_payment":
                return "show_payment"

            elif name == "search_faq":
                return "show_faq"

            elif name == "escalate_to_human":
                return "show_handoff"

            elif name == "get_queue_status":
                return "show_queue_status"

        return None

    # ==================================================================
    # REAL DB function implementations
    # ==================================================================

    async def _fn_real_book_appointment(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.schemas.appointment import AppointmentCreate
        from app.services import appointment_service

        scheduled_at = datetime.strptime(
            f"{args['date']} {args['time']}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)

        data = AppointmentCreate(
            patient_id=uuid.UUID(args.get("patient_id", str(uuid.uuid4()))),
            doctor_id=uuid.UUID(args["doctor_id"]),
            service_id=uuid.UUID(args["service_id"]),
            scheduled_at=scheduled_at,
            duration_minutes=30,
        )
        appt = await appointment_service.book_appointment(db, clinic_id, data)
        return {
            "appointment_id": str(appt.id),
            "doctor_id": str(appt.doctor_id),
            "scheduled_at": appt.scheduled_at.isoformat(),
            "status": appt.status.value,
        }

    async def _fn_real_check_in(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.services import appointment_service, patient_service

        identifier = args["patient_identifier"]

        # Try as UUID first (appointment_id or patient_id)
        try:
            parsed_uuid = uuid.UUID(identifier)
        except ValueError:
            parsed_uuid = None

        if parsed_uuid:
            # Could be an appointment UUID — try direct check-in
            try:
                appt = await appointment_service.check_in(db, clinic_id, parsed_uuid)
                return {
                    "appointment_id": str(appt.id),
                    "status": appt.status.value,
                    "message": "Successfully checked in",
                }
            except Exception:
                # Not an appointment UUID — try as patient_id below
                pass

            # Try as patient_id — find today's scheduled appointment
            today = date.today()
            appts = await appointment_service.list_appointments(
                db, clinic_id, date_from=today, date_to=today, patient_id=parsed_uuid,
            )
            scheduled = [a for a in appts if a.status.value == "SCHEDULED"]
            if scheduled:
                appt = await appointment_service.check_in(db, clinic_id, scheduled[0].id)
                return {
                    "appointment_id": str(appt.id),
                    "status": appt.status.value,
                    "message": "Successfully checked in",
                }
            return {"error": True, "message": "No scheduled appointment found for today"}

        # Not a UUID — treat as phone number
        # Normalize: strip spaces/dashes, add +998 if needed
        phone = identifier.strip().replace(" ", "").replace("-", "")
        if phone.startswith("998") and not phone.startswith("+"):
            phone = "+" + phone
        elif not phone.startswith("+998") and len(phone) >= 9:
            phone = "+998" + phone.lstrip("+")

        patient = await patient_service.lookup_by_phone(db, clinic_id, phone)
        if not patient:
            return {"error": True, "message": "Patient not found with this phone number"}

        patient_uuid = uuid.UUID(str(patient["id"]))
        today = date.today()
        appts = await appointment_service.list_appointments(
            db, clinic_id, date_from=today, date_to=today, patient_id=patient_uuid,
        )
        scheduled = [a for a in appts if a.status.value == "SCHEDULED"]
        if not scheduled:
            return {
                "error": True,
                "message": "No scheduled appointment found for today",
                "patient_name": patient.get("full_name", ""),
            }

        appt = await appointment_service.check_in(db, clinic_id, scheduled[0].id)
        return {
            "appointment_id": str(appt.id),
            "status": appt.status.value,
            "patient_name": patient.get("full_name", ""),
            "message": "Successfully checked in",
        }

    async def _fn_real_lookup_patient(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.services import patient_service

        result = await patient_service.lookup_by_phone(db, clinic_id, args["phone"])
        if result:
            return {
                "found": True,
                "patient_id": str(result["id"]),
                "full_name": result["full_name"],
                "language_preference": result.get("language_preference", "uz"),
            }
        return {"found": False, "message": "Patient not found with this phone number"}

    async def _fn_real_register_patient(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.schemas.patient import PatientCreate
        from app.services import patient_service

        dob = args.get("date_of_birth")
        data = PatientCreate(
            full_name=args["name"],
            phone=args["phone"],
            date_of_birth=date.fromisoformat(dob) if dob else None,
            language_preference=args.get("language", "uz"),
        )
        result = await patient_service.register_patient(db, clinic_id, data)
        return {
            "patient_id": str(result["id"]),
            "full_name": result["full_name"],
            "message": "Patient registered successfully",
        }

    async def _fn_real_get_available_slots(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.services import doctor_service

        target_date = date.fromisoformat(args["date"])
        doctor_id = uuid.UUID(args["doctor_id"])
        slots = await doctor_service.get_available_slots(db, clinic_id, doctor_id, target_date)
        available = [
            {"start": s.start_time.strftime("%H:%M"), "end": s.end_time.strftime("%H:%M")}
            for s in slots
            if s.is_available
        ]
        return {
            "doctor_id": args["doctor_id"],
            "date": args["date"],
            "available_slots": available,
            "total_available": len(available),
        }

    async def _fn_real_get_department_info(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.services import department_service

        departments = await department_service.list_departments(db, clinic_id)
        query = args["department_name"].lower()
        for dept in departments:
            name = dept.get("name", "") if isinstance(dept, dict) else getattr(dept, "name", "")
            if query in name.lower():
                if isinstance(dept, dict):
                    return {
                        "department_id": str(dept.get("id", "")),
                        "name": dept.get("name", ""),
                        "description": dept.get("description", ""),
                        "floor": dept.get("floor"),
                        "room_number": dept.get("room_number", ""),
                        "doctor_count": dept.get("doctor_count", 0),
                    }
                return {
                    "department_id": str(dept.id),
                    "name": dept.name,
                    "description": dept.description or "",
                    "floor": dept.floor,
                    "room_number": dept.room_number or "",
                }
        return {"error": f"Department '{args['department_name']}' not found"}

    async def _fn_real_get_doctor_info(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.services import doctor_service

        doctors = await doctor_service.list_doctors(db, clinic_id)
        query = args["doctor_name"].lower()
        for doc in doctors:
            if query in doc.full_name.lower():
                return {
                    "doctor_id": str(doc.id),
                    "full_name": doc.full_name,
                    "specialty": doc.specialty or "",
                    "department": doc.department.name if doc.department else "",
                    "is_active": doc.is_active,
                }
        return {"error": f"Doctor '{args['doctor_name']}' not found"}

    async def _fn_real_process_payment(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.schemas.payment import PaymentInitiate
        from app.services import payment_service

        data = PaymentInitiate(
            patient_id=uuid.UUID(args["patient_id"]),
            amount=float(args["amount"]),
            method=args["method"].upper(),
        )
        payment = await payment_service.initiate_payment(db, clinic_id, data)
        return {
            "payment_id": str(payment.id),
            "amount": str(payment.amount),
            "method": payment.method,
            "status": payment.status.value if hasattr(payment.status, "value") else str(payment.status),
            "message": "Payment initiated",
        }

    async def _fn_real_get_queue_status(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.services import queue_service

        stats = await queue_service.get_queue_stats(db, clinic_id)
        dept_id = args["department_id"]
        for stat in stats:
            if str(stat.get("department_id", "")) == dept_id:
                return stat
        return {
            "department_id": dept_id,
            "waiting_count": 0,
            "avg_wait_minutes": 0,
            "message": "No queue data for this department",
        }

    async def _fn_real_issue_queue_ticket(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.schemas.queue import QueueTicketCreate
        from app.services import queue_service

        data = QueueTicketCreate(
            patient_id=uuid.UUID(args["patient_id"]),
            department_id=uuid.UUID(args["department_id"]),
        )
        ticket = await queue_service.issue_ticket(db, clinic_id, data)
        return {
            "ticket_number": ticket.ticket_number,
            "estimated_wait_minutes": ticket.estimated_wait_minutes,
            "message": f"Your queue ticket is {ticket.ticket_number}",
        }

    async def _fn_real_search_faq(
        self, db: Any, clinic_id: uuid.UUID, args: dict
    ) -> dict:
        from app.services import faq_service

        faqs = await faq_service.list_faqs(db, clinic_id)
        query = args["query"].lower()
        matches = []
        for faq in faqs:
            q = (faq.question or "").lower()
            a = (faq.answer or "").lower()
            if query in q or query in a or any(word in q for word in query.split()):
                matches.append({
                    "question": faq.question,
                    "answer": faq.answer,
                    "language": faq.language,
                })
            if len(matches) >= 3:
                break
        if matches:
            return {"results": matches, "count": len(matches)}
        return {"results": [], "count": 0, "message": "No matching FAQs found"}

    async def _fn_escalate_to_human(self, args: dict) -> dict:
        reason = args.get("reason", "Visitor requested human assistance")
        logger.info("Escalation to human staff", extra={"reason": reason})
        return {
            "escalated": True,
            "reason": reason,
            "message": "A staff member has been notified and will assist you shortly.",
        }

    # ==================================================================
    # DEMO function implementations — used when DB is unavailable
    # ==================================================================

    async def _fn_demo_get_department_info(self, department_name: str = "", **kw: Any) -> dict:
        departments = _DEMO_DEPARTMENTS
        query = department_name.lower()
        for dept in departments:
            if query in dept["name"].lower() or query in dept.get("description", "").lower():
                # Include doctors for this department so the frontend can display them
                dept_id = dept["id"]
                doctors = _DEMO_DOCTORS.get(dept_id, [])
                return {**dept, "doctors": doctors}
        # Return all departments if no match
        return {"departments": departments, "count": len(departments)}

    async def _fn_demo_get_doctor_info(self, doctor_name: str = "", **kw: Any) -> dict:
        query = doctor_name.lower()
        for dept_doctors in _DEMO_DOCTORS.values():
            for doc in dept_doctors:
                if query in doc["name"].lower():
                    return doc
        return {"error": f"'{doctor_name}' topilmadi"}

    async def _fn_demo_get_available_slots(
        self, doctor_id: str = "", date: str = "", **kw: Any
    ) -> dict:
        today = __import__("datetime").date.today()
        if date in ("bugun", "today", "сегодня"):
            target = today
        elif date in ("ertaga", "tomorrow", "завтра"):
            target = today + timedelta(days=1)
        else:
            try:
                target = datetime.strptime(date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                target = today

        all_slots = [
            "09:00", "09:30", "10:00", "10:30", "11:00",
            "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00",
        ]
        random.seed(hash(f"{doctor_id}{target}"))
        available = [s for s in all_slots if random.random() > 0.4]

        return {
            "doctor_id": doctor_id,
            "date": target.strftime("%Y-%m-%d"),
            "date_display": target.strftime("%d.%m.%Y"),
            "available_slots": available,
            "total_available": len(available),
        }

    async def _fn_demo_book_appointment(
        self,
        doctor_id: str = "",
        patient_name: str = "",
        patient_phone: str = "",
        date: str = "",
        time: str = "",
        service_id: str = "",
        **kw: Any,
    ) -> dict:
        phone = patient_phone.replace(" ", "").replace("-", "")
        if not phone.startswith("+998"):
            digits = "".join(c for c in phone if c.isdigit())
            phone = "+998" + digits[-9:] if len(digits) >= 9 else "+998" + digits

        code = f"MZB-{random.randint(10000, 99999)}"

        # Find doctor name from demo data
        doctor_name = doctor_id
        for dept_doctors in _DEMO_DOCTORS.values():
            for doc in dept_doctors:
                if doc["id"] == doctor_id:
                    doctor_name = doc["name"]
                    break

        return {
            "success": True,
            "confirmation_code": code,
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "patient_name": patient_name,
            "patient_phone": phone,
            "date": date,
            "time": time,
        }

    async def _fn_demo_check_in(self, patient_identifier: str = "", **kw: Any) -> dict:
        return {
            "success": True,
            "patient_name": "Bemor",
            "appointment_time": "14:00",
            "doctor": "Nasirxodjaev Yo.B.",
            "department": "Endokrinologiya",
            "queue_position": 3,
            "estimated_wait": "15 daqiqa",
        }

    async def _fn_demo_lookup_patient(self, phone: str = "", **kw: Any) -> dict:
        return {"found": False, "message": "Bemor topilmadi. Ro'yxatdan o'tish kerak."}

    async def _fn_demo_register_patient(
        self, name: str = "", phone: str = "", **kw: Any
    ) -> dict:
        return {
            "patient_id": str(uuid.uuid4()),
            "full_name": name,
            "phone": phone,
            "message": "Bemor ro'yxatdan o'tkazildi",
        }

    async def _fn_demo_get_queue_status(self, department_id: str = "", **kw: Any) -> dict:
        return {
            "department": department_id,
            "current_number": random.randint(10, 30),
            "waiting_count": random.randint(2, 8),
            "estimated_wait_minutes": random.randint(5, 25),
        }

    async def _fn_demo_search_faq(self, query: str = "", **kw: Any) -> dict:
        faqs = [
            {"q": "ish vaqti", "a": "Nano Medical Clinic dushanba-shanba 08:00-17:00 ishlaydi. Yakshanba dam olish."},
            {"q": "to'lov", "a": "Naqd, Uzcard, Humo, Click, Payme qabul qilinadi."},
            {"q": "konsultatsiya narx", "a": "Konsultatsiya 260,000 so'm, professor konsultatsiyasi 500,000 so'm."},
            {"q": "checkup", "a": "Erkaklar va ayollar uchun to'liq checkup 2,000,000 so'm."},
            {"q": "manzil", "a": "Toshkent shahri, Olmazor tumani, Talabalar ko'chasi, 52-uy."},
            {"q": "telefon", "a": "+998 78 113 08 88, +998 55 500 05 50, +998 99 467 80 00."},
            {"q": "narx palata", "a": "Terapiya palata 1,500,000, Xirurgiya 1,200,000, Radiologiya 1,100,000, Reanimatsiya 2,100,000 so'm/kun."},
            {"q": "shifokor", "a": "Endokrinolog, jarroh (proktolog), nevropatolog, kardiolog va mammolog ishlaydi."},
        ]
        q_lower = query.lower()
        matches = [f for f in faqs if any(w in q_lower for w in f["q"].split())]
        if matches:
            return {"results": [{"question": m["q"], "answer": m["a"]} for m in matches[:3]]}
        return {"results": [], "message": "Topilmadi. Qabulxonaga murojaat qiling."}

    async def _fn_demo_process_payment(self, **kw: Any) -> dict:
        return {"message": "To'lov demo rejimida. Haqiqiy to'lov tizimi ulanmagan."}

    async def _fn_demo_issue_queue_ticket(self, **kw: Any) -> dict:
        ticket = f"A-{random.randint(100, 999)}"
        return {
            "ticket_number": ticket,
            "estimated_wait_minutes": random.randint(5, 20),
            "message": f"Sizning navbat raqamingiz: {ticket}",
        }


# ── Demo data ────────────────────────────────────────────────────────────────

_DEMO_DEPARTMENTS = [
    {"id": "endokrinologiya", "name": "Endokrinologiya", "description": "Endokrin tizim kasalliklari", "floor": 1, "room": "101"},
    {"id": "xirurgiya", "name": "Xirurgiya", "description": "Jarrohlik xizmatlari", "floor": 1, "room": "102"},
    {"id": "nevrologiya", "name": "Nevrologiya", "description": "Asab tizimi kasalliklari", "floor": 2, "room": "201"},
    {"id": "kardiologiya", "name": "Kardiologiya", "description": "Yurak-qon tomir kasalliklari", "floor": 2, "room": "202"},
    {"id": "mammologiya", "name": "Mammologiya", "description": "Ko'krak bezi kasalliklari", "floor": 2, "room": "203"},
    {"id": "terapiya", "name": "Terapiya", "description": "Umumiy terapevtik xizmatlar", "floor": 1, "room": "103"},
    {"id": "radiologiya", "name": "Radiologiya", "description": "Radiologik tekshiruvlar", "floor": 1, "room": "104"},
    {"id": "reanimatsiya", "name": "Reanimatsiya", "description": "Shoshilinch tibbiy yordam", "floor": 1, "room": "105"},
]

_DEMO_DOCTORS: dict[str, list[dict]] = {
    "endokrinologiya": [
        {"id": "dr-nasirxodjaev", "name": "Nasirxodjaev Yo.B.", "full_name": "Nasirxodjaev Yo'ldosh Botirovich", "specialty": "Endokrinolog-radiolog", "department_id": "endokrinologiya", "department_name": "Endokrinologiya", "experience": "28 yil", "rating": 4.9},
    ],
    "xirurgiya": [
        {"id": "dr-aripova", "name": "Aripova N.M.", "full_name": "Aripova Nargiza Mirkomilovna", "specialty": "Proktolog, yiringli jarroh", "department_id": "xirurgiya", "department_name": "Xirurgiya", "experience": "35 yil", "rating": 4.8},
    ],
    "nevrologiya": [
        {"id": "dr-malikov-nevro", "name": "Malikov A.V.", "full_name": "Malikov Abdulla Valijonovich", "specialty": "Nevropatolog", "department_id": "nevrologiya", "department_name": "Nevrologiya", "experience": "30 yil", "rating": 4.9},
    ],
    "kardiologiya": [
        {"id": "dr-malikov-kardio", "name": "Malikov A.V.", "full_name": "Malikov Abdulla Valijonovich", "specialty": "Kardiolog", "department_id": "kardiologiya", "department_name": "Kardiologiya", "experience": "35 yil", "rating": 4.9},
    ],
    "mammologiya": [
        {"id": "dr-alimxodjaeva", "name": "Prof. Alimxodjaeva L.T.", "full_name": "Alimxodjaeva Lola Toshpulatovna", "specialty": "Professor, Mammolog", "department_id": "mammologiya", "department_name": "Mammologiya", "experience": "30 yil", "rating": 5.0},
    ],
}


# Module-level singleton
gemini_service = GeminiService()
