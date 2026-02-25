import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id, get_current_user, get_db
from app.core.response import success_response
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard(
    target_date: date | None = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    d = target_date or datetime.now(timezone.utc).date()
    stats = await analytics_service.dashboard_stats(db, clinic_id, d)
    return success_response(stats)


@router.get("/trends")
async def trends(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    data = await analytics_service.visitor_trends(db, clinic_id, days)
    return success_response(data)


@router.get("/intents")
async def intents(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _user=Depends(get_current_user),
) -> dict:
    data = await analytics_service.intent_distribution(db, clinic_id, date_from, date_to)
    return success_response(data)
