"""
resume_engine.py — Main orchestrator for dynamic resume tailoring.

Pipeline:
  JD text + job_id
    → ResumeParser   → ResumeData (structured base resume)
    → JDAnalyzer     → JDAnalysis (required_skills, tone, pain_points, …)
    → SectionOptimizer → tailored ResumeData (surgical bullet rewrites)
    → ATSOptimizer   → ATSReport (score + missing keywords)
    → inject_missing_keywords → final keyword cleanup pass
    → ResumePDFBuilder → data/resume_v{job_id}.pdf
    → ResumeVariant   (returned + optionally persisted to DB)

Design notes:
  - Base resume (data/resume.txt + data/resume.pdf) is NEVER mutated.
  - Each call produces an independent variant file.
  - All heavy I/O (PDF build) runs in ProcessPoolExecutor to avoid blocking
    the FastAPI event loop.
  - DB persistence is optional — caller can pass session=None to skip it.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from typing import Optional

from .resume_model import ResumeData, ResumeParser, ResumeVariant
from .jd_analyzer import JDAnalysis, JDAnalyzer
from .section_optimizer import SectionOptimizer
from .ats_optimizer import ATSOptimizer, ATSReport
from .pdf_builder import ResumePDFBuilder

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level singletons (lazy-init, shared across calls)
# ---------------------------------------------------------------------------

_jd_analyzer: Optional[JDAnalyzer] = None
_ats_optimizer: ATSOptimizer = ATSOptimizer()
_pdf_builder: ResumePDFBuilder = ResumePDFBuilder()
_process_pool: Optional[ProcessPoolExecutor] = None


def _get_jd_analyzer() -> JDAnalyzer:
    global _jd_analyzer
    if _jd_analyzer is None:
        _jd_analyzer = JDAnalyzer()
    return _jd_analyzer


def _get_process_pool() -> ProcessPoolExecutor:
    global _process_pool
    if _process_pool is None:
        _process_pool = ProcessPoolExecutor(max_workers=2)
    return _process_pool


# ---------------------------------------------------------------------------
# PDF build helper — runs in subprocess (ReportLab is CPU-bound)
# ---------------------------------------------------------------------------

def _build_pdf_subprocess(resume_dict: dict, job_id: int) -> str:
    """
    Called inside a ProcessPoolExecutor worker.
    Re-constructs ResumeData from dict (dataclasses aren't picklable directly).
    """
    import copy
    from .resume_model import ResumeData, ResumeSection, ResumeBullet
    from .pdf_builder import ResumePDFBuilder

    # Reconstruct from plain dicts (produced by _resume_to_dict)
    sections = []
    for s in resume_dict["sections"]:
        bullets = [ResumeBullet(**b) for b in s["bullets"]]
        sec = ResumeSection(
            type=s["type"], title=s["title"],
            header=s.get("header", ""), bullets=bullets,
            raw_text=s.get("raw_text", ""),
        )
        sections.append(sec)

    resume = ResumeData(
        name=resume_dict["name"],
        tagline=resume_dict["tagline"],
        email=resume_dict["email"],
        phone=resume_dict["phone"],
        linkedin=resume_dict["linkedin"],
        github=resume_dict["github"],
        website=resume_dict["website"],
        sections=sections,
        all_skills=resume_dict.get("all_skills", []),
        source_path=resume_dict.get("source_path", "data/resume.txt"),
    )

    builder = ResumePDFBuilder()
    return builder.build(resume, job_id)


def _resume_to_dict(resume: ResumeData) -> dict:
    """Shallow serialization so ResumeData can cross process boundary."""
    from dataclasses import asdict
    return asdict(resume)


# ---------------------------------------------------------------------------
# ResumeEngine
# ---------------------------------------------------------------------------

class ResumeEngine:
    """
    Single entry point for on-demand resume tailoring.

    Usage (async context — FastAPI handler):
        engine = ResumeEngine()
        variant = await engine.tailor(jd_text, job_id=42)
        # variant.pdf_path → "data/resume_v42.pdf"
        # variant.ats_score → 87.3

    Usage (sync / CLI):
        import asyncio
        variant = asyncio.run(engine.tailor(jd_text, job_id=42))
    """

    def __init__(
        self,
        resume_path: str = "data/resume.txt",
        use_subprocess_for_pdf: bool = False,   # set True in prod to unblock event loop
    ):
        self._resume_path         = resume_path
        self._use_subprocess      = use_subprocess_for_pdf
        self._section_optimizer   = SectionOptimizer()   # lazy-inits AI inside
        self._ats_optimizer       = _ats_optimizer
        self._pdf_builder         = _pdf_builder
        self._base_resume: Optional[ResumeData] = None   # cached parse

    # ── Public API ─────────────────────────────────────────────────────────────

    async def tailor(
        self,
        jd_text: str,
        job_id: int,
        job_title: str = "",
        company: str = "",
        db_session=None,                    # SQLAlchemy session (optional)
    ) -> ResumeVariant:
        """
        Full tailoring pipeline.

        Args:
            jd_text:    Raw job description text (any length)
            job_id:     Primary key in jobs table — used for PDF filename
            job_title:  Human-readable role name (for variant metadata)
            company:    Company name (for variant metadata)
            db_session: If provided, persists variant to Application table

        Returns:
            ResumeVariant with pdf_path, ats_score, diff_summary, etc.
        """
        log.info("ResumeEngine: tailoring for job_id=%d company=%s", job_id, company or "?")

        # ── Step 1: Parse base resume (cached after first call) ───────────────
        base_resume = self._get_base_resume()

        # ── Step 2: Analyze JD ────────────────────────────────────────────────
        jd_analysis = await _get_jd_analyzer().analyze(jd_text)
        log.debug(
            "JD analysis: role=%s seniority=%s required=%d keywords",
            jd_analysis.role_focus, jd_analysis.seniority_level,
            len(jd_analysis.critical_keywords),
        )

        # ── Step 3: Pre-optimization ATS score (baseline) ────────────────────
        baseline_report = self._ats_optimizer.score(base_resume, jd_analysis)
        log.info("Baseline ATS score: %.0f/100", baseline_report.overall_score)

        # ── Step 4: Section optimization (surgical rewrites) ─────────────────
        tailored = await self._section_optimizer.optimize(base_resume, jd_analysis)

        # ── Step 5: Post-optimization ATS score + keyword injection ──────────
        ats_report = self._ats_optimizer.score(tailored, jd_analysis)
        injected   = self._ats_optimizer.inject_missing_keywords(tailored, jd_analysis, ats_report)
        if injected:
            # Re-score after injection
            ats_report = self._ats_optimizer.score(tailored, jd_analysis)

        log.info(
            "Tailored ATS score: %.0f/100 (Δ%.0f) | %d bullets modified | %d keywords injected",
            ats_report.overall_score,
            ats_report.overall_score - baseline_report.overall_score,
            len(tailored.modified_bullets()),
            injected,
        )

        # ── Step 6: Build PDF ─────────────────────────────────────────────────
        pdf_path = await self._build_pdf(tailored, job_id)

        # ── Step 7: Assemble variant metadata ────────────────────────────────
        variant = ResumeVariant(
            job_id          = job_id,
            job_title       = job_title,
            company         = company,
            pdf_path        = pdf_path,
            ats_score       = ats_report.overall_score,
            keywords_added  = ats_report.found_keywords[:10],
            bullets_changed = len(tailored.modified_bullets()),
            diff_summary    = tailored.diff_report(),
            created_at      = datetime.now(timezone.utc).isoformat(),
        )

        # ── Step 8: Persist to DB (optional) ─────────────────────────────────
        if db_session:
            await self._persist_variant(variant, ats_report, db_session)

        return variant

    async def score_only(self, jd_text: str) -> ATSReport:
        """
        Score current resume against a JD without modifying anything.
        Useful for the dashboard's "ATS match preview" feature.
        """
        base_resume = self._get_base_resume()
        jd_analysis = await _get_jd_analyzer().analyze(jd_text)
        return self._ats_optimizer.score(base_resume, jd_analysis)

    def reload_base_resume(self) -> None:
        """Force re-parse of resume.txt (call after user uploads new resume)."""
        self._base_resume = None
        log.info("Base resume cache cleared — will re-parse on next call")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_base_resume(self) -> ResumeData:
        if self._base_resume is None:
            log.debug("Parsing base resume from %s", self._resume_path)
            self._base_resume = ResumeParser.parse_file(self._resume_path)
        return self._base_resume

    async def _build_pdf(self, resume: ResumeData, job_id: int) -> str:
        """Build PDF, offloading to subprocess if configured."""
        if self._use_subprocess:
            loop       = asyncio.get_event_loop()
            pool       = _get_process_pool()
            resume_dict = _resume_to_dict(resume)
            pdf_path   = await loop.run_in_executor(
                pool, _build_pdf_subprocess, resume_dict, job_id
            )
        else:
            # Direct call — fine for dev / low concurrency
            pdf_path = self._pdf_builder.build(resume, job_id)
        return pdf_path

    @staticmethod
    async def _persist_variant(
        variant: ResumeVariant, report: ATSReport, db_session
    ) -> None:
        """
        Update the Application row for this job with resume variant metadata.
        No-ops gracefully if Application row doesn't exist yet.
        """
        try:
            from src.models import Application
            app = db_session.query(Application).filter_by(job_id=variant.job_id).first()
            if app:
                app.resume_version = variant.pdf_path
                app.ats_score      = variant.ats_score
                db_session.commit()
                log.debug("Persisted variant for job_id=%d", variant.job_id)
        except Exception as exc:
            log.warning("Could not persist resume variant: %s", exc)


# ---------------------------------------------------------------------------
# Convenience: module-level singleton for import-and-use pattern
# ---------------------------------------------------------------------------

_default_engine: Optional[ResumeEngine] = None


def get_engine() -> ResumeEngine:
    """Return (or create) the default ResumeEngine singleton."""
    global _default_engine
    if _default_engine is None:
        _default_engine = ResumeEngine()
    return _default_engine
