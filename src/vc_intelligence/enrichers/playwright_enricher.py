"""
Playwright Founder Contact Enricher
Headless browser extractor for JavaScript-heavy single page application (SPA)
team and about pages. Extracts founder names, titles, mailto links, and LinkedIn profiles.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from src.vc_intelligence.interfaces import IFounderEnricher
from src.vc_intelligence.models import RawPortfolioCompany, RawFounder

log = logging.getLogger("vc_intelligence.playwright_enricher")


class PlaywrightFounderEnricher(IFounderEnricher):
    """
    DOM-level extractor using Playwright headless Chromium.
    """

    async def enrich_founders(self, company: RawPortfolioCompany) -> List[RawFounder]:
        """
        Navigate to startup /about or /team page using Playwright and parse DOM cards.
        """
        # If founders were already discovered via directory scraper (e.g. YC/Accel), enrich their emails
        if company.founders:
            return self._enrich_existing_founders(company)

        target_url = company.website or (f"https://{company.domain}" if company.domain else None)
        if not target_url:
            return []

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.debug("Playwright not installed; skipping PlaywrightFounderEnricher")
            return self._enrich_existing_founders(company)

        discovered: List[RawFounder] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Try /about and /team
                for path in ["/about", "/team", "/"]:
                    full_url = f"{target_url.rstrip('/')}{path}"
                    try:
                        await page.goto(full_url, timeout=15000, wait_until="domcontentloaded")
                        content = await page.content()

                        # Extract mailto links
                        mailtos = await page.eval_on_selector_all(
                            "a[href^='mailto:']", "elements => elements.map(e => e.href)"
                        )
                        # Extract linkedin links
                        linkedins = await page.eval_on_selector_all(
                            "a[href*='linkedin.com/in/']", "elements => elements.map(e => e.href)"
                        )

                        # Look for founder patterns in text
                        text = await page.inner_text("body")
                        founder_matches = re.findall(
                            r"([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–—|,:]\s*(Co-Founder|Founder|Chief Executive Officer|CEO|CTO)",
                            text,
                        )

                        for name, title in founder_matches[:4]:
                            clean_name = name.strip()
                            email = None
                            for m in mailtos:
                                raw_email = m.replace("mailto:", "").split("?")[0].strip()
                                if any(part.lower() in raw_email.lower() for part in clean_name.split()):
                                    email = raw_email
                                    break

                            linkedin = None
                            for l_url in linkedins:
                                if any(part.lower() in l_url.lower() for part in clean_name.split()):
                                    linkedin = l_url
                                    break

                            discovered.append(
                                RawFounder(
                                    full_name=clean_name,
                                    title=title,
                                    email=email,
                                    email_confidence=0.85 if email else 0.0,
                                    linkedin_url=linkedin,
                                    source="playwright",
                                )
                            )

                        if discovered:
                            break
                    except Exception as nav_exc:
                        log.debug(f"Navigation to {full_url} failed: {nav_exc}")

                await browser.close()
        except Exception as exc:
            log.warning(f"Playwright browser execution failed: {exc}")

        if not discovered and company.founders:
            return self._enrich_existing_founders(company)

        return discovered

    def _enrich_existing_founders(self, company: RawPortfolioCompany) -> List[RawFounder]:
        """Synthesize probable emails for existing founders."""
        enriched: List[RawFounder] = []
        domain = company.domain or ""

        for f in company.founders:
            email = f.email
            confidence = f.email_confidence
            if not email and domain:
                first = f.full_name.split()[0].lower()
                email = f"{first}@{domain}"
                confidence = 0.70

            enriched.append(
                RawFounder(
                    full_name=f.full_name,
                    title=f.title or "Co-Founder",
                    email=email,
                    email_confidence=confidence,
                    linkedin_url=f.linkedin_url,
                    twitter_handle=f.twitter_handle,
                    bio=f.bio,
                    source=f.source or "playwright_enriched",
                )
            )
        return enriched
