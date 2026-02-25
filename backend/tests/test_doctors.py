import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.department import Department
from app.models.doctor import Doctor, DoctorSchedule
from app.models.service import Service


@pytest.mark.asyncio
async def test_list_doctors(
    client: AsyncClient,
    auth_headers: dict,
    seed_doctor: Doctor,
) -> None:
    resp = await client.get("/api/v1/doctors/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    assert body["data"][0]["full_name"] == "Dr. Karimov"


@pytest.mark.asyncio
async def test_list_doctors_filter_by_department(
    client: AsyncClient,
    auth_headers: dict,
    seed_doctor: Doctor,
    seed_department: Department,
) -> None:
    resp = await client.get(
        f"/api/v1/doctors/?department_id={seed_department.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1

    # Non-existent department returns empty
    resp2 = await client.get(
        f"/api/v1/doctors/?department_id={uuid.uuid4()}",
        headers=auth_headers,
    )
    assert len(resp2.json()["data"]) == 0


@pytest.mark.asyncio
async def test_create_doctor(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    resp = await client.post(
        "/api/v1/doctors/",
        headers=auth_headers,
        json={
            "full_name": "Dr. Testov",
            "specialty": "Nevropatolog",
            "department_id": str(seed_department.id),
        },
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["full_name"] == "Dr. Testov"


@pytest.mark.asyncio
async def test_create_doctor_with_schedule(
    client: AsyncClient,
    auth_headers: dict,
    seed_doctor: Doctor,
) -> None:
    """Set schedule via PUT endpoint."""
    schedule = [
        {
            "day_of_week": 0,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "break_start": "13:00:00",
            "break_end": "14:00:00",
        },
        {
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    ]
    resp = await client.put(
        f"/api/v1/doctors/{seed_doctor.id}/schedule",
        headers=auth_headers,
        json=schedule,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 2


def _next_weekday(weekday: int) -> date:
    """Return the next date matching given weekday (0=Monday)."""
    today = date.today()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


@pytest.mark.asyncio
async def test_available_slots_basic(
    client: AsyncClient,
    auth_headers: dict,
    seed_doctor: Doctor,
    seed_schedule: DoctorSchedule,
) -> None:
    """09:00-17:00 with break 13:00-14:00 → should have slots, break excluded."""
    monday = _next_weekday(0)
    resp = await client.get(
        f"/api/v1/doctors/{seed_doctor.id}/slots?date={monday}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    slots = data["slots"]

    # 8 hours, 30 min each = 16 slots total (including break slots)
    assert len(slots) == 16

    # Break slots (13:00 and 13:30) should NOT be available
    break_slots = [s for s in slots if s["start_time"] in ("13:00:00", "13:30:00")]
    for s in break_slots:
        assert s["is_available"] is False


@pytest.mark.asyncio
async def test_available_slots_existing_appointment_excluded(
    client: AsyncClient,
    auth_headers: dict,
    seed_doctor: Doctor,
    seed_schedule: DoctorSchedule,
    seed_clinic: dict,
    seed_patient: object,
    seed_service: Service,
    db_session: AsyncSession,
) -> None:
    """Slot with existing appointment should be marked unavailable."""
    monday = _next_weekday(0)
    appt_time = datetime.combine(monday, time(10, 0), tzinfo=timezone.utc)

    appt = Appointment(
        clinic_id=seed_clinic["clinic_id"],
        patient_id=seed_patient.id,  # type: ignore[union-attr]
        doctor_id=seed_doctor.id,
        service_id=seed_service.id,
        scheduled_at=appt_time,
        duration_minutes=30,
    )
    db_session.add(appt)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/doctors/{seed_doctor.id}/slots?date={monday}",
        headers=auth_headers,
    )
    slots = resp.json()["data"]["slots"]

    # 10:00 slot should be unavailable
    slot_10 = next(s for s in slots if s["start_time"] == "10:00:00")
    assert slot_10["is_available"] is False

    # 10:30 should still be available (no overlap)
    slot_10_30 = next(s for s in slots if s["start_time"] == "10:30:00")
    assert slot_10_30["is_available"] is True


@pytest.mark.asyncio
async def test_available_slots_sunday_no_schedule(
    client: AsyncClient,
    auth_headers: dict,
    seed_doctor: Doctor,
    seed_schedule: DoctorSchedule,
) -> None:
    """Sunday (day 6) has no schedule → empty slots."""
    sunday = _next_weekday(6)
    resp = await client.get(
        f"/api/v1/doctors/{seed_doctor.id}/slots?date={sunday}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["slots"]) == 0


@pytest.mark.asyncio
async def test_available_slots_correct_count(
    client: AsyncClient,
    auth_headers: dict,
    seed_doctor: Doctor,
    seed_schedule: DoctorSchedule,
) -> None:
    """Count available (not break) slots: 16 total - 2 break = 14 available."""
    monday = _next_weekday(0)
    resp = await client.get(
        f"/api/v1/doctors/{seed_doctor.id}/slots?date={monday}",
        headers=auth_headers,
    )
    slots = resp.json()["data"]["slots"]
    available = [s for s in slots if s["is_available"]]
    assert len(available) == 14
