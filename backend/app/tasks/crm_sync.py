"""Background task: retry failed CRM operations from Redis queue.

Designed for use with arq worker. Can also be invoked directly for testing.

Usage with arq:
    class WorkerSettings:
        functions = [retry_failed_crm_operations]
        cron_jobs = [cron(retry_failed_crm_operations, minute={0, 5, 10, ...})]
"""
import json
from datetime import datetime, timezone

from loguru import logger

from app.core.redis import get_redis
from app.integrations.crm.factory import get_crm

CRM_RETRY_QUEUE = "crm:retry_queue"
CRM_DEAD_LETTER_QUEUE = "crm:dead_letter"
MAX_RETRIES = 5


async def retry_failed_crm_operations(_ctx: dict | None = None) -> int:
    """Process failed CRM operations from the retry queue.

    Pops entries from the queue, attempts the operation, and either
    succeeds (discards entry) or re-queues with incremented retry count.
    After MAX_RETRIES, moves to dead letter queue.

    Returns number of operations processed.
    """
    redis = get_redis()
    processed = 0

    try:
        queue_length = await redis.llen(CRM_RETRY_QUEUE)
        if queue_length == 0:
            return 0

        logger.info(f"CRM retry: {queue_length} operations in queue")

        # Process up to 50 per run to avoid blocking
        batch_size = min(queue_length, 50)

        for _ in range(batch_size):
            raw = await redis.rpop(CRM_RETRY_QUEUE)
            if raw is None:
                break

            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                logger.error("CRM retry: invalid JSON entry, discarding")
                continue

            operation = entry.get("operation")
            clinic_settings = entry.get("clinic_settings", {})
            payload = entry.get("payload", {})
            retries = entry.get("retries", 0)

            crm = get_crm(clinic_settings)
            if crm is None:
                logger.warning(
                    "CRM retry: CRM no longer configured, discarding",
                    extra={"operation": operation},
                )
                continue

            try:
                await _execute_operation(crm, operation, payload)
                processed += 1
                logger.info(
                    "CRM retry succeeded",
                    extra={"operation": operation, "attempt": retries + 1},
                )

            except Exception as e:
                retries += 1
                if retries >= MAX_RETRIES:
                    logger.error(
                        "CRM retry exhausted, moving to dead letter queue",
                        extra={
                            "operation": operation,
                            "retries": retries,
                            "error": str(e),
                        },
                    )
                    entry["retries"] = retries
                    entry["last_error"] = str(e)
                    entry["dead_at"] = datetime.now(timezone.utc).isoformat()
                    await redis.lpush(CRM_DEAD_LETTER_QUEUE, json.dumps(entry))
                else:
                    logger.warning(
                        "CRM retry failed, re-queuing",
                        extra={
                            "operation": operation,
                            "retries": retries,
                            "error": str(e),
                        },
                    )
                    entry["retries"] = retries
                    entry["last_error"] = str(e)
                    await redis.lpush(CRM_RETRY_QUEUE, json.dumps(entry))

    finally:
        await redis.aclose()

    if processed > 0:
        logger.info(f"CRM retry: {processed} operations succeeded")

    return processed


async def _execute_operation(crm, operation: str, payload: dict) -> None:  # type: ignore[no-untyped-def]
    """Execute a single CRM operation by name."""
    match operation:
        case "create_contact":
            await crm.create_contact(payload.get("patient_data", {}))
        case "create_deal":
            await crm.create_deal(
                payload.get("contact_id", ""),
                payload.get("deal_data", {}),
            )
        case "update_deal":
            await crm.update_deal(
                payload.get("deal_id", ""),
                payload.get("data", {}),
            )
        case "update_contact":
            await crm.update_contact(
                payload.get("crm_id", ""),
                payload.get("data", {}),
            )
        case "add_note":
            await crm.add_note(
                payload.get("contact_id", ""),
                payload.get("note", ""),
            )
        case _:
            logger.error(f"CRM retry: unknown operation '{operation}', discarding")
