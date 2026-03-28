"""
src/resume_engine — Dynamic Resume Intelligence Engine

Instead of showing a match_score, this engine FIXES the gap automatically.

Pipeline (DAG):
  JD text ──► JDAnalyzer ──────────────────────────────────────────────┐
                                                                         ▼
  Base resume ──► ResumeParser ──► SectionOptimizer ──► ATSOptimizer ──► PDFBuilder
                                         ▲                                    │
                              (uses JDAnalysis)                               ▼
                                                                    resume_v{job_id}.pdf

Components:
    resume_model     — Structured dataclasses for resume (not a text blob)
    jd_analyzer      — LLM extracts: required_skills, pain_points, tone, exact_phrases
    section_optimizer— Rewrites bullets to mirror JD language, fill skill gaps
    ats_optimizer    — Keyword injection, density scoring, ATS readability check
    pdf_builder      — Dynamic ReportLab PDF from structured ResumeData
    resume_engine    — Main orchestrator, variant tracking, diff generation
"""

from .resume_model import ResumeData, ResumeSection, ResumeBullet, ResumeVariant
from .jd_analyzer import JDAnalyzer, JDAnalysis
from .section_optimizer import SectionOptimizer
from .ats_optimizer import ATSOptimizer, ATSReport
from .pdf_builder import ResumePDFBuilder
from .resume_engine import ResumeEngine

__all__ = [
    "ResumeData", "ResumeSection", "ResumeBullet", "ResumeVariant",
    "JDAnalyzer", "JDAnalysis",
    "SectionOptimizer",
    "ATSOptimizer", "ATSReport",
    "ResumePDFBuilder",
    "ResumeEngine",
]
