from loguru import logger

from app.integrations.crm.base import CRMAdapter


def get_crm(clinic_settings: dict | None) -> CRMAdapter | None:
    """Return the appropriate CRM adapter based on clinic settings.

    Args:
        clinic_settings: The clinic's `settings` JSONB column, expected to contain:
            - crm_enabled: bool
            - crm_provider: "bitrix24" | "amocrm"
            - crm_config: dict with provider-specific keys

    Returns:
        CRMAdapter instance or None if CRM is not configured/enabled.
    """
    if not clinic_settings:
        return None

    if not clinic_settings.get("crm_enabled"):
        return None

    provider = clinic_settings.get("crm_provider")
    crm_config = clinic_settings.get("crm_config")

    if not provider or not crm_config:
        logger.warning("CRM enabled but provider/config missing in clinic settings")
        return None

    match provider:
        case "bitrix24":
            if not crm_config.get("webhook_url"):
                logger.warning("Bitrix24 CRM enabled but webhook_url not configured")
                return None
            from app.integrations.crm.bitrix24 import Bitrix24Adapter
            return Bitrix24Adapter(crm_config)
        case "amocrm":
            if not crm_config.get("api_url") or not crm_config.get("api_key"):
                logger.warning("AmoCRM enabled but api_url/api_key not configured")
                return None
            from app.integrations.crm.amocrm import AmoCRMAdapter
            return AmoCRMAdapter(crm_config)
        case _:
            logger.warning(f"Unknown CRM provider: {provider}")
            return None
