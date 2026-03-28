"""
personalization_engine.py — Main orchestrator for the Personalization Engine.

Pipeline (all steps run concurrently where possible):
  contact + job
      │
      ├── CompanyResearcher.research(domain, company_name)   ─┐
      ├── ContactResearcher.research(name, email, linkedin)   ├─ asyncio.gather()
      └── ResumeEngine.score_only(jd_text)  [optional]        ┘
      │
      ↓
  HookGenerator.generate(company, contact, jd, resume)
      │
      ↓
  EmailComposer.compose(hooks, ...)
  EmailComposer.compose_cover_letter(hooks, ...)
      │
      ↓
  PersonalizedOutreach  (returned to OutreachOrchestrator)

DAG node contract (for LangGraph integration):
  Input:  {"contact": Contact, "job": Job, "jd_text": str}
  Output: {"personalized_outreach": PersonalizedOutreach}

Integration with OutreachOrchestrator:
  outreach_orchestrator.orchestrate() calls:
      personalization_engine.personalize(contact, job, jd_text)
  and uses result.email.subject + result.email.body as the send payload.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from .models import CompanyProfile, ContactProfile, PersonalizedOutreach
from .company_researcher import CompanyResearcher
from .contact_researcher import ContactResearcher
from .hook_generator import HookGenerator
from .email_composer import EmailComposer

log = logging.getLogger(__name__)


class PersonalizationEngine:
    """
    Single entry point for personalizing outreach.

    Usage:
        engine = PersonalizationEngine()
        outreach = await engine.personalize(
            contact_name="John Doe",
            contact_email="john@stripe.com",
            linkedin_url="linkedin.com/in/johndoe",
            company_name="Stripe",
            domain="stripe.com",
            jd_text="<full job description>",
            job_title="Senior Software Engineer",
        )
        # outreach.email.subject  → personalized subject
        # outreach.email.body     → ≤150 word cold email
        # outreach.cover_letter   → 300 word cover letter
        # outreach.personalization_score → 0-100
    """

    def __init__(self, ai_service=None):
        self._ai                 = ai_service or self._load_ai()
        self._company_researcher = CompanyResearcher()
        self._contact_researcher = ContactResearcher()
        self._hook_generator     = HookGenerator(self._ai)
        self._email_composer     = EmailComposer(self._ai)
        self._resume_engine      = None   # lazy-init (heavy import)

    # ── Public API ─────────────────────────────────────────────────────────────

    async def personalize(
        self,
        contact_name:   str,
        contact_email:  str   = "",
        linkedin_url:   str   = "",
        github_hint:    str   = "",
        company_name:   str   = "",
        domain:         str   = "",
        jd_text:        str   = "",
        job_title:      str   = "",
        job_id:         int   = 0,
    ) -> PersonalizedOutreach:
        """
        Full personalization pipeline for one contact × one job.

        All three research steps run concurrently.
        Falls back gracefully if any source is unavailable.
        """
        t0 = time.monotonic()

        # ── Derive domain from email if not given ──────────────────────────────
        if not domain and "@" in contact_email:
            domain = contact_email.split("@")[1]
        if not company_name and domain:
            company_name = domain.split(".")[0].title()

        # ── Analyze JD (needed for hooks) ──────────────────────────────────────
        jd = await self._analyze_jd(jd_text)

        # ── Concurrent research ────────────────────────────────────────────────
        results = await asyncio.gather(
            self._company_researcher.research(domain, company_name),
            self._contact_researcher.research(
                contact_name, contact_email, linkedin_url, github_hint
            ),
            return_exceptions=True,
        )

        company_profile = results[0] if not isinstance(results[0], Exception) else CompanyProfile(
            domain=domain, name=company_name
        )
        contact_profile = results[1] if not isinstance(results[1], Exception) else ContactProfile(
            name=contact_name
        )

        if isinstance(results[0], Exception):
            log.warning("Company research failed: %s", results[0])
        if isinstance(results[1], Exception):
            log.warning("Contact research failed: %s", results[1])

        # ── Load resume (optional — for role-fit hooks) ────────────────────────
        resume = await self._load_resume()

        # ── Generate hooks ─────────────────────────────────────────────────────
        hooks = self._hook_generator.generate(
            company_profile, contact_profile, jd, resume, max_hooks=3
        )

        log.info(
            "Personalization: %d hooks (best: %s strength=%.2f) for %s @ %s",
            len(hooks),
            hooks[0].type.value if hooks else "none",
            hooks[0].strength if hooks else 0,
            contact_name,
            company_name,
        )

        # ── Compose email ──────────────────────────────────────────────────────
        email = self._email_composer.compose(
            hooks, company_profile, contact_profile, jd, resume
        )

        # ── Compose cover letter ───────────────────────────────────────────────
        cover_letter = self._email_composer.compose_cover_letter(
            hooks, company_profile, contact_profile, jd, resume
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        log.info(
            "PersonalizationEngine: score=%.0f words=%d elapsed=%dms",
            email.personalization_score, email.word_count, elapsed_ms,
        )

        return PersonalizedOutreach(
            contact_name          = contact_name,
            company               = company_name,
            email                 = email,
            cover_letter          = cover_letter,
            personalization_score = email.personalization_score,
            company_profile       = company_profile,
            contact_profile       = contact_profile,
            research_time_ms      = elapsed_ms,
        )

    async def batch_personalize(
        self,
        contacts: list,        # List of dicts with contact fields
        jd_text:  str,
        job_title: str = "",
        concurrency: int = 5,
    ) -> list:
        """
        Personalize for multiple contacts concurrently.
        Uses a semaphore to avoid overwhelming rate-limited APIs.
        """
        sem = asyncio.Semaphore(concurrency)

        async def _one(contact: dict) -> PersonalizedOutreach:
            async with sem:
                return await self.personalize(
                    contact_name  = contact.get("name", ""),
                    contact_email = contact.get("email", ""),
                    linkedin_url  = contact.get("linkedin_url", ""),
                    github_hint   = contact.get("github", ""),
                    company_name  = contact.get("company", ""),
                    domain        = contact.get("domain", ""),
                    jd_text       = jd_text,
                    job_title     = job_title,
                )

        results = await asyncio.gather(*[_one(c) for c in contacts], return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _analyze_jd(self, jd_text: str):
        """Analyze JD text. Returns JDAnalysis or a minimal stub."""
        try:
            from src.resume_engine.jd_analyzer import JDAnalyzer
            analyzer = JDAnalyzer()
            return await analyzer.analyze(jd_text)
        except Exception as exc:
            log.warning("JD analysis failed: %s — using stub", exc)
            return _JDStub(jd_text)

    async def _load_resume(self):
        """Lazily load base resume for role-fit hooks."""
        try:
            if self._resume_engine is None:
                from src.resume_engine.resume_engine import get_engine
                self._resume_engine = get_engine()
            return self._resume_engine._get_base_resume()
        except Exception:
            return None

    @staticmethod
    def _load_ai():
        try:
            from src.ai.unified_ai_service import UnifiedAIService
            return UnifiedAIService()
        except Exception:
            return None

    # ── Context manager for session cleanup ────────────────────────────────────

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self._company_researcher.__aexit__()
        await self._contact_researcher.__aexit__()


# ---------------------------------------------------------------------------
# Minimal JD stub (when JD analyzer is unavailable)
# ---------------------------------------------------------------------------

class _JDStub:
    """Minimal JDAnalysis stand-in when resume_engine is not available."""

    def __init__(self, jd_text: str):
        import re
        self.jd_text        = jd_text
        self.role_focus     = "Software Engineer"
        self.seniority_level = "mid"
        self.tone           = "professional"
        self.company_name   = ""
        self.pain_points    = []
        self.culture_keywords = []
        self.exact_phrases  = []

        # Quick regex extraction of tech keywords
        _TECH = re.compile(
            r"\b(Python|FastAPI|Django|Node\.?js|React|TypeScript|Go|Rust|Java"
            r"|Kubernetes|Docker|AWS|PostgreSQL|Redis|Kafka|ML|AI|LLM|GraphQL)\b",
            re.IGNORECASE,
        )
        self.required_skills = list(dict.fromkeys(
            m.group(0) for m in _TECH.finditer(jd_text)
        ))[:8]
        self.nice_to_have    = []
        self.tech_stack      = self.required_skills[:]
        self.all_keywords    = self.required_skills[:]
        self.critical_keywords = self.required_skills[:]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[PersonalizationEngine] = None


def get_engine() -> PersonalizationEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = PersonalizationEngine()
    return _default_engine
