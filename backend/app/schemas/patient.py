import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=9, max_length=20)
    date_of_birth: date | None = None
    language_preference: str = Field(default="uz", pattern=r"^(uz|ru|en)$")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not cleaned.replace("+", "").isdigit():
            raise ValueError("Phone must contain only digits and optional leading +")
        return cleaned


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=9, max_length=20)
    date_of_birth: date | None = None
    language_preference: str | None = Field(default=None, pattern=r"^(uz|ru|en)$")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not cleaned.replace("+", "").isdigit():
            raise ValueError("Phone must contain only digits and optional leading +")
        return cleaned


class PatientRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    clinic_id: uuid.UUID
    full_name: str
    phone: str
    date_of_birth: date | None = None
    language_preference: str
    has_face_embedding: bool = False
    created_at: datetime
    updated_at: datetime


class PatientLookup(BaseModel):
    phone: str = Field(..., min_length=9, max_length=20)
