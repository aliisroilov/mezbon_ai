from abc import ABC, abstractmethod


class CRMAdapter(ABC):
    """Abstract base class for CRM integrations.

    All data passed to these methods must be pre-decrypted plaintext.
    Never pass encrypted PII fields directly.
    """

    @abstractmethod
    async def create_contact(self, patient_data: dict) -> str:
        """Create a contact in the CRM from patient data.

        Args:
            patient_data: Dict with keys like full_name, phone, date_of_birth,
                         language_preference. Must be decrypted plaintext.

        Returns:
            CRM contact ID as string.
        """
        ...

    @abstractmethod
    async def update_contact(self, crm_id: str, data: dict) -> None:
        """Update an existing CRM contact.

        Args:
            crm_id: The CRM-side contact identifier.
            data: Fields to update (decrypted plaintext).
        """
        ...

    @abstractmethod
    async def create_deal(self, contact_id: str, deal_data: dict) -> str:
        """Create a deal/opportunity linked to a contact.

        Args:
            contact_id: CRM contact ID.
            deal_data: Dict with keys like title, amount, appointment_id,
                      service_name, doctor_name, scheduled_at.

        Returns:
            CRM deal ID as string.
        """
        ...

    @abstractmethod
    async def update_deal(self, deal_id: str, data: dict) -> None:
        """Update a deal (e.g. mark as won after payment).

        Args:
            deal_id: CRM deal ID.
            data: Fields to update (e.g. status, amount).
        """
        ...

    @abstractmethod
    async def add_note(self, contact_id: str, note: str) -> None:
        """Add a text note/comment to a CRM contact.

        Args:
            contact_id: CRM contact ID.
            note: Note text.
        """
        ...
