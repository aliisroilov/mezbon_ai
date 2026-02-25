import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.patient import Patient


@pytest.mark.asyncio
async def test_issue_ticket_sequential(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
    seed_patient: Patient,
) -> None:
    """Tickets should have sequential numbers."""
    resp1 = await client.post(
        "/api/v1/queue/",
        headers=auth_headers,
        json={
            "department_id": str(seed_department.id),
            "patient_id": str(seed_patient.id),
        },
    )
    assert resp1.status_code == 201
    t1 = resp1.json()["data"]
    assert t1["ticket_number"] == "T-001"  # "Terapiya" → prefix "T"
    assert t1["status"] == "WAITING"

    resp2 = await client.post(
        "/api/v1/queue/",
        headers=auth_headers,
        json={
            "department_id": str(seed_department.id),
        },
    )
    assert resp2.status_code == 201
    t2 = resp2.json()["data"]
    assert t2["ticket_number"] == "T-002"


@pytest.mark.asyncio
async def test_get_queue_ordered(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    """Queue returns tickets ordered by created_at."""
    # Issue 3 tickets
    for _ in range(3):
        await client.post(
            "/api/v1/queue/",
            headers=auth_headers,
            json={"department_id": str(seed_department.id)},
        )

    resp = await client.get(
        f"/api/v1/queue/?department_id={seed_department.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    tickets = resp.json()["data"]
    assert len(tickets) == 3
    # Ordered by created_at ascending
    numbers = [t["ticket_number"] for t in tickets]
    assert numbers == ["T-001", "T-002", "T-003"]


@pytest.mark.asyncio
async def test_call_next(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    """Call next → oldest WAITING becomes IN_PROGRESS."""
    # Issue 2 tickets
    await client.post(
        "/api/v1/queue/",
        headers=auth_headers,
        json={"department_id": str(seed_department.id)},
    )
    await client.post(
        "/api/v1/queue/",
        headers=auth_headers,
        json={"department_id": str(seed_department.id)},
    )

    # Call next (using department_id as the path param)
    resp = await client.patch(
        f"/api/v1/queue/{seed_department.id}/call",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "IN_PROGRESS"
    assert data["ticket_number"] == "T-001"  # oldest first
    assert data["called_at"] is not None


@pytest.mark.asyncio
async def test_complete_ticket(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    """Complete → IN_PROGRESS ticket becomes COMPLETED."""
    # Issue ticket
    resp1 = await client.post(
        "/api/v1/queue/",
        headers=auth_headers,
        json={"department_id": str(seed_department.id)},
    )
    ticket_id = resp1.json()["data"]["id"]

    # Call it
    await client.patch(
        f"/api/v1/queue/{seed_department.id}/call",
        headers=auth_headers,
    )

    # Complete it
    resp3 = await client.patch(
        f"/api/v1/queue/{ticket_id}/complete",
        headers=auth_headers,
    )
    assert resp3.status_code == 200
    assert resp3.json()["data"]["status"] == "COMPLETED"
    assert resp3.json()["data"]["completed_at"] is not None


@pytest.mark.asyncio
async def test_queue_stats(
    client: AsyncClient,
    auth_headers: dict,
    seed_department: Department,
) -> None:
    """Queue stats returns correct counts per department."""
    # Issue 3 tickets, call 1
    for _ in range(3):
        await client.post(
            "/api/v1/queue/",
            headers=auth_headers,
            json={"department_id": str(seed_department.id)},
        )

    # Call one
    await client.patch(
        f"/api/v1/queue/{seed_department.id}/call",
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/queue/stats", headers=auth_headers)
    assert resp.status_code == 200
    stats = resp.json()["data"]
    assert len(stats) >= 1

    dept_stat = next(
        s for s in stats if s["department_id"] == str(seed_department.id)
    )
    assert dept_stat["waiting_count"] == 2  # 3 issued - 1 called
