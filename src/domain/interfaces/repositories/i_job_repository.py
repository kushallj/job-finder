"""
Domain Interface: IJobRepository
Clean Architecture Port defining contract for job data persistence and queries.
Adheres to Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from src.domain.entities.job import Job


class IJobRepository(ABC):
    """
    Abstract interface for job persistence and retrieval operations.

    Implementations must guarantee bounded time complexity and memory safety.
    """

    @abstractmethod
    async def get_by_id(self, job_id: int) -> Optional[Job]:
        """Fetch a single job by internal integer primary key."""
        pass

    @abstractmethod
    async def get_by_fingerprint(self, fingerprint: str) -> Optional[Job]:
        """Fetch a job by unique fingerprint hash in O(1) indexed time."""
        pass

    @abstractmethod
    async def save(self, job: Job) -> Job:
        """Persist or update a job entity, returning saved instance."""
        pass

    @abstractmethod
    async def save_batch(self, jobs: List[Job]) -> Tuple[int, int]:
        """
        Batch upsert jobs in bulk.

        Returns:
            Tuple[int, int]: (inserted_count, updated_count)
        """
        pass

    @abstractmethod
    async def query_filtered(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        region: Optional[str] = None,
        experience_level: Optional[str] = None,
        years_of_experience: Optional[int] = None,
        date_posted: Optional[str] = None,
        tech_stack: Optional[str] = None,
        source: Optional[str] = None,
        sort_by: str = "fetched_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Job], int]:
        """
        Multi-facet ORM search query.

        Returns:
            Tuple[List[Job], int]: (matched_jobs_slice, total_count)
        """
        pass

    @abstractmethod
    async def count_total(self) -> int:
        """Count total indexed job opportunities."""
        pass
