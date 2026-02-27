"""Socket.IO event handlers for kiosk → backend communication.

Events handled:
  - kiosk:face_frame   — camera detected a face (image bytes)
  - kiosk:speech_audio  — visitor spoke (audio bytes)
  - kiosk:touch_action  — visitor tapped a button
  - kiosk:heartbeat     — device health telemetry
"""

from __future__ import annotations

import base64
from typing import Any
from uuid import UUID

from loguru import logger

from datetime import datetime

from app.sockets.server import sio, get_sid_meta, emit_to_device, emit_to_admin


def register_kiosk_events(
    get_orchestrator: Any,
    get_db_factory: Any,
) -> None:
    """Register all kiosk Socket.IO event handlers.

    Parameters
    ----------
    get_orchestrator:
        Callable that returns the ``Orchestrator`` singleton.
    get_db_factory:
        Callable that returns the ``async_sessionmaker``.
    """

    @sio.on("kiosk:face_frame")
    async def handle_face_frame(sid: str, data: dict[str, Any]) -> None:
        """Receive a camera frame, run face detection via orchestrator.

        Expected data:
            {"device_id": str, "frame": str}  # frame = base64-encoded JPEG
        """
        meta = get_sid_meta(sid)
        if meta is None:
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "NOT_AUTHENTICATED",
                "message": "Connection not authenticated",
            }, to=sid)
            return

        device_id = data.get("device_id") or meta.get("device_id")
        frame_b64 = data.get("frame")

        if not device_id or not frame_b64:
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "INVALID_PAYLOAD",
                "message": "device_id and frame are required",
            }, to=sid)
            return

        # Reject oversized payloads (max 5MB base64 ≈ 3.75MB image)
        if len(frame_b64) > 5 * 1024 * 1024:
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "PAYLOAD_TOO_LARGE",
                "message": "Frame exceeds maximum size",
            }, to=sid)
            return

        clinic_id = UUID(meta["clinic_id"])

        try:
            image_bytes = base64.b64decode(frame_b64)
        except Exception:
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "INVALID_FRAME",
                "message": "Could not decode base64 frame",
            }, to=sid)
            return

        try:
            orchestrator = get_orchestrator()
            response = await orchestrator.handle_face_detected(
                device_id=device_id,
                clinic_id=clinic_id,
                image_bytes=image_bytes,
            )

            response_data = response.model_dump()
            await emit_to_device("ai:response", response_data, device_id)
            await emit_to_device("ai:state_change", {
                "session_id": response.session_id,
                "state": response.state,
            }, device_id)

            # Notify admin about new visitor
            await emit_to_admin("visitor:new", {
                "device_id": device_id,
                "session_id": response.session_id,
                "patient": response.patient,
                "state": response.state,
            }, str(clinic_id))

        except Exception as exc:
            logger.opt(exception=True).error(
                "Error handling face_frame",
                extra={"sid": sid, "device_id": device_id},
            )
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "PROCESSING_ERROR",
                "message": str(exc),
            }, to=sid)

    @sio.on("kiosk:speech_audio")
    async def handle_speech_audio(sid: str, data: dict[str, Any]) -> None:
        """Receive visitor speech audio, run STT → Gemini → TTS.

        Expected data:
            {"device_id": str, "audio": bytes|str, "format": str}
            audio can be raw bytes (Socket.IO binary) or base64 string.
        """
        meta = get_sid_meta(sid)
        if meta is None:
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "NOT_AUTHENTICATED",
                "message": "Connection not authenticated",
            }, to=sid)
            return

        device_id = data.get("device_id") or meta.get("device_id")
        session_id = data.get("session_id") or ""
        audio_raw = data.get("audio")

        if not device_id or not audio_raw:
            await sio.emit("ai:error", {
                "session_id": session_id,
                "code": "INVALID_PAYLOAD",
                "message": "device_id and audio are required",
            }, to=sid)
            return

        # Reject oversized payloads (max 10MB for audio)
        audio_size = len(audio_raw) if isinstance(audio_raw, (bytes, str)) else 0
        if audio_size > 10 * 1024 * 1024:
            await sio.emit("ai:error", {
                "session_id": session_id,
                "code": "PAYLOAD_TOO_LARGE",
                "message": "Audio exceeds maximum size",
            }, to=sid)
            return

        # If no session_id yet, create a proper session via SessionManager
        if not session_id:
            clinic_id = UUID(meta["clinic_id"])
            orchestrator = get_orchestrator()
            session_id = await orchestrator.session_mgr.create_session(
                device_id, clinic_id
            )
            # Transition IDLE → DETECTED → GREETING so handle_speech works
            from app.ai.session_manager import SessionState
            await orchestrator.session_mgr.transition(session_id, SessionState.DETECTED)
            await orchestrator.session_mgr.transition(session_id, SessionState.GREETING)

        # Normalise audio to bytes
        if isinstance(audio_raw, str):
            try:
                audio_bytes = base64.b64decode(audio_raw)
            except Exception:
                await sio.emit("ai:error", {
                    "session_id": session_id,
                    "code": "INVALID_AUDIO",
                    "message": "Could not decode base64 audio",
                }, to=sid)
                return
        elif isinstance(audio_raw, (bytes, bytearray)):
            audio_bytes = bytes(audio_raw)
        else:
            await sio.emit("ai:error", {
                "session_id": session_id,
                "code": "INVALID_AUDIO",
                "message": "Unsupported audio format",
            }, to=sid)
            return

        logger.info(
            "🎤 speech_audio received",
            extra={
                "sid": sid,
                "session_id": session_id,
                "audio_bytes": len(audio_bytes),
                "device_id": device_id,
                "audio_type": type(audio_raw).__name__,
            },
        )
        # DEBUG: confirm device room membership
        rooms = sio.rooms(sid)
        logger.info(
            "🔍 DEBUG: socket rooms for this sid",
            extra={"sid": sid, "rooms": list(rooms), "target_room": f"device_{device_id}"},
        )

        # Immediately acknowledge receipt so the frontend shows "processing"
        await emit_to_device("ai:processing", {
            "session_id": session_id,
        }, device_id)

        try:
            orchestrator = get_orchestrator()
            response = await orchestrator.handle_speech(
                session_id=session_id,
                audio_bytes=audio_bytes,
            )

            logger.info(
                "✅ speech_audio response ready",
                extra={
                    "session_id": session_id,
                    "text": response.text[:80] if response.text else "(EMPTY)",
                    "text_len": len(response.text) if response.text else 0,
                    "transcript": response.transcript[:60] if response.transcript else "(EMPTY)",
                    "state": response.state,
                    "ui_action": response.ui_action,
                },
            )

            response_data = response.model_dump()
            logger.info(
                "📤 EMITTING ai:response to device",
                extra={
                    "device_id": device_id,
                    "room": f"device_{device_id}",
                    "response_keys": list(response_data.keys()),
                    "text_preview": str(response_data.get("text", ""))[:100],
                },
            )
            await emit_to_device("ai:response", response_data, device_id)
            await emit_to_device("ai:state_change", {
                "session_id": response.session_id,
                "state": response.state,
            }, device_id)

        except Exception as exc:
            logger.opt(exception=True).error(
                "Error handling speech_audio",
                extra={"sid": sid, "session_id": session_id},
            )
            await sio.emit("ai:error", {
                "session_id": session_id,
                "code": "PROCESSING_ERROR",
                "message": str(exc),
            }, to=sid)

    @sio.on("kiosk:chat_text")
    async def handle_chat_text(sid: str, data: dict[str, Any]) -> None:
        """Receive visitor text directly (bypasses STT).

        Use this when Muxlisa STT is down or when the kiosk uses
        the browser's Web Speech API for client-side STT.

        Expected data:
            {"device_id": str, "session_id": str, "text": str, "language": str}
        """
        meta = get_sid_meta(sid)
        if meta is None:
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "NOT_AUTHENTICATED",
                "message": "Connection not authenticated",
            }, to=sid)
            return

        device_id = data.get("device_id") or meta.get("device_id")
        session_id = data.get("session_id") or ""
        text = (data.get("text") or "").strip()
        language = data.get("language", "uz")

        if not device_id or not text:
            await sio.emit("ai:error", {
                "session_id": session_id,
                "code": "INVALID_PAYLOAD",
                "message": "device_id and text are required",
            }, to=sid)
            return

        # Create session if needed
        if not session_id:
            clinic_id = UUID(meta["clinic_id"])
            orchestrator = get_orchestrator()
            session_id = await orchestrator.session_mgr.create_session(
                device_id, clinic_id
            )
            from app.ai.session_manager import SessionState
            await orchestrator.session_mgr.transition(session_id, SessionState.DETECTED)
            await orchestrator.session_mgr.transition(session_id, SessionState.GREETING)

        logger.info(
            "💬 chat_text received",
            extra={
                "sid": sid,
                "session_id": session_id,
                "text": text[:80],
                "language": language,
                "device_id": device_id,
            },
        )

        # Acknowledge receipt
        await emit_to_device("ai:processing", {
            "session_id": session_id,
        }, device_id)

        try:
            orchestrator = get_orchestrator()

            # Update language if provided
            if language:
                await orchestrator.session_mgr.set_language(session_id, language)

            # Get session and build context
            session = await orchestrator.session_mgr.get_session(session_id)
            if session is None:
                await sio.emit("ai:error", {
                    "session_id": session_id,
                    "code": "SESSION_EXPIRED",
                    "message": "Session expired, please start again",
                }, to=sid)
                return

            clinic_id = UUID(session["clinic_id"])
            await orchestrator.session_mgr.touch(session_id)

            from app.ai.session_manager import SessionState
            current_state = SessionState(session["state"])

            # Intent is handled by Gemini via function calling — no separate classification needed

            # Chat with Gemini
            updated_state = await orchestrator.session_mgr.get_state(session_id) or current_state
            context = await orchestrator.session_mgr.get_context(session_id)
            # Get session language (set by kiosk UI language switch)
            session_language = language or session.get("language", "uz")
            patient_context = orchestrator._build_patient_context(context, state=updated_state.value, language=session_language)

            # Clean message, no state injection
            enriched = text

            async with orchestrator.db_factory() as db:
                chat_response = await orchestrator.gemini.chat(
                    session_id=session_id,
                    message=enriched,
                    patient_context=patient_context,
                    clinic_id=clinic_id,
                    db=db,
                    language=session_language,
                )

            response_text = orchestrator._sanitise_response_text(
                chat_response.text, language
            )

            # Update state from response
            new_state = orchestrator._resolve_state_from_response(chat_response, session)
            if new_state:
                await orchestrator._transition_through(session_id, new_state)

            final_state = await orchestrator.session_mgr.get_state(session_id) or current_state

            from app.ai.orchestrator import OrchestratorResponse, _STATE_UI_ACTIONS
            response = OrchestratorResponse(
                text=response_text,
                audio_base64=None,
                ui_action=chat_response.ui_action or _STATE_UI_ACTIONS.get(final_state),
                ui_data=orchestrator._extract_ui_data(chat_response),
                state=final_state.value,
                patient=orchestrator._patient_from_context(context),
                session_id=session_id,
                transcript=text,
            )

            response_data = response.model_dump()
            logger.info(
                "✅ chat_text response ready",
                extra={
                    "session_id": session_id,
                    "text": response_text[:80],
                    "state": final_state.value,
                    "ui_action": response.ui_action,
                },
            )
            await emit_to_device("ai:response", response_data, device_id)
            await emit_to_device("ai:state_change", {
                "session_id": response.session_id,
                "state": response.state,
            }, device_id)

        except Exception as exc:
            logger.opt(exception=True).error(
                "Error handling chat_text",
                extra={"sid": sid, "session_id": session_id},
            )
            await sio.emit("ai:error", {
                "session_id": session_id,
                "code": "PROCESSING_ERROR",
                "message": str(exc),
            }, to=sid)

    @sio.on("kiosk:touch_action")
    async def handle_touch_action(sid: str, data: dict[str, Any]) -> None:
        """Receive a touch/button action from the kiosk UI.

        Expected data:
            {"device_id": str, "session_id": str, "action": str, "data": dict}
        """
        meta = get_sid_meta(sid)
        if meta is None:
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "NOT_AUTHENTICATED",
                "message": "Connection not authenticated",
            }, to=sid)
            return

        device_id = data.get("device_id") or meta.get("device_id")
        session_id = data.get("session_id")
        action = data.get("action")
        action_data = data.get("data", {})

        if not device_id or not session_id or not action:
            await sio.emit("ai:error", {
                "session_id": session_id or "",
                "code": "INVALID_PAYLOAD",
                "message": "device_id, session_id, and action are required",
            }, to=sid)
            return

        try:
            orchestrator = get_orchestrator()
            response = await orchestrator.handle_touch(
                session_id=session_id,
                action=action,
                data=action_data,
            )

            response_data = response.model_dump()
            await emit_to_device("ai:response", response_data, device_id)
            await emit_to_device("ai:state_change", {
                "session_id": response.session_id,
                "state": response.state,
            }, device_id)

        except Exception as exc:
            logger.opt(exception=True).error(
                "Error handling touch_action",
                extra={"sid": sid, "session_id": session_id, "action": action},
            )
            await sio.emit("ai:error", {
                "session_id": session_id,
                "code": "PROCESSING_ERROR",
                "message": str(exc),
            }, to=sid)

    @sio.on("kiosk:heartbeat")
    async def handle_heartbeat(sid: str, data: dict[str, Any]) -> None:
        """Receive device health telemetry.

        Expected data:
            {"device_id": str, "uptime_seconds": int, "cpu_usage": float,
             "memory_usage": float, "errors": dict|null}
        """
        meta = get_sid_meta(sid)
        if meta is None:
            return

        device_id = data.get("device_id") or meta.get("device_id")
        if not device_id:
            return

        clinic_id = UUID(meta["clinic_id"])

        try:
            # Lazy import to avoid circular imports at module load
            from app.services import device_service
            from app.schemas.device import HeartbeatData
            from app.core.database import async_session_factory

            heartbeat_data = HeartbeatData(
                uptime_seconds=data.get("uptime_seconds", 0),
                cpu_usage=data.get("cpu_usage", 0.0),
                memory_usage=data.get("memory_usage", 0.0),
                errors=data.get("errors"),
            )

            async with async_session_factory() as db:
                await device_service.record_heartbeat(
                    db, clinic_id, UUID(device_id), heartbeat_data
                )
                await db.commit()

            # Notify admin dashboard
            await emit_to_admin("device:status", {
                "device_id": device_id,
                "status": "ONLINE",
                "cpu_usage": data.get("cpu_usage", 0.0),
                "memory_usage": data.get("memory_usage", 0.0),
                "uptime_seconds": data.get("uptime_seconds", 0),
            }, str(clinic_id))

        except Exception as exc:
            logger.opt(exception=True).warning(
                "Error processing heartbeat",
                extra={"sid": sid, "device_id": device_id},
            )

    @sio.on("kiosk:print_receipt")
    async def handle_print_receipt(sid: str, data: dict[str, Any]) -> None:
        """Handle print receipt request from kiosk.

        Expected data:
            {
                "receipt_type": "queue_ticket" | "booking_confirmation" | "payment_receipt",
                "data": { ... receipt-specific fields ... }
            }
        """
        meta = get_sid_meta(sid)
        if meta is None:
            await sio.emit("ai:error", {
                "session_id": "",
                "code": "NOT_AUTHENTICATED",
                "message": "Connection not authenticated",
            }, to=sid)
            return

        device_id = data.get("device_id") or meta.get("device_id")
        receipt_type = data.get("receipt_type")
        receipt_data = data.get("data", {})

        if not receipt_type:
            await sio.emit("printer:error", {
                "error": "receipt_type is required",
                "receipt_type": None,
            }, to=sid)
            return

        logger.info(
            "Print receipt request",
            extra={"receipt_type": receipt_type, "device_id": device_id},
        )

        try:
            from app.services.printer_service import get_printer_service

            printer = get_printer_service()
            success = False

            if receipt_type == "queue_ticket":
                success = printer.print_queue_ticket(
                    ticket_number=receipt_data.get("ticket_number", ""),
                    patient_name=receipt_data.get("patient_name", "Guest"),
                    department_name=receipt_data.get("department_name", ""),
                    floor=receipt_data.get("floor", 1),
                    room=receipt_data.get("room", "101"),
                    estimated_wait=receipt_data.get("estimated_wait", 15),
                    doctor_name=receipt_data.get("doctor_name"),
                    clinic_name=receipt_data.get("clinic_name", "NANO MEDICAL CLINIC"),
                    clinic_address=receipt_data.get("clinic_address", "Toshkent, Chilonzor tumani"),
                )

            elif receipt_type == "booking_confirmation":
                success = printer.print_booking_confirmation(
                    booking_id=receipt_data.get("booking_id", ""),
                    patient_name=receipt_data.get("patient_name", "Guest"),
                    department_name=receipt_data.get("department_name", ""),
                    doctor_name=receipt_data.get("doctor_name", ""),
                    appointment_date=receipt_data.get("appointment_date", ""),
                    appointment_time=receipt_data.get("appointment_time", ""),
                    service_name=receipt_data.get("service_name", ""),
                    price=receipt_data.get("price", 0),
                    clinic_name=receipt_data.get("clinic_name", "NANO MEDICAL CLINIC"),
                    clinic_address=receipt_data.get("clinic_address", "Toshkent, Chilonzor tumani"),
                )

            elif receipt_type == "payment_receipt":
                success = printer.print_payment_receipt(
                    payment_id=receipt_data.get("payment_id", ""),
                    patient_name=receipt_data.get("patient_name", "Guest"),
                    amount=receipt_data.get("amount", 0),
                    payment_method=receipt_data.get("payment_method", ""),
                    service_name=receipt_data.get("service_name", ""),
                    clinic_name=receipt_data.get("clinic_name", "NANO MEDICAL CLINIC"),
                    clinic_address=receipt_data.get("clinic_address", "Toshkent, Chilonzor tumani"),
                )

            await sio.emit("printer:status", {
                "success": success,
                "receipt_type": receipt_type,
                "timestamp": datetime.now().isoformat(),
            }, to=sid)

        except Exception as exc:
            logger.opt(exception=True).error(
                "Print error",
                extra={"receipt_type": receipt_type, "device_id": device_id},
            )
            await sio.emit("printer:error", {
                "error": str(exc),
                "receipt_type": receipt_type,
            }, to=sid)
