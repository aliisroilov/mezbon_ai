import uuid
from datetime import datetime, time, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.department import Department
from app.models.doctor import Doctor, DoctorSchedule
from app.models.patient import Patient
from app.models.service import Service
from tests.test_doctors import _next_weekday


@pytest.mark.asyncio
async def test_book_appointment(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_doctor: Doctor,
    seed_patient: Patient,
    seed_service: Service,
) -> None:
    monday = _next_weekday(0)
    scheduled_at = datetime.combine(monday, time(10, 0), tzinfo=timezone.utc)

    resp = await client.post(
        "/api/v1/appointments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "doctor_id": str(seed_doctor.id),
            "service_id": str(seed_service.id),
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "SCHEDULED"
    assert body["data"]["patient_id"] == str(seed_patient.id)


@pytest.mark.asyncio
async def test_book_same_slot_conflict(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_doctor: Doctor,
    seed_patient: Patient,
    seed_service: Service,
    db_session: AsyncSession,
) -> None:
    """Booking the same doctor at the same time → 409."""
    monday = _next_weekday(0)
    scheduled_at = datetime.combine(monday, time(11, 0), tzinfo=timezone.utc)

    # Create a second patient for the conflict test
    from app.core.encryption import encrypt_field

    patient2 = Patient(
        clinic_id=seed_clinic["clinic_id"],
        full_name_enc=encrypt_field("Second Patient"),
        phone_enc=encrypt_field("+998902222222"),
        dob_enc="",
    )
    db_session.add(patient2)
    await db_session.flush()

    # Book first appointment
    resp1 = await client.post(
        "/api/v1/appointments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "doctor_id": str(seed_doctor.id),
            "service_id": str(seed_service.id),
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
        },
    )
    assert resp1.status_code == 201

    # Book same slot for different patient → conflict on doctor
    resp2 = await client.post(
        "/api/v1/appointments/",
        headers=auth_headers,
        json={
            "patient_id": str(patient2.id),
            "doctor_id": str(seed_doctor.id),
            "service_id": str(seed_service.id),
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
        },
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_check_in(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_doctor: Doctor,
    seed_patient: Patient,
    seed_service: Service,
    db_session: AsyncSession,
) -> None:
    """Check-in for today's appointment works."""
    now = datetime.now(timezone.utc)
    scheduled_at = now.replace(hour=15, minute=0, second=0, microsecond=0)

    appt = Appointment(
        clinic_id=seed_clinic["clinic_id"],
        patient_id=seed_patient.id,
        doctor_id=seed_doctor.id,
        service_id=seed_service.id,
        scheduled_at=scheduled_at,
        duration_minutes=30,
    )
    db_session.add(appt)
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/appointments/{appt.id}/check-in",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "CHECKED_IN"


@pytest.mark.asyncio
async def test_check_in_wrong_date(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_doctor: Doctor,
    seed_patient: Patient,
    seed_service: Service,
    db_session: AsyncSession,
) -> None:
    """Check-in for a future date → 422."""
    future = datetime.now(timezone.utc) + timedelta(days=3)
    scheduled_at = future.replace(hour=10, minute=0, second=0, microsecond=0)

    appt = Appointment(
        clinic_id=seed_clinic["clinic_id"],
        patient_id=seed_patient.id,
        doctor_id=seed_doctor.id,
        service_id=seed_service.id,
        scheduled_at=scheduled_at,
        duration_minutes=30,
    )
    db_session.add(appt)
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/appointments/{appt.id}/check-in",
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cancel_appointment(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_doctor: Doctor,
    seed_patient: Patient,
    seed_service: Service,
    db_session: AsyncSession,
) -> None:
    monday = _next_weekday(0)
    scheduled_at = datetime.combine(monday, time(14, 0), tzinfo=timezone.utc)

    appt = Appointment(
        clinic_id=seed_clinic["clinic_id"],
        patient_id=seed_patient.id,
        doctor_id=seed_doctor.id,
        service_id=seed_service.id,
        scheduled_at=scheduled_at,
        duration_minutes=30,
    )
    db_session.add(appt)
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_frees_slot(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_doctor: Doctor,
    seed_patient: Patient,
    seed_service: Service,
    db_session: AsyncSession,
) -> None:
    """After cancelling, the same slot can be re-booked."""
    monday = _next_weekday(0)
    scheduled_at = datetime.combine(monday, time(15, 0), tzinfo=timezone.utc)

    # Book
    resp1 = await client.post(
        "/api/v1/appointments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "doctor_id": str(seed_doctor.id),
            "service_id": str(seed_service.id),
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
        },
    )
    appt_id = resp1.json()["data"]["id"]

    # Cancel
    await client.post(
        f"/api/v1/appointments/{appt_id}/cancel",
        headers=auth_headers,
    )

    # Re-book same slot → should succeed
    resp3 = await client.post(
        "/api/v1/appointments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "doctor_id": str(seed_doctor.id),
            "service_id": str(seed_service.id),
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
        },
    )
    assert resp3.status_code == 201


@pytest.mark.asyncio
async def test_list_appointments_with_filters(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_doctor: Doctor,
    seed_patient: Patient,
    seed_service: Service,
    db_session: AsyncSession,
) -> None:
    monday = _next_weekday(0)
    scheduled_at = datetime.combine(monday, time(9, 0), tzinfo=timezone.utc)

    appt = Appointment(
        clinic_id=seed_clinic["clinic_id"],
        patient_id=seed_patient.id,
        doctor_id=seed_doctor.id,
        service_id=seed_service.id,
        scheduled_at=scheduled_at,
        duration_minutes=30,
    )
    db_session.add(appt)
    await db_session.flush()

    # Filter by doctor
    resp = await client.get(
        f"/api/v1/appointments/?doctor_id={seed_doctor.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1

    # Filter by status
    resp2 = await client.get(
        "/api/v1/appointments/?status=SCHEDULED",
        headers=auth_headers,
    )
    assert len(resp2.json()["data"]) >= 1

    # Filter by date
    resp3 = await client.get(
        f"/api/v1/appointments/?date_from={monday}&date_to={monday}",
        headers=auth_headers,
    )
    assert len(resp3.json()["data"]) >= 1
