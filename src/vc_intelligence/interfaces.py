"""
VC Intelligence Interfaces (Protocols & ABCs)
Following SOLID Principles:
- Single Responsibility (SRP): Clean division between scraper, enricher, and repository.
- Open/Closed (OCP): New VCs implement IVCPortfolioScraper without changing existing orchestrators.
- Liskov Substitution (LSP): Any scraper or enricher is swappable.
- Interface Segregation (ISP): Separate ports for directory scraping vs contact enrichment.
- Dependency Inversion (DIP): High-level service depends solely on these abstractions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Protocol, runtime_checkable

from src.vc_intelligence.models import RawPortfolioCompany, RawFounder


@runtime_checkable
class IVCPortfolioScraper(Protocol):
    """
    Contract for extracting portfolio company directories from a specific VC firm.
    Implementations must handle pagination, dynamic DOM rendering (via Playwright or HTTP),
    and return strongly-typed RawPortfolioCompany objects.
    """

    @property
    def vc_name(self) -> str:
        """Official human-readable name of the VC (e.g. 'Y Combinator')."""
        ...

    @property
    def slug(self) -> str:
        """Unique slug identifier matching the database record (e.g. 'y-combinator')."""
        ...

    async def scrape_companies(self, max_companies: int = 50) -> List[RawPortfolioCompany]:
        """
        Asynchronously scrape portfolio companies from the VC directory.

        Args:
            max_companies: Maximum companies to fetch in single pass.

        Returns:
            List[RawPortfolioCompany]: Normalized portfolio company entities.
        """
        ...


@runtime_checkable
class IFounderEnricher(Protocol):
    """
    Contract for extracting founder profiles, bios, LinkedIn URLs, and corporate emails
    from startup company websites, team pages, or structured search APIs.
    """

    async def enrich_founders(self, company: RawPortfolioCompany) -> List[RawFounder]:
        """
        Extract founders and contact info for a specific portfolio company.

        Args:
            company: Raw company entity containing website, domain, and description.

        Returns:
            List[RawFounder]: List of discovered founders and verified/inferred emails.
        """
        ...


class IVCRepository(ABC):
    """
    Contract for persistence, caching, and deduplication of VC intelligence records.
    """

    @abstractmethod
    def get_firm_by_slug(self, slug: str) -> Optional[Any]:
        """Retrieve VC firm database model by unique slug."""
        pass

    @abstractmethod
    def list_firms(self, region: Optional[str] = None) -> List[Any]:
        """List all tracked VC firms with summary metrics, optionally filtered by region."""
        pass

    @abstractmethod
    def seed_100_firms(self) -> int:
        """Seed or update all 100 global VC firms into database. Returns count of firms seeded."""
        pass

    @abstractmethod
    def save_companies(
        self, vc_firm_id: int, companies: List[RawPortfolioCompany]
    ) -> Tuple[int, int]:
        """
        Persist portfolio companies, performing upserts to avoid duplicates.
        Returns: Tuple of (newly_created_count, updated_count).
        """
        pass

    @abstractmethod
    def get_company_by_id(self, company_id: int) -> Optional[Any]:
        """Retrieve portfolio company model by primary key."""
        pass

    @abstractmethod
    def save_founders(self, company_id: int, founders: List[RawFounder]) -> int:
        """
        Persist discovered company founders with deduplication on (company_id, full_name).
        Returns: Number of founders created or updated.
        """
        pass

    @abstractmethod
    def should_enrich_company(self, company_id: int, max_age_days: int = 30) -> bool:
        """
        Deduplication guard: Check if company's founders have already been enriched
        within max_age_days. Returns True if enrichment should be performed, False if cached.
        """
        pass
