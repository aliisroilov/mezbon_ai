import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient


@pytest.mark.asyncio
async def test_register_patient(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
) -> None:
    resp = await client.post(
        "/api/v1/patients/",
        headers=auth_headers,
        json={
            "full_name": "Zulfiya Sultanova",
            "phone": "+998901234567",
            "date_of_birth": "1995-06-15",
            "language_preference": "uz",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["full_name"] == "Zulfiya Sultanova"
    assert data["phone"] == "+998901234567"
    assert data["has_face_embedding"] is False


@pytest.mark.asyncio
async def test_get_patient_decrypted(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    resp = await client.get(
        f"/api/v1/patients/{seed_patient.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["full_name"] == "Alisher Usmanov"
    assert data["phone"] == "+998901112233"


@pytest.mark.asyncio
async def test_pii_encrypted_in_db(
    db_session: AsyncSession,
    seed_patient: Patient,
) -> None:
    """Raw DB values should be encrypted, NOT plaintext."""
    result = await db_session.execute(
        select(Patient.full_name_enc, Patient.phone_enc).where(
            Patient.id == seed_patient.id
        )
    )
    row = result.one()
    # Encrypted values are base64-encoded, not readable names/phones
    assert row[0] != "Alisher Usmanov"
    assert row[1] != "+998901112233"
    # They should be non-empty strings
    assert len(row[0]) > 0
    assert len(row[1]) > 0


@pytest.mark.asyncio
async def test_lookup_by_phone(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    resp = await client.post(
        "/api/v1/patients/lookup",
        headers=auth_headers,
        json={"phone": "+998901112233"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data is not None
    assert data["full_name"] == "Alisher Usmanov"
    assert data["id"] == str(seed_patient.id)


@pytest.mark.asyncio
async def test_lookup_by_phone_not_found(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    resp = await client.post(
        "/api/v1/patients/lookup",
        headers=auth_headers,
        json={"phone": "+998999999999"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] is None


@pytest.mark.asyncio
async def test_list_patients(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    resp = await client.get("/api/v1/patients/", headers=auth_headers)
    assert resp.status_code == 200
    patients = resp.json()["data"]
    assert len(patients) >= 1
    # All patients should have decrypted names
    assert all(p["full_name"] for p in patients)


@pytest.mark.asyncio
async def test_update_patient(
    client: AsyncClient,
    auth_headers: dict,
    seed_patient: Patient,
) -> None:
    resp = await client.patch(
        f"/api/v1/patients/{seed_patient.id}",
        headers=auth_headers,
        json={"full_name": "Alisher Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["full_name"] == "Alisher Updated"
