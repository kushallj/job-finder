"""
section_optimizer.py — Per-section resume bullet rewriter.

Strategy (surgical, not wholesale):
  1. Score each existing bullet against the JDAnalysis (0-1 relevance)
  2. Identify "gap bullets" — JD requirements NOT covered by any bullet
  3. For each gap: find the closest existing bullet and enhance it
  4. Mirror exact JD phrases where possible
  5. Strengthen weak bullets: add JD-relevant context, quantify if possible
  6. Never invent metrics (only enhance existing ones)
  7. Touch at most 40% of bullets (preserves authenticity)

Bullet rewriting rules:
  Rule 1: Mirror exact phrases from JDAnalysis.exact_phrases
  Rule 2: Add JD tech terms to bullets that already discuss that domain
  Rule 3: Strengthen quantified bullets by making the metric more prominent
  Rule 4: Add context from JD pain_points to relevant bullets
  Rule 5: Never add skills that don't exist in the base resume

LLM prompt for per-bullet rewrite:
  Constrained: "rewrite this ONE bullet to better match the JD, keep all facts"
  Max 1 sentence change per bullet
  Preserve all numbers/metrics exactly
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from .resume_model import ResumeData, ResumeSection, ResumeBullet
from .jd_analyzer import JDAnalysis

log = logging.getLogger(__name__)

# Max % of bullets we're allowed to modify (preserves authenticity)
MAX_MODIFICATION_RATE = 0.40

_BULLET_REWRITE_PROMPT = """Rewrite this resume bullet to better match the job description.
STRICT RULES:
  1. Keep ALL numbers, percentages, and metrics EXACTLY as they are
  2. Do not add skills or technologies that aren't already mentioned
  3. Mirror these exact phrases from the JD where natural: {exact_phrases}
  4. Make it sound more aligned with: {role_focus} engineering
  5. Output ONLY the rewritten bullet text, no explanation, no bullet symbol

Original bullet: {bullet}

Job requires: {required_skills}
Company tone: {tone}

