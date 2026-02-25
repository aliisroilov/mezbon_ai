import httpx
from loguru import logger

from app.integrations.crm.base import CRMAdapter


class Bitrix24Adapter(CRMAdapter):
    """Bitrix24 CRM integration via REST webhook API.

    Expects crm_config dict with:
        - webhook_url: str — Bitrix24 inbound webhook URL
          e.g. "https://your-domain.bitrix24.uz/rest/1/abc123xyz/"
    """

    def __init__(self, crm_config: dict) -> None:
        self._webhook_url = crm_config["webhook_url"].rstrip("/")
        self._client = httpx.AsyncClient(timeout=15.0)

    async def _call(self, method: str, params: dict) -> dict:
        """Make a Bitrix24 REST API call."""
        url = f"{self._webhook_url}/{method}"
        try:
            resp = await self._client.post(url, json=params)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"Bitrix24 API error: {data['error_description']}")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(
                "Bitrix24 HTTP error",
                extra={"method": method, "status": e.response.status_code},
            )
            raise
        except Exception as e:
            logger.error(
                "Bitrix24 API call failed",
                extra={"method": method, "error": str(e)},
            )
            raise

    async def create_contact(self, patient_data: dict) -> str:
        """Create a Bitrix24 contact from patient data.

        Bitrix24 contact fields:
            NAME, LAST_NAME, PHONE, COMMENTS, UF_* (custom fields)
        """
        name_parts = patient_data.get("full_name", "").split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        fields = {
            "NAME": first_name,
            "LAST_NAME": last_name,
            "PHONE": [{"VALUE": patient_data.get("phone", ""), "VALUE_TYPE": "MOBILE"}],
            "COMMENTS": f"Language: {patient_data.get('language_preference', 'uz')}",
        }

        if patient_data.get("date_of_birth"):
            fields["BIRTHDATE"] = patient_data["date_of_birth"]

        result = await self._call("crm.contact.add", {"fields": fields})
        contact_id = str(result["result"])

        logger.info(
            "Bitrix24 contact created",
            extra={"crm_contact_id": contact_id},
        )
        return contact_id

    async def update_contact(self, crm_id: str, data: dict) -> None:
        """Update a Bitrix24 contact."""
        fields: dict = {}

        if "full_name" in data:
            name_parts = data["full_name"].split(maxsplit=1)
            fields["NAME"] = name_parts[0] if name_parts else ""
            fields["LAST_NAME"] = name_parts[1] if len(name_parts) > 1 else ""

        if "phone" in data:
            fields["PHONE"] = [{"VALUE": data["phone"], "VALUE_TYPE": "MOBILE"}]

        if "date_of_birth" in data:
            fields["BIRTHDATE"] = data["date_of_birth"]

        if fields:
            await self._call("crm.contact.update", {"id": crm_id, "fields": fields})
            logger.info("Bitrix24 contact updated", extra={"crm_contact_id": crm_id})

    async def create_deal(self, contact_id: str, deal_data: dict) -> str:
        """Create a Bitrix24 deal linked to a contact.

        Bitrix24 deal fields:
            TITLE, OPPORTUNITY (amount), CONTACT_ID, COMMENTS, STAGE_ID, etc.
        """
        fields = {
            "TITLE": deal_data.get("title", "Appointment"),
            "CONTACT_ID": contact_id,
            "OPPORTUNITY": str(deal_data.get("amount", 0)),
            "CURRENCY_ID": "UZS",
            "STAGE_ID": "NEW",
            "COMMENTS": self._build_deal_comment(deal_data),
        }

        result = await self._call("crm.deal.add", {"fields": fields})
        deal_id = str(result["result"])

        logger.info(
            "Bitrix24 deal created",
            extra={"crm_deal_id": deal_id, "crm_contact_id": contact_id},
        )
        return deal_id

    async def update_deal(self, deal_id: str, data: dict) -> None:
        """Update a Bitrix24 deal (e.g. mark as won after payment)."""
        fields: dict = {}

        if "status" in data:
            stage_map = {
                "won": "WON",
                "lost": "LOSE",
                "in_progress": "EXECUTING",
            }
            fields["STAGE_ID"] = stage_map.get(data["status"], data["status"])

        if "amount" in data:
            fields["OPPORTUNITY"] = str(data["amount"])

        if fields:
            await self._call("crm.deal.update", {"id": deal_id, "fields": fields})
            logger.info("Bitrix24 deal updated", extra={"crm_deal_id": deal_id})

    async def add_note(self, contact_id: str, note: str) -> None:
        """Add a timeline comment to a Bitrix24 contact."""
        await self._call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": contact_id,
                    "ENTITY_TYPE": "contact",
                    "COMMENT": note,
                }
            },
        )
        logger.info("Bitrix24 note added", extra={"crm_contact_id": contact_id})

    @staticmethod
    def _build_deal_comment(deal_data: dict) -> str:
        parts = []
        if deal_data.get("service_name"):
            parts.append(f"Service: {deal_data['service_name']}")
        if deal_data.get("doctor_name"):
            parts.append(f"Doctor: {deal_data['doctor_name']}")
        if deal_data.get("scheduled_at"):
            parts.append(f"Date: {deal_data['scheduled_at']}")
        if deal_data.get("appointment_id"):
            parts.append(f"Appointment ID: {deal_data['appointment_id']}")
        return "\n".join(parts) if parts else ""
