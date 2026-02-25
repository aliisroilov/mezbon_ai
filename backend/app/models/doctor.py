import uuid
from datetime import time

from sqlalchemy import Boolean, ForeignKey, Index, Integer, SmallInteger, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantModel


class Doctor(TenantModel):
    __tablename__ = "doctors"

    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE")
    )
    full_name: Mapped[str] = mapped_column(String(255))
    specialty: Mapped[str] = mapped_column(String(255), default="")
    bio: Mapped[str] = mapped_column(String(2000), default="")
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    department: Mapped["Department"] = relationship(  # noqa: F821
        back_populates="doctors"
    )
    schedules: Mapped[list["DoctorSchedule"]] = relationship(
        back_populates="doctor", lazy="selectin", cascade="all, delete-orphan"
    )
    services: Mapped[list["Service"]] = relationship(  # noqa: F821
        secondary="doctor_services", back_populates="doctors", lazy="selectin"
    )


class DoctorSchedule(TenantModel):
    __tablename__ = "doctor_schedules"
    __table_args__ = (
        Index("ix_doctor_schedules_doctor_day", "doctor_id", "day_of_week"),
    )

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE")
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger)  # 0=Monday .. 6=Sunday
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    break_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    doctor: Mapped["Doctor"] = relationship(back_populates="schedules")
