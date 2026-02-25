import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FAQCreate(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    language: str = Field(default="uz", pattern=r"^(uz|ru|en)$")
    department_id: uuid.UUID | None = None
    sort_order: int = 0


class FAQUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=1)
    answer: str | None = Field(default=None, min_length=1)
    language: str | None = Field(default=None, pattern=r"^(uz|ru|en)$")
    department_id: uuid.UUID | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class FAQRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    clinic_id: uuid.UUID
    question: str
    answer: str
    language: str
    department_id: uuid.UUID | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
