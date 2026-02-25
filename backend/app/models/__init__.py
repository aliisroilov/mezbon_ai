"""
All models imported here so Alembic autogenerate can detect them.
"""

from app.models.base import BaseModel, TenantModel
from app.models.clinic import Clinic
from app.models.department import Department
from app.models.doctor import Doctor, DoctorSchedule
from app.models.service import Service, doctor_services
from app.models.patient import Patient
from app.models.consent import ConsentRecord
from app.models.appointment import Appointment
from app.models.payment import Payment
from app.models.queue import QueueTicket
from app.models.device import Device, DeviceHeartbeat
from app.models.faq import FAQ
from app.models.content import Announcement
from app.models.visit_log import VisitLog
from app.models.audit_log import AuditLog
from app.models.user import User

__all__ = [
    "BaseModel",
    "TenantModel",
    "Clinic",
    "Department",
    "Doctor",
    "DoctorSchedule",
    "Service",
    "doctor_services",
    "Patient",
    "ConsentRecord",
    "Appointment",
    "Payment",
    "QueueTicket",
    "Device",
    "DeviceHeartbeat",
    "FAQ",
    "Announcement",
    "VisitLog",
    "AuditLog",
    "User",
]
