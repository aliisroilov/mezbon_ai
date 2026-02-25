import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantModel


class ConsentType(str, enum.Enum):
    FACE_RECOGNITION = "FACE_RECOGNITION"
    DATA_PROCESSING = "DATA_PROCESSING"


class ConsentRecord(TenantModel):
    __tablename__ = "consent_records"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    consent_type: Mapped[ConsentType] = mapped_column(
        Enum(ConsentType, name="consent_type_enum")
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    device_id: Mapped[str] = mapped_column(String(255))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
