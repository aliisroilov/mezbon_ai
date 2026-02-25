import uuid
from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TenantModel

# Association table for Doctor <-> Service many-to-many
doctor_services = Table(
    "doctor_services",
    Base.metadata,
    Column(
        "doctor_id",
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Service(TenantModel):
    __tablename__ = "services"

    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1000), default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    price_uzs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    doctors: Mapped[list["Doctor"]] = relationship(  # noqa: F821
        secondary="doctor_services", back_populates="services", lazy="selectin"
    )
