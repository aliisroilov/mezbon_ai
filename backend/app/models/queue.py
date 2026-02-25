import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantModel


class QueueStatus(str, enum.Enum):
    WAITING = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class QueueTicket(TenantModel):
    __tablename__ = "queue_tickets"
    __table_args__ = (
        Index(
            "ix_queue_tickets_clinic_status_created",
            "clinic_id",
            "status",
            "created_at",
        ),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE")
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="SET NULL"),
        nullable=True,
    )
    ticket_number: Mapped[str] = mapped_column(String(20))
    status: Mapped[QueueStatus] = mapped_column(
        Enum(QueueStatus, name="queue_status_enum"),
        default=QueueStatus.WAITING,
    )
    estimated_wait_minutes: Mapped[int] = mapped_column(Integer, default=0)
    called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )