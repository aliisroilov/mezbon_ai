from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantModel


class Announcement(TenantModel):
    __tablename__ = "announcements"

    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(2), default="uz")
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active_to: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=True)
