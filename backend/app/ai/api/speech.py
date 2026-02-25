"""Speech API routes — STT, TTS, and language detection."""

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.ai.muxlisa_service import muxlisa_service
from app.api.deps import get_current_user
from app.core.response import success_response

router = APIRouter(prefix="/ai", tags=["AI Speech"])


class TTSRequestBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = Field(default="uz", pattern=r"^(uz|ru|en)$")
    voice: str = "female"


class DetectLanguageBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(..., description="Audio file (WAV/MP3/OGG)"),
    _user=Depends(get_current_user),
) -> dict:
    """Convert uploaded audio to text.

    Returns transcript, detected language, and confidence score.
    """
    audio_bytes = await audio.read()
    # Infer format from filename or content type
    fmt = "wav"
    if audio.filename:
        ext = audio.filename.rsplit(".", 1)[-1].lower()
        if ext in ("mp3", "ogg", "wav", "webm", "flac"):
            fmt = ext

    result = await muxlisa_service.speech_to_text(audio_bytes, audio_format=fmt)
    return success_response(result.model_dump())


@router.post("/tts")
async def text_to_speech(
    body: TTSRequestBody,
    _user=Depends(get_current_user),
) -> Response:
    """Convert text to speech audio.

    Returns WAV audio bytes directly as an audio response.
    """
    audio_bytes = await muxlisa_service.text_to_speech(
        text=body.text,
        language=body.language,
        voice=body.voice,
    )
    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=speech.wav"},
    )


@router.post("/detect-language")
async def detect_language(
    body: DetectLanguageBody,
    _user=Depends(get_current_user),
) -> dict:
    """Detect language from text using heuristics.

    Returns language code: uz, ru, or en.
    """
    lang = muxlisa_service.detect_language(body.text)
    return success_response({"language": lang})
