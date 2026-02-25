import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_valid(client: AsyncClient, seed_clinic: dict) -> None:
    resp = await client.post("/api/v1/auth/login", json={
        "email": seed_clinic["admin_email"],
        "password": seed_clinic["admin_password"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, seed_clinic: dict) -> None:
    resp = await client.post("/api/v1/auth/login", json={
        "email": seed_clinic["admin_email"],
        "password": "wrongpassword",
    })
    assert resp.status_code == 403
    body = resp.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient, seed_clinic: dict) -> None:
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.uz",
        "password": "whatever",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, seed_clinic: dict) -> None:
    # First login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": seed_clinic["admin_email"],
        "password": seed_clinic["admin_password"],
    })
    refresh_token = login_resp.json()["data"]["refresh_token"]

    # Refresh
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]


@pytest.mark.asyncio
async def test_expired_token_rejected(client: AsyncClient, seed_clinic: dict) -> None:
    resp = await client.get(
        "/api/v1/departments/",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_missing_auth_header(client: AsyncClient, seed_clinic: dict) -> None:
    resp = await client.get("/api/v1/departments/")
    assert resp.status_code == 422  # FastAPI missing required header
