"""
ats_optimizer.py — ATS (Applicant Tracking System) scoring and optimization.

What ATS systems actually check (based on Greenhouse, Lever, Workday research):

  1. Keyword matching (50% of ATS score):
     - Exact keyword presence: "Python" in resume vs "Python" in JD
     - Phrase matching: "REST API" vs "REST APIs" (most ATS normalize plurals)
     - Section weighting: skills section > experience > summary

  2. Keyword density (15%):
     - Optimal: 3-5% of resume words are JD keywords
     - Too low: fails screening. Too high: flagged as keyword stuffing

  3. Standard section headers (15%):
     - Must have: Experience, Education, Skills (or close variants)
     - Missing "Education" → some ATS auto-reject

  4. File format / readability (20%):
     - Single-column layout (no tables)
     - Standard fonts
     - No headers/footers (ATS often can't parse them)
     - PDF text-selectable (not scanned image)

ATSReport output:
  overall_score     — 0-100
  keyword_coverage  — % of JD required keywords found in resume
  missing_keywords  — keywords in JD but NOT in resume
  density_score     — keyword density quality
  section_score     — structural completeness
  suggestions       — actionable fixes, ranked by impact
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .resume_model import ResumeData
from .jd_analyzer import JDAnalysis

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------

@dataclass
class ATSSuggestion:
    priority:     str    # "high" | "medium" | "low"
    action:       str    # "add" | "rephrase" | "move"
    keyword:      str
    current_text: str = ""
    suggested:    str = ""

    def __str__(self) -> str:
        return f"[{self.priority.upper()}] {self.action}: '{self.keyword}'"


@dataclass
class ATSReport:
    overall_score:    float                       # 0-100
    keyword_coverage: float                       # 0-100 (% of required keywords found)
    density_score:    float                       # 0-100
    section_score:    float                       # 0-100
    format_score:     float                       # 0-100 (placeholder, always 85+)
    found_keywords:   List[str]                   = field(default_factory=list)
    missing_keywords: List[str]                   = field(default_factory=list)
    suggestions:      List[ATSSuggestion]         = field(default_factory=list)
    keyword_density:  Dict[str, int]              = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"ATS Score: {self.overall_score:.0f}/100",
            f"  Keyword coverage:  {self.keyword_coverage:.0f}%  ({len(self.found_keywords)} found, {len(self.missing_keywords)} missing)",
            f"  Keyword density:   {self.density_score:.0f}/100",
            f"  Section structure: {self.section_score:.0f}/100",
        ]
        if self.missing_keywords:
            lines.append(f"\nMissing keywords: {', '.join(self.missing_keywords[:10])}")
        if self.suggestions:
            lines.append("\nTop suggestions:")
            for s in self.suggestions[:5]:
                lines.append(f"  {s}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ATSOptimizer
# ---------------------------------------------------------------------------

class ATSOptimizer:
    """
    Scores a resume against a JD and generates optimization suggestions.

    Usage:
        optimizer = ATSOptimizer()
        report = optimizer.score(resume_data, jd_analysis)
        print(report.summary())
    """

    # Optimal keyword density range
    DENSITY_MIN = 0.025     # 2.5%
    DENSITY_MAX = 0.055     # 5.5%

    # Required sections for full marks
    REQUIRED_SECTIONS = {"summary", "skills", "experience", "education"}

    def score(self, resume: ResumeData, jd: JDAnalysis) -> ATSReport:
        """Compute full ATS report for resume vs JD."""
        resume_text  = self._extract_resume_text(resume)
        word_count   = len(resume_text.split())

        # 1. Keyword coverage
        found, missing = self._check_keyword_coverage(resume_text, jd)
        coverage = (len(found) / max(len(jd.critical_keywords), 1)) * 100

        # 2. Keyword density
        density_score, kw_density = self._score_density(resume_text, jd, word_count)

        # 3. Section structure
        section_score = self._score_sections(resume)

        # 4. Format (heuristic — we control the PDF builder)
        format_score = 90.0   # our PDFBuilder uses single-column, standard fonts

        # 5. Overall (weighted)
        overall = (
            coverage      * 0.50 +
            density_score * 0.15 +
            section_score * 0.15 +
            format_score  * 0.20
        )
        overall = min(100.0, overall)

        # 6. Suggestions
        suggestions = self._generate_suggestions(missing, jd, resume)

        return ATSReport(
            overall_score    = overall,
            keyword_coverage = coverage,
            density_score    = density_score,
            section_score    = section_score,
            format_score     = format_score,
            found_keywords   = found,
            missing_keywords = missing,
            suggestions      = suggestions,
            keyword_density  = kw_density,
        )

    def inject_missing_keywords(
        self, resume: ResumeData, jd: JDAnalysis, report: ATSReport
    ) -> int:
        """
        Inject missing high-priority keywords into the resume's skills section.
        Called after SectionOptimizer — this is the final keyword cleanup pass.

        Returns number of keywords injected.
        """
        if not report.missing_keywords:
            return 0

        skills_sec = resume.get_section("skills")
        if not skills_sec or not skills_sec.bullets:
            return 0

        # Prioritize: required > nice-to-have > tech_stack
        high_priority = [
            kw for kw in report.missing_keywords
            if kw in jd.required_skills or kw in jd.tech_stack
        ][:5]   # max 5 additions

        if not high_priority:
            return 0

        # Find best bullet to add to (existing Languages/Frameworks line)
        target = None
        for b in skills_sec.bullets:
            if any(k in b.text.lower() for k in ("python", "react", "framework", "language")):
                target = b
                break

        if not target:
            target = skills_sec.bullets[0]

        # Check which are already there (case-insensitive)
        text_lower = target.text.lower()
        to_add     = [kw for kw in high_priority if kw.lower() not in text_lower]

        if not to_add:
            return 0

        new_text = target.text.rstrip(". ") + ", " + ", ".join(to_add)
        target.mark_modified(new_text)
        log.debug("ATS injection: added %s", to_add)
        return len(to_add)

    # ── Internal scorers ─────────────────────────────────────────────────────

    @staticmethod
    def _extract_resume_text(resume: ResumeData) -> str:
        """Flatten all resume text for keyword scanning."""
        parts = [resume.name, resume.tagline]
        for sec in resume.sections:
            parts.append(sec.title)
            if sec.header:
                parts.append(sec.header)
            for b in sec.bullets:
                parts.append(b.text)
        return " ".join(parts)

    @staticmethod
    def _check_keyword_coverage(
        resume_text: str, jd: JDAnalysis
    ) -> Tuple[List[str], List[str]]:
        """
        Check which critical JD keywords are present in the resume.
        Case-insensitive, normalizes plurals (Python == Python, API == APIs).
        """
        text_lower = resume_text.lower()
        found   = []
        missing = []

        for kw in jd.critical_keywords:
            kw_lower  = kw.lower().rstrip("s")   # normalize plural
            text_norm = re.sub(r"s\b", "", text_lower)  # normalize plural in text
            if kw_lower in text_lower or kw_lower in text_norm:
                found.append(kw)
            else:
                missing.append(kw)

        return found, missing

    def _score_density(
        self, resume_text: str, jd: JDAnalysis, word_count: int
    ) -> Tuple[float, Dict[str, int]]:
        """
        Score keyword density.
        Optimal: 2.5-5.5% of resume words are JD keywords.
        """
        kw_count = 0
        kw_freq: Dict[str, int] = {}
        text_lower = resume_text.lower()

        for kw in jd.all_keywords:
            count = text_lower.count(kw.lower())
            if count > 0:
                kw_freq[kw] = count
                kw_count   += count

        if word_count == 0:
            return 50.0, kw_freq

        density = kw_count / word_count

        if density < self.DENSITY_MIN:
            # Below minimum: linear scale from 0 to DENSITY_MIN
            score = (density / self.DENSITY_MIN) * 60.0
        elif density <= self.DENSITY_MAX:
            # Optimal range
            score = 85.0 + (density - self.DENSITY_MIN) / (self.DENSITY_MAX - self.DENSITY_MIN) * 15.0
        else:
            # Above maximum: decreasing penalty (keyword stuffing)
            excess = density - self.DENSITY_MAX
            score  = max(40.0, 100.0 - excess * 500)

        return min(100.0, score), kw_freq

    def _score_sections(self, resume: ResumeData) -> float:
        """Score presence of required sections."""
        present_types = {sec.type for sec in resume.sections}
        hit_count     = len(self.REQUIRED_SECTIONS & present_types)
        return (hit_count / len(self.REQUIRED_SECTIONS)) * 100.0

    @staticmethod
    def _generate_suggestions(
        missing: List[str], jd: JDAnalysis, resume: ResumeData
    ) -> List[ATSSuggestion]:
        """Generate prioritized suggestions for improving ATS score."""
        suggestions = []

        for kw in missing:
            priority = "high" if kw in jd.required_skills else (
                "medium" if kw in jd.tech_stack else "low"
            )
            # Find the best section to add this keyword
            if any(kw.lower() in b.text.lower() for sec in resume.get_sections("experience")
                   for b in sec.bullets):
                action = "rephrase"
                hint   = f"This technology is mentioned in experience — make it more prominent"
            else:
                action = "add"
                hint   = f"Add '{kw}' to your Technical Skills section"

            suggestions.append(ATSSuggestion(
                priority     = priority,
                action       = action,
                keyword      = kw,
                suggested    = hint,
            ))

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda x: priority_order[x.priority])

        return suggestions
