"""
email_composer.py — Hyper-personalized cold email + cover letter composer.

Cold email structure (optimal for response rates):
  ┌─────────────────────────────────────────────────────┐
  │  Subject: [specific, personalized, ≤8 words]        │
  ├─────────────────────────────────────────────────────┤
  │  Hi {first_name},                                   │
  │                                                     │
  │  [Hook — 1-2 sentences, proves genuine research]    │
  │                                                     │
  │  [Who I am + single strongest achievement]          │
  │                                                     │
  │  [Why this specific company/role — 1 sentence]      │
  │                                                     │
  │  [CTA — clear, low-friction, 1 sentence]            │
  │                                                     │
  │  Best,                                              │
  │  {my_name}                                          │
  └─────────────────────────────────────────────────────┘

Target: < 150 words (data shows 75-100 word emails get highest reply rates)
Subject: < 8 words, highly specific (never "Opportunity" or "Quick question")

Subject line templates (fed into A/B manager):
  - CONTACT: "{their_project} + {my_work}"           → most personalized
  - COMPANY: "Re: {company_signal}"                  → timely
  - SKILL:   "{shared_skill} engineer → {role_title}" → role-specific
  - HOOK:    "{one-word-hook} → {role}"              → curiosity
  - GENERIC: "{my_name} — {role} at {company}"       → fallback

Cover letter:
  Same structure but 250-300 words with a paragraph on role-fit details.
  ATS-readable: no tables, standard ASCII, section structure.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, TYPE_CHECKING

from .models import CompanyProfile, ContactProfile, Hook, HookType, PersonalizedEmail

if TYPE_CHECKING:
    from src.resume_engine.jd_analyzer import JDAnalysis
    from src.resume_engine.resume_model import ResumeData

log = logging.getLogger(__name__)

# Sender identity (pulled from config; fallback to placeholder)
try:
    from src.config import settings as _cfg
    _MY_NAME     = getattr(_cfg, "sender_name",  "Kushall Jain")
    _MY_EMAIL    = getattr(_cfg, "sender_email", "")
    _MY_LINKEDIN = getattr(_cfg, "linkedin_url", "linkedin.com/in/kushall-jain")
except Exception:
    _MY_NAME     = "Kushall Jain"
    _MY_EMAIL    = ""
    _MY_LINKEDIN = "linkedin.com/in/kushall-jain"

_MY_TAGLINE = (
    "Software Engineer — Python/FastAPI/React, 3+ yrs fintech & consumer scale"
)


class EmailComposer:
    """
    Composes cold emails and cover letters from hooks + context.

    Usage:
        composer = EmailComposer(ai_service)
        email = composer.compose(hooks, company, contact, jd, resume)
    """

    def __init__(self, ai_service=None):
        self._ai = ai_service

    # ── Public API ─────────────────────────────────────────────────────────────

    def compose(
        self,
        hooks:    List[Hook],
        company:  CompanyProfile,
        contact:  ContactProfile,
        jd:       "JDAnalysis",
        resume:   Optional["ResumeData"] = None,
    ) -> PersonalizedEmail:
        """
        Compose a personalized cold email.
        Uses template composition (instant, deterministic) + optional LLM polish.
        """
        first_name  = _first_name(contact.name)
        best_hook   = hooks[0] if hooks else None
        achievement = _best_achievement(resume, jd) if resume else ""
        role_title  = getattr(jd, "role_focus", "Software Engineer").title()

        # ── Body ──────────────────────────────────────────────────────────────
        body = self._compose_body(
            first_name, best_hook, achievement, company, jd, role_title
        )

        # ── Subjects (A/B pool) ───────────────────────────────────────────────
        subjects = self._compose_subjects(hooks, company, contact, jd, role_title)

        # ── Personalization score ─────────────────────────────────────────────
        score = self._compute_score(hooks, company, contact)

        email = PersonalizedEmail(
            subject               = subjects[0],
            body                  = body,
            hooks_used            = hooks,
            personalization_score = score,
            word_count            = len(body.split()),
            subject_variants      = subjects,
        )

        # Optional LLM polish (only if score < 60 — template hooks need more work)
        if self._ai and score < 60:
            try:
                import asyncio
                polished = asyncio.get_event_loop().run_until_complete(
                    self._llm_polish(email, company, contact, jd)
                )
                if polished:
                    return polished
            except Exception as exc:
                log.debug("LLM email polish failed: %s", exc)

        return email

    def compose_cover_letter(
        self,
        hooks:   List[Hook],
        company: CompanyProfile,
        contact: ContactProfile,
        jd:      "JDAnalysis",
        resume:  Optional["ResumeData"] = None,
    ) -> str:
        """
        Compose a 250-300 word ATS-readable cover letter.
        """
        role_title  = getattr(jd, "role_focus", "Software Engineer").title()
        achievement = _best_achievement(resume, jd) if resume else ""
        best_hook   = hooks[0].text if hooks else ""
        top_skills  = ", ".join(getattr(jd, "required_skills", [])[:3])
        pain_point  = getattr(jd, "pain_points", [""])[0]

        paragraphs = []

        # Para 1: Opener + hook
        opener = (
            f"I'm writing to express my interest in the {role_title} role at {company.name}. "
            f"{best_hook}" if best_hook else
            f"I'm writing to express my interest in the {role_title} role at {company.name}. "
            f"Your team's work in {', '.join(company.tech_stack[:2]) or 'this space'} aligns "
            f"closely with my background."
        )
        paragraphs.append(opener)

        # Para 2: Strongest achievement + skills
        if achievement:
            para2 = (
                f"In my recent role, {achievement}. "
                f"I bring hands-on experience with {top_skills or 'the core stack you use'}, "
                f"having built and maintained production systems serving real users at scale."
            )
        else:
            para2 = (
                f"I bring 3+ years of experience building production-grade systems in Python, "
                f"FastAPI, and React — covering backend APIs, async pipelines, and data-heavy "
                f"applications. My most recent work at Progfin touched fintech compliance "
                f"infra and real-time data pipelines."
            )
        paragraphs.append(para2)

        # Para 3: Role-specific fit
        if pain_point:
            para3 = (
                f"The challenge of {_truncate(pain_point, 80)} is one I've navigated directly. "
                f"I'd be excited to bring that experience to {company.name} and grow within "
                f"the scope this role offers."
            )
        else:
            para3 = (
                f"What draws me to {company.name} specifically is "
                f"{self._why_this_company(company, jd)}. "
                f"I believe my technical depth and drive to ship meaningful work make me "
                f"a strong fit for this role."
            )
        paragraphs.append(para3)

        # Para 4: CTA
        cta = (
            f"I'd love to discuss how my background maps to what your team needs. "
            f"My resume and portfolio: {_MY_LINKEDIN}."
        )
        paragraphs.append(cta)

        body = "\n\n".join(paragraphs)
        sign = f"\nBest regards,\n{_MY_NAME}"
        return body + sign

    # ── Email body builder ─────────────────────────────────────────────────────

    def _compose_body(
        self,
        first_name:  str,
        hook:        Optional[Hook],
        achievement: str,
        company:     CompanyProfile,
        jd:          "JDAnalysis",
        role_title:  str,
    ) -> str:
        role_title_str = role_title or "Software Engineer"
        lines = [f"Hi {first_name},", ""]

        # Line 1: Hook (1-2 sentences)
        if hook and hook.type != HookType.GENERIC:
            lines.append(hook.text)
        else:
            lines.append(
                f"I've been following {company.name}'s engineering work "
                f"and the {role_title_str} role caught my attention."
            )
        lines.append("")

        # Line 2: Who I am + achievement
        if achievement:
            lines.append(
                f"I'm a software engineer with 3+ years in Python/FastAPI/React. "
                f"Most recently: {_truncate(achievement, 80)}."
            )
        else:
            lines.append(
                f"I'm a software engineer with 3+ years building production systems "
                f"in Python, FastAPI, and React — most recently at Progfin (fintech)."
            )
        lines.append("")

        # Line 3: Why this company
        lines.append(self._why_this_company(company, jd))
        lines.append("")

        # Line 4: CTA
        lines.append(
            "Would a 20-minute call make sense? Happy to share more or send over work samples."
        )
        lines.append("")

        lines.append("Best,")
        lines.append(_MY_NAME)
        if _MY_LINKEDIN:
            lines.append(_MY_LINKEDIN)

        return "\n".join(lines)

    def _why_this_company(self, company: CompanyProfile, jd: "JDAnalysis") -> str:
        if company.recent_repos:
            repo = company.recent_repos[0].split(":")[0].strip()
            return f"The open-source work (especially {repo}) and the technical depth of this role are exactly what I'm looking for."
        if company.tech_stack:
            tech = company.tech_stack[0]
            return f"The tech stack (particularly {tech}) and the scale at {company.name} are a strong match for where I want to grow."
        if jd.pain_points:
            return f"The challenges around {_truncate(jd.pain_points[0], 60)} are a space I'm excited to contribute to."
        return f"The kind of engineering problems {company.name} is tackling are exactly what I want to be working on next."

    # ── Subject line builder ───────────────────────────────────────────────────

    def _compose_subjects(
        self,
        hooks:      List[Hook],
        company:    CompanyProfile,
        contact:    ContactProfile,
        jd:         "JDAnalysis",
        role_title: str,
    ) -> List[str]:
        subjects = []

        # S1: Contact resonance subject
        for h in hooks:
            if h.type == HookType.CONTACT_RESONANCE and "repo:" in h.evidence:
                repo = h.evidence.split("repo:")[-1].strip()[:20]
                subjects.append(f"{repo} + {role_title} @ {company.name}")
                break
            if h.type == HookType.CONTACT_RESONANCE and "blog:" in h.evidence:
                blog_kw = h.evidence.split("blog:")[-1].strip().split()[0][:15]
                subjects.append(f"Your post on {blog_kw} — {role_title} interest")
                break

        # S2: Company signal subject
        for h in hooks:
            if h.type == HookType.COMPANY_SIGNAL and "hn:" in h.evidence:
                subjects.append(f"Re: {_truncate(h.evidence.split('hn:')[-1].strip(), 45)}")
                break
            if h.type == HookType.COMPANY_SIGNAL and "github_repo:" in h.evidence:
                repo = h.evidence.split("github_repo:")[-1].strip()[:25]
                subjects.append(f"{repo} → {role_title} engineer")
                break

        # S3: Tech alignment subject
        for h in hooks:
            if h.type == HookType.TECH_ALIGNMENT and "tech_overlap:" in h.evidence:
                skill = h.evidence.split("tech_overlap:")[-1].strip()[:15]
                subjects.append(f"{skill} engineer → {company.name} {role_title}")
                break

        # S4: Role fit subject
        if jd.required_skills:
            subjects.append(f"{jd.required_skills[0]} + {role_title} — {_MY_NAME}")

        # S5: Generic fallback (always present)
        subjects.append(f"{_MY_NAME} — {role_title} at {company.name}")

        return list(dict.fromkeys(subjects))[:5]   # dedup, max 5

    # ── Personalization score ──────────────────────────────────────────────────

    @staticmethod
    def _compute_score(
        hooks: List[Hook], company: CompanyProfile, contact: ContactProfile
    ) -> float:
        score = 0.0

        # Contact-specific research (max 40 pts)
        if contact.is_rich:
            score += 40
        elif contact.github_username:
            score += 20

        # Company-specific research (max 30 pts)
        if company.is_rich:
            score += 30
        elif company.tech_stack:
            score += 15

        # Hook quality (max 20 pts)
        if hooks:
            best_strength = max(h.strength for h in hooks)
            score += best_strength * 20

        # Email length compliance bonus (max 10 pts)
        score += 10   # composer always targets < 150 words

        return min(100.0, score)

    # ── LLM polish ────────────────────────────────────────────────────────────

    async def _llm_polish(
        self,
        email:   PersonalizedEmail,
        company: CompanyProfile,
        contact: ContactProfile,
        jd:      "JDAnalysis",
    ) -> Optional[PersonalizedEmail]:
        """
        Ask LLM to make the email sound more natural.
        Constraints: keep all facts, keep ≤ 150 words, don't add false claims.
        """
        prompt = (
            f"Polish this cold email to sound more natural and genuine. "
            f"RULES: keep ALL facts exactly, stay ≤ 150 words, no fluff, "
            f"no fake claims. Output ONLY the email body.\n\n"
            f"Original:\n{email.body}"
        )
        try:
            backend = getattr(self._ai, "backend", None)
            if backend and hasattr(backend, "generate"):
                polished_body = await backend.generate(prompt)
                if polished_body and len(polished_body.split()) <= 180:
                    return PersonalizedEmail(
                        subject               = email.subject,
                        body                  = polished_body.strip(),
                        hooks_used            = email.hooks_used,
                        personalization_score = email.personalization_score,
                        word_count            = len(polished_body.split()),
                        subject_variants      = email.subject_variants,
                    )
        except Exception as exc:
            log.debug("LLM polish: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_name(full_name: str) -> str:
    return full_name.strip().split()[0] if full_name.strip() else "there"


def _truncate(text: str, n: int) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n-1].rstrip() + "…"


def _best_achievement(resume: "ResumeData", jd: "JDAnalysis") -> str:
    """Find the single most impactful achievement bullet aligned with the JD."""
    best_bullet = None
    best_score  = -1.0

    for sec in resume.get_sections("experience"):
        for b in sec.bullets:
            if not b.has_metric:
                continue
            score = sum(1 for s in jd.required_skills if s.lower() in b.text.lower())
            if score > best_score:
                best_score  = score
                best_bullet = b.text

    return best_bullet or ""
