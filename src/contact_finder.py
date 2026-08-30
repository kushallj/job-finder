"""
contact_finder.py — Finds HR and Engineering contacts for companies.

FIXED:
  • Removed the self-importing line that caused the circular ImportError:
      `from src.contact_finder import ContactFinder, Contact as ContactData`
    That line belonged in outreach_processor.py (the consumer), NOT here.
  • This file only imports from stdlib and third-party packages.
  • Anything that needs ContactFinder or Contact imports them FROM this file.

Ownership: this module is the sole source of truth for Contact data structures
and company contact discovery. Nothing here imports from src.*.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Optional DNS validation (pip install dnspython)
try:
    import dns.resolver
    _DNS_AVAILABLE = True
except ImportError:
    _DNS_AVAILABLE = False

log = logging.getLogger(__name__)


# =============================================================================
# Data model
# =============================================================================

@dataclass
class Contact:
    """
    A single contact at a company.
    confidence_score: 0–100 (higher = more likely to be real and reachable)
    """
    name:             str
    title:            str
    email:            Optional[str]       = None
    linkedin_url:     Optional[str]       = None
    company:          str                 = ""
    department:       str                 = ""
    confidence_score: float               = 0.0   # float, not int — consistent everywhere


# =============================================================================
# ContactFinder
# =============================================================================

class ContactFinder:
    """
    Finds HR and Engineering Manager contacts for a given company.

    Discovery cascade (backtracking — tries next on failure):
      1. Company website scrape (team / leadership / contact pages)
      2. DNS MX + email pattern generation (no API needed)
      3. Generic role-based fallback (always returns something)

    LinkedIn search is stubbed — wire in your API when available.
    Google Search scraping was intentionally removed (fragile, rate-limited,
    legally grey). DNS MX is the correct public-infrastructure replacement.
    """

    # Pages to scrape on a company website
    _TEAM_PAGES = ["/about", "/team", "/leadership", "/contact", "/careers", "/people"]

    # Role → typical email prefixes
    ROLE_PATTERNS: List[tuple] = [
        ("Recruiter",           ["recruiting", "talent", "hr", "people", "hiring"]),
        ("Engineering Manager", ["engineering", "em", "eng", "tech"]),
        ("CTO",                 ["cto"]),
        ("Hiring Manager",      ["careers", "jobs"]),
    ]

    def __init__(self):
        self._http = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def find_company_contacts(
        self, company_name: str, job_title: str = ""
    ) -> List[Contact]:
        """
        Main entry point. Uses EmailIntelligenceService (Google Boolean dorking,
        Clearbit domain resolution, GitHub commit harvesting, and pattern synthesis),
        then falls back to website scraping and DNS pattern generation.
        """
        all_contacts: List[Contact] = []

        # Strategy 0: High-accuracy Email Intelligence Waterfall
        try:
            from src.email_intelligence import email_intelligence_service
            intel_res = await email_intelligence_service.discover_company_decision_makers(
                db=None, company=company_name, job_title=job_title, limit=5
            )
            for c_data in intel_res.get("contacts", []):
                all_contacts.append(Contact(
                    name=c_data.get("name") or "Engineering Leader",
                    title=c_data.get("title") or "Engineering Leader",
                    email=c_data.get("email"),
                    company=company_name,
                    confidence_score=float(c_data.get("confidence_score") or 75.0),
                ))
        except Exception as exc:
            log.debug("EmailIntelligenceService waterfall error: %s", exc)

        # Strategy 1: website scrape
        if not all_contacts:
            website_contacts = await self._search_company_website(company_name)
            all_contacts.extend(website_contacts)

        # Strategy 2: DNS MX + pattern generation
        if not all_contacts:
            dns_contacts = await self._dns_pattern_contacts(company_name)
            all_contacts.extend(dns_contacts)

        # Strategy 3: generic fallback (always runs if still empty)
        if not all_contacts:
            all_contacts.extend(self._generic_fallback(company_name))

        # Deduplicate, boost relevant titles, sort by score
        deduped    = self._deduplicate(all_contacts)
        boosted    = self._boost_scores(deduped, job_title)
        filtered   = [c for c in boosted if c.confidence_score >= 20]
        return sorted(filtered, key=lambda c: c.confidence_score, reverse=True)

    # ── Strategy 1: website scraping ─────────────────────────────────────────

    async def _search_company_website(self, company_name: str) -> List[Contact]:
        """Scrape public team/contact pages on the company's own website."""
        domain = await self._resolve_domain_http(company_name)
        if not domain:
            return []

        base = f"https://{domain}"
        contacts: List[Contact] = []

        # Scrape each candidate page concurrently
        pages = [f"{base}{path}" for path in self._TEAM_PAGES]
        results = await asyncio.gather(
            *[self._scrape_page(url, company_name) for url in pages],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, list):
                contacts.extend(r)

        return contacts

    async def _scrape_page(self, url: str, company: str) -> List[Contact]:
        """Fetch one URL and extract emails + nearby names."""
        try:
            resp = await self._http.get(url)
            if resp.status_code != 200:
                return []
            return self._extract_contacts_from_html(resp.text, company)
        except Exception as exc:
            log.debug("Scrape failed for %s: %s", url, exc)
            return []

    def _extract_contacts_from_html(self, html: str, company: str) -> List[Contact]:
        """Pull emails and nearby capitalised names out of raw HTML."""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        email_re = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        emails = email_re.findall(html)

        contacts = []
        for email in emails:
            # Skip obviously non-personal emails
            if any(x in email.lower() for x in ("noreply", "no-reply", "support@", "info@")):
                continue
            name = self._extract_name_near_email(text, email)
            contacts.append(Contact(
                name=name,
                title="",
                email=email,
                company=company,
                confidence_score=35.0,
            ))
        return contacts

    @staticmethod
    def _extract_name_near_email(text: str, email: str) -> str:
        """
        Find a 'FirstName LastName' pattern within 120 chars of the email.
        Returns 'Unknown' if nothing plausible found.
        """
        idx = text.find(email)
        if idx == -1:
            return "Unknown"
        window = text[max(0, idx - 120): idx + 120]
        names = re.findall(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", window)
        return names[0] if names else "Unknown"

    # ── Strategy 2: DNS MX + patterns ────────────────────────────────────────

    async def _dns_pattern_contacts(self, company_name: str) -> List[Contact]:
        """
        Validate domain via DNS MX (public infrastructure, always fast),
        then generate role-based email patterns.

        Why DNS MX over HTTP HEAD?
          HEAD requests are slow and many companies block bots.
          MX records are public DNS data — instant, never blocked.
        """
        domain = await self._resolve_domain_dns(company_name)
        if not domain:
            return []

        contacts = []
        for role, prefixes in self.ROLE_PATTERNS:
            email = f"{prefixes[0]}@{domain}"
            contacts.append(Contact(
                name=role,
                title=role,
                email=email,
                company=company_name,
                confidence_score=40.0,
            ))
        return contacts

    async def _resolve_domain_dns(self, company_name: str) -> Optional[str]:
        """Try common TLDs, validate each with an MX lookup. O(candidates)."""
        if not _DNS_AVAILABLE:
            log.debug("dnspython not installed — skipping MX validation")
            return None

        clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
        candidates = [
            f"{clean}.com", f"{clean}.io", f"{clean}.co",
            f"{clean}.ai",  f"{clean}.net", f"{clean}.tech",
        ]
        loop = asyncio.get_event_loop()
        for domain in candidates:
            try:
                await loop.run_in_executor(
                    None,
                    lambda d=domain: dns.resolver.resolve(d, "MX", lifetime=2),
                )
                log.debug("MX confirmed: %s", domain)
                return domain
            except Exception:
                continue
        return None

    async def _resolve_domain_http(self, company_name: str) -> Optional[str]:
        """
        Fallback domain resolver using HTTP HEAD when DNS isn't available.
        Used only for website scraping (strategy 1).
        """
        clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
        candidates = [f"{clean}.com", f"{clean}.io", f"{clean}.co", f"{clean}.ai"]
        for domain in candidates:
            try:
                resp = await self._http.head(f"https://{domain}", timeout=5.0)
                if resp.status_code < 400:
                    return domain
            except Exception:
                continue
        return None

    # ── Strategy 3: generic fallback ─────────────────────────────────────────

    def _generic_fallback(self, company_name: str) -> List[Contact]:
        """
        Always returns contacts — even if DNS and scraping both fail.
        Uses best-guess domain. Human should verify before sending.
        """
        clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
        domain = f"{clean}.com"
        return [
            Contact(
                name=role,
                title=role,
                email=f"{prefixes[0]}@{domain}",
                company=company_name,
                confidence_score=20.0,
            )
            for role, prefixes in self.ROLE_PATTERNS
        ]

    # ── Dedup + scoring ───────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(contacts: List[Contact]) -> List[Contact]:
        """O(n) dedup keyed on email (lowercased) or name+company."""
        seen: Dict[str, Contact] = {}
        for c in contacts:
            key = c.email.lower() if c.email else f"{c.name}|{c.company}"
            if key not in seen:
                seen[key] = c
        return list(seen.values())

    @staticmethod
    def _boost_scores(contacts: List[Contact], job_title: str) -> List[Contact]:
        """
        Boost confidence for contacts whose title matches the job context.
        Keeps the scoring logic in one place — easy to tune.
        """
        is_tech_job = any(
            w in job_title.lower()
            for w in ("engineer", "developer", "tech", "software", "data", "ml", "ai")
        )
        hr_keywords  = {"hr", "human resource", "people", "talent", "recruit", "hiring"}
        eng_keywords = {"engineering", "tech", "cto", "vp eng", "director"}

        for c in contacts:
            t = (c.title or "").lower()
            if any(k in t for k in hr_keywords):
                c.confidence_score += 25
            if is_tech_job and any(k in t for k in eng_keywords):
                c.confidence_score += 20
            # Penalise unknown names — downstream preflight will block them anyway
            if not c.name or c.name.lower() in ("unknown", "n/a", "", "none"):
                c.confidence_score -= 15
        return contacts

    # ── Cleanup ───────────────────────────────────────────────name────────────

    async def close(self):
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False