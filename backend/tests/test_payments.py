import uuid
from datetime import datetime, time, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.payment import Payment, PaymentMethod, PaymentTransactionStatus
from app.models.service import Service


@pytest.mark.asyncio
async def test_initiate_payment(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    resp = await client.post(
        "/api/v1/payments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "amount": "150000.00",
            "method": "CASH",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "PENDING"
    assert data["amount"] == "150000.00"
    assert data["method"] == "CASH"
    assert data["patient_id"] == str(seed_patient.id)


@pytest.mark.asyncio
async def test_initiate_payment_with_appointment(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_doctor: Doctor,
    seed_patient: Patient,
    seed_service: Service,
    db_session: AsyncSession,
) -> None:
    """Payment linked to appointment."""
    from tests.test_doctors import _next_weekday

    monday = _next_weekday(0)
    scheduled_at = datetime.combine(monday, time(10, 0), tzinfo=timezone.utc)

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
        "/api/v1/payments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "appointment_id": str(appt.id),
            "amount": "150000.00",
            "method": "UZCARD",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["appointment_id"] == str(appt.id)


@pytest.mark.asyncio
async def test_webhook_completes_payment(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
    seed_patient: Patient,
    db_session: AsyncSession,
) -> None:
    """Mock webhook → payment status becomes COMPLETED."""
    txn_id = f"TXN-{uuid.uuid4().hex[:8]}"
    payment = Payment(
        clinic_id=seed_clinic["clinic_id"],
        patient_id=seed_patient.id,
        amount=200000,
        method=PaymentMethod.CLICK,
        transaction_id=txn_id,
    )
    db_session.add(payment)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/payments/webhook",
        json={
            "transaction_id": txn_id,
            "status": "completed",
            "provider": "click",
            "payload": {"order_id": "12345"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_list_payments(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    # Create a payment first
    await client.post(
        "/api/v1/payments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "amount": "50000.00",
            "method": "CASH",
        },
    )

    resp = await client.get("/api/v1/payments/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_list_payments_filter_by_patient(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    await client.post(
        "/api/v1/payments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "amount": "50000.00",
            "method": "CASH",
        },
    )

    resp = await client.get(
        f"/api/v1/payments/?patient_id={seed_patient.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    payments = resp.json()["data"]
    assert all(p["patient_id"] == str(seed_patient.id) for p in payments)


@pytest.mark.asyncio
async def test_get_payment(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    create_resp = await client.post(
        "/api/v1/payments/",
        headers=auth_headers,
        json={
            "patient_id": str(seed_patient.id),
            "amount": "75000.00",
            "method": "HUMO",
        },
    )
    payment_id = create_resp.json()["data"]["id"]

    resp = await client.get(
        f"/api/v1/payments/{payment_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == payment_id
