import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantModel


class VisitLog(TenantModel):
    __tablename__ = "visit_logs"

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE")
    )
    session_id: Mapped[str] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language_used: Mapped[str] = mapped_column(String(5), default="uz")
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    was_successful: Mapped[bool] = mapped_column(Boolean, default=False)
    handed_off_to_human: Mapped[bool] = mapped_column(Boolean, default=False)
