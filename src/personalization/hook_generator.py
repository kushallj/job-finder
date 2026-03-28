"""
hook_generator.py — Genuine connection hook synthesizer.

A "hook" is a 1-2 sentence personalized opener that proves you did real
research — not "I saw you're hiring" but "I noticed your team open-sourced
{X} last month — the {Y} design is exactly the pattern I used at {my_company}".

Hook types (ordered by specificity / strength):
  CONTACT_RESONANCE  — their own code / writing / project  (strongest: 0.9)
  COMPANY_SIGNAL     — recent company news / launch / repo  (strong:    0.75)
  TECH_ALIGNMENT     — shared technology interest           (medium:    0.6)
  ROLE_FIT           — specific JD requirement ↔ my achievement (medium: 0.55)
  CULTURE_FIT        — culture / values alignment           (weak:      0.4)
  GENERIC            — fallback (no data)                   (lowest:    0.1)

Generation strategy:
  Tier 1 — Template rules  (deterministic, instant, always produces a result)
  Tier 2 — LLM polish     (makes it sound more natural; optional)

Tier 1 template rules fire on specific data signals:
  - contact.pinned_repos → CONTACT_RESONANCE
  - contact.blog_posts   → CONTACT_RESONANCE
  - company.recent_repos → COMPANY_SIGNAL
  - company.hn_mentions  → COMPANY_SIGNAL
  - tech overlap (resume ∩ company.tech_stack) → TECH_ALIGNMENT
  - resume metric ↔ jd pain_point → ROLE_FIT
  - culture keyword overlap → CULTURE_FIT
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, TYPE_CHECKING

from .models import CompanyProfile, ContactProfile, Hook, HookType

if TYPE_CHECKING:
    from src.resume_engine.jd_analyzer import JDAnalysis
    from src.resume_engine.resume_model import ResumeData

log = logging.getLogger(__name__)

# Minimum hook strength to include (filters out near-empty templates)
_MIN_STRENGTH = 0.15

# My identity tokens (drawn from resume + used to make hooks first-person)
_MY_COMPANY_NAMES = ["Progfin", "ByteDance", "TikTok"]


class HookGenerator:
    """
    Generates genuine personalized hooks from research profiles + JD + resume.

    Usage:
        generator = HookGenerator(ai_service)
        hooks = generator.generate(
            company_profile, contact_profile, jd_analysis, resume_data
        )
        best = hooks[0]   # highest strength first
    """

    def __init__(self, ai_service=None):
        self._ai = ai_service

    def generate(
        self,
        company:  CompanyProfile,
        contact:  ContactProfile,
        jd:       "JDAnalysis",
        resume:   Optional["ResumeData"] = None,
        max_hooks: int = 3,
    ) -> List[Hook]:
        """
        Generate up to `max_hooks` hooks, ordered by strength descending.
        Always returns at least 1 hook (generic fallback).
        """
        candidates: List[Hook] = []

        # ── Tier 1: contact-specific hooks ────────────────────────────────────
        candidates.extend(self._contact_hooks(contact, company))

        # ── Tier 2: company-specific hooks ────────────────────────────────────
        candidates.extend(self._company_hooks(company))

        # ── Tier 3: tech alignment hooks ──────────────────────────────────────
        candidates.extend(self._tech_hooks(company, contact, jd, resume))

        # ── Tier 4: role fit hooks ─────────────────────────────────────────────
        if resume:
            candidates.extend(self._role_fit_hooks(jd, resume))

        # ── Tier 5: culture fit hooks ─────────────────────────────────────────
        candidates.extend(self._culture_hooks(company, jd))

        # Filter weak hooks, de-duplicate, sort by strength
        seen_texts: set = set()
        unique = []
        for h in sorted(candidates, key=lambda x: x.strength, reverse=True):
            if h.strength < _MIN_STRENGTH:
                continue
            normalized = re.sub(r"\s+", " ", h.text.lower())[:60]
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique.append(h)

        # Guarantee at least one hook
        if not unique:
            unique = [_generic_fallback(company, jd)]

        return unique[:max_hooks]

    # ── Contact resonance hooks ────────────────────────────────────────────────

    def _contact_hooks(
        self, contact: ContactProfile, company: CompanyProfile
    ) -> List[Hook]:
        hooks = []

        # Blog post hook
        if contact.blog_posts:
            title = contact.blog_posts[0]
            hooks.append(Hook(
                type     = HookType.CONTACT_RESONANCE,
                text     = (
                    f"I came across your post \"{_truncate(title, 60)}\" — "
                    f"the approach you described maps closely to a problem I tackled "
                    f"at {_my_recent_company()}."
                ),
                evidence = f"blog: {title}",
                strength = 0.90,
            ))

        # Pinned repo hook
        if contact.pinned_repos:
            repo = contact.pinned_repos[0].split(":")[0].strip()
            desc = contact.pinned_repos[0].split(":", 1)[1].strip() if ":" in contact.pinned_repos[0] else ""
            hooks.append(Hook(
                type     = HookType.CONTACT_RESONANCE,
                text     = (
                    f"Your {repo} project caught my attention{(' — ' + _truncate(desc, 50)) if desc else ''}. "
                    f"I've worked on similar problems in production."
                ),
                evidence = f"pinned_repo: {repo}",
                strength = 0.88,
            ))

        # Recent repo hook (starred/most prominent)
        if contact.recent_repos and not contact.pinned_repos:
            repo_line = contact.recent_repos[0]
            repo_name = repo_line.split(":")[0].strip()
            hooks.append(Hook(
                type     = HookType.CONTACT_RESONANCE,
                text     = (
                    f"I noticed your work on {repo_name} on GitHub — "
                    f"it's the kind of {_infer_domain(contact)} engineering I've been deep in."
                ),
                evidence = f"repo: {repo_name}",
                strength = 0.75,
            ))

        # Bio keyword hook
        if contact.bio and len(contact.bio) > 15:
            hooks.append(Hook(
                type     = HookType.CONTACT_RESONANCE,
                text     = (
                    f"Your background in {_truncate(contact.bio, 60)} "
                    f"resonates — I've been building in that space at {_my_recent_company()}."
                ),
                evidence = f"github_bio: {contact.bio[:40]}",
                strength = 0.55,
            ))

        return hooks

    # ── Company signal hooks ───────────────────────────────────────────────────

    def _company_hooks(self, company: CompanyProfile) -> List[Hook]:
        hooks = []

        # HN story hook (highest signal — the team reads HN)
        if company.hn_mentions:
            story = company.hn_mentions[0]
            hooks.append(Hook(
                type     = HookType.COMPANY_SIGNAL,
                text     = (
                    f"I saw \"{_truncate(story, 70)}\" hit the front page — "
                    f"the problem you're solving is one I've thought a lot about."
                ),
                evidence = f"hn: {story}",
                strength = 0.80,
            ))

        # Recent open-source repo hook
        if company.recent_repos:
            repo = company.recent_repos[0].split(":")[0].strip()
            desc = company.recent_repos[0].split(":", 1)[1].strip() if ":" in company.recent_repos[0] else ""
            hooks.append(Hook(
                type     = HookType.COMPANY_SIGNAL,
                text     = (
                    f"I've been following {company.name}'s open-source work — "
                    f"{repo}{(': ' + _truncate(desc, 50)) if desc else ''} "
                    f"is a pattern I've implemented in production."
                ),
                evidence = f"github_repo: {repo}",
                strength = 0.78,
            ))

        # Growth signal hook
        if company.growth_signals:
            signal = _truncate(company.growth_signals[0], 80)
            hooks.append(Hook(
                type     = HookType.COMPANY_SIGNAL,
                text     = (
                    f"Congrats on {signal} — it's clear {company.name} is at "
                    f"an exciting inflection point, which is exactly the stage "
                    f"I've thrived in before."
                ),
                evidence = f"growth: {signal}",
                strength = 0.65,
            ))

        # Blog headline hook
        if company.recent_news:
            headline = company.recent_news[0]
            hooks.append(Hook(
                type     = HookType.COMPANY_SIGNAL,
                text     = (
                    f"Your post \"{_truncate(headline, 70)}\" was a great read — "
                    f"it's aligned with the technical direction I've been pursuing."
                ),
                evidence = f"blog: {headline}",
                strength = 0.60,
            ))

        return hooks

    # ── Tech alignment hooks ───────────────────────────────────────────────────

    def _tech_hooks(
        self,
        company:  CompanyProfile,
        contact:  ContactProfile,
        jd:       "JDAnalysis",
        resume:   Optional["ResumeData"],
    ) -> List[Hook]:
        hooks = []

        # Find overlap between their tech and my skills
        my_skills = set(jd.required_skills + jd.tech_stack)
        their_tech = set(company.tech_stack + contact.languages)
        overlap    = list(my_skills & {t.lower() for t in their_tech})

        if overlap:
            skill = overlap[0].title()
            hooks.append(Hook(
                type     = HookType.TECH_ALIGNMENT,
                text     = (
                    f"Seeing {skill} in your stack caught my eye — "
                    f"I've been working with it in production at scale at {_my_recent_company()}."
                ),
                evidence = f"tech_overlap: {skill}",
                strength = 0.60,
            ))

        # Contact's language vs my stack
        if contact.languages and resume:
            lang = contact.languages[0]
            hooks.append(Hook(
                type     = HookType.TECH_ALIGNMENT,
                text     = (
                    f"{lang} is my primary language too — "
                    f"it'd be great to compare notes on how you're using it at {company.name}."
                ),
                evidence = f"language: {lang}",
                strength = 0.50,
            ))

        return hooks

    # ── Role fit hooks ─────────────────────────────────────────────────────────

    def _role_fit_hooks(
        self, jd: "JDAnalysis", resume: "ResumeData"
    ) -> List[Hook]:
        hooks = []

        # Find a bullet with a metric that aligns with a JD pain point
        for pain in jd.pain_points[:3]:
            for sec in resume.get_sections("experience"):
                for b in sec.bullets:
                    if b.has_metric and any(
                        w in b.text.lower()
                        for w in pain.lower().split()
                        if len(w) > 4
                    ):
                        achievement = _truncate(b.text, 90)
                        hooks.append(Hook(
                            type     = HookType.ROLE_FIT,
                            text     = (
                                f"Your JD mentions {_truncate(pain, 40)} — "
                                f"I've directly tackled this: {achievement}."
                            ),
                            evidence = f"pain_point: {pain} | bullet: {b.text[:40]}",
                            strength = 0.55,
                        ))
                        break

        # Top required skill → my strongest relevant bullet
        if jd.required_skills:
            top_skill = jd.required_skills[0]
            for sec in resume.get_sections("experience"):
                for b in sec.bullets:
                    if top_skill.lower() in b.text.lower() and b.has_metric:
                        hooks.append(Hook(
                            type     = HookType.ROLE_FIT,
                            text     = (
                                f"The role calls for {top_skill} expertise — "
                                f"here's a concrete example: {_truncate(b.text, 80)}."
                            ),
                            evidence = f"required_skill: {top_skill}",
                            strength = 0.52,
                        ))
                        break

        return hooks

    # ── Culture fit hooks ──────────────────────────────────────────────────────

    def _culture_hooks(
        self, company: CompanyProfile, jd: "JDAnalysis"
    ) -> List[Hook]:
        hooks = []
        culture_words = company.culture_keywords + jd.culture_keywords

        if "open source" in " ".join(culture_words).lower():
            hooks.append(Hook(
                type     = HookType.CULTURE_FIT,
                text     = (
                    f"The open-source culture at {company.name} stands out — "
                    f"it aligns with how I prefer to work and learn."
                ),
                evidence = "culture: open_source",
                strength = 0.40,
            ))
        elif "ownership" in " ".join(culture_words).lower():
            hooks.append(Hook(
                type     = HookType.CULTURE_FIT,
                text     = (
                    f"The emphasis on ownership at {company.name} resonates — "
                    f"I thrive in environments where engineers drive decisions end-to-end."
                ),
                evidence = "culture: ownership",
                strength = 0.38,
            ))

        return hooks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generic_fallback(company: CompanyProfile, jd: "JDAnalysis") -> Hook:
    role = getattr(jd, "role_focus", "engineering")
    return Hook(
        type     = HookType.GENERIC,
        text     = (
            f"I've been following {company.name}'s work and the {role} "
            f"challenges you're tackling align closely with my experience."
        ),
        evidence = "generic",
        strength = 0.10,
    )


def _my_recent_company() -> str:
    return _MY_COMPANY_NAMES[0]   # Progfin (most recent)


def _truncate(text: str, n: int) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n-1].rstrip() + "…"


def _infer_domain(contact: ContactProfile) -> str:
    """Infer a short domain description from contact's technical keywords."""
    kws = contact.technical_keywords
    if any(k in kws for k in ("ML", "AI", "LLM", "transformer")):
        return "ML/AI"
    if any(k in kws for k in ("distributed", "infra", "platform", "Kubernetes")):
        return "platform/infra"
    if any(k in kws for k in ("compiler", "parser", "systems")):
        return "systems"
    if any(k in kws for k in ("React", "frontend")):
        return "frontend"
    return "backend"
