"""
VC Scraper Registry (Factory Pattern)
Adheres to Open/Closed Principle (OCP):
Allows registration of new VC scrapers without modifying orchestrators or callers.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Type, Optional
from src.vc_intelligence.interfaces import IVCPortfolioScraper

log = logging.getLogger("vc_intelligence.registry")


class VCScraperRegistry:
    """Central registry and factory for VC portfolio scrapers."""

    _registry: Dict[str, Type[IVCPortfolioScraper]] = {}

    @classmethod
    def register(cls, scraper_cls: Type[IVCPortfolioScraper]) -> Type[IVCPortfolioScraper]:
        """
        Class decorator or function to register a new VC scraper strategy.
        Example:
            @VCScraperRegistry.register
            class YCScraper: ...
        """
        instance = scraper_cls()
        slug = instance.slug
        cls._registry[slug] = scraper_cls
        log.debug(f"Registered VC scraper strategy: {slug} ({scraper_cls.__name__})")
        return scraper_cls

    @classmethod
    def get(cls, slug: str) -> Optional[IVCPortfolioScraper]:
        """Instantiate and return the scraper strategy registered for the given slug."""
        scraper_cls = cls._registry.get(slug)
        if not scraper_cls:
            return None
        return scraper_cls()

    @classmethod
    def list_available_slugs(cls) -> List[str]:
        """Return list of all registered VC slugs."""
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, slug: str) -> bool:
        """Check if a VC slug has an active scraper strategy."""
        return slug in cls._registry
