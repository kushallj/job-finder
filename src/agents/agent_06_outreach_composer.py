"""
agent_06_outreach_composer.py — Signal-Aware Outreach Composer Agent.

STRATEGY
--------
The strongest hook type in src/personalization/hook_generator.py is
COMPANY_SIGNAL ("recent company news / launch / repo"). This agent's whole
job is to make sure that hook is never generic — it feeds the *exact*
funding/IPO/leadership signal from config/target_companies.yml (refreshed
by agent_01_signal_scout.py) straight into CompanyProfile.growth_signals,
so the generated email opens with something like:

    "Saw Fibe just filed its DRHP for a ~₹750 Cr IPO raise — impact lending
    in renewable energy is exactly the fintech+cleantech overlap I've
    worked across..."

instead of a generic "I saw you're hiring" opener.

It wraps the existing, already-sophisticated HookGenerator + EmailComposer
rather than reimplementing them. It only adds: signal-seeded CompanyProfile
construction, JD/ResumeData construction from config/profile.yml + the
matched role, and a template-only fallback path if the full personalization
stack (or an AI provider) isn't available.

DAG node contract:
    Input:  AgentContext, company: str, role_title: str, jd_text: str = "",
            contact_name: str = "Hiring Manager"
    Output: AgentResult.data = {"subject": str, "body": str, "hooks_used": [...], "used_full_stack": bool}
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from .base import AgentContext, AgentResult, BaseAgent

try:
    from src.personalization.models import CompanyProfile, ContactProfile
    from src.personalization.hook_generator import HookGenerator
    from src.personalization.email_composer import EmailComposer
    from src.resume_engine.jd_analyzer import JDAnalysis
    from src.resume_engine.resume_model import ResumeData
    _STACK_AVAILABLE = True
except Exception:  # noqa: BLE001
    _STACK_AVAILABLE = False


class OutreachComposerAgent(BaseAgent):
    name = "outreach_composer"

    def run(self, company: str, role_title: str, jd_text: str = "",
            contact_name: str = "Hiring Manager") -> AgentResult:
        return self._timed(self._run, company, role_title, jd_text, contact_name)

    def _run(self, company: str, role_title: str, jd_text: str, contact_name: str) -> AgentResult:
        if _STACK_AVAILABLE:
            try:
                return self._compose_full_stack(company, role_title, jd_text, contact_name)
            except Exception:  # noqa: BLE001
                self.log.warning("Full personalization stack failed, falling back to template", exc_info=True)
        return self._compose_template(company, role_title, jd_text, contact_name)

    # -- Tier 1: real integration with HookGenerator + EmailComposer -----

    def _compose_full_stack(self, company: str, role_title: str, jd_text: str, contact_name: str) -> AgentResult:
        company_cfg = self.context.company(company) or {}
        signals = [s.get("detail", "") for s in company_cfg.get("signals", [])]

        company_profile = CompanyProfile(
            domain=company_cfg.get("domain", ""),
            name=company,
            tagline=company_cfg.get("industry", ""),
            growth_signals=signals,
            recent_news=signals,
        )
        contact_profile = ContactProfile(name=contact_name)

        jd = JDAnalysis(
            required_skills=self._lead_with_skills(),
            tech_stack=self._lead_with_skills(),
            role_focus="backend" if "backend" in role_title.lower() else "fullstack",
            company_name=company,
        )
        resume_data = self._build_resume_data()

        hooks = HookGenerator().generate(company_profile, contact_profile, jd, resume_data)

        composer = EmailComposer()
        try:
            email = asyncio.run(composer.compose(hooks, company_profile, contact_profile, jd, resume_data))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            email = loop.run_until_complete(
                composer.compose(hooks, company_profile, contact_profile, jd, resume_data)
            )

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Composed signal-seeded outreach for {company} ({role_title}) "
                    f"using {len(hooks)} hooks, personalization score {getattr(email, 'personalization_score', '?')}.",
            data={
                "subject": email.subject,
                "body": email.body,
                "subject_variants": getattr(email, "subject_variants", [email.subject]),
                "hooks_used": [getattr(h, "text", str(h)) for h in hooks],
                "used_full_stack": True,
            },
        )

    # -- Tier 2: deterministic template fallback (always works) ----------

    def _compose_template(self, company: str, role_title: str, jd_text: str, contact_name: str) -> AgentResult:
        profile = self.context.profile
        narrative = profile.get("narrative", {})
        company_cfg = self.context.company(company) or {}
        signals = company_cfg.get("signals", [])
        hook = signals[0]["detail"] if signals else f"{company}'s recent growth"

        proof_points = narrative.get("proof_points_by_theme", {})
        jd_l = jd_text.lower()
        proof = (
            proof_points.get("security") if any(w in jd_l for w in ["security", "auth", "access"])
            else proof_points.get("performance") if any(w in jd_l for w in ["performance", "scale", "latency"])
            else proof_points.get("ownership")
        ) or next(iter(proof_points.values()), "")

        subject = f"{role_title} — {hook[:40]}"
        body = (
            f"Hi {contact_name},\n\n"
            f"Saw that {hook.lower()}. {narrative.get('one_liner', '')}\n\n"
            f"{proof}\n\n"
            f"Would love to talk about the {role_title} role at {company} if there's a fit.\n\n"
            f"Best,\n{profile.get('candidate', {}).get('name', '')}"
        )

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Composed template-based outreach for {company} ({role_title}); "
                    f"full personalization stack unavailable.",
            data={
                "subject": subject, "body": body,
                "subject_variants": [subject], "hooks_used": [hook],
                "used_full_stack": False,
            },
            warnings=["src.personalization / src.resume_engine stack not fully importable — used template fallback."],
        )

    # -- helpers -----------------------------------------------------------

    def _lead_with_skills(self) -> List[str]:
        return self.context.profile.get("positioning", {}).get("lead_with", [])

    def _build_resume_data(self):
        candidate = self.context.profile.get("candidate", {})
        return ResumeData(
            name=candidate.get("name", ""),
            tagline=self.context.profile.get("positioning", {}).get("headline", ""),
            email=candidate.get("email", ""),
            phone=candidate.get("phone", ""),
            linkedin=candidate.get("linkedin", ""),
            github=candidate.get("github", ""),
            website=candidate.get("website", ""),
            all_skills=self._lead_with_skills(),
        )


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = OutreachComposerAgent(ctx).run(
        company="SolarSquare", role_title="Backend Software Engineer",
        jd_text="Django, FastAPI, PostgreSQL, hiring after Series C",
        contact_name="Priya",
    )
    print(result.to_json())
