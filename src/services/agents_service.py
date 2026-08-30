"""
src/services/agents_service.py — business logic for the src/agents/ (15-agent
target-company) system, kept separate from src/api/routers/agents_router.py
per the router/service split documented in ARCHITECTURE_REFACTOR_ROUTERS.md.

Design notes:
  - AgentContext.load() re-reads config/profile.yml + config/target_companies.yml
    on every call rather than caching at process startup, so config edits
    take effect immediately without a server restart — these are small
    local YAML files, not a network round-trip.
  - Every function here returns the agent's AgentResult as a plain dict
    (dataclasses.asdict) so it's directly JSON-serializable by FastAPI.
  - Nothing here sends email or applies to a job — same hard rule as the
    rest of this repo. run_outreach_draft_service only drafts; use the
    existing /api/outreach/send endpoint (with its own confirmation flow)
    to actually send.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from src.agents.base import AgentContext, get_state_conn
from src.agents.agent_04_resume_tailor import ResumeTailorAgent
from src.agents.agent_05_contact_mapper import ContactMapperAgent
from src.agents.agent_06_outreach_composer import OutreachComposerAgent
from src.agents.agent_08_interview_prepper import InterviewPrepAgent
from src.agents.agent_09_feedback_strategist import FeedbackStrategistAgent
from src.agents.agent_11_query_hunter import _load_query_bank
from src.agents.agent_13_pitcher import PitcherAgent
from src.agents.agent_14_interviewer import InterviewerAgent
from src.agents.agent_15_negotiator import NegotiatorAgent
from src.agents.orchestrator import run_daily_pipeline, run_leads_sourcing, run_challenge_and_content

log = logging.getLogger("job_finder.agents")


def _ctx() -> AgentContext:
    try:
        return AgentContext.load()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _result_dict(result) -> Dict[str, Any]:
    return asdict(result)


# ── Companies / config ──────────────────────────────────────────────────

async def list_companies_service() -> Dict[str, Any]:
    ctx = _ctx()
    return {"companies": ctx.companies, "sector_context": ctx.sector_context}


async def get_profile_service() -> Dict[str, Any]:
    return _ctx().profile


# ── Daily pipeline (agents 1,2,3,7,4,5,6) ────────────────────────────────

async def run_daily_service(tiers: Optional[List[int]]) -> Dict[str, Any]:
    ctx = _ctx()
    try:
        return run_daily_pipeline(ctx, tiers=tiers)
    except Exception as exc:  # noqa: BLE001
        log.exception("Daily pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Leads / X-ray sourcing (agent 11) ────────────────────────────────────

async def run_leads_service(categories: Optional[List[str]]) -> Dict[str, Any]:
    ctx = _ctx()
    return run_leads_sourcing(ctx, categories=categories)


async def get_query_bank_service() -> Dict[str, Any]:
    return {"queries": _load_query_bank()}


async def list_leads_service(status: Optional[str], category: Optional[str], limit: int) -> Dict[str, Any]:
    conn = get_state_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boolean_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT, category TEXT, title TEXT, url TEXT UNIQUE,
            snippet TEXT, status TEXT DEFAULT 'new', discovered_at REAL NOT NULL
        )
    """)
    query = "SELECT id, query_id, category, title, url, snippet, status, discovered_at FROM boolean_leads WHERE 1=1"
    params: List[Any] = []
    if status:
        query += " AND status=?"
        params.append(status)
    if category:
        query += " AND category=?"
        params.append(category)
    query += " ORDER BY discovered_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    cols = ["id", "query_id", "category", "title", "url", "snippet", "status", "discovered_at"]
    return {"leads": [dict(zip(cols, row)) for row in rows]}


async def update_lead_status_service(lead_id: int, status: str) -> Dict[str, Any]:
    if status not in ("new", "reviewed", "converted"):
        raise HTTPException(status_code=400, detail="status must be new|reviewed|converted")
    conn = get_state_conn()
    conn.execute("UPDATE boolean_leads SET status=? WHERE id=?", (status, lead_id))
    conn.commit()
    conn.close()
    return {"id": lead_id, "status": status}


# ── Interview prep (agent 8) ─────────────────────────────────────────────

async def run_interview_prep_service(company: str, role_title: str) -> Dict[str, Any]:
    ctx = _ctx()
    result = InterviewPrepAgent(ctx).run(company=company, role_title=role_title)
    return _result_dict(result)


# ── Networker: Challenge Solver + Influencer (agents 10, 12) ─────────────

async def run_networker_service(company: str, job_description: str) -> Dict[str, Any]:
    ctx = _ctx()
    return run_challenge_and_content(ctx, company, job_description)


# ── Pitcher (agent 13) ────────────────────────────────────────────────────

async def run_pitch_service(company: str, job_description: str) -> Dict[str, Any]:
    ctx = _ctx()
    result = PitcherAgent(ctx).run(company=company, job_description=job_description)
    return _result_dict(result)


# ── Interviewer (agent 14) ────────────────────────────────────────────────

async def get_interview_questions_service(company: str, role_title: str, job_description: str,
                                           num_questions: int) -> Dict[str, Any]:
    ctx = _ctx()
    result = InterviewerAgent(ctx).generate_questions(
        company=company, role_title=role_title,
        job_description=job_description, num_questions=num_questions,
    )
    return _result_dict(result)


async def score_interview_answer_service(question: str, answer: str, focus_area: str) -> Dict[str, Any]:
    ctx = _ctx()
    result = InterviewerAgent(ctx).score_answer(question=question, answer=answer, focus_area=focus_area)
    return _result_dict(result)


# ── Negotiator (agent 15) ─────────────────────────────────────────────────

async def get_negotiation_benchmark_service(company: str) -> Dict[str, Any]:
    ctx = _ctx()
    result = NegotiatorAgent(ctx).benchmark(company)
    return _result_dict(result)


async def get_negotiation_counter_service(company: str, offer_amount_lpa: float) -> Dict[str, Any]:
    ctx = _ctx()
    result = NegotiatorAgent(ctx).counter_script(company, offer_amount_lpa)
    return _result_dict(result)


# ── Outreach draft-only (agents 4, 5, 6) — never sends ────────────────────

async def run_outreach_draft_service(company: str, role_title: str, job_description: str) -> Dict[str, Any]:
    """Drafts a tailored resume framing + ranked contact + outreach email.
    Does NOT send anything — pair with the existing /api/outreach/send
    endpoint (which has its own confirmation flow) to actually send."""
    ctx = _ctx()
    tailor = ResumeTailorAgent(ctx).run(company=company, job_description=job_description)
    contacts = ContactMapperAgent(ctx).run(company=company, role_title=role_title)
    top_contact = contacts.data.get("top_contact") or {}
    outreach = OutreachComposerAgent(ctx).run(
        company=company, role_title=role_title, jd_text=job_description,
        contact_name=top_contact.get("name", "Hiring Manager"),
    )
    return {
        "tailor": _result_dict(tailor),
        "contacts": _result_dict(contacts),
        "outreach": _result_dict(outreach),
    }


# ── Weekly learning (agent 9) ──────────────────────────────────────────────

async def run_weekly_learning_service() -> Dict[str, Any]:
    ctx = _ctx()
    result = FeedbackStrategistAgent(ctx).run()
    return _result_dict(result)
