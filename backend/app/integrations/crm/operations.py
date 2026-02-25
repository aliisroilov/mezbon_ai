"""CRM operation helpers for use by service layer.

All operations are fire-and-forget: CRM failures never crash the main flow.
Failed operations are queued in Redis for background retry.
"""
import json
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.integrations.crm.factory import get_crm
from app.models.audit_log import AuditLog

CRM_RETRY_QUEUE = "crm:retry_queue"
CRM_RETRY_TTL_SECONDS = 86400  # 24 hours max retention


async def _log_crm_audit(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    new_value: dict | None = None,
) -> None:
    """Record CRM operation in audit log."""
    audit = AuditLog(
        clinic_id=clinic_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        new_value=new_value,
    )
    db.add(audit)
    await db.flush()


async def _enqueue_retry(
    operation: str,
    clinic_id: str,
    clinic_settings: dict,
    payload: dict,
) -> None:
    """Push a failed CRM operation to Redis retry queue."""
    try:
        redis = get_redis()
        entry = json.dumps({
            "operation": operation,
            "clinic_id": clinic_id,
            "clinic_settings": clinic_settings,
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retries": 0,
        })
        await redis.lpush(CRM_RETRY_QUEUE, entry)
        await redis.aclose()
        logger.info("CRM operation queued for retry", extra={"operation": operation})
    except Exception as e:
        logger.warning(
            "Failed to enqueue CRM retry (non-fatal)",
            extra={"operation": operation, "error": str(e)},
        )


async def sync_contact_create(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    clinic_settings: dict | None,
    patient_id: uuid.UUID,
    patient_data: dict,
) -> str | None:
    """Create a CRM contact for a newly registered patient.

    Returns CRM contact ID on success, None on failure/disabled.
    """
    crm = get_crm(clinic_settings)
    if crm is None:
        return None

    try:
        crm_contact_id = await crm.create_contact(patient_data)

        await _log_crm_audit(
            db,
            clinic_id,
            action="crm.contact.create",
            entity_type="patient",
            entity_id=patient_id,
            new_value={"crm_contact_id": crm_contact_id},
        )

        logger.info(
            "CRM contact created for patient",
            extra={
                "patient_id": str(patient_id),
                "crm_contact_id": crm_contact_id,
            },
        )
        return crm_contact_id

    except Exception as e:
        logger.warning(
            "CRM contact creation failed (non-fatal)",
            extra={"patient_id": str(patient_id), "error": str(e)},
        )
        await _enqueue_retry(
            operation="create_contact",
            clinic_id=str(clinic_id),
            clinic_settings=clinic_settings or {},
            payload={"patient_id": str(patient_id), "patient_data": patient_data},
        )
        return None


async def sync_deal_create(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    clinic_settings: dict | None,
    contact_id: str,
    appointment_id: uuid.UUID,
    deal_data: dict,
) -> str | None:
    """Create a CRM deal for a new appointment.

    Returns CRM deal ID on success, None on failure/disabled.
    """
    crm = get_crm(clinic_settings)
    if crm is None:
        return None

    try:
        crm_deal_id = await crm.create_deal(contact_id, deal_data)

        await _log_crm_audit(
            db,
            clinic_id,
            action="crm.deal.create",
            entity_type="appointment",
            entity_id=appointment_id,
            new_value={
                "crm_deal_id": crm_deal_id,
                "crm_contact_id": contact_id,
            },
        )

        logger.info(
            "CRM deal created for appointment",
            extra={
                "appointment_id": str(appointment_id),
                "crm_deal_id": crm_deal_id,
            },
        )
        return crm_deal_id

    except Exception as e:
        logger.warning(
            "CRM deal creation failed (non-fatal)",
            extra={"appointment_id": str(appointment_id), "error": str(e)},
        )
        await _enqueue_retry(
            operation="create_deal",
            clinic_id=str(clinic_id),
            clinic_settings=clinic_settings or {},
            payload={
                "contact_id": contact_id,
                "appointment_id": str(appointment_id),
                "deal_data": deal_data,
            },
        )
        return None


async def sync_deal_update(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    clinic_settings: dict | None,
    deal_id: str,
    payment_id: uuid.UUID,
    data: dict,
) -> None:
    """Update a CRM deal (e.g. mark as won after payment)."""
    crm = get_crm(clinic_settings)
    if crm is None:
        return

    try:
        await crm.update_deal(deal_id, data)

        await _log_crm_audit(
            db,
            clinic_id,
            action="crm.deal.update",
            entity_type="payment",
            entity_id=payment_id,
            new_value={"crm_deal_id": deal_id, **data},
        )

        logger.info(
            "CRM deal updated",
            extra={"crm_deal_id": deal_id, "payment_id": str(payment_id)},
        )

    except Exception as e:
        logger.warning(
            "CRM deal update failed (non-fatal)",
            extra={"crm_deal_id": deal_id, "error": str(e)},
        )
        await _enqueue_retry(
            operation="update_deal",
            clinic_id=str(clinic_id),
            clinic_settings=clinic_settings or {},
            payload={"deal_id": deal_id, "payment_id": str(payment_id), "data": data},
        )
