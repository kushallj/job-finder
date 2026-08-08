"""
discovery_engine.py — Main Email Discovery Engine orchestrator.

This is the top-level class that wires the 5 layers into one clean interface.

DAG execution plan:
  All of Layer 1 (collection) runs concurrently via asyncio.gather().
  Layer 2 (pattern mining) starts as soon as any Layer 1 source completes.
  Layer 3 (candidate generation) runs per-known-name, blocking on Layer 2.
  Layer 4 (SMTP verification) runs in ThreadPoolExecutor, concurrent batches.
  Layer 5 (scoring + dedup) runs synchronously, O(n log n) sort.

Output: List[DiscoveredEmail] sorted by confidence desc.
  Each result has: email, name, title, company, confidence, sources, verified

Integration with existing email_discovery.py:
  The existing EmailDiscoveryService (12+ providers) is called as one of the
  Layer 1 sources. This engine wraps it, adds GitHub + web crawling, and applies
  proper pattern mining + confidence scoring on top.

Usage:
    engine = EmailDiscoveryEngine()
    contacts = await engine.discover(
        company_name = "Stripe",
        domain       = "stripe.com",
        person_names = [("John", "Doe"), ("Sarah", "Connor")],   # optional
    )
    for c in contacts:
        print(c.email, c.confidence, c.sources)
    await engine.close()
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from src.email_discovery import DiscoveredEmail, EmailDiscoveryService
from src.email_engine.github_miner import GitHubMiner, GitHubContact
from src.email_engine.web_crawler import TeamPageCrawler, CrawlContact
from src.email_engine.wayback_miner import WaybackMiner, WaybackContact
from src.email_engine.pattern_miner import PatternMiner, PatternDB, PatternResult, _normalize_domain
from src.email_engine.confidence_scorer import ConfidenceScorer, ScoringSignals

log = logging.getLogger(__name__)


class EmailDiscoveryEngine:
    """
    5-layer email discovery pipeline.

    Layer 1: Concurrent data collection
      - Existing providers (Hunter, Apollo, Snov, etc.) via EmailDiscoveryService
      - GitHub org commit mining via GitHubMiner
      - Team page web crawling via TeamPageCrawler

    Layer 2: Pattern mining
      - PatternMiner derives dominant email format from Layer 1 results
      - PatternDB persists domain→format mappings for O(1) future lookups

    Layer 3: Candidate generation
      - For each known person name, generate all format permutations
      - Rank by pattern confidence

    Layer 4: SMTP verification
      - Run in ThreadPoolExecutor (blocking I/O, imaplib-style)
      - MX lookup → catch-all detection → SMTP RCPT TO
      - Batch: up to 20 concurrent verifications

    Layer 5: Confidence scoring + dedup + rank
      - Multi-factor score per DiscoveredEmail
      - Cross-source corroboration boost
      - Final sort by confidence

    Usage:
        engine = EmailDiscoveryEngine()
        results = await engine.discover("Stripe", "stripe.com")
        await engine.close()
    """

    SMTP_WORKERS    = 20   # parallel SMTP verifications (I/O bound → threads)
    MIN_CONFIDENCE  = 30   # drop results below this threshold

    def __init__(
        self,
        discovery_service: Optional[EmailDiscoveryService] = None,
        github_miner:      Optional[GitHubMiner]           = None,
        web_crawler:       Optional[TeamPageCrawler]       = None,
        wayback_miner:     Optional[WaybackMiner]          = None,
        pattern_db_path:   str                             = "email_patterns.db",
        enable_smtp:       bool                            = True,
        min_confidence:    int                             = 30,
    ):
        self._providers    = discovery_service or EmailDiscoveryService()
        self._github       = github_miner or GitHubMiner()
        self._crawler      = web_crawler or TeamPageCrawler()
        self._wayback      = wayback_miner or WaybackMiner()
        self._pattern_db   = PatternDB(db_path=pattern_db_path)
        self._miner        = PatternMiner(db=self._pattern_db)
        self._scorer       = ConfidenceScorer()
        self._smtp_pool    = ThreadPoolExecutor(max_workers=self.SMTP_WORKERS, thread_name_prefix="smtp")
        self._enable_smtp  = enable_smtp
        self._min_conf     = min_confidence

    # ── Public API ────────────────────────────────────────────────────────────

    async def discover(
        self,
        company_name:  str,
        domain:        str,
        person_names:  Optional[List[Tuple[str, str]]] = None,
        limit:         int = 20,
        skip_smtp:     bool = False,
    ) -> List[DiscoveredEmail]:
        """
        Full 5-layer discovery pipeline for `company_name`/`domain`.

        Args:
            company_name: Company display name (e.g. "Stripe")
            domain:       Root domain (e.g. "stripe.com")
            person_names: Optional [(first, last), ...] to generate candidates for
            limit:        Max results to return
            skip_smtp:    Skip SMTP verification (faster but less accurate)

        Returns:
            List[DiscoveredEmail] sorted by confidence desc, max `limit` items
        """
        domain = _normalize_domain(domain)
        log.info(
            "EmailDiscoveryEngine: starting discovery company=%s domain=%s names=%d",
            company_name, domain, len(person_names or []),
        )

        # ── Layer 1: Concurrent collection ────────────────────────────────────
        collected = await self._layer1_collect(company_name, domain, limit)
        log.info("Layer 1 complete: %d raw emails collected", len(collected))

        # ── Layer 2: Pattern mining ────────────────────────────────────────────
        pattern_result = self._layer2_mine_patterns(collected, domain, person_names)
        log.info(
            "Layer 2 complete: best_pattern=%s confidence=%.0f%%",
            pattern_result.best_format.template if pattern_result.best_format else "none",
            pattern_result.confidence * 100,
        )

        # ── Layer 3: Candidate generation for known names ─────────────────────
        candidates = self._layer3_generate_candidates(person_names or [], domain, pattern_result)
        if candidates:
            log.info("Layer 3 complete: %d candidates generated for %d names",
                     len(candidates), len(person_names or []))
            # Merge candidates into collected (add new, don't overwrite existing)
            existing_emails = {e.email for e in collected}
            for email, conf in candidates:
                if email not in existing_emails:
                    parts = email.split("@")[0].split(".")
                    name  = " ".join(p.title() for p in parts[:2]) if len(parts) >= 2 else ""
                    collected.append(DiscoveredEmail(
                        email      = email,
                        name       = name,
                        title      = "",
                        company    = company_name,
                        confidence = conf,
                        source     = "generated",
                        sources    = ["generated"],
                    ))

        # ── Layer 4: SMTP verification ────────────────────────────────────────
        if self._enable_smtp and not skip_smtp:
            collected = await self._layer4_verify(collected)
            log.info("Layer 4 complete: SMTP verification done")

        # ── Layer 5: Score + dedup + rank ─────────────────────────────────────
        results = self._layer5_score_and_rank(collected, pattern_result)
        results = [r for r in results if r.confidence >= self._min_conf][:limit]

        log.info(
            "Discovery complete: %d results (top confidence: %d%%)",
            len(results),
            results[0].confidence if results else 0,
        )
        return results

    # ── Layer 1: Collection ───────────────────────────────────────────────────

    async def _layer1_collect(
        self,
        company_name: str,
        domain: str,
        limit: int,
    ) -> List[DiscoveredEmail]:
        """Run all collection sources concurrently."""
        tasks = [
            asyncio.create_task(
                self._collect_from_providers(company_name, domain, limit),
                name="providers",
            ),
            asyncio.create_task(
                self._collect_from_github(company_name, domain),
                name="github",
            ),
            asyncio.create_task(
                self._collect_from_crawler(domain),
                name="crawler",
            ),
            asyncio.create_task(
                self._collect_from_wayback(domain),
                name="wayback",
            ),
        ]

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        all_emails: Dict[str, DiscoveredEmail] = {}
        for batch in results_list:
            if isinstance(batch, list):
                for email_obj in batch:
                    key = email_obj.email.lower()
                    if key in all_emails:
                        all_emails[key].merge(email_obj)
                    else:
                        all_emails[key] = email_obj

        return list(all_emails.values())

    async def _collect_from_providers(
        self, company: str, domain: str, limit: int
    ) -> List[DiscoveredEmail]:
        try:
            return await self._providers.discover_contacts(company, domain, limit=limit)
        except Exception as e:
            log.warning("Provider collection failed: %s", e)
            return []

    async def _collect_from_github(
        self, company: str, domain: str
    ) -> List[DiscoveredEmail]:
        try:
            contacts: List[GitHubContact] = await self._github.mine_org(company, domain)
            return [
                DiscoveredEmail(
                    email      = c.email,
                    name       = c.name,
                    title      = "",
                    company    = c.company,
                    confidence = c.confidence,
                    source     = "github_commits",
                    sources    = ["github_commits"],
                )
                for c in contacts
            ]
        except Exception as e:
            log.warning("GitHub collection failed: %s", e)
            return []

    async def _collect_from_crawler(self, domain: str) -> List[DiscoveredEmail]:
        try:
            contacts: List[CrawlContact] = await self._crawler.crawl(domain)
            return [
                DiscoveredEmail(
                    email      = c.email,
                    name       = c.name,
                    title      = c.title,
                    company    = domain,
                    confidence = c.confidence,
                    source     = "web_crawler",
                    sources    = ["web_crawler"],
                    linkedin_url = c.linkedin_url,
                )
                for c in contacts
                if c.email
            ]
        except Exception as e:
            log.warning("Web crawler collection failed: %s", e)
            return []

    async def _collect_from_wayback(self, domain: str) -> List[DiscoveredEmail]:
        try:
            contacts: List[WaybackContact] = await self._wayback.mine(domain)
            return [
                DiscoveredEmail(
                    email      = c.email,
                    name       = c.name,
                    title      = c.title,
                    company    = domain,
                    confidence = c.confidence,
                    source     = "wayback_machine",
                    sources    = ["wayback_machine"],
                )
                for c in contacts
                if c.email
            ]
        except Exception as e:
            log.warning("Wayback Machine collection failed: %s", e)
            return []

    # ── Layer 2: Pattern mining ───────────────────────────────────────────────

    def _layer2_mine_patterns(
        self,
        collected: List[DiscoveredEmail],
        domain: str,
        known_names: Optional[List[Tuple[str, str]]],
    ) -> PatternResult:
        """Mine email patterns from collected emails."""
        # Check cache first
        cached = self._miner.get_cached(domain)
        if cached and cached.total_emails >= 5:
            log.debug("Pattern cache hit for %s (n=%d)", domain, cached.total_emails)
            return cached

        emails = [e.email for e in collected if e.email]
        names  = known_names or [
            self._split_name(e.name) for e in collected
            if e.name and e.name.lower() not in ("unknown", "")
        ]

        return self._miner.mine(
            emails=emails,
            domain=domain,
            known_names=[n for n in names if n[0] and n[1]],
        )

    # ── Layer 3: Candidate generation ────────────────────────────────────────

    def _layer3_generate_candidates(
        self,
        person_names: List[Tuple[str, str]],
        domain: str,
        pattern_result: PatternResult,
    ) -> List[Tuple[str, int]]:
        """Generate email candidates for each known person."""
        all_candidates: List[Tuple[str, int]] = []
        seen: set = set()

        for first, last in person_names:
            if not first or not last:
                continue
            candidates = self._miner.generate_candidates(first, last, domain, pattern_result)
            for email, score in candidates:
                if email not in seen:
                    seen.add(email)
                    all_candidates.append((email, score))

        return all_candidates

    # ── Layer 4: SMTP verification ────────────────────────────────────────────

    async def _layer4_verify(
        self, emails: List[DiscoveredEmail]
    ) -> List[DiscoveredEmail]:
        """
        Run SMTP verification in thread pool (blocking I/O).
        Only verify emails with confidence > 40 (no point verifying junk).
        """
        from src.email_discovery import SMTPVerifier

        to_verify = [e for e in emails if e.confidence > 40 and not e.smtp_checked]
        if not to_verify:
            return emails

        loop = asyncio.get_event_loop()

        async def verify_one(email_obj: DiscoveredEmail) -> DiscoveredEmail:
            try:
                result = await loop.run_in_executor(
                    self._smtp_pool,
                    SMTPVerifier.verify,
                    email_obj.email,
                )
                email_obj.smtp_checked = True
                if result.get("is_catchall"):
                    # Catch-all: domain exists but can't confirm specific address
                    email_obj.confidence = min(email_obj.confidence, 50)
                elif result.get("deliverable"):
                    email_obj.verified   = True
                    email_obj.confidence = min(100, email_obj.confidence + 20)
                elif result.get("mx_found") and not result.get("deliverable"):
                    # MX exists but address bounced → reduce confidence heavily
                    email_obj.confidence = max(5, email_obj.confidence - 40)
            except Exception as e:
                log.debug("SMTP verify error for %s: %s", email_obj.email, e)
            return email_obj

        # Run in batches of SMTP_WORKERS
        batch_size = self.SMTP_WORKERS
        for i in range(0, len(to_verify), batch_size):
            batch   = to_verify[i: i + batch_size]
            updated = await asyncio.gather(*[verify_one(e) for e in batch])
            # Replace in original list
            for updated_email in updated:
                for j, orig in enumerate(emails):
                    if orig.email == updated_email.email:
                        emails[j] = updated_email
                        break

        return emails

    # ── Layer 5: Scoring + dedup + rank ──────────────────────────────────────

    def _layer5_score_and_rank(
        self,
        collected: List[DiscoveredEmail],
        pattern_result: PatternResult,
    ) -> List[DiscoveredEmail]:
        """Apply confidence scorer to all emails and return sorted list."""
        now = datetime.now(timezone.utc)

        for email_obj in collected:
            parts = email_obj.name.split() if email_obj.name else []
            first = parts[0] if parts else ""
            last  = parts[-1] if len(parts) > 1 else ""

            # Build signals
            local = email_obj.email.split("@")[0] if "@" in email_obj.email else ""
            candidates = self._miner.generate_candidates(first, last, email_obj.email.split("@")[-1], pattern_result)
            top_email  = candidates[0][0] if candidates else ""

            signals = ScoringSignals(
                smtp_verified      = True  if email_obj.verified else (None if not email_obj.smtp_checked else False),
                smtp_catch_all     = False,
                smtp_blocked       = not email_obj.smtp_checked,
                pattern_confidence = pattern_result.confidence,
                matches_top_pattern = (email_obj.email == top_email),
                format_base_score  = 50,
                sources            = email_obj.sources or [email_obj.source],
                has_first_name     = bool(first and first.lower() not in ("unknown", "")),
                has_last_name      = bool(last and last.lower() not in ("unknown", "")),
                name_is_unknown    = not email_obj.name or email_obj.name.lower() in ("unknown", ""),
                discovered_at      = now,
            )

            scored = self._scorer.score(email_obj.email, signals)
            # Blend: take max of existing confidence and scored result
            email_obj.confidence = max(email_obj.confidence, scored.final_score)

        # Dedup: keep highest-confidence per email
        seen: Dict[str, DiscoveredEmail] = {}
        for e in collected:
            key = e.email.lower()
            if key not in seen or e.confidence > seen[key].confidence:
                seen[key] = e

        return sorted(seen.values(), key=lambda x: x.confidence, reverse=True)

    # ── find_contacts adapter ─────────────────────────────────────────────────

    async def find_contacts(
        self,
        company_name: str,
        job_title: str = "",
        limit: int = 5,
        smtp_verify: bool = False,
    ) -> List[Dict]:
        """
        Drop-in replacement for EmailDiscoveryService.find_contacts().
        Resolves domain, then runs the full 5-layer pipeline (providers +
        GitHub mining + web crawling + pattern mining + SMTP verification).
        Returns List[Dict] with the same keys as EmailDiscoveryService.
        """
        domain = await self._providers.domain_resolver.resolve(company_name) or ""
        if not domain:
            from src.email_discovery import clean_company_slug
            domain = clean_company_slug(company_name) + ".com"
            log.warning("Domain resolution failed for '%s', guessing: %s", company_name, domain)

        results = await self.discover(
            company_name=company_name,
            domain=domain,
            limit=limit,
            skip_smtp=not smtp_verify,
        )

        return [
            {
                "email":        r.email,
                "name":         r.name,
                "title":        r.title,
                "company":      r.company,
                "confidence":   r.confidence,
                "source":       r.source,
                "verified":     r.verified,
                "linkedin_url": r.linkedin_url,
                "phone":        getattr(r, "phone", ""),
                "sources":      r.sources,
            }
            for r in results
        ]

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def close(self) -> None:
        await self._providers.close()
        await self._github.close()
        await self._crawler.close()
        await self._wayback.close()
        self._smtp_pool.shutdown(wait=False)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _split_name(full_name: str) -> Tuple[str, str]:
        """Split "John Doe" → ("John", "Doe"). Handle single names."""
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return parts[0], parts[-1]
        if len(parts) == 1:
            return parts[0], ""
        return "", ""
