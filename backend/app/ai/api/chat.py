"""Chat API route — main entry point for kiosk interaction."""

import base64
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.face_service import face_service
from app.ai.gemini_service import gemini_service
from app.ai.muxlisa_service import muxlisa_service
from app.ai.orchestrator import Orchestrator, OrchestratorResponse
from app.ai.session_manager import session_manager
from app.api.deps import get_current_user
from app.core.database import async_session_factory
from app.core.response import success_response

router = APIRouter(prefix="/ai", tags=["AI Chat"])


def _get_orchestrator() -> Orchestrator:
    """Build orchestrator from module-level singletons."""
    return Orchestrator(
        gemini=gemini_service,
        face=face_service,
        muxlisa=muxlisa_service,
        session_mgr=session_manager,
        db_session_factory=async_session_factory,
    )


class ProcessRequest(BaseModel):
    """Kiosk sends this for every interaction."""

    session_id: str | None = None
    device_id: str = Field(..., min_length=1)
    clinic_id: UUID
    input_type: str = Field(..., pattern=r"^(face|speech|touch|timeout)$")
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("/process")
async def process_input(
    body: ProcessRequest,
    _user=Depends(get_current_user),
) -> dict:
    """Main entry point from the kiosk.

    Handles face detection, speech input, touch actions, and timeouts.
    Routes to the appropriate orchestrator method.
    """
    orch = _get_orchestrator()

    if body.input_type == "face":
        # data.image_base64 → raw bytes
        image_b64 = body.data.get("image_base64", "")
        image_bytes = base64.b64decode(image_b64) if image_b64 else b""
        result = await orch.handle_face_detected(
            device_id=body.device_id,
            clinic_id=body.clinic_id,
            image_bytes=image_bytes,
        )

    elif body.input_type == "speech":
        if not body.session_id:
            return success_response(
                OrchestratorResponse(
                    text="Sessiya topilmadi.",
                    state="IDLE",
                    session_id="",
                ).model_dump()
            )
        audio_b64 = body.data.get("audio_base64", "")
        audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
        result = await orch.handle_speech(
            session_id=body.session_id,
            audio_bytes=audio_bytes,
        )

    elif body.input_type == "touch":
        if not body.session_id:
            return success_response(
                OrchestratorResponse(
                    text="Sessiya topilmadi.",
                    state="IDLE",
                    session_id="",
                ).model_dump()
            )
        action = body.data.get("action", "")
        action_data = body.data.get("payload", {})
        result = await orch.handle_touch(
            session_id=body.session_id,
            action=action,
            data=action_data,
        )

    elif body.input_type == "timeout":
        if not body.session_id:
            return success_response(
                OrchestratorResponse(
                    text="Sessiya tugadi.",
                    state="IDLE",
                    session_id="",
                ).model_dump()
            )
        result = await orch.handle_timeout(session_id=body.session_id)

    else:
        return success_response(
            OrchestratorResponse(
                text="Noto'g'ri so'rov turi.",
                state="IDLE",
                session_id=body.session_id or "",
            ).model_dump()
        )

    return success_response(result.model_dump())
