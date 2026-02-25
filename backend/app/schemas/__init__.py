"""
Pydantic v2 schemas for request/response validation.
"""

from app.schemas.common import APIResponse, ErrorDetail, PaginationMeta, PaginationParams
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentRead
from app.schemas.doctor import (
    DoctorCreate,
    DoctorUpdate,
    DoctorRead,
    ScheduleCreate,
    ScheduleRead,
    TimeSlot,
    AvailableSlotsResponse,
)
from app.schemas.patient import PatientCreate, PatientUpdate, PatientRead, PatientLookup
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentRead,
    CheckInRequest,
)
from app.schemas.payment import PaymentInitiate, PaymentRead, PaymentWebhook
from app.schemas.queue import QueueTicketCreate, QueueTicketRead, QueueStats
from app.schemas.device import DeviceRegister, DeviceUpdate, DeviceRead, HeartbeatData
from app.schemas.faq import FAQCreate, FAQUpdate, FAQRead
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    IntentClassification,
    FaceDetectionResponse,
    FaceIdentifyResponse,
    STTRequest,
    STTResponse,
    TTSRequest,
    TTSResponse,
)

__all__ = [
    # Common
    "APIResponse",
    "ErrorDetail",
    "PaginationMeta",
    "PaginationParams",
    # Auth
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    # Department
    "DepartmentCreate",
    "DepartmentUpdate",
    "DepartmentRead",
    # Doctor
    "DoctorCreate",
    "DoctorUpdate",
    "DoctorRead",
    "ScheduleCreate",
    "ScheduleRead",
    "TimeSlot",
    "AvailableSlotsResponse",
    # Patient
    "PatientCreate",
    "PatientUpdate",
    "PatientRead",
    "PatientLookup",
    # Appointment
    "AppointmentCreate",
    "AppointmentUpdate",
    "AppointmentRead",
    "CheckInRequest",
    # Payment
    "PaymentInitiate",
    "PaymentRead",
    "PaymentWebhook",
    # Queue
    "QueueTicketCreate",
    "QueueTicketRead",
    "QueueStats",
    # Device
    "DeviceRegister",
    "DeviceUpdate",
    "DeviceRead",
    "HeartbeatData",
    # FAQ
    "FAQCreate",
    "FAQUpdate",
    "FAQRead",
    # AI
    "ChatRequest",
    "ChatResponse",
    "IntentClassification",
    "FaceDetectionResponse",
    "FaceIdentifyResponse",
    "STTRequest",
    "STTResponse",
    "TTSRequest",
    "TTSResponse",
]
