"""Central AI orchestrator — ties face, speech, LLM, and session together."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.face_service import FaceService
from app.ai.gemini_service import GeminiService
from app.ai.muxlisa_service import MuxlisaService
from app.ai.session_manager import SessionManager, SessionState
from app.services import patient_service

# Intent → SessionState mapping
_INTENT_TO_STATE: dict[str, SessionState] = {
    "APPOINTMENT_BOOKING": SessionState.APPOINTMENT_BOOKING,
    "CHECK_IN": SessionState.CHECK_IN,
    "INFORMATION": SessionState.INFORMATION_INQUIRY,
    "FAQ": SessionState.INFORMATION_INQUIRY,
    "PAYMENT": SessionState.PAYMENT,
    "COMPLAINT": SessionState.COMPLAINT,
    "HAND_OFF": SessionState.HAND_OFF,
    "FAREWELL": SessionState.FAREWELL,
}

# State → UI action hints
_STATE_UI_ACTIONS: dict[SessionState, str] = {
    SessionState.GREETING: "show_greeting",
    SessionState.INTENT_DISCOVERY: "show_intent_options",
    SessionState.SELECT_DEPARTMENT: "show_departments",
    SessionState.SELECT_DOCTOR: "show_doctors",
    SessionState.SELECT_TIMESLOT: "show_slots",
    SessionState.CONFIRM_BOOKING: "show_booking_confirmation",
    SessionState.BOOKING_PAYMENT: "show_payment",
    SessionState.BOOKING_COMPLETE: "show_booking_complete",
    SessionState.CHECK_IN: "show_checkin",
    SessionState.VERIFY_IDENTITY: "show_verification",
    SessionState.CONFIRM_APPOINTMENT: "show_appointment_confirmation",
    SessionState.ISSUE_QUEUE_TICKET: "show_queue_ticket",
    SessionState.ROUTE_TO_DEPARTMENT: "show_route",
    SessionState.INFORMATION_INQUIRY: "show_info",
    SessionState.FAQ_RESPONSE: "show_faq",
    SessionState.SHOW_DEPARTMENT_INFO: "show_department_info",
    SessionState.SHOW_DOCTOR_PROFILE: "show_doctor_profile",
    SessionState.SELECT_PAYMENT_METHOD: "show_payment_methods",
    SessionState.PROCESS_PAYMENT: "show_payment_processing",
    SessionState.PAYMENT_RECEIPT: "show_receipt",
    SessionState.RECORD_FEEDBACK: "show_feedback_form",
    SessionState.HAND_OFF: "show_handoff",
    SessionState.FAREWELL: "show_farewell",
}


class OrchestratorResponse(BaseModel):
    """Standard response from the orchestrator to the kiosk."""

    text: str
    audio_base64: str | None = None
    ui_action: str | None = None
    ui_data: dict[str, Any] | None = None
    state: str
    language: str | None = None
    patient: dict[str, Any] | None = None
    session_id: str
    transcript: str | None = None


class Orchestrator:
    """Central coordinator — connects ALL AI services."""

    def __init__(
        self,
        gemini: GeminiService,
        face: FaceService,
        muxlisa: MuxlisaService,
        session_mgr: SessionManager,
        db_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.gemini = gemini
        self.face = face
        self.muxlisa = muxlisa
        self.session_mgr = session_mgr
        self.db_factory = db_session_factory

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def handle_face_detected(
        self,
        device_id: str,
        clinic_id: UUID,
        image_bytes: bytes,
    ) -> OrchestratorResponse:
        """Camera detected a face — start or resume a session."""
        session_id = await self.session_mgr.create_session(device_id, clinic_id)
        await self.session_mgr.transition(session_id, SessionState.DETECTED)

        patient_data: dict[str, Any] | None = None
        greeting_text: str

        async with self.db_factory() as db:
            try:
                identified = await self.face.identify(image_bytes, clinic_id, db)
            except Exception:
                logger.opt(exception=True).warning("Face identification failed")
                identified = None

            if identified and identified.patient_id:
                try:
                    patient_data = await patient_service.get_patient(
                        db, clinic_id, identified.patient_id
                    )
                except Exception:
                    logger.opt(exception=True).warning("Patient lookup failed")

        if patient_data:
            name = patient_data.get("full_name", "")
            await self.session_mgr.set_context(session_id, "patient_id", str(patient_data["id"]))
            await self.session_mgr.set_context(session_id, "patient_name", name)
            greeting_text = await self._gemini_greeting(
                session_id, clinic_id, patient_data
            )
        else:
            greeting_text = await self._gemini_greeting(session_id, clinic_id)

        await self.session_mgr.transition(session_id, SessionState.GREETING)

        return OrchestratorResponse(
            text=greeting_text,
            audio_base64=None,  # TTS disabled — Muxlisa returns HTTP 500
            ui_action="show_greeting",
            state=SessionState.GREETING.value,
            patient=patient_data,
            session_id=session_id,
        )

    async def handle_speech(
        self,
        session_id: str,
        audio_bytes: bytes,
    ) -> OrchestratorResponse:
        """Visitor spoke something — STT → Gemini → TTS."""
        t_total = time.monotonic()

        session = await self.session_mgr.get_session(session_id)
        if session is None:
            return self._expired_response(session_id)

        clinic_id_str = session.get("clinic_id")
        if not clinic_id_str:
            return self._expired_response(session_id)
        clinic_id = UUID(clinic_id_str)
        await self.session_mgr.touch(session_id)

        # 1. Speech-to-text
        t_stt = time.monotonic()
        stt_result = await self.muxlisa.speech_to_text(audio_bytes)
        stt_ms = (time.monotonic() - t_stt) * 1000
        transcript = stt_result.transcript
        language = stt_result.language

        if language and language != session.get("language"):
            await self.session_mgr.set_language(session_id, language)

        if not transcript.strip() or len(transcript.strip()) < 3:
            lang = language or session.get("language", "uz")
            # Track consecutive empty transcripts to avoid spamming
            empty_count = int(
                (await self.session_mgr.get_context(session_id)).get(
                    "empty_transcript_count", 0
                )
            )
            empty_count += 1
            await self.session_mgr.set_context(
                session_id, "empty_transcript_count", empty_count
            )

            if empty_count == 1:
                text = _EMPTY_STT_TEXTS.get(lang, _EMPTY_STT_TEXTS["uz"])
            elif empty_count == 2:
                text = _EMPTY_STT_TEXTS_2.get(lang, _EMPTY_STT_TEXTS_2["uz"])
            else:
                # 3+ consecutive empty transcripts — stay silent, don't spam
                return OrchestratorResponse(
                    text="",
                    state=session["state"],
                    session_id=session_id,
                )

            return OrchestratorResponse(
                text=text,
                audio_base64=None,  # TTS disabled
                state=session["state"],
                session_id=session_id,
            )

        # Real speech received — reset empty transcript counter
        await self.session_mgr.set_context(session_id, "empty_transcript_count", 0)

        current_state = SessionState(session["state"])

        # Intent is handled by Gemini via function calling — no separate classification needed
        intent_ms = 0

        # 3. Chat with Gemini — state is passed via patient_context into system prompt
        updated_state = await self.session_mgr.get_state(session_id) or current_state
        context = await self.session_mgr.get_context(session_id)
        session_language = session.get("language", "uz")
        patient_context = self._build_patient_context(context, state=updated_state.value, language=session_language)

        # Clean user message, no state injection
        enriched_message = transcript

        t_llm = time.monotonic()
        try:
            async with self.db_factory() as db:
                chat_response = await self.gemini.chat(
                    session_id=session_id,
                    message=enriched_message,
                    patient_context=patient_context,
                    clinic_id=clinic_id,
                    db=db,
                    language=session_language,
                )
        except Exception as exc:
            logger.opt(exception=True).error(
                "Gemini chat failed, returning fallback",
                extra={"session_id": session_id},
            )
            fallback = _FALLBACK_TEXTS.get(language or "uz", _FALLBACK_TEXTS["uz"])
            return OrchestratorResponse(
                text=fallback,
                audio_base64=None,  # TTS disabled
                state=current_state.value,
                session_id=session_id,
            )

        llm_ms = (time.monotonic() - t_llm) * 1000

        # 4. Sanitise response text — ensure it's natural language, not JSON
        response_text = self._sanitise_response_text(chat_response.text, language or "uz")

        # 5. Update state based on Gemini's ui_action / next_state
        new_state = self._resolve_state_from_response(chat_response, session)
        if new_state:
            await self._transition_through(session_id, new_state)

        final_state = await self.session_mgr.get_state(session_id) or current_state

        # TTS disabled — Muxlisa returns HTTP 500, skip entirely

        total_ms = (time.monotonic() - t_total) * 1000
        logger.info(
            "⏱ Pipeline timing",
            extra={
                "session_id": session_id,
                "stt_ms": round(stt_ms, 1),
                "intent_ms": round(intent_ms, 1),
                "llm_ms": round(llm_ms, 1),
                "total_ms": round(total_ms, 1),
            },
        )

        return OrchestratorResponse(
            text=response_text,
            audio_base64=None,  # TTS disabled
            ui_action=chat_response.ui_action or _STATE_UI_ACTIONS.get(final_state),
            ui_data=self._extract_ui_data(chat_response),
            state=final_state.value,
            language=language or session.get("language"),
            patient=self._patient_from_context(context),
            session_id=session_id,
            transcript=transcript,
        )

    async def handle_touch(
        self,
        session_id: str,
        action: str,
        data: dict[str, Any],
    ) -> OrchestratorResponse:
        """Visitor tapped a button on the kiosk."""
        session = await self.session_mgr.get_session(session_id)
        if session is None:
            return self._expired_response(session_id)

        clinic_id_str = session.get("clinic_id")
        if not clinic_id_str:
            return self._expired_response(session_id)
        clinic_id = UUID(clinic_id_str)
        await self.session_mgr.touch(session_id)
        current_state = SessionState(session.get("state", "IDLE"))
        language = session.get("language", "uz")

        # Ping — session is alive, just refresh TTL and return current state
        if action == "ping":
            return OrchestratorResponse(
                text="",
                state=current_state.value,
                session_id=session_id,
            )

        # Store selection in context
        if action == "select_intent" and "intent" in data:
            intent = data["intent"].upper()
            target = _INTENT_TO_STATE.get(intent)
            if target:
                await self.session_mgr.transition(session_id, SessionState.INTENT_DISCOVERY)
                await self.session_mgr.transition(session_id, target)
        elif action == "select_department" and "department_id" in data:
            await self.session_mgr.set_context(session_id, "department_id", data["department_id"])
            await self.session_mgr.transition(session_id, SessionState.SELECT_DEPARTMENT)
            await self.session_mgr.transition(session_id, SessionState.SELECT_DOCTOR)
        elif action == "select_doctor" and "doctor_id" in data:
            await self.session_mgr.set_context(session_id, "doctor_id", data["doctor_id"])
            await self.session_mgr.transition(session_id, SessionState.SELECT_TIMESLOT)
        elif action == "select_slot" and "slot" in data:
            await self.session_mgr.set_context(session_id, "slot", data["slot"])
            await self.session_mgr.transition(session_id, SessionState.CONFIRM_BOOKING)
        elif action in ("confirm", "confirm_booking"):
            await self._handle_confirm(session_id, current_state)
        elif action == "check_in_complete":
            await self.session_mgr.transition(session_id, SessionState.ISSUE_QUEUE_TICKET)
        elif action == "cancel":
            await self.session_mgr.transition(session_id, SessionState.FAREWELL)
        elif action == "payment_method" and "method" in data:
            await self.session_mgr.set_context(session_id, "payment_method", data["method"])
            await self.session_mgr.transition(session_id, SessionState.PROCESS_PAYMENT)
        elif action == "back":
            # Allow going back to intent discovery
            await self.session_mgr.transition(session_id, SessionState.INTENT_DISCOVERY)

        # Build a natural-language response via Gemini
        current_state = SessionState(
            (await self.session_mgr.get_session(session_id) or session).get("state", "IDLE")
        )
        message = f"[USER_ACTION: {action}] {json.dumps(data)}" if data else f"[USER_ACTION: {action}]"
        context = await self.session_mgr.get_context(session_id)
        patient_context = self._build_patient_context(context, state=current_state.value, language=language)

        async with self.db_factory() as db:
            chat_response = await self.gemini.chat(
                session_id=session_id,
                message=message,
                patient_context=patient_context,
                clinic_id=clinic_id,
                db=db,
                language=language,
            )

        final_state = await self.session_mgr.get_state(session_id) or current_state
        response_text = self._sanitise_response_text(chat_response.text, language)

        return OrchestratorResponse(
            text=response_text,
            audio_base64=None,  # TTS disabled
            ui_action=chat_response.ui_action or _STATE_UI_ACTIONS.get(final_state),
            ui_data=self._extract_ui_data(chat_response),
            state=final_state.value,
            language=language,
            patient=self._patient_from_context(context),
            session_id=session_id,
        )

    async def handle_timeout(self, session_id: str) -> OrchestratorResponse:
        """Session approaching timeout — prompt or farewell."""
        session = await self.session_mgr.get_session(session_id)
        if session is None:
            return self._expired_response(session_id)

        language = session.get("language", "uz")
        context = await self.session_mgr.get_context(session_id)

        # Check if this is a second timeout (already warned)
        if context.get("timeout_warned"):
            text = _FAREWELL_TEXTS.get(language, _FAREWELL_TEXTS["uz"])
            await self.session_mgr.transition(session_id, SessionState.FAREWELL)
            await self.session_mgr.reset(session_id)
            return OrchestratorResponse(
                text=text,
                audio_base64=None,  # TTS disabled
                ui_action="show_farewell",
                state=SessionState.FAREWELL.value,
                session_id=session_id,
            )

        # First timeout — ask if still there
        text = _TIMEOUT_TEXTS.get(language, _TIMEOUT_TEXTS["uz"])
        await self.session_mgr.set_context(session_id, "timeout_warned", True)
        await self.session_mgr.touch(session_id)

        return OrchestratorResponse(
            text=text,
            audio_base64=None,  # TTS disabled
            ui_action="show_timeout_prompt",
            state=session["state"],
            session_id=session_id,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # Full booking flow including the entry from INTENT_DISCOVERY
    _FULL_BOOKING_FLOW = [
        SessionState.INTENT_DISCOVERY,
        SessionState.APPOINTMENT_BOOKING,
        SessionState.SELECT_DEPARTMENT,
        SessionState.SELECT_DOCTOR,
        SessionState.SELECT_TIMESLOT,
        SessionState.CONFIRM_BOOKING,
        SessionState.BOOKING_PAYMENT,
        SessionState.BOOKING_COMPLETE,
    ]

    # Check-in flow
    _CHECKIN_FLOW = [
        SessionState.INTENT_DISCOVERY,
        SessionState.CHECK_IN,
        SessionState.VERIFY_IDENTITY,
        SessionState.CONFIRM_APPOINTMENT,
        SessionState.ISSUE_QUEUE_TICKET,
        SessionState.ROUTE_TO_DEPARTMENT,
    ]

    # Info flow
    _INFO_FLOW = [
        SessionState.INTENT_DISCOVERY,
        SessionState.INFORMATION_INQUIRY,
        SessionState.FAQ_RESPONSE,
    ]

    _ALL_FLOWS = [_FULL_BOOKING_FLOW, _CHECKIN_FLOW, _INFO_FLOW]

    async def _transition_through(
        self, session_id: str, target: SessionState
    ) -> bool:
        """Transition to *target*, walking through intermediate states if needed.

        A direct transition is attempted first.  If it fails (because the
        state machine requires intermediate steps), we bridge through
        INTENT_DISCOVERY and then walk through the appropriate flow.
        """
        # Direct transition
        if await self.session_mgr.transition(session_id, target):
            return True

        current = await self.session_mgr.get_state(session_id)
        if current is None:
            return False

        # Try to walk through a known flow
        for flow in self._ALL_FLOWS:
            if target in flow:
                # Bridge to INTENT_DISCOVERY first if not already in the flow
                if current not in flow and current != SessionState.INTENT_DISCOVERY:
                    await self.session_mgr.transition(session_id, SessionState.INTENT_DISCOVERY)
                    current = await self.session_mgr.get_state(session_id) or current

                if current in flow:
                    cur_idx = flow.index(current)
                    tgt_idx = flow.index(target)
                    if tgt_idx > cur_idx:
                        for intermediate in flow[cur_idx + 1 : tgt_idx + 1]:
                            if not await self.session_mgr.transition(session_id, intermediate):
                                return False
                        return True

                # If we're at INTENT_DISCOVERY but not in the flow, walk from start
                if current == SessionState.INTENT_DISCOVERY and flow[0] == SessionState.INTENT_DISCOVERY:
                    tgt_idx = flow.index(target)
                    for intermediate in flow[1 : tgt_idx + 1]:
                        if not await self.session_mgr.transition(session_id, intermediate):
                            return False
                    return True

        # Last resort: try INTENT_DISCOVERY as a bridge
        if current != SessionState.INTENT_DISCOVERY:
            await self.session_mgr.transition(session_id, SessionState.INTENT_DISCOVERY)
            if await self.session_mgr.transition(session_id, target):
                return True

        # Last resort: force direct transition to prevent dead-ends
        # This handles cases where the state machine is too rigid
        logger.warning(
            "Force-transitioning (rigid state machine bypass)",
            extra={"session_id": session_id, "target": target.value},
        )
        session = await self.session_mgr.get_session(session_id)
        if session:
            session["state"] = target.value
            import json as _json
            await self.session_mgr.redis.set(
                f"session:{session_id}",
                _json.dumps(session),
                ex=900,
            )
            return True

        return False

    async def _gemini_greeting(
        self,
        session_id: str,
        clinic_id: UUID,
        patient_data: dict[str, Any] | None = None,
    ) -> str:
        """Ask Gemini to generate a greeting."""
        session = await self.session_mgr.get_session(session_id)
        session_language = session.get("language", "uz") if session else "uz"

        if patient_data:
            name = patient_data.get("full_name", "")
            message = f"[SYSTEM: Returning patient detected. Name: {name}. Generate a warm personalized greeting.]"
            patient_context = {"patient_id": str(patient_data["id"]), "name": name}
        else:
            message = "[SYSTEM: New visitor detected. Generate a welcoming greeting introducing yourself as Mezbon.]"
            patient_context = None

        async with self.db_factory() as db:
            response = await self.gemini.chat(
                session_id=session_id,
                message=message,
                patient_context=patient_context,
                clinic_id=clinic_id,
                db=db,
                language=session_language,
            )
        return response.text

    @staticmethod
    def _sanitise_response_text(text: str, language: str) -> str:
        """Ensure the response text is usable — replace empty/garbage with fallback.

        The gemini_service already strips JSON and code; this just handles the
        case where the final text is empty or too short to be useful.
        """
        cleaned = text.strip()
        if not cleaned or len(cleaned) < 3:
            return _FALLBACK_TEXTS.get(language, _FALLBACK_TEXTS["uz"])
        return cleaned

    async def _handle_confirm(
        self, session_id: str, current_state: SessionState
    ) -> None:
        """Process a confirm action based on the current state."""
        if current_state == SessionState.CONFIRM_BOOKING:
            await self.session_mgr.transition(session_id, SessionState.BOOKING_PAYMENT)
        elif current_state == SessionState.CONFIRM_APPOINTMENT:
            await self.session_mgr.transition(session_id, SessionState.ISSUE_QUEUE_TICKET)
        elif current_state == SessionState.PROCESS_PAYMENT:
            await self.session_mgr.transition(session_id, SessionState.PAYMENT_RECEIPT)

    def _resolve_state_from_response(
        self, chat_response: Any, session: dict[str, Any]
    ) -> SessionState | None:
        """Determine target state from Gemini's response hints."""
        next_state = getattr(chat_response, "next_state", None)
        if next_state:
            try:
                return SessionState(next_state)
            except ValueError:
                logger.debug("Invalid next_state from Gemini", extra={"next_state": next_state})

        ui = chat_response.ui_action
        if not ui:
            return None

        # Reverse lookup from UI action to state
        for state, action in _STATE_UI_ACTIONS.items():
            if action == ui:
                return state
        return None

    @staticmethod
    def _build_patient_context(context: dict[str, Any], state: str = "", language: str = "uz") -> dict[str, Any] | None:
        """Build patient context dict from session context.

        Args:
            context: Session context dict (session["context"]).
            state: Current session state string.
            language: Session language from session["language"] — NOT from context.
        """
        patient_id = context.get("patient_id")
        result: dict[str, Any] = {}
        if patient_id:
            result = {
                "id": patient_id,
                "full_name": context.get("patient_name", ""),
                "language_preference": language,
            }
        if state:
            result["current_state"] = state
        return result if result else None

    @staticmethod
    def _patient_from_context(context: dict[str, Any]) -> dict[str, Any] | None:
        """Extract patient info from session context for the response."""
        patient_id = context.get("patient_id")
        if not patient_id:
            return None
        return {
            "id": patient_id,
            "name": context.get("patient_name", ""),
        }

    @staticmethod
    def _extract_ui_data(chat_response: Any) -> dict[str, Any] | None:
        """Extract structured UI data from Gemini function call results.

        Transforms raw function-call results into the shape the kiosk
        frontend expects:
          - ``departments``: list of department dicts
          - ``doctors``: list of doctor dicts
          - ``slots``: list of ``{start_time, end_time, is_available}``
          - ``ticket``: queue ticket dict
          - ``appointment``: booking confirmation dict
          - ``function_results``: raw results (always included as fallback)
        """
        if not chat_response.function_calls:
            return None

        ui_data: dict[str, Any] = {
            "function_results": chat_response.function_calls,
        }

        for fc in chat_response.function_calls:
            result = fc.get("result") or {}
            name = fc["name"]

            if name == "get_department_info":
                if "departments" in result:
                    ui_data["departments"] = result["departments"]
                elif "department_id" in result or "name" in result:
                    # Single department returned — wrap in a list
                    ui_data["departments"] = [result]
                # Department info may include doctors for that department
                if "doctors" in result and isinstance(result["doctors"], list):
                    ui_data["doctors"] = result["doctors"]

            elif name == "get_doctor_info":
                if "doctors" in result:
                    ui_data["doctors"] = result["doctors"]
                elif "doctor_id" in result or "full_name" in result:
                    ui_data["doctors"] = [result]

            elif name == "get_available_slots":
                raw_slots = result.get("available_slots", [])
                ui_data["slots"] = [
                    {
                        "start_time": s if isinstance(s, str) else s.get("start", ""),
                        "end_time": s if isinstance(s, str) else s.get("end", ""),
                        "is_available": True,
                    }
                    for s in raw_slots
                ]

            elif name == "issue_queue_ticket":
                ui_data["ticket"] = {
                    "ticket_number": result.get("ticket_number", ""),
                    "estimated_wait_minutes": result.get("estimated_wait_minutes", 0),
                }

            elif name == "book_appointment":
                ui_data["appointment"] = result
                # Also create a ticket from booking result so queue_ticket screen works
                code = result.get("confirmation_code") or result.get("ticket_number") or ""
                if code and "ticket" not in ui_data:
                    ui_data["ticket"] = {
                        "ticket_number": code,
                        "estimated_wait_minutes": result.get("estimated_wait_minutes", 10),
                        "doctor_name": result.get("doctor_name", ""),
                        "time": result.get("time", ""),
                        "date": result.get("date", ""),
                    }

        return ui_data

    def _expired_response(self, session_id: str) -> OrchestratorResponse:
        """Return a response for an expired / missing session."""
        return OrchestratorResponse(
            text="Sessiya tugadi. Iltimos, qaytadan boshlang.",
            ui_action="show_farewell",
            state=SessionState.IDLE.value,
            session_id=session_id,
        )


