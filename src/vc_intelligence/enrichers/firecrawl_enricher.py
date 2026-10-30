"""
Firecrawl Founder Contact Enricher
Extracts founders, titles, bios, LinkedIn URLs, and corporate emails from
company websites using Firecrawl's schema-guided structured LLM extraction.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional
import httpx

from src.config import settings
from src.vc_intelligence.interfaces import IFounderEnricher
from src.vc_intelligence.models import RawPortfolioCompany, RawFounder

log = logging.getLogger("vc_intelligence.firecrawl_enricher")

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"


class FirecrawlFounderEnricher(IFounderEnricher):
    """
    Enriches portfolio company founder records using Firecrawl structured extraction.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.firecrawl_api_key

    async def enrich_founders(self, company: RawPortfolioCompany) -> List[RawFounder]:
        """
        Extract founders and contact details for a portfolio company.
        """
        if not company.website and not company.domain:
            return []

        # If founders were already discovered via directory scraper (e.g. YC/Accel), enrich their emails
        if company.founders:
            return self._enrich_existing_founders(company)

        if not self.api_key:
            log.debug("Firecrawl API key not set, falling back to heuristic contact synthesis")
            return self._heuristic_fallback(company)

        target_url = company.website or f"https://{company.domain}"
        about_urls = [
            f"{target_url.rstrip('/')}/about",
            f"{target_url.rstrip('/')}/team",
            f"{target_url.rstrip('/')}/company",
            target_url,
        ]

        for url in about_urls[:2]:
            try:
                extracted = await self._scrape_with_firecrawl(url, company.domain)
                if extracted:
                    log.info(f"Firecrawl enriched {len(extracted)} founders for {company.name}")
                    return extracted
            except Exception as exc:
                log.warning(f"Firecrawl scrape failed for {url}: {exc}")

        return self._heuristic_fallback(company)

    async def _scrape_with_firecrawl(self, url: str, domain: Optional[str]) -> List[RawFounder]:
        """Call Firecrawl /v1/scrape with schema-guided extraction."""
        schema = {
            "type": "object",
            "properties": {
                "founders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "title": {"type": "string"},
                            "email": {"type": "string"},
                            "linkedin_url": {"type": "string"},
                            "twitter_handle": {"type": "string"},
                            "bio": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                }
            },
        }

        payload = {
            "url": url,
            "formats": ["extract"],
            "extract": {
                "schema": schema,
                "prompt": "Extract the names, titles, LinkedIn profile links, and direct emails of the company founders or executive leadership.",
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(FIRECRAWL_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                log.warning(f"Firecrawl returned status {resp.status_code}: {resp.text[:200]}")
                return []

            data = resp.json()
            extract_data = data.get("data", {}).get("extract", {})
            founders_raw = extract_data.get("founders", [])

            results: List[RawFounder] = []
            for f in founders_raw:
                name = f.get("name")
                if not name or len(name.split()) < 2:
                    continue

                email = f.get("email")
                confidence = 0.90 if email else 0.0

                if not email and domain:
                    email, confidence = self._synthesize_email(name, domain)

                results.append(
                    RawFounder(
                        full_name=name.strip(),
                        title=f.get("title") or "Co-Founder",
                        email=email,
                        email_confidence=confidence,
                        linkedin_url=f.get("linkedin_url"),
                        twitter_handle=f.get("twitter_handle"),
                        bio=f.get("bio"),
                        source="firecrawl",
                    )
                )

            return results

    def _enrich_existing_founders(self, company: RawPortfolioCompany) -> List[RawFounder]:
        """Add email predictions and confidence scores to directory-scraped founders."""
        enriched: List[RawFounder] = []
        domain = company.domain or (re.sub(r"^https?://(www\.)?", "", company.website or "").split("/")[0])

        for f in company.founders:
            email = f.email
            confidence = f.email_confidence

            if not email and domain:
                email, confidence = self._synthesize_email(f.full_name, domain)

            enriched.append(
                RawFounder(
                    full_name=f.full_name,
                    title=f.title or "Co-Founder",
                    email=email,
                    email_confidence=confidence,
                    linkedin_url=f.linkedin_url,
                    twitter_handle=f.twitter_handle,
                    bio=f.bio,
                    source=f.source or "directory_enriched",
                )
            )
        return enriched

    def _heuristic_fallback(self, company: RawPortfolioCompany) -> List[RawFounder]:
        """Fallback when no direct API is available."""
        if company.founders:
            return self._enrich_existing_founders(company)
        return []

    @staticmethod
    def _synthesize_email(full_name: str, domain: str) -> tuple[str, float]:
        """
        Synthesize most probable founder email pattern (first@domain or first.last@domain).
        Founders of startups overwhelmingly use first@domain (>65% probability)
        or first.last@domain (~25% probability).
        """
        parts = [re.sub(r"[^\w]", "", p.lower()) for p in full_name.split() if p.strip()]
        if not parts:
            return f"founder@{domain}", 0.30

        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""

        if first and domain:
            email = f"{first}@{domain}"
            return email, 0.70

        return f"founder@{domain}", 0.30
