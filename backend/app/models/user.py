import enum

from sqlalchemy import Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantModel


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    CLINIC_ADMIN = "CLINIC_ADMIN"
    STAFF = "STAFF"


class User(TenantModel):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_clinic_email", "clinic_id", "email", unique=True),
    )

    email: Mapped[str] = mapped_column(String(255), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"),
        default=UserRole.STAFF,
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    clinic: Mapped["Clinic"] = relationship(  # noqa: F821
        back_populates="users"
    )
