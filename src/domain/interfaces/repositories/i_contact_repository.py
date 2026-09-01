"""
Domain Interface: IContactRepository
Clean Architecture Port defining contract for hiring contacts persistence.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.contact import Contact


class IContactRepository(ABC):
    """Abstract interface for contact data access."""

    @abstractmethod
    async def get_by_id(self, contact_id: int) -> Optional[Contact]:
        """Fetch contact by identifier."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Contact]:
        """Fetch contact by unique email in O(1) indexed time."""
        pass

    @abstractmethod
    async def get_by_company(self, company: str, limit: int = 10) -> List[Contact]:
        """Fetch verified contacts for a specific company."""
        pass

    @abstractmethod
    async def save(self, contact: Contact) -> Contact:
        """Persist or update contact record."""
        pass

    @abstractmethod
    async def count_total(self) -> int:
        """Count total verified contacts."""
        pass
