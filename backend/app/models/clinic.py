from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Clinic(BaseModel):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(500), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    settings: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Tashkent")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    departments: Mapped[list["Department"]] = relationship(  # noqa: F821
        back_populates="clinic", lazy="selectin"
    )
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="clinic", lazy="selectin"
    )
