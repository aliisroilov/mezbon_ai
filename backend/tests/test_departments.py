import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department


@pytest.mark.asyncio
async def test_list_departments(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    resp = await client.get("/api/v1/departments/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1


@pytest.mark.asyncio
async def test_create_department(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
) -> None:
    resp = await client.post(
        "/api/v1/departments/",
        headers=auth_headers,
        json={
            "name": "Kardiologiya",
            "description": "Heart department",
            "floor": 2,
            "room_number": "201",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Kardiologiya"
    assert body["data"]["floor"] == 2
    assert body["data"]["doctor_count"] == 0


@pytest.mark.asyncio
async def test_get_department(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    resp = await client.get(
        f"/api/v1/departments/{seed_department.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Terapiya"
    assert body["data"]["id"] == str(seed_department.id)


@pytest.mark.asyncio
async def test_update_department(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    resp = await client.patch(
        f"/api/v1/departments/{seed_department.id}",
        headers=auth_headers,
        json={"name": "Updated Name", "floor": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Updated Name"
    assert body["data"]["floor"] == 3


@pytest.mark.asyncio
async def test_delete_department(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    resp = await client.delete(
        f"/api/v1/departments/{seed_department.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_get_nonexistent_department(
    client: AsyncClient,
    auth_headers: dict,
    seed_clinic: dict,
) -> None:
    resp = await client.get(
        f"/api/v1/departments/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation(
    client: AsyncClient,
    auth_headers: dict,
    other_auth_headers: dict,
    seed_department: Department,
    another_clinic: dict,
) -> None:
    """Clinic B cannot see clinic A departments."""
    # Clinic A can see it
    resp_a = await client.get("/api/v1/departments/", headers=auth_headers)
    assert len(resp_a.json()["data"]) >= 1

    # Clinic B sees empty
    resp_b = await client.get("/api/v1/departments/", headers=other_auth_headers)
    assert len(resp_b.json()["data"]) == 0

    # Clinic B cannot get clinic A's department directly
    resp_b_get = await client.get(
        f"/api/v1/departments/{seed_department.id}",
        headers=other_auth_headers,
    )
    assert resp_b_get.status_code == 404
