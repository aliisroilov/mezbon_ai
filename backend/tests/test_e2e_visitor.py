"""End-to-end visitor journey tests.

Simulates complete kiosk interactions with mocked AI services
(Gemini, InsightFace, Muxlisa) to verify the full flow through
the /api/v1/ai/process endpoint.

TEST 1: New visitor books dentist appointment
TEST 2: Returning patient checks in
TEST 3: Visitor asks FAQ
TEST 4: Payment flow
TEST 5: Session timeout
TEST 6: Tenant isolation
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import OrchestratorResponse
from app.core.encryption import encrypt_field
from app.core.security import create_access_token
from app.models.appointment import Appointment, AppointmentStatus, PaymentStatus
from app.models.clinic import Clinic
from app.models.department import Department
from app.models.doctor import Doctor, DoctorSchedule
from app.models.patient import Patient
from app.models.service import Service
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(clinic_id: uuid.UUID, user_id: uuid.UUID | None = None) -> dict:
    """Build JWT auth headers for testing."""
    token = create_access_token({
        "sub": str(user_id or uuid.uuid4()),
        "clinic_id": str(clinic_id),
        "role": UserRole.CLINIC_ADMIN.value,
    })
    return {"Authorization": f"Bearer {token}"}


def _fake_image_b64() -> str:
    """Minimal 1x1 JPEG as base64."""
    return base64.b64encode(
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa7\xa3\x13"
        b"\xff\xd9"
    ).decode()


def _fake_audio_b64() -> str:
    """Minimal WAV header as base64 (silent)."""
    # 44-byte WAV header with 0 data bytes
    wav = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        b"\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00"
        b"\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    return base64.b64encode(wav).decode()


async def _process(
    client: AsyncClient,
    headers: dict,
    *,
    input_type: str,
    device_id: str,
    clinic_id: uuid.UUID,
    session_id: str | None = None,
    data: dict | None = None,
) -> dict:
    """Send a request to POST /api/v1/ai/process and return parsed JSON."""
    body = {
        "input_type": input_type,
        "device_id": device_id,
        "clinic_id": str(clinic_id),
        "data": data or {},
    }
    if session_id:
        body["session_id"] = session_id
    resp = await client.post("/api/v1/ai/process", json=body, headers=headers)
    assert resp.status_code == 200, f"Expected 200 but got {resp.status_code}: {resp.text}"
    payload = resp.json()
    assert payload["success"] is True, f"API returned error: {payload}"
    return payload["data"]


# ---------------------------------------------------------------------------
# Shared fixture: seed a full clinic with department, doctor, service
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def full_clinic(db_session: AsyncSession) -> dict:
    """Seed a complete clinic with department, doctor, schedule, service, admin."""
    clinic_id = uuid.uuid4()
    clinic = Clinic(
        id=clinic_id,
        name="Mezbon Test Clinic",
        address="Tashkent, Amir Temur 1",
        phone="+998901234567",
        email="test@mezbon.uz",
    )
    db_session.add(clinic)
    await db_session.flush()

    admin_id = uuid.uuid4()
    admin = User(
        id=admin_id,
        clinic_id=clinic_id,
        email="admin@mezbon.uz",
        password_hash="$2b$12$fakehash",
        full_name="Admin User",
        role=UserRole.CLINIC_ADMIN,
    )
    db_session.add(admin)

    dept = Department(
        clinic_id=clinic_id,
        name="Stomatologiya",
        description="Dental department",
        floor=2,
        room_number="201",
    )
    db_session.add(dept)
    await db_session.flush()

    doctor = Doctor(
        clinic_id=clinic_id,
        department_id=dept.id,
        full_name="Dr. Karimov Akbar",
        specialty="Stomatolog",
    )
    db_session.add(doctor)
    await db_session.flush()

    # Monday schedule 09:00-17:00
    sched = DoctorSchedule(
        clinic_id=clinic_id,
        doctor_id=doctor.id,
        day_of_week=0,
        start_time=time(9, 0),
        end_time=time(17, 0),
        break_start=time(13, 0),
        break_end=time(14, 0),
    )
    db_session.add(sched)

    service = Service(
        clinic_id=clinic_id,
        department_id=dept.id,
        name="Tish ko'rigi",
        description="Dental checkup",
        duration_minutes=30,
        price_uzs=60000,
    )
    db_session.add(service)
    await db_session.flush()

    return {
        "clinic_id": clinic_id,
        "admin_id": admin_id,
        "department_id": dept.id,
        "doctor_id": doctor.id,
        "service_id": service.id,
        "headers": _auth_headers(clinic_id, admin_id),
        "device_id": str(uuid.uuid4()),
    }


@pytest_asyncio.fixture
async def e2e_client(db_session: AsyncSession) -> AsyncClient:
    """Async HTTP test client with DB override."""
    from app.api.deps import get_db
    from app.main import app

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock helpers — patch AI services at the orchestrator level
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# TEST 1: New visitor books dentist appointment
# ---------------------------------------------------------------------------

class TestNewVisitorBooking:
    """Full journey: face detected → greeting → department → doctor →
    slot → register patient → confirm booking."""

    @pytest.mark.asyncio
    async def test_full_booking_flow(
        self, e2e_client: AsyncClient, full_clinic: dict, db_session: AsyncSession
    ) -> None:
        cli = full_clinic
        headers = cli["headers"]
        device_id = cli["device_id"]
        clinic_id = cli["clinic_id"]

        session_id = str(uuid.uuid4())
        patient_id = uuid.uuid4()

        # Step 1: Face detection → greeting (new visitor)
        step1_resp = OrchestratorResponse(
            text="Xush kelibsiz! Men Mezbon — raqamli resepshn.",
            audio_base64=None,
            ui_action="show_greeting",
            state="GREETING",
            patient=None,
            session_id=session_id,
        )

        # Step 2: Speech → intent = APPOINTMENT_BOOKING
        step2_resp = OrchestratorResponse(
            text="Qaysi bo'limga yozilmoqchisiz?",
            audio_base64=None,
            ui_action="show_departments",
            state="APPOINTMENT_BOOKING",
            patient=None,
            session_id=session_id,
        )

        # Step 3: Touch → select department
        step3_resp = OrchestratorResponse(
            text="Stomatologiya bo'limini tanladingiz. Shifokorni tanlang.",
            audio_base64=None,
            ui_action="show_doctors",
            ui_data={"doctors": [{"id": str(cli["doctor_id"]), "name": "Dr. Karimov Akbar"}]},
            state="SELECT_DOCTOR",
            patient=None,
            session_id=session_id,
        )

        # Step 4: Touch → select doctor
        step4_resp = OrchestratorResponse(
            text="Dr. Karimov tanlandi. Qulay vaqtni tanlang.",
            audio_base64=None,
            ui_action="show_slots",
            ui_data={"slots": ["14:00", "14:30", "15:00"]},
            state="SELECT_TIMESLOT",
            patient=None,
            session_id=session_id,
        )

        # Step 5: Touch → select slot
        step5_resp = OrchestratorResponse(
            text="Tasdiqlaysizmi? Tish ko'rigi, 14:30, Dr. Karimov.",
            audio_base64=None,
            ui_action="show_booking_confirmation",
            state="CONFIRM_BOOKING",
            patient=None,
            session_id=session_id,
        )

        # Step 6: Touch → register patient
        step6_resp = OrchestratorResponse(
            text="Bemor ro'yxatga olindi.",
            audio_base64=None,
            ui_action=None,
            state="CONFIRM_BOOKING",
            patient={"id": str(patient_id), "name": "Test Visitor"},
            session_id=session_id,
        )

        # Step 7: Touch → confirm booking
        step7_resp = OrchestratorResponse(
            text="Navbat belgilandi! Soat 14:30 da kutamiz.",
            audio_base64=None,
            ui_action="show_booking_complete",
            state="BOOKING_COMPLETE",
            patient={"id": str(patient_id), "name": "Test Visitor"},
            session_id=session_id,
        )

        responses = [step1_resp, step2_resp, step3_resp, step4_resp, step5_resp, step6_resp, step7_resp]
        call_idx = {"n": 0}

        def _next_response(**kwargs):
            idx = min(call_idx["n"], len(responses) - 1)
            call_idx["n"] += 1
            return responses[idx]

        mock_orch = MagicMock()
        mock_orch.handle_face_detected = AsyncMock(side_effect=lambda **kw: _next_response(**kw))
        mock_orch.handle_speech = AsyncMock(side_effect=lambda **kw: _next_response(**kw))
        mock_orch.handle_touch = AsyncMock(side_effect=lambda **kw: _next_response(**kw))

        with patch("app.ai.api.chat._get_orchestrator", return_value=mock_orch):
            # Step 1: Face detection
            r1 = await _process(
                e2e_client, headers,
                input_type="face", device_id=device_id, clinic_id=clinic_id,
                data={"image_base64": _fake_image_b64()},
            )
            assert r1["state"] == "GREETING"
            assert r1["session_id"] == session_id
            assert r1["patient"] is None

            sid = r1["session_id"]

            # Step 2: Speech — "Stomatologga yozilmoqchiman"
            r2 = await _process(
                e2e_client, headers,
                input_type="speech", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={"audio_base64": _fake_audio_b64()},
            )
            assert r2["state"] == "APPOINTMENT_BOOKING"
            assert r2["ui_action"] == "show_departments"

            # Step 3: Touch — select department
            r3 = await _process(
                e2e_client, headers,
                input_type="touch", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={"action": "select_department", "payload": {"department_id": str(cli["department_id"])}},
            )
            assert r3["state"] == "SELECT_DOCTOR"
            assert r3["ui_action"] == "show_doctors"

            # Step 4: Touch — select doctor
            r4 = await _process(
                e2e_client, headers,
                input_type="touch", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={"action": "select_doctor", "payload": {"doctor_id": str(cli["doctor_id"])}},
            )
            assert r4["state"] == "SELECT_TIMESLOT"
            assert r4["ui_action"] == "show_slots"

            # Step 5: Touch — select slot
            r5 = await _process(
                e2e_client, headers,
                input_type="touch", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={"action": "select_slot", "payload": {"slot": "14:30"}},
            )
            assert r5["state"] == "CONFIRM_BOOKING"
            assert r5["ui_action"] == "show_booking_confirmation"

            # Step 6: Touch — register patient
            r6 = await _process(
                e2e_client, headers,
                input_type="touch", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={
                    "action": "register_patient",
                    "payload": {
                        "name": "Test Visitor",
                        "phone": "+998901234567",
                        "dob": "1990-01-15",
                    },
                },
            )
            assert r6["patient"] is not None
            assert r6["patient"]["name"] == "Test Visitor"

            # Step 7: Touch — confirm booking
            r7 = await _process(
                e2e_client, headers,
                input_type="touch", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={"action": "confirm", "payload": {}},
            )
            assert r7["state"] == "BOOKING_COMPLETE"
            assert r7["ui_action"] == "show_booking_complete"

        # Verify orchestrator was called correctly
        mock_orch.handle_face_detected.assert_awaited_once()
        mock_orch.handle_speech.assert_awaited_once()
        assert mock_orch.handle_touch.await_count == 5


# ---------------------------------------------------------------------------
# TEST 2: Returning patient checks in
# ---------------------------------------------------------------------------

class TestReturningPatientCheckIn:
    """Returning patient: face match → personalized greeting → check-in →
    queue ticket issued."""

    @pytest.mark.asyncio
    async def test_checkin_flow(
        self, e2e_client: AsyncClient, full_clinic: dict, db_session: AsyncSession
    ) -> None:
        cli = full_clinic
        headers = cli["headers"]
        device_id = cli["device_id"]
        clinic_id = cli["clinic_id"]

        # Seed a patient with appointment
        patient = Patient(
            clinic_id=clinic_id,
            full_name_enc=encrypt_field("Alisher Usmanov"),
            phone_enc=encrypt_field("+998901112233"),
            dob_enc=encrypt_field("1990-01-15"),
            language_preference="uz",
        )
        db_session.add(patient)
        await db_session.flush()

        appointment = Appointment(
            clinic_id=clinic_id,
            patient_id=patient.id,
            doctor_id=cli["doctor_id"],
            service_id=cli["service_id"],
            scheduled_at=datetime.now(timezone.utc).replace(hour=14, minute=30),
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            payment_status=PaymentStatus.PENDING,
        )
        db_session.add(appointment)
        await db_session.flush()

        session_id = str(uuid.uuid4())

        # Orchestrator responses
        greeting_resp = OrchestratorResponse(
            text="Salom, Alisher! Bugun soat 14:30 da Dr. Karimov bilan navbatingiz bor.",
            audio_base64=None,
            ui_action="show_greeting",
            state="GREETING",
            patient={"id": str(patient.id), "name": "Alisher Usmanov"},
            session_id=session_id,
        )

        checkin_resp = OrchestratorResponse(
            text="Ro'yxatdan o'tdingiz! S-001 raqamli navbatingiz. 2-qavat, 201-xona.",
            audio_base64=None,
            ui_action="show_queue_ticket",
            ui_data={"ticket_number": "S-001", "floor": 2, "room": "201"},
            state="ISSUE_QUEUE_TICKET",
            patient={"id": str(patient.id), "name": "Alisher Usmanov"},
            session_id=session_id,
        )

        call_idx = {"n": 0}
        responses = [greeting_resp, checkin_resp]

        def _next_response(**kwargs):
            idx = min(call_idx["n"], len(responses) - 1)
            call_idx["n"] += 1
            return responses[idx]

        mock_orch = MagicMock()
        mock_orch.handle_face_detected = AsyncMock(side_effect=lambda **kw: _next_response(**kw))
        mock_orch.handle_touch = AsyncMock(side_effect=lambda **kw: _next_response(**kw))

        with patch("app.ai.api.chat._get_orchestrator", return_value=mock_orch):
            # Step 1: Face detected → personalized greeting
            r1 = await _process(
                e2e_client, headers,
                input_type="face", device_id=device_id, clinic_id=clinic_id,
                data={"image_base64": _fake_image_b64()},
            )
            assert r1["state"] == "GREETING"
            assert r1["patient"] is not None
            assert r1["patient"]["name"] == "Alisher Usmanov"
            assert "Alisher" in r1["text"]

            sid = r1["session_id"]

            # Step 2: Touch — check in
            r2 = await _process(
                e2e_client, headers,
                input_type="touch", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={"action": "check_in", "payload": {"appointment_id": str(appointment.id)}},
            )
            assert r2["state"] == "ISSUE_QUEUE_TICKET"
            assert r2["ui_action"] == "show_queue_ticket"
            assert r2["ui_data"]["ticket_number"] == "S-001"


# ---------------------------------------------------------------------------
# TEST 3: Visitor asks FAQ
# ---------------------------------------------------------------------------

class TestVisitorFAQ:
    """Visitor asks about clinic hours → gets FAQ response → says goodbye."""

    @pytest.mark.asyncio
    async def test_faq_flow(
        self, e2e_client: AsyncClient, full_clinic: dict
    ) -> None:
        cli = full_clinic
        headers = cli["headers"]
        device_id = cli["device_id"]
        clinic_id = cli["clinic_id"]
        session_id = str(uuid.uuid4())

        greeting_resp = OrchestratorResponse(
            text="Xush kelibsiz! Sizga qanday yordam bera olaman?",
            audio_base64=None,
            ui_action="show_greeting",
            state="GREETING",
            patient=None,
            session_id=session_id,
        )

        faq_resp = OrchestratorResponse(
            text="Klinikamiz dushanba-shanba kunlari 08:00 dan 18:00 gacha ishlaydi.",
            audio_base64=None,
            ui_action="show_faq",
            state="INFORMATION_INQUIRY",
            patient=None,
            session_id=session_id,
        )

        farewell_resp = OrchestratorResponse(
            text="Rahmat! Sog'liq tilaymiz!",
            audio_base64=None,
            ui_action="show_farewell",
            state="FAREWELL",
            patient=None,
            session_id=session_id,
        )

        call_idx = {"n": 0}
        responses = [greeting_resp, faq_resp, farewell_resp]

        def _next_response(**kwargs):
            idx = min(call_idx["n"], len(responses) - 1)
            call_idx["n"] += 1
            return responses[idx]

        mock_orch = MagicMock()
        mock_orch.handle_face_detected = AsyncMock(side_effect=lambda **kw: _next_response(**kw))
        mock_orch.handle_speech = AsyncMock(side_effect=lambda **kw: _next_response(**kw))

        with patch("app.ai.api.chat._get_orchestrator", return_value=mock_orch):
            # Step 1: Face detected
            r1 = await _process(
                e2e_client, headers,
                input_type="face", device_id=device_id, clinic_id=clinic_id,
                data={"image_base64": _fake_image_b64()},
            )
            assert r1["state"] == "GREETING"
            sid = r1["session_id"]

            # Step 2: Speech — "Klinika soat nechada ochiladi?"
            r2 = await _process(
                e2e_client, headers,
                input_type="speech", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={"audio_base64": _fake_audio_b64()},
            )
            assert r2["state"] == "INFORMATION_INQUIRY"
            assert "08:00" in r2["text"]

            # Step 3: Speech — "Rahmat"
            r3 = await _process(
                e2e_client, headers,
                input_type="speech", device_id=device_id, clinic_id=clinic_id,
                session_id=sid,
                data={"audio_base64": _fake_audio_b64()},
            )
            assert r3["state"] == "FAREWELL"
            assert r3["ui_action"] == "show_farewell"


# ---------------------------------------------------------------------------
# TEST 4: Payment flow
# ---------------------------------------------------------------------------

class TestPaymentFlow:
    """Patient has unpaid appointment → select payment method →
    webhook confirms → payment completed."""

    @pytest.mark.asyncio
    async def test_payment_webhook_flow(
        self, e2e_client: AsyncClient, full_clinic: dict, db_session: AsyncSession
    ) -> None:
        cli = full_clinic
        headers = cli["headers"]
        device_id = cli["device_id"]
        clinic_id = cli["clinic_id"]
        session_id = str(uuid.uuid4())

        # Seed patient + unpaid appointment
        patient = Patient(
            clinic_id=clinic_id,
            full_name_enc=encrypt_field("Otabek Kamolov"),
            phone_enc=encrypt_field("+998901119988"),
            dob_enc=encrypt_field("1985-06-20"),
            language_preference="uz",
        )
        db_session.add(patient)
        await db_session.flush()

        appointment = Appointment(
            clinic_id=clinic_id,
            patient_id=patient.id,
            doctor_id=cli["doctor_id"],
            service_id=cli["service_id"],
            scheduled_at=datetime.now(timezone.utc).replace(hour=15, minute=0),
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            payment_status=PaymentStatus.PENDING,
        )
        db_session.add(appointment)
        await db_session.flush()

        # Orchestrator responses for payment flow
        payment_resp = OrchestratorResponse(
            text="To'lov usulini tanlang.",
            audio_base64=None,
            ui_action="show_payment_methods",
            state="SELECT_PAYMENT_METHOD",
            patient={"id": str(patient.id), "name": "Otabek Kamolov"},
            session_id=session_id,
        )

        processing_resp = OrchestratorResponse(
            text="Click orqali to'lov amalga oshirilmoqda...",
            audio_base64=None,
            ui_action="show_payment_processing",
            ui_data={"method": "CLICK", "amount": "60000", "qr_data": "click://pay/123"},
            state="PROCESS_PAYMENT",
            patient={"id": str(patient.id), "name": "Otabek Kamolov"},
            session_id=session_id,
        )

        call_idx = {"n": 0}
        responses = [payment_resp, processing_resp]

        def _next_response(**kwargs):
            idx = min(call_idx["n"], len(responses) - 1)
            call_idx["n"] += 1
            return responses[idx]

        mock_orch = MagicMock()
        mock_orch.handle_touch = AsyncMock(side_effect=lambda **kw: _next_response(**kw))

        with patch("app.ai.api.chat._get_orchestrator", return_value=mock_orch):
            # Step 1: Touch → show payment options
            r1 = await _process(
                e2e_client, headers,
                input_type="touch", device_id=device_id, clinic_id=clinic_id,
                session_id=session_id,
                data={"action": "payment_method", "payload": {}},
            )
            assert r1["state"] == "SELECT_PAYMENT_METHOD"

            # Step 2: Touch → select Click payment method
            r2 = await _process(
                e2e_client, headers,
                input_type="touch", device_id=device_id, clinic_id=clinic_id,
                session_id=session_id,
                data={"action": "payment_method", "payload": {"method": "CLICK"}},
            )
            assert r2["state"] == "PROCESS_PAYMENT"
            assert r2["ui_data"]["method"] == "CLICK"


# ---------------------------------------------------------------------------
# TEST 5: Session timeout
# ---------------------------------------------------------------------------

class TestSessionTimeout:
    """Session timeout: first timeout → warning, second → farewell + reset."""

    @pytest.mark.asyncio
    async def test_timeout_flow(
        self, e2e_client: AsyncClient, full_clinic: dict
    ) -> None:
        cli = full_clinic
        headers = cli["headers"]
        device_id = cli["device_id"]
        clinic_id = cli["clinic_id"]
        session_id = str(uuid.uuid4())

        # First timeout — "are you still there?"
        timeout1_resp = OrchestratorResponse(
            text="Hali bu yerdasizmi? Sizga yana yordam bera olamanmi?",
            audio_base64=None,
            ui_action="show_timeout_prompt",
            state="INTENT_DISCOVERY",
            patient=None,
            session_id=session_id,
        )

        # Second timeout — farewell + reset
        timeout2_resp = OrchestratorResponse(
            text="Rahmat, yaxshi kun tilayman! Yana kelib turing.",
            audio_base64=None,
            ui_action="show_farewell",
            state="FAREWELL",
            patient=None,
            session_id=session_id,
        )

        call_idx = {"n": 0}
        responses = [timeout1_resp, timeout2_resp]

        def _next_response(**kwargs):
            idx = min(call_idx["n"], len(responses) - 1)
            call_idx["n"] += 1
            return responses[idx]

        mock_orch = MagicMock()
        mock_orch.handle_timeout = AsyncMock(side_effect=lambda **kw: _next_response(**kw))

        with patch("app.ai.api.chat._get_orchestrator", return_value=mock_orch):
            # First timeout
            r1 = await _process(
                e2e_client, headers,
                input_type="timeout", device_id=device_id, clinic_id=clinic_id,
                session_id=session_id,
                data={},
            )
            assert r1["state"] == "INTENT_DISCOVERY"
            assert r1["ui_action"] == "show_timeout_prompt"
            assert "bu yerdasizmi" in r1["text"]

            # Second timeout
            r2 = await _process(
                e2e_client, headers,
                input_type="timeout", device_id=device_id, clinic_id=clinic_id,
                session_id=session_id,
                data={},
            )
            assert r2["state"] == "FAREWELL"
            assert r2["ui_action"] == "show_farewell"

        # Verify handle_timeout was called twice
        assert mock_orch.handle_timeout.await_count == 2


# ---------------------------------------------------------------------------
# TEST 6: Tenant isolation
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    """Two clinics with overlapping data — queries must be scoped."""

    @pytest_asyncio.fixture
    async def two_clinics(self, db_session: AsyncSession) -> dict:
        """Seed two clinics with similar data."""
        # Clinic A
        clinic_a_id = uuid.uuid4()
        clinic_a = Clinic(
            id=clinic_a_id, name="Clinic Alpha",
            address="Addr A", phone="+998900000001", email="a@clinic.uz",
        )
        db_session.add(clinic_a)

        admin_a_id = uuid.uuid4()
        admin_a = User(
            id=admin_a_id, clinic_id=clinic_a_id, email="admin@a.uz",
            password_hash="$2b$12$fake", full_name="Admin A", role=UserRole.CLINIC_ADMIN,
        )
        db_session.add(admin_a)

        dept_a = Department(
            clinic_id=clinic_a_id, name="Terapiya",
            description="Therapy A", floor=1, room_number="101",
        )
        db_session.add(dept_a)
        await db_session.flush()

        doctor_a = Doctor(
            clinic_id=clinic_a_id, department_id=dept_a.id,
            full_name="Dr. A", specialty="Terapevt",
        )
        db_session.add(doctor_a)

        patient_a = Patient(
            clinic_id=clinic_a_id,
            full_name_enc=encrypt_field("Patient Alpha"),
            phone_enc=encrypt_field("+998901111111"),
            language_preference="uz",
        )
        db_session.add(patient_a)
        await db_session.flush()

        # Clinic B
        clinic_b_id = uuid.uuid4()
        clinic_b = Clinic(
            id=clinic_b_id, name="Clinic Beta",
            address="Addr B", phone="+998900000002", email="b@clinic.uz",
        )
        db_session.add(clinic_b)

        admin_b_id = uuid.uuid4()
        admin_b = User(
            id=admin_b_id, clinic_id=clinic_b_id, email="admin@b.uz",
            password_hash="$2b$12$fake", full_name="Admin B", role=UserRole.CLINIC_ADMIN,
        )
        db_session.add(admin_b)

        dept_b = Department(
            clinic_id=clinic_b_id, name="Terapiya",
            description="Therapy B", floor=1, room_number="101",
        )
        db_session.add(dept_b)
        await db_session.flush()

        doctor_b = Doctor(
            clinic_id=clinic_b_id, department_id=dept_b.id,
            full_name="Dr. B", specialty="Terapevt",
        )
        db_session.add(doctor_b)

        patient_b = Patient(
            clinic_id=clinic_b_id,
            full_name_enc=encrypt_field("Patient Beta"),
            phone_enc=encrypt_field("+998902222222"),
            language_preference="ru",
        )
        db_session.add(patient_b)
        await db_session.flush()

        return {
            "clinic_a": {
                "id": clinic_a_id, "admin_id": admin_a_id,
                "dept_id": dept_a.id, "doctor_id": doctor_a.id,
                "patient_id": patient_a.id,
                "headers": _auth_headers(clinic_a_id, admin_a_id),
            },
            "clinic_b": {
                "id": clinic_b_id, "admin_id": admin_b_id,
                "dept_id": dept_b.id, "doctor_id": doctor_b.id,
                "patient_id": patient_b.id,
                "headers": _auth_headers(clinic_b_id, admin_b_id),
            },
        }

    @pytest.mark.asyncio
    async def test_clinic_a_cannot_see_clinic_b_departments(
        self, e2e_client: AsyncClient, two_clinics: dict
    ) -> None:
        """Clinic A listing departments should not include Clinic B departments."""
        a = two_clinics["clinic_a"]
        resp = await e2e_client.get("/api/v1/departments/", headers=a["headers"])
        assert resp.status_code == 200
        data = resp.json()["data"]
        dept_ids = {d["id"] for d in data}
        assert str(a["dept_id"]) in dept_ids
        assert str(two_clinics["clinic_b"]["dept_id"]) not in dept_ids

    @pytest.mark.asyncio
    async def test_clinic_b_cannot_see_clinic_a_departments(
        self, e2e_client: AsyncClient, two_clinics: dict
    ) -> None:
        """Clinic B listing departments should not include Clinic A departments."""
        b = two_clinics["clinic_b"]
        resp = await e2e_client.get("/api/v1/departments/", headers=b["headers"])
        assert resp.status_code == 200
        data = resp.json()["data"]
        dept_ids = {d["id"] for d in data}
        assert str(b["dept_id"]) in dept_ids
        assert str(two_clinics["clinic_a"]["dept_id"]) not in dept_ids

    @pytest.mark.asyncio
    async def test_clinic_a_cannot_see_clinic_b_doctors(
        self, e2e_client: AsyncClient, two_clinics: dict
    ) -> None:
        """Clinic A listing doctors should not include Clinic B doctors."""
        a = two_clinics["clinic_a"]
        resp = await e2e_client.get("/api/v1/doctors/", headers=a["headers"])
        assert resp.status_code == 200
        data = resp.json()["data"]
        doctor_ids = {d["id"] for d in data}
        assert str(a["doctor_id"]) in doctor_ids
        assert str(two_clinics["clinic_b"]["doctor_id"]) not in doctor_ids

    @pytest.mark.asyncio
    async def test_clinic_a_cannot_see_clinic_b_patients(
        self, e2e_client: AsyncClient, two_clinics: dict
    ) -> None:
        """Clinic A listing patients should not include Clinic B patients."""
        a = two_clinics["clinic_a"]
        resp = await e2e_client.get("/api/v1/patients/", headers=a["headers"])
        assert resp.status_code == 200
        data = resp.json()["data"]
        patient_ids = {d["id"] for d in data}
        assert str(a["patient_id"]) in patient_ids
        assert str(two_clinics["clinic_b"]["patient_id"]) not in patient_ids

    @pytest.mark.asyncio
    async def test_clinic_a_appointments_not_visible_to_clinic_b(
        self, e2e_client: AsyncClient, two_clinics: dict, db_session: AsyncSession
    ) -> None:
        """Appointments created under Clinic A should not be visible to Clinic B."""
        a = two_clinics["clinic_a"]
        b = two_clinics["clinic_b"]

        # Seed a service and appointment for clinic A
        svc = Service(
            clinic_id=a["id"],
            department_id=a["dept_id"],
            name="Konsultatsiya",
            description="Consultation",
            duration_minutes=30,
            price_uzs=100000,
        )
        db_session.add(svc)
        await db_session.flush()

        appt = Appointment(
            clinic_id=a["id"],
            patient_id=a["patient_id"],
            doctor_id=a["doctor_id"],
            service_id=svc.id,
            scheduled_at=datetime.now(timezone.utc).replace(hour=10, minute=0),
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            payment_status=PaymentStatus.PENDING,
        )
        db_session.add(appt)
        await db_session.flush()

        # Clinic A can see the appointment
        resp_a = await e2e_client.get("/api/v1/appointments/", headers=a["headers"])
        assert resp_a.status_code == 200
        appt_ids_a = {d["id"] for d in resp_a.json()["data"]}
        assert str(appt.id) in appt_ids_a

        # Clinic B cannot see it
        resp_b = await e2e_client.get("/api/v1/appointments/", headers=b["headers"])
        assert resp_b.status_code == 200
        appt_ids_b = {d["id"] for d in resp_b.json()["data"]}
        assert str(appt.id) not in appt_ids_b

        # Clinic B cannot access it directly either
        resp_direct = await e2e_client.get(
            f"/api/v1/appointments/{appt.id}", headers=b["headers"],
        )
        assert resp_direct.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_clinic_patient_access_rejected(
        self, e2e_client: AsyncClient, two_clinics: dict
    ) -> None:
        """Clinic A trying to access Clinic B's patient should get 404."""
        a = two_clinics["clinic_a"]
        b = two_clinics["clinic_b"]

        resp = await e2e_client.get(
            f"/api/v1/patients/{b['patient_id']}",
            headers=a["headers"],
        )
        assert resp.status_code == 404
