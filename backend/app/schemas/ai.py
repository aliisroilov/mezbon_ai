import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InputType(str, Enum):
    TEXT = "text"
    SPEECH = "speech"
    TOUCH = "touch"


class ChatRequest(BaseModel):
    session_id: str
    message: str = ""
    input_type: InputType = InputType.TEXT


class ChatResponse(BaseModel):
    text: str
    audio_url: str | None = None
    function_calls: list[dict[str, Any]] = Field(default_factory=list)
    ui_action: str | None = None
    next_state: str | None = None


class IntentClassification(BaseModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    entities: dict[str, Any] = Field(default_factory=dict)


class FaceDetectionRequest(BaseModel):
    image: bytes


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DetectedFace(BaseModel):
    bbox: BoundingBox
    confidence: float = Field(ge=0.0, le=1.0)


class FaceDetectionResponse(BaseModel):
    faces: list[DetectedFace] = Field(default_factory=list)


class FaceIdentifyResponse(BaseModel):
    patient_id: uuid.UUID | None = None
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    patient_name: str | None = None


class STTRequest(BaseModel):
    audio: bytes
    format: str = "wav"


class STTResponse(BaseModel):
    transcript: str
    language: str = "uz"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: str = Field(default="uz", pattern=r"^(uz|ru|en)$")
    voice: str = "default"


class TTSResponse(BaseModel):
    audio_url: str | None = None
    audio_bytes: bytes | None = None
