"""
VC Scraper Registry (Factory Pattern)
Adheres to Open/Closed Principle (OCP):
Allows registration of new VC scrapers without modifying orchestrators or callers.
Provides universal fallback to UniversalVCScraper for all 100 global VC firms.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Type, Optional, Any
from src.vc_intelligence.interfaces import IVCPortfolioScraper

log = logging.getLogger("vc_intelligence.registry")


class VCScraperRegistry:
    """Central registry and factory for VC portfolio scrapers."""

    _registry: Dict[str, Type[IVCPortfolioScraper]] = {}
    _vc_100_cache: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def _load_100_firms(cls) -> Dict[str, Dict[str, Any]]:
        """Load and cache the 100 VC firms dataset indexed by slug."""
        if cls._vc_100_cache is not None:
            return cls._vc_100_cache

        json_path = Path(__file__).parent.parent / "data" / "vc_100_firms.json"
        if not json_path.exists():
            return {}

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls._vc_100_cache = {item["slug"]: item for item in data}
        except Exception as e:
            log.warning(f"Failed to load vc_100_firms.json: {e}")
            cls._vc_100_cache = {}

        return cls._vc_100_cache

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
        """
        Instantiate and return the scraper strategy registered for the given slug.
        If no specialized scraper exists, dynamically constructs a UniversalVCScraper
        for any of the 100 registered global VC firms.
        """
        # 1. Specialized scraper strategy priority
        scraper_cls = cls._registry.get(slug)
        if scraper_cls:
            return scraper_cls()

        # 2. Universal VC scraper strategy fallback for 100 global firms
        firms_map = cls._load_100_firms()
        firm_info = firms_map.get(slug)
        if firm_info:
            from src.vc_intelligence.scrapers.universal_vc_scraper import UniversalVCScraper
            return UniversalVCScraper(
                vc_name=firm_info["name"],
                slug=firm_info["slug"],
                portfolio_url=firm_info["portfolio_url"],
                country_focus=firm_info.get("country_focus", "Global"),
            )

        return None

    @classmethod
    def list_available_slugs(cls) -> List[str]:
        """Return list of all registered and 100 global VC slugs."""
        slugs = set(cls._registry.keys())
        slugs.update(cls._load_100_firms().keys())
        return sorted(list(slugs))

    @classmethod
    def is_registered(cls, slug: str) -> bool:
        """Check if a VC slug has an active or universal scraper strategy."""
        return slug in cls._registry or slug in cls._load_100_firms()
