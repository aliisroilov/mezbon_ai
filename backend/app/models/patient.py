from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantModel


class Patient(TenantModel):
    __tablename__ = "patients"

    full_name_enc: Mapped[str] = mapped_column(String(500))
    phone_enc: Mapped[str] = mapped_column(String(500))
    dob_enc: Mapped[str] = mapped_column(String(500), default="")
    language_preference: Mapped[str] = mapped_column(String(5), default="uz")
    face_embedding_enc: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
