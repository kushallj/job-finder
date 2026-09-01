"""
Domain Interface: IScraperStrategy
Strategy Pattern Port defining contract for extracting job postings from ATS portals.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.domain.entities.job import Job


class IScraperStrategy(ABC):
    """
    Abstract Strategy for extracting jobs from a particular provider or ATS.

    Adheres to Open/Closed Principle (OCP) and Liskov Substitution Principle (LSP).
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Unique identifier of the scraping strategy."""
        pass

    @abstractmethod
    async def fetch_jobs_for_target(
        self, target: Dict[str, Any], max_jobs: int = 50
    ) -> List[Job]:
        """
        Execute concurrent scraping for a specific target entity.

        Args:
            target: Configuration dictionary containing name, identifier, or endpoint URL.
            max_jobs: Maximum number of jobs to fetch in single pass.

        Returns:
            List[Job]: Parsed domain entities.
        """
        pass
