"""
orchestrator.py — Runs the nine target-company agents as one pipeline.

Pipeline order (mirrors CLAUDE.md's existing NEXUS architecture diagram,
extended with the target-company-specific agents):

    1  SignalScoutAgent        → refresh/read funding-hiring signals
    2  ATSHunterAgent          → discover live open roles at target companies
    3  FitScorerAgent          → score every discovered role (CLAUDE.md rubric)
    7  PriorityScheduleAgent   → rank today's send queue (fit + signal freshness)
    4  ResumeTailorAgent       → per queued role, tailor headline/bullets
    5  ContactMapperAgent      → per queued role, rank decision-makers
    6  OutreachComposerAgent   → per queued role, draft signal-seeded email

    8  InterviewPrepAgent      — NOT run in the daily pipeline; call directly
                                  once a company moves to "Interview" status.
    9  FeedbackStrategistAgent — run weekly (or via /nexus digest), not daily;
                                  needs enough sent history to be meaningful.
   11  QueryHunterAgent        — run via --stage leads; executes the boolean/
                                  X-ray query bank (config/boolean_queries.yml)
                                  through a ToS-compliant search backend.
   10  ChallengeSolverAgent    — run via --stage networker, paired with
   12  InfluencerAgent           InfluencerAgent: finds a real, evidenced
                                  challenge and drafts topical LinkedIn/X
                                  content from it. Never auto-posts.

Never auto-sends anything (CLAUDE.md hard rule) — this orchestrator only
produces `data/agent_run_report.md` for human review, same contract as
`/nexus pipeline`.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List

from .base import AgentContext, DATA_DIR
from .agent_01_signal_scout import SignalScoutAgent
from .agent_02_ats_hunter import ATSHunterAgent
from .agent_03_fit_scorer import FitScorerAgent
from .agent_04_resume_tailor import ResumeTailorAgent
from .agent_05_contact_mapper import ContactMapperAgent
from .agent_06_outreach_composer import OutreachComposerAgent
from .agent_07_priority_scheduler import PriorityScheduleAgent
from .agent_08_interview_prepper import InterviewPrepAgent
from .agent_09_feedback_strategist import FeedbackStrategistAgent
from .agent_10_challenge_solver import ChallengeSolverAgent
from .agent_11_query_hunter import QueryHunterAgent
from .agent_12_influencer import InfluencerAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("nexus.agents.orchestrator")

REPORT_PATH = DATA_DIR / "agent_run_report.md"


def run_daily_pipeline(ctx: AgentContext, tiers: List[int] = None) -> Dict[str, Any]:
    tiers = tiers or [1, 2]  # default: don't spend budget on tier-3 watch-list companies

    log.info("[1/7] Signal Scout — refreshing target-company signals")
    signal_result = SignalScoutAgent(ctx).run()

    log.info("[2/7] ATS Hunter — discovering live open roles")
    hunt_result = ATSHunterAgent(ctx).run(tiers=tiers)
    roles = []
    for company, jobs in hunt_result.data.get("roles_by_company", {}).items():
        for j in jobs:
            roles.append({**j, "company": company})

    log.info("[3/7] Fit Scorer — scoring %d discovered roles", len(roles))
    fit_result = FitScorerAgent(ctx).run(roles)

    log.info("[4/7] Priority Scheduler — ranking today's send queue")
    priority_result = PriorityScheduleAgent(ctx).run(
        fit_result.data.get("scored", []),
        signal_result.data.get("hot_companies", []),
    )
    queue = priority_result.data.get("queue", [])

    log.info("[5/7] Resume Tailor + [6/7] Contact Mapper + [7/7] Outreach Composer — per queued role")
    drafts = []
    for item in queue:
        company = item["company"]
        title = item.get("title", "")
        url = item.get("url", "")
        tailor = ResumeTailorAgent(ctx).run(company=company, job_description=title)
        contacts = ContactMapperAgent(ctx).run(company=company, role_title=title)
        top_contact = contacts.data.get("top_contact") or {}
        outreach = OutreachComposerAgent(ctx).run(
            company=company, role_title=title,
            contact_name=top_contact.get("name", "Hiring Manager"),
        )
        drafts.append({
            "company": company, "title": title, "url": url,
            "priority_score": item.get("priority_score"),
            "headline": tailor.data.get("headline"),
            "top_contact": top_contact,
            "subject": outreach.data.get("subject"),
            "body": outreach.data.get("body"),
        })

    report = _render_report(signal_result, hunt_result, fit_result, priority_result, drafts)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    log.info("Report written to %s — review before sending anything.", REPORT_PATH)

    return {
        "signals": signal_result.data,
        "roles_found": len(roles),
        "scored": fit_result.data,
        "queue": queue,
        "drafts": drafts,
        "report_path": str(REPORT_PATH),
    }


def run_interview_prep(ctx: AgentContext, company: str, role_title: str = "") -> str:
    result = InterviewPrepAgent(ctx).run(company=company, role_title=role_title)
    return result.data.get("dossier_markdown", "")


def run_leads_sourcing(ctx: AgentContext, categories: List[str] = None) -> Dict[str, Any]:
    """Runs the boolean/X-ray query bank (config/boolean_queries.yml) via
    QueryHunterAgent — this is the CRM-lead-generation stage. Separate from
    the daily pipeline because it may cost search-API quota."""
    result = QueryHunterAgent(ctx).run(categories=categories)
    return result.data


def run_challenge_and_content(ctx: AgentContext, company: str, job_description: str = "") -> Dict[str, Any]:
    """Chains ChallengeSolverAgent -> InfluencerAgent so a real, evidenced
    challenge feeds directly into a topical LinkedIn/X content draft,
    instead of generic outreach or generic posts."""
    challenge_result = ChallengeSolverAgent(ctx).run(company=company, job_description=job_description)
    content_result = InfluencerAgent(ctx).run(
        angle="challenge" if challenge_result.data.get("identified_challenge") else "signal_reaction",
        company=company,
        challenge_data=challenge_result.data,
    )
    return {"challenge": challenge_result.data, "content_drafts": content_result.data}


def run_weekly_learning(ctx: AgentContext) -> Dict[str, Any]:
    result = FeedbackStrategistAgent(ctx).run()
    return result.data


def _render_report(signal_result, hunt_result, fit_result, priority_result, drafts) -> str:
    lines = ["# NEXUS Agent Run Report", ""]
    lines.append(f"- Signal scout: {signal_result.summary}")
    lines.append(f"- ATS hunter: {hunt_result.summary}")
    lines.append(f"- Fit scorer: {fit_result.summary}")
    lines.append(f"- Priority scheduler: {priority_result.summary}")
    lines.append("")
    lines.append("## Today's Outreach Queue (review before sending — nothing is auto-sent)")
    lines.append("")
    lines.append("| Priority | Company | Role | Top Contact | Subject |")
    lines.append("|---|---|---|---|---|")
    for d in drafts:
        contact_name = (d.get("top_contact") or {}).get("name", "—")
        lines.append(f"| {d.get('priority_score')} | {d['company']} | {d['title']} | {contact_name} | {d.get('subject', '')} |")
    lines.append("")
    for d in drafts:
        lines.append(f"### {d['company']} — {d['title']}")
        lines.append(f"**Headline framing:** {d.get('headline', '')}")
        lines.append("")
        lines.append("```")
        lines.append(d.get("body", ""))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run the NEXUS 12-agent target-company pipeline.")
    parser.add_argument("--stage", choices=["daily", "interview-prep", "weekly-learning", "leads", "networker"],
                         default="daily")
    parser.add_argument("--company", help="Required for --stage interview-prep/networker")
    parser.add_argument("--role", default="", help="Optional role title for --stage interview-prep")
    parser.add_argument("--jd", default="", help="Job description text for --stage networker (much stronger result)")
    parser.add_argument("--categories", nargs="*", default=None,
                         help="Restrict --stage leads to these boolean_queries.yml categories")
    parser.add_argument("--tiers", nargs="*", type=int, default=None, help="Restrict daily pipeline to these tiers")
    args = parser.parse_args()

    ctx = AgentContext.load()

    if args.stage == "daily":
        result = run_daily_pipeline(ctx, tiers=args.tiers)
        print(f"Done. {result['roles_found']} roles found, {len(result['queue'])} queued. "
              f"Report: {result['report_path']}")
    elif args.stage == "interview-prep":
        if not args.company:
            parser.error("--company is required for --stage interview-prep")
        print(run_interview_prep(ctx, args.company, args.role))
    elif args.stage == "leads":
        result = run_leads_sourcing(ctx, categories=args.categories)
        if result.get("executed"):
            print(f"Executed queries, found {len(result['leads'])} leads (see data/agent_state.db -> boolean_leads).")
        else:
            print(f"No search backend configured — {len(result['rendered_queries'])} queries rendered below.\n")
            for q in result["rendered_queries"]:
                print(f"[{q['category']}] {q['query']}\n  -> {q['purpose']}\n")
    elif args.stage == "networker":
        if not args.company:
            parser.error("--company is required for --stage networker")
        result = run_challenge_and_content(ctx, args.company, args.jd)
        print("CHALLENGE:\n" + result["challenge"].get("solution_sketch", "(none found — paste a JD for better results)"))
        print("\nLINKEDIN DRAFT:\n" + result["content_drafts"]["platform_drafts"]["linkedin"])
        print("\nX DRAFT:\n" + result["content_drafts"]["platform_drafts"]["x"])
    elif args.stage == "weekly-learning":
        result = run_weekly_learning(ctx)
        print(result)


if __name__ == "__main__":
    main()