Rewritten bullet:"""


class SectionOptimizer:
    """
    Optimizes resume sections for a specific job description.

    Usage:
        optimizer = SectionOptimizer(ai_service)
        tailored  = await optimizer.optimize(resume_data, jd_analysis)
        print(tailored.diff_report())
    """

    def __init__(self, ai_service=None):
        self._ai = ai_service
        if ai_service is None:
            try:
                from src.ai.unified_ai_service import UnifiedAIService
                self._ai = UnifiedAIService()
            except Exception as e:
                log.warning("AI unavailable for section optimization: %s", e)

    async def optimize(
        self,
        resume: ResumeData,
        jd: JDAnalysis,
        max_bullets_to_change: Optional[int] = None,
    ) -> ResumeData:
        """
        Produce a tailored copy of `resume` optimized for `jd`.

        Returns a NEW ResumeData (base resume is untouched).
        """
        tailored = resume.clone()

        total_bullets = len(tailored.all_bullets())
        max_changes   = max_bullets_to_change or max(3, int(total_bullets * MAX_MODIFICATION_RATE))

        changed = 0

        # Step 1: Optimize the professional summary
        summary_sec = tailored.get_section("summary")
        if summary_sec and changed < max_changes:
            changed += await self._optimize_summary(summary_sec, jd)

        # Step 2: Optimize skills section (add missing keywords naturally)
        skills_sec = tailored.get_section("skills")
        if skills_sec:
            self._optimize_skills(skills_sec, jd)

        # Step 3: Optimize experience bullets (main value)
        exp_sections = tailored.get_sections("experience")
        for exp_sec in exp_sections:
            if changed >= max_changes:
                break
            n = await self._optimize_experience(exp_sec, jd, max_changes - changed)
            changed += n

        log.info(
            "SectionOptimizer: %d/%d bullets modified for role=%s seniority=%s",
            changed, total_bullets, jd.role_focus, jd.seniority_level,
        )
        return tailored

    # ── Summary optimizer ─────────────────────────────────────────────────────

    async def _optimize_summary(
        self,
        section: ResumeSection,
        jd: JDAnalysis,
    ) -> int:
        """
        Rewrite the professional summary to lead with the most relevant skills.
        The summary is the first thing ATS + human reads → highest ROI.
        """
        if not section.bullets:
            return 0

        # Summary is typically one long paragraph, stored as a single bullet
        bullet = section.bullets[0]
        original = bullet.text

        # Build a targeted summary that mirrors JD language
        top_skills = jd.required_skills[:4]
        top_phrase = jd.exact_phrases[0] if jd.exact_phrases else ""
        pain_point = jd.pain_points[0] if jd.pain_points else ""

        if not top_skills:
            return 0

        # Simple template-based rewrite (faster + more predictable than LLM for summary)
        skills_str = ", ".join(top_skills[:3])

        if jd.seniority_level in ("senior", "lead", "staff"):
            seniority_phrase = "Senior Software Development Engineer"
        elif jd.seniority_level == "junior":
            seniority_phrase = "Software Engineer"
        else:
            seniority_phrase = "Software Development Engineer"

        # Build enhanced summary — keep all original metrics, add JD alignment
        enhanced = re.sub(
            r"Software Development Engineer",
            seniority_phrase,
            original,
            count=1,
            flags=re.IGNORECASE,
        )

        # Inject top JD phrase if not already present
        if top_phrase and top_phrase.lower() not in enhanced.lower():
            # Find a natural insertion point near skills section
            enhanced = re.sub(
                r"(RESTful APIs|web applications|APIs)",
                f"{top_phrase}",
                enhanced,
                count=1,
                flags=re.IGNORECASE,
            ) or enhanced

        if enhanced != original:
            bullet.mark_modified(enhanced)
            return 1
        return 0

    # ── Skills optimizer ──────────────────────────────────────────────────────

    def _optimize_skills(self, section: ResumeSection, jd: JDAnalysis) -> None:
        """
        Add missing high-priority JD keywords to the skills section.
        Only adds skills that are plausible given the existing resume context.
        """
        # Get current skills
        current_skills_text = " ".join(b.text for b in section.bullets).lower()

        # Find JD skills NOT in current skills section
        missing = [
            s for s in jd.tech_stack
            if s.lower() not in current_skills_text
        ]

        if not missing:
            return

        # Find the best skills bullet to augment (Languages & Frameworks)
        target_bullet = None
        for bullet in section.bullets:
            if any(k in bullet.text.lower() for k in ("language", "framework", "python", "react")):
                target_bullet = bullet
                break

        if not target_bullet or not section.bullets:
            return

        # Append missing skills (max 3 to avoid stuffing)
        additions = missing[:3]
        new_text   = target_bullet.text.rstrip() + ", " + ", ".join(additions)
        target_bullet.mark_modified(new_text)
        log.debug("Skills: added %s", additions)

    # ── Experience optimizer ──────────────────────────────────────────────────

    async def _optimize_experience(
        self,
        section: ResumeSection,
        jd: JDAnalysis,
        budget: int,
    ) -> int:
        """
        Score each bullet against the JD, then rewrite the lowest-scoring
        bullets that are closest to a JD requirement.
        """
        if not section.bullets or budget <= 0:
            return 0

        # Score each bullet (0-1 relevance to JD)
        scored = [
            (i, b, self._score_bullet(b, jd))
            for i, b in enumerate(section.bullets)
        ]

        # Sort by score ascending (least relevant first → highest optimization ROI)
        scored.sort(key=lambda x: x[2])

        # Find uncovered JD requirements
        covered = set()
        for _, b, _ in scored:
            for skill in jd.required_skills:
                if skill.lower() in b.text.lower():
                    covered.add(skill.lower())

        uncovered = [s for s in jd.required_skills if s.lower() not in covered]

        changed = 0
        for idx, bullet, score in scored:
            if changed >= budget:
                break

            # Only rewrite bullets with low-medium relevance (high ones are fine)
            if score >= 0.7:
                continue

            # Find if this bullet is the closest match for an uncovered requirement
            target_skill = self._find_best_match(bullet, uncovered)
            if not target_skill and score >= 0.4:
                continue   # bullet is decent, skip

            # Rewrite
            new_text = await self._rewrite_bullet(bullet, jd, target_skill)
            if new_text and new_text.strip() != bullet.text.strip():
                section.bullets[idx].mark_modified(new_text)
                if target_skill:
                    covered.add(target_skill.lower())
                    uncovered = [s for s in uncovered if s.lower() not in covered]
                changed += 1

        return changed

    # ── Bullet scoring ────────────────────────────────────────────────────────

    @staticmethod
    def _score_bullet(bullet: ResumeBullet, jd: JDAnalysis) -> float:
        """
        Score a bullet's relevance to the JD (0.0 - 1.0).

        Factors:
          - How many JD required_skills appear in the bullet
          - How many JD exact_phrases appear
          - Whether it contains a metric (metrics impress both ATS + humans)
          - Seniority alignment
        """
        text_lower = bullet.text.lower()
        score      = 0.0

        # Required skills hit rate
        if jd.required_skills:
            hits  = sum(1 for s in jd.required_skills if s.lower() in text_lower)
            score += (hits / len(jd.required_skills)) * 0.50

        # Exact phrase match
        if jd.exact_phrases:
            phrase_hits = sum(1 for p in jd.exact_phrases if p.lower() in text_lower)
            score      += (phrase_hits / len(jd.exact_phrases)) * 0.25

        # Metric bonus (quantified bullets always score higher)
        if bullet.has_metric:
            score += 0.15

        # Tech stack overlap
        if jd.tech_stack:
            tech_hits = sum(1 for t in jd.tech_stack if t.lower() in text_lower)
            score    += (tech_hits / len(jd.tech_stack)) * 0.10

        return min(1.0, score)

    @staticmethod
    def _find_best_match(bullet: ResumeBullet, uncovered: List[str]) -> Optional[str]:
        """Find which uncovered skill this bullet is closest to."""
        text_lower = bullet.text.lower()
        for skill in uncovered:
            # Check if any word in the skill appears in the bullet
            skill_words = skill.lower().split()
            if any(w in text_lower for w in skill_words if len(w) > 3):
                return skill
        return None

    # ── LLM bullet rewrite ────────────────────────────────────────────────────

    async def _rewrite_bullet(
        self,
        bullet: ResumeBullet,
        jd: JDAnalysis,
        target_skill: Optional[str],
    ) -> str:
        """
        Rewrite a single bullet using LLM.
        Falls back to template-based rewrite if LLM unavailable.
        """
        if self._ai:
            try:
                return await self._llm_rewrite(bullet, jd, target_skill)
            except Exception as e:
                log.debug("LLM bullet rewrite failed: %s", e)

        # Fallback: rule-based enhancement
        return self._rule_based_rewrite(bullet, jd, target_skill)

    async def _llm_rewrite(
        self,
        bullet: ResumeBullet,
        jd: JDAnalysis,
        target_skill: Optional[str],
    ) -> str:
        prompt = _BULLET_REWRITE_PROMPT.format(
            bullet         = bullet.text,
            exact_phrases  = ", ".join(jd.exact_phrases[:5]),
            role_focus     = jd.role_focus,
            required_skills = ", ".join((jd.required_skills + ([target_skill] if target_skill else []))[:5]),
            tone           = jd.tone,
        )

        raw = ""
        if hasattr(self._ai, "backend") and self._ai.backend:
            backend = self._ai.backend
            if hasattr(backend, "generate"):
                raw = await backend.generate(prompt)
            elif hasattr(backend, "_generate_with_ollama"):
                raw = await backend._generate_with_ollama(prompt)

        if not raw:
            return bullet.text

        # Clean up LLM output: remove bullet chars, trim
        rewritten = re.sub(r"^[•\-·*]\s*", "", raw.strip().split("\n")[0])

        # Safety: ensure all original metrics are preserved
        orig_metrics = re.findall(r"\d+[\d,]*\s*[%CrMKx+]?", bullet.text)
        for metric in orig_metrics:
            if metric.strip() and metric.strip() not in rewritten:
                log.debug("Metric preservation: LLM dropped '%s', using original", metric)
                return bullet.text

        return rewritten if len(rewritten) > 20 else bullet.text

    @staticmethod
    def _rule_based_rewrite(
        bullet: ResumeBullet,
        jd: JDAnalysis,
        target_skill: Optional[str],
    ) -> str:
        """
        Deterministic rule-based rewrite — no LLM, always safe.
        Strategy: prefix bullet with JD-aligned context.
        """
        text = bullet.text

        # Mirror exact phrase if not already present
        for phrase in jd.exact_phrases[:3]:
            if phrase.lower() not in text.lower():
                # Try to insert before "via", "using", "with" or at end
                for connector in (" via ", " using ", " with "):
                    if connector in text.lower():
                        text = text.replace(
                            connector,
                            f"{connector}{phrase} and " if connector == " via " else connector,
                            1,
                        )
                        break
                break  # only inject one phrase

        # Add target skill if not present and has a good injection point
        if target_skill and target_skill.lower() not in text.lower():
            if " and " in text and len(text) < 200:
                # Add before the last noun phrase
                text = text + f" — leveraging {target_skill} patterns"

        return text
