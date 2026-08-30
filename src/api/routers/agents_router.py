from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.services.agents_service import (
    list_companies_service,
    get_profile_service,
    run_daily_service,
    run_leads_service,
    get_query_bank_service,
    list_leads_service,
    update_lead_status_service,
    run_interview_prep_service,
    run_networker_service,
    run_pitch_service,
    get_interview_questions_service,
    score_interview_answer_service,
    get_negotiation_benchmark_service,
    get_negotiation_counter_service,
    run_outreach_draft_service,
    run_weekly_learning_service,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ── Request models ──────────────────────────────────────────────────────

class DailyPipelineRequest(BaseModel):
    tiers: Optional[List[int]] = Field(default=None, description="Restrict to these company tiers")


class LeadsRequest(BaseModel):
    categories: Optional[List[str]] = Field(default=None, description="Filter boolean_queries.yml categories")


class CompanyRoleRequest(BaseModel):
    company: str
    role_title: str = ""
    job_description: str = ""


class NetworkerRequest(BaseModel):
    company: str
    job_description: str = ""


class InterviewQuestionsRequest(BaseModel):
    company: str
    role_title: str = ""
    job_description: str = ""
    num_questions: int = 5


class InterviewScoreRequest(BaseModel):
    question: str
    answer: str
    focus_area: str = ""


class NegotiateCounterRequest(BaseModel):
    company: str
    offer_amount_lpa: float


class LeadStatusUpdateRequest(BaseModel):
    status: str  # new | reviewed | converted


# ── Companies / config ──────────────────────────────────────────────────

@router.get("/companies")
async def list_companies():
    return await list_companies_service()


@router.get("/profile")
async def get_profile():
    return await get_profile_service()


# ── Daily pipeline (agents 1,2,3,7,4,5,6) ────────────────────────────────

@router.post("/daily")
async def run_daily(req: DailyPipelineRequest):
    return await run_daily_service(req.tiers)


# ── Leads / X-ray sourcing (agent 11) ────────────────────────────────────

@router.post("/leads")
async def run_leads(req: LeadsRequest):
    return await run_leads_service(req.categories)


@router.get("/leads/bank")
async def get_query_bank():
    return await get_query_bank_service()


@router.get("/leads/list")
async def list_leads(status: Optional[str] = None, category: Optional[str] = None,
                      limit: int = Query(default=100, ge=1, le=1000)):
    return await list_leads_service(status, category, limit)


@router.put("/leads/{lead_id}/status")
async def update_lead_status(lead_id: int, req: LeadStatusUpdateRequest):
    return await update_lead_status_service(lead_id, req.status)


# ── Interview prep (agent 8) ─────────────────────────────────────────────

@router.post("/interview-prep")
async def interview_prep(req: CompanyRoleRequest):
    return await run_interview_prep_service(req.company, req.role_title)


# ── Networker: Challenge Solver + Influencer (agents 10, 12) ─────────────

@router.post("/networker")
async def networker(req: NetworkerRequest):
    return await run_networker_service(req.company, req.job_description)


# ── Pitcher (agent 13) ────────────────────────────────────────────────────

@router.post("/pitch")
async def pitch(req: CompanyRoleRequest):
    return await run_pitch_service(req.company, req.job_description)


# ── Interviewer (agent 14) ────────────────────────────────────────────────

@router.post("/interview/questions")
async def interview_questions(req: InterviewQuestionsRequest):
    return await get_interview_questions_service(
        req.company, req.role_title, req.job_description, req.num_questions
    )


@router.post("/interview/score")
async def interview_score(req: InterviewScoreRequest):
    return await score_interview_answer_service(req.question, req.answer, req.focus_area)


# ── Negotiator (agent 15) ─────────────────────────────────────────────────

@router.get("/negotiate/benchmark")
async def negotiate_benchmark(company: str):
    return await get_negotiation_benchmark_service(company)


@router.post("/negotiate/counter")
async def negotiate_counter(req: NegotiateCounterRequest):
    return await get_negotiation_counter_service(req.company, req.offer_amount_lpa)


# ── Outreach draft-only (agents 4, 5, 6) — never sends ────────────────────

@router.post("/outreach-draft")
async def outreach_draft(req: CompanyRoleRequest):
    """Drafts a tailored resume framing + ranked contact + outreach email.
    Does NOT send anything — pair with the existing /api/outreach/send
    endpoint (which has its own confirmation flow) to actually send."""
    return await run_outreach_draft_service(req.company, req.role_title, req.job_description)


# ── Weekly learning (agent 9) ──────────────────────────────────────────────

@router.post("/weekly-learning")
async def weekly_learning():
    return await run_weekly_learning_service()
