import uuid

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantModel


class Department(TenantModel):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1000), default="")
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    clinic: Mapped["Clinic"] = relationship(  # noqa: F821
        back_populates="departments"
    )
    doctors: Mapped[list["Doctor"]] = relationship(  # noqa: F821
        back_populates="department", lazy="selectin"
    )
