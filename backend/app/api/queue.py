import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.models.queue import QueueStatus
from app.schemas.queue import QueueTicketCreate, QueueTicketRead
from app.services import queue_service
from app.sockets import notify_queue_update

router = APIRouter(prefix="/queue", tags=["queue"])


def _serialize(ticket) -> dict:
    return QueueTicketRead(
        **{k: v for k, v in ticket.__dict__.items() if not k.startswith("_")},
    ).model_dump(mode="json")


@router.get("/")
async def list_tickets(
    department_id: uuid.UUID | None = None,
    status: QueueStatus | None = None,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    tickets = await queue_service.list_tickets(
        db, clinic_id, department_id=department_id, status=status
    )
    return success_response([_serialize(t) for t in tickets])


@router.post("/", status_code=201)
async def issue_ticket(
    body: QueueTicketCreate,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    ticket = await queue_service.issue_ticket(db, clinic_id, body)
    ticket_data = _serialize(ticket)
    await notify_queue_update(clinic_id, ticket.department_id, ticket_data, action="created")
    return success_response(ticket_data)


@router.patch("/{ticket_id}/call")
async def call_next(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    # ticket_id here is actually department_id for "call next in department"
    ticket = await queue_service.call_next(db, clinic_id, ticket_id)
    ticket_data = _serialize(ticket)
    await notify_queue_update(clinic_id, ticket.department_id, ticket_data, action="called")
    return success_response(ticket_data)


@router.patch("/{ticket_id}/complete")
async def complete_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    ticket = await queue_service.complete_ticket(db, clinic_id, ticket_id)
    ticket_data = _serialize(ticket)
    await notify_queue_update(clinic_id, ticket.department_id, ticket_data, action="completed")
    return success_response(ticket_data)


@router.get("/stats")
async def queue_stats(
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    stats = await queue_service.get_queue_stats(db, clinic_id)
    return success_response(stats)
