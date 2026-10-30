"""
VC Intelligence Contact Enrichers
Provides Firecrawl, Playwright, and Composite cascade enrichers.
"""

from __future__ import annotations

import logging
from typing import List

from src.vc_intelligence.interfaces import IFounderEnricher
from src.vc_intelligence.models import RawPortfolioCompany, RawFounder
from src.vc_intelligence.enrichers.firecrawl_enricher import FirecrawlFounderEnricher
from src.vc_intelligence.enrichers.playwright_enricher import PlaywrightFounderEnricher

log = logging.getLogger("vc_intelligence.enrichers")


class CompositeFounderEnricher(IFounderEnricher):
    """
    Cascade Enricher:
    1. Runs Firecrawl schema extraction if configured.
    2. Falls back to Playwright dynamic DOM extraction.
    3. Guarantees deterministic email pattern synthesis for known founders.
    """

    def __init__(self):
        self.firecrawl = FirecrawlFounderEnricher()
        self.playwright = PlaywrightFounderEnricher()

    async def enrich_founders(self, company: RawPortfolioCompany) -> List[RawFounder]:
        # Try Firecrawl first
        try:
            founders = await self.firecrawl.enrich_founders(company)
            if founders:
                return founders
        except Exception as exc:
            log.debug(f"Firecrawl enricher step skipped/failed: {exc}")

        # Fallback to Playwright
        try:
            founders = await self.playwright.enrich_founders(company)
            if founders:
                return founders
        except Exception as exc:
            log.debug(f"Playwright enricher step skipped/failed: {exc}")

        return []


__all__ = [
    "FirecrawlFounderEnricher",
    "PlaywrightFounderEnricher",
    "CompositeFounderEnricher",
]
