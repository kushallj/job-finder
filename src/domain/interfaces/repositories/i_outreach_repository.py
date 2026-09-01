"""
Domain Interface: IOutreachRepository
Clean Architecture Port defining contract for outreach records persistence.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.outreach_record import OutreachRecord


class IOutreachRepository(ABC):
    """Abstract interface for managing outreach attempts and history."""

    @abstractmethod
    async def get_by_id(self, record_id: int) -> Optional[OutreachRecord]:
        """Fetch outreach record by ID."""
        pass

    @abstractmethod
    async def get_by_job_id(self, job_id: int) -> List[OutreachRecord]:
        """Fetch all outreach attempts associated with a specific job."""
        pass

    @abstractmethod
    async def get_recent(self, limit: int = 10) -> List[OutreachRecord]:
        """Fetch most recently dispatched outreach records."""
        pass

    @abstractmethod
    async def save(self, record: OutreachRecord) -> OutreachRecord:
        """Persist or update an outreach record."""
        pass

    @abstractmethod
    async def count_total(self) -> int:
        """Count total outreach attempts."""
        pass

    @abstractmethod
    async def count_sent(self) -> int:
        """Count total successfully sent outreach emails."""
        pass
