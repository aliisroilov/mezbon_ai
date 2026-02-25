"""initial_schema

Revision ID: fa080a235ff1
Revises:
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "fa080a235ff1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- clinics (no FK, root table) ---
    op.create_table(
        "clinics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(500), nullable=False, server_default=""),
        sa.Column("phone", sa.String(50), nullable=False, server_default=""),
        sa.Column("email", sa.String(255), nullable=False, server_default=""),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("settings", JSONB, nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Tashkent"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- departments ---
    op.create_table(
        "departments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("room_number", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- doctors ---
    op.create_table(
        "doctors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("specialty", sa.String(255), nullable=False, server_default=""),
        sa.Column("bio", sa.String(2000), nullable=False, server_default=""),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- doctor_schedules ---
    op.create_table(
        "doctor_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("doctor_id", UUID(as_uuid=True), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_doctor_schedules_doctor_day", "doctor_schedules", ["doctor_id", "day_of_week"])

    # --- services ---
    op.create_table(
        "services",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("price_uzs", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- doctor_services (association) ---
    op.create_table(
        "doctor_services",
        sa.Column("doctor_id", UUID(as_uuid=True), sa.ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
    )

    # --- patients ---
    op.create_table(
        "patients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("full_name_enc", sa.String(500), nullable=False),
        sa.Column("phone_enc", sa.String(500), nullable=False),
        sa.Column("dob_enc", sa.String(500), nullable=False, server_default=""),
        sa.Column("language_preference", sa.String(5), nullable=False, server_default="uz"),
        sa.Column("face_embedding_enc", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- consent_records ---
    op.create_table(
        "consent_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_type", sa.Enum("FACE_RECOGNITION", "DATA_PROCESSING", name="consent_type_enum", create_constraint=True), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- appointments ---
    op.create_table(
        "appointments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doctor_id", UUID(as_uuid=True), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("status", sa.Enum("SCHEDULED", "CHECKED_IN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "NO_SHOW", name="appointment_status_enum", create_constraint=True), nullable=False, server_default="SCHEDULED"),
        sa.Column("payment_status", sa.Enum("PENDING", "PAID", "REFUNDED", name="payment_status_enum", create_constraint=True), nullable=False, server_default="PENDING"),
        sa.Column("notes", sa.String(2000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_appointments_clinic_scheduled", "appointments", ["clinic_id", "scheduled_at"])

    # --- payments ---
    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.Enum("CASH", "UZCARD", "HUMO", "CLICK", "PAYME", name="payment_method_enum", create_constraint=True), nullable=False),
        sa.Column("transaction_id", sa.String(255), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "COMPLETED", "FAILED", "REFUNDED", name="payment_transaction_status_enum", create_constraint=True), nullable=False, server_default="PENDING"),
        sa.Column("provider_response", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- queue_tickets ---
    op.create_table(
        "queue_tickets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doctor_id", UUID(as_uuid=True), sa.ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ticket_number", sa.String(20), nullable=False),
        sa.Column("status", sa.Enum("WAITING", "IN_PROGRESS", "COMPLETED", "NO_SHOW", name="queue_status_enum", create_constraint=True), nullable=False, server_default="WAITING"),
        sa.Column("estimated_wait_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_queue_tickets_clinic_status_created", "queue_tickets", ["clinic_id", "status", "created_at"])

    # --- devices ---
    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("serial_number", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location_description", sa.String(500), nullable=False, server_default=""),
        sa.Column("status", sa.Enum("ONLINE", "OFFLINE", "MAINTENANCE", name="device_status_enum", create_constraint=True), nullable=False, server_default="OFFLINE"),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_devices_clinic_serial", "devices", ["clinic_id", "serial_number"], unique=True)

    # --- device_heartbeats ---
    op.create_table(
        "device_heartbeats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uptime_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cpu_usage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("memory_usage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("errors", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- faqs ---
    op.create_table(
        "faqs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("language", sa.String(2), nullable=False, server_default="uz"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- announcements ---
    op.create_table(
        "announcements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("language", sa.String(2), nullable=False, server_default="uz"),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- visit_logs ---
    op.create_table(
        "visit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("intent", sa.String(100), nullable=True),
        sa.Column("language_used", sa.String(5), nullable=False, server_default="uz"),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("was_successful", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("handed_off_to_human", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("role", sa.Enum("SUPER_ADMIN", "CLINIC_ADMIN", "STAFF", name="user_role_enum", create_constraint=True), nullable=False, server_default="STAFF"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_clinic_email", "users", ["clinic_id", "email"], unique=True)


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("audit_logs")
    op.drop_table("visit_logs")
    op.drop_table("announcements")
    op.drop_table("faqs")
    op.drop_table("device_heartbeats")
    op.drop_table("devices")
    op.drop_table("queue_tickets")
    op.drop_table("payments")
    op.drop_table("appointments")
    op.drop_table("consent_records")
    op.drop_table("patients")
    op.drop_table("doctor_services")
    op.drop_table("services")
    op.drop_table("doctor_schedules")
    op.drop_table("doctors")
    op.drop_table("departments")
    op.drop_table("clinics")

    sa.Enum(name="user_role_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="consent_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="device_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="queue_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_transaction_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_method_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="appointment_status_enum").drop(op.get_bind(), checkfirst=True)
