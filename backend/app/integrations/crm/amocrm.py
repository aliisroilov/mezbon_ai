import httpx
from loguru import logger

from app.integrations.crm.base import CRMAdapter


class AmoCRMAdapter(CRMAdapter):
    """AmoCRM API v4 integration.

    Expects crm_config dict with:
        - api_url: str — AmoCRM subdomain URL, e.g. "https://your-domain.amocrm.ru"
        - api_key: str — Long-lived API token (or OAuth access token)
        - pipeline_id: int (optional) — Pipeline ID for deals, defaults to main
    """

    def __init__(self, crm_config: dict) -> None:
        self._api_url = crm_config["api_url"].rstrip("/")
        self._pipeline_id = crm_config.get("pipeline_id")
        self._client = httpx.AsyncClient(
            base_url=f"{self._api_url}/api/v4",
            timeout=15.0,
            headers={
                "Authorization": f"Bearer {crm_config['api_key']}",
                "Content-Type": "application/json",
            },
        )

    async def _request(
        self, method: str, path: str, json: dict | list | None = None
    ) -> dict:
        """Make an AmoCRM API v4 request."""
        try:
            resp = await self._client.request(method, path, json=json)
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "AmoCRM HTTP error",
                extra={"path": path, "status": e.response.status_code},
            )
            raise
        except Exception as e:
            logger.error(
                "AmoCRM API call failed",
                extra={"path": path, "error": str(e)},
            )
            raise

    async def create_contact(self, patient_data: dict) -> str:
        """Create an AmoCRM contact.

        AmoCRM v4 contacts: POST /api/v4/contacts
        Payload: [{ name, custom_fields_values: [...] }]
        """
        contact_payload = {
            "name": patient_data.get("full_name", ""),
            "custom_fields_values": [],
        }

        if patient_data.get("phone"):
            contact_payload["custom_fields_values"].append({
                "field_code": "PHONE",
                "values": [{"value": patient_data["phone"], "enum_code": "MOB"}],
            })

        result = await self._request(
            "POST", "/contacts", json=[contact_payload]
        )

        contact_id = str(
            result.get("_embedded", {}).get("contacts", [{}])[0].get("id", "")
        )

        logger.info(
            "AmoCRM contact created",
            extra={"crm_contact_id": contact_id},
        )
        return contact_id

    async def update_contact(self, crm_id: str, data: dict) -> None:
        """Update an AmoCRM contact."""
        update_payload: dict = {}

        if "full_name" in data:
            update_payload["name"] = data["full_name"]

        custom_fields = []
        if "phone" in data:
            custom_fields.append({
                "field_code": "PHONE",
                "values": [{"value": data["phone"], "enum_code": "MOB"}],
            })

        if custom_fields:
            update_payload["custom_fields_values"] = custom_fields

        if update_payload:
            update_payload["id"] = int(crm_id)
            await self._request("PATCH", "/contacts", json=[update_payload])
            logger.info("AmoCRM contact updated", extra={"crm_contact_id": crm_id})

    async def create_deal(self, contact_id: str, deal_data: dict) -> str:
        """Create an AmoCRM lead (deal) linked to a contact.

        AmoCRM v4 leads: POST /api/v4/leads
        """
        lead_payload: dict = {
            "name": deal_data.get("title", "Appointment"),
            "price": int(deal_data.get("amount", 0)),
            "_embedded": {
                "contacts": [{"id": int(contact_id)}],
            },
        }

        if self._pipeline_id:
            lead_payload["pipeline_id"] = self._pipeline_id

        result = await self._request("POST", "/leads", json=[lead_payload])

        deal_id = str(
            result.get("_embedded", {}).get("leads", [{}])[0].get("id", "")
        )

        logger.info(
            "AmoCRM lead created",
            extra={"crm_deal_id": deal_id, "crm_contact_id": contact_id},
        )
        return deal_id

    async def update_deal(self, deal_id: str, data: dict) -> None:
        """Update an AmoCRM lead."""
        update_payload: dict = {"id": int(deal_id)}

        if "status" in data:
            status_map = {
                "won": 142,   # Default "Successfully implemented" status
                "lost": 143,  # Default "Closed and not implemented" status
            }
            status_id = status_map.get(data["status"])
            if status_id:
                update_payload["status_id"] = status_id

        if "amount" in data:
            update_payload["price"] = int(data["amount"])

        await self._request("PATCH", "/leads", json=[update_payload])
        logger.info("AmoCRM lead updated", extra={"crm_deal_id": deal_id})

    async def add_note(self, contact_id: str, note: str) -> None:
        """Add a note to an AmoCRM contact.

        AmoCRM v4 notes: POST /api/v4/contacts/{id}/notes
        """
        note_payload = [{
            "note_type": "common",
            "params": {"text": note},
        }]

        await self._request(
            "POST", f"/contacts/{contact_id}/notes", json=note_payload
        )
        logger.info("AmoCRM note added", extra={"crm_contact_id": contact_id})