# ------------------------------------------------------------------
# Localised timeout / farewell messages
# ------------------------------------------------------------------

_EMPTY_STT_TEXTS: dict[str, str] = {
    "uz": "Eshitmadim, iltimos qaytadan ayting. Yoki ekrandagi tugmalardan foydalanishingiz mumkin.",
    "ru": "Не расслышала, повторите, пожалуйста. Или можете использовать кнопки на экране.",
    "en": "I didn't catch that, could you please repeat? You can also use the buttons on screen.",
}

_EMPTY_STT_TEXTS_2: dict[str, str] = {
    "uz": "Ovozingiz yetib kelmayapti. Ekrandagi tugmalardan foydalaning — men yordam beraman!",
    "ru": "Не слышу вас. Используйте кнопки на экране — я помогу!",
    "en": "I can't hear you well. Please use the buttons on screen — I'm here to help!",
}

_FALLBACK_TEXTS: dict[str, str] = {
    "uz": "Sizga qanday yordam bera olaman? Gapiring yoki ekrandagi tugmalardan foydalaning.",
    "ru": "Чем могу помочь? Говорите или используйте кнопки на экране.",
    "en": "How can I help you? Please speak or use the buttons on screen.",
}

_TIMEOUT_TEXTS: dict[str, str] = {
    "uz": "Hali shu yerdamisiz? Yana biror narsa bilan yordam kerakmi?",
    "ru": "Вы ещё здесь? Нужна ещё какая-нибудь помощь?",
    "en": "Are you still there? Need any more help?",
}

_FAREWELL_TEXTS: dict[str, str] = {
    "uz": "Rahmat, yaxshi kun tilayman! Sog'liq bo'lsin!",
    "ru": "Спасибо, хорошего дня! Будьте здоровы!",
    "en": "Thank you, have a wonderful day! Take care!",
}
