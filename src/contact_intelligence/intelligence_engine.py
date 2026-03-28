"""
intelligence_engine.py — Main orchestrator for Contact Intelligence.

Integrates:
  ContactFinder       (existing — discovery)
  EmailDiscoveryEngine (existing — email verification)
  RoleHierarchy       (new — tier classification + DM probability)
  ContactGraphBuilder (new — graph construction)
  GraphRanker         (new — personalized PageRank ranking)

Pipeline:
  company_name + job_title
      ↓
  ContactFinder.find_company_contacts()     → raw Contact list
  EmailDiscoveryEngine.discover()           → verified emails (optional)
      ↓  (merged & de-duped)
  ContactGraphBuilder.build()               → ContactGraph
      ↓
  GraphRanker.rank()                        → List[RankedContact]
      ↓
  IntelligenceResult  (returned to OutreachOrchestrator)

Output (IntelligenceResult):
  ranked_contacts   — List[RankedContact] sorted by outreach_priority
  graph             — full ContactGraph (for path queries)
  top_contact       — single best contact to reach out to first
  outreach_order    — recommended sequence (DM first, then gatekeeper, then peer)
  company_size_est  — estimated headcount (used for DM matrix)

DAG node contract (for LangGraph integration):
  Input:  {"company": str, "domain": str, "job_title": str}
  Output: {"ranked_contacts": List[RankedContact], "top_contact": RankedContact}
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from .contact_graph import ContactGraphBuilder
from .graph_ranker import GraphRanker, RankedContact
from .contact_graph import ContactGraph

log = logging.getLogger(__name__)

# Company size estimation (used when not provided)
# We estimate from job posting volume and domain signals in the future.
# For now, default to 150 (mid-size → "small" bucket).
_DEFAULT_COMPANY_SIZE = 150


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class IntelligenceResult:
    """Complete contact intelligence output for one company × job."""
    company:          str
    job_title:        str
    ranked_contacts:  List[RankedContact]
    graph:            ContactGraph
    company_size_est: int

    @property
    def top_contact(self) -> Optional[RankedContact]:
        return self.ranked_contacts[0] if self.ranked_contacts else None

    @property
    def outreach_order(self) -> List[RankedContact]:
        """
        Smart outreach sequence:
          1. Direct decision maker(s)
          2. Process gatekeeper (recruiter) — so they know your name
          3. Peer referrers — can do internal forwarding
          4. Others
        """
        dm_tier_order = {
            "direct_decision_maker": 0,
            "budget_owner":          1,
            "process_gatekeeper":    2,
            "peer_referrer":         3,
            "executive_sponsor":     4,
            "unknown":               5,
        }
        return sorted(
            self.ranked_contacts,
            key=lambda rc: (
                dm_tier_order.get(rc.decision_path_role, 5),
                -rc.outreach_priority,
            )
        )

    def summary(self) -> str:
        lines = [
            f"Contact Intelligence: {self.company} ({len(self.ranked_contacts)} contacts)",
            f"Graph: {self.graph.summary()}",
        ]
        for i, rc in enumerate(self.ranked_contacts[:5], 1):
            lines.append(
                f"  {i}. {rc.name} ({rc.title}) | "
                f"priority={rc.outreach_priority:.0f} | "
                f"{rc.recommended_approach} | {rc.decision_path_role}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# IntelligenceEngine
# ---------------------------------------------------------------------------

class IntelligenceEngine:
    """
    Main orchestrator for contact intelligence and ranking.

    Usage:
        engine = IntelligenceEngine()
        result = await engine.analyze(
            company_name="Stripe",
            domain="stripe.com",
            job_title="Senior Software Engineer",
        )
        for rc in result.outreach_order:
            print(rc)
    """

    def __init__(self):
        self._graph_builder  = ContactGraphBuilder()
        self._ranker         = GraphRanker()
        self._contact_finder = None   # lazy-init
        self._email_engine   = None   # lazy-init

    # ── Public API ─────────────────────────────────────────────────────────────

    async def analyze(
        self,
        company_name:   str,
        domain:         str         = "",
        job_title:      str         = "",
        company_size:   int         = _DEFAULT_COMPANY_SIZE,
        use_email_engine: bool      = False,   # enable SMTP verification (slow)
        max_contacts:   int         = 20,
    ) -> IntelligenceResult:
        """
        Full contact intelligence pipeline.

        Args:
            company_name:   Company display name ("Stripe")
            domain:         Company domain ("stripe.com")
            job_title:      Target role ("Senior SWE")
            company_size:   Estimated headcount (0 = unknown)
            use_email_engine: Run EmailDiscoveryEngine for SMTP verification
            max_contacts:   Max contacts to process (cap for performance)
        """
        log.info("IntelligenceEngine: analyzing %s for '%s'", company_name, job_title)

        # ── Step 1: Discover contacts ──────────────────────────────────────────
        raw_contacts = await self._discover_contacts(
            company_name, domain, job_title, use_email_engine
        )
        raw_contacts = raw_contacts[:max_contacts]

        if not raw_contacts:
            log.warning("IntelligenceEngine: no contacts found for %s", company_name)
            empty_graph = ContactGraph(company=company_name)
            return IntelligenceResult(
                company          = company_name,
                job_title        = job_title,
                ranked_contacts  = [],
                graph            = empty_graph,
                company_size_est = company_size,
            )

        log.debug("IntelligenceEngine: %d raw contacts for %s", len(raw_contacts), company_name)

        # ── Step 2: Build contact graph ────────────────────────────────────────
        graph = self._graph_builder.build(
            raw_contacts,
            company      = company_name,
            company_size = company_size or _DEFAULT_COMPANY_SIZE,
        )

        # ── Step 3: Rank via personalized PageRank ─────────────────────────────
        ranked = self._ranker.rank(graph, job_title=job_title)

        log.info(
            "IntelligenceEngine: %d contacts ranked | top: %s (priority=%.0f, approach=%s)",
            len(ranked),
            ranked[0].name if ranked else "none",
            ranked[0].outreach_priority if ranked else 0,
            ranked[0].recommended_approach if ranked else "none",
        )

        return IntelligenceResult(
            company          = company_name,
            job_title        = job_title,
            ranked_contacts  = ranked,
            graph            = graph,
            company_size_est = company_size,
        )

    async def analyze_batch(
        self,
        companies: list,    # [{"company_name": str, "domain": str, "job_title": str}, ...]
        concurrency: int = 5,
    ) -> List[IntelligenceResult]:
        """Analyze multiple companies concurrently."""
        sem = asyncio.Semaphore(concurrency)

        async def _one(spec: dict) -> IntelligenceResult:
            async with sem:
                return await self.analyze(**spec)

        results = await asyncio.gather(*[_one(s) for s in companies], return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]

    # ── Internal discovery ─────────────────────────────────────────────────────

    async def _discover_contacts(
        self,
        company_name:     str,
        domain:           str,
        job_title:        str,
        use_email_engine: bool,
    ) -> list:
        """
        Collect contacts from all available sources, merge, deduplicate.
        """
        contacts = []

        # Source 1: ContactFinder (website scraping + DNS)
        finder_contacts = await self._run_contact_finder(company_name, job_title)
        contacts.extend(finder_contacts)

        # Source 2: EmailDiscoveryEngine (if enabled and domain known)
        if use_email_engine and domain:
            email_contacts = await self._run_email_engine(company_name, domain)
            contacts.extend(email_contacts)

        # Source 3: DB contacts (already found from previous runs)
        db_contacts = self._load_db_contacts(company_name)
        contacts.extend(db_contacts)

        return self._merge_contacts(contacts)

    async def _run_contact_finder(self, company_name: str, job_title: str) -> list:
        try:
            if self._contact_finder is None:
                from src.contact_finder import ContactFinder
                self._contact_finder = ContactFinder()
            return await self._contact_finder.find_company_contacts(company_name, job_title)
        except Exception as exc:
            log.debug("ContactFinder failed for %s: %s", company_name, exc)
            return []

    async def _run_email_engine(self, company_name: str, domain: str) -> list:
        """Run EmailDiscoveryEngine and convert results to Contact objects."""
        try:
            if self._email_engine is None:
                from src.email_engine.discovery_engine import EmailDiscoveryEngine
                self._email_engine = EmailDiscoveryEngine()

            results = await self._email_engine.discover(
                company=company_name,
                domain=domain,
                person_names=[],
                limit=10,
            )
            # Convert EmailResult → Contact
            from src.contact_finder import Contact
            return [
                Contact(
                    name             = r.name or "Unknown",
                    title            = "",
                    email            = r.email,
                    company          = company_name,
                    confidence_score = r.confidence * 100,
                )
                for r in results
                if r.email
            ]
        except Exception as exc:
            log.debug("EmailDiscoveryEngine for %s: %s", company_name, exc)
            return []

    @staticmethod
    def _load_db_contacts(company_name: str) -> list:
        """Load previously discovered contacts from DB."""
        try:
            from src.database import SessionLocal
            from src.models import Contact as DBContact
            db = SessionLocal()
            rows = db.query(DBContact).filter(
                DBContact.company.ilike(f"%{company_name}%")
            ).limit(30).all()
            db.close()

            from src.contact_finder import Contact
            return [
                Contact(
                    name             = r.name,
                    title            = r.title or "",
                    email            = r.email,
                    company          = r.company,
                    confidence_score = float(r.confidence_score or 0),
                )
                for r in rows
            ]
        except Exception:
            return []

    @staticmethod
    def _merge_contacts(contacts: list) -> list:
        """
        Deduplicate contacts by email (case-insensitive).
        Merge: keep highest confidence_score for duplicate emails.
        """
        seen: dict = {}
        for c in contacts:
            key = (c.email or "").lower() or f"{c.name}|{c.company}"
            if key in seen:
                # Keep whichever has higher confidence
                if c.confidence_score > seen[key].confidence_score:
                    seen[key] = c
            else:
                seen[key] = c
        return list(seen.values())


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[IntelligenceEngine] = None


def get_engine() -> IntelligenceEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = IntelligenceEngine()
    return _default_engine
