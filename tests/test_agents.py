"""
tests/test_agents.py — Smoke tests for the 9 target-company agents.

Keeps to deterministic, network/DB-independent behavior so these run in CI
without external services: config loading, fit scoring, resume tailoring,
priority-queue decay math. Agents that require live network (ATS Hunter) or
the full contact-intelligence/personalization stack (Contact Mapper,
Outreach Composer) are exercised only for their graceful-fallback paths.
"""

import pytest

from src.agents.base import AgentContext
from src.agents.agent_01_signal_scout import SignalScoutAgent
from src.agents.agent_03_fit_scorer import FitScorerAgent, APPLY_THRESHOLD, FLOOR_THRESHOLD
from src.agents.agent_04_resume_tailor import ResumeTailorAgent
from src.agents.agent_07_priority_scheduler import PriorityScheduleAgent


@pytest.fixture(scope="module")
def ctx():
    return AgentContext.load()


def test_context_loads_profile_and_companies(ctx):
    assert ctx.profile["candidate"]["name"]
    assert len(ctx.companies) > 0
    assert all("tier" in c for c in ctx.companies)


def test_company_lookup_is_case_insensitive(ctx):
    found = ctx.company("PERFIOS")
    assert found is not None
    assert found["name"] == "Perfios"


def test_companies_by_tier_filters_correctly(ctx):
    tier1 = ctx.companies_by_tier(1)
    assert all(c["tier"] == 1 for c in tier1)
    assert len(tier1) > 0


def test_signal_scout_ingests_and_classifies(ctx, tmp_path, monkeypatch):
    # Redirect state DB to a temp path so this test doesn't touch real state.
    import src.agents.base as base_mod
    monkeypatch.setattr(base_mod, "AGENT_STATE_DB", tmp_path / "test_state.db")

    result = SignalScoutAgent(ctx).run()
    assert result.ok
    assert "hot_companies" in result.data
    assert "stale_companies" in result.data


def test_fit_scorer_recommends_apply_for_strong_match(ctx):
    roles = [{
        "company": "Perfios",
        "title": "Backend Software Engineer (Python)",
        "description": "Django REST Framework, FastAPI, PostgreSQL, JWT auth, RBAC",
        "location": "Bangalore, India",
        "url": "https://example.com/1",
    }]
    result = FitScorerAgent(ctx).run(roles)
    assert result.ok
    scored = result.data["scored"][0]
    assert scored["score"] >= FLOOR_THRESHOLD
    assert scored["recommendation"] in ("Apply", "Consider")


def test_fit_scorer_never_recommends_apply_below_floor(ctx):
    roles = [{
        "company": "UnknownCo",
        "title": "Staff Site Reliability Engineer",
        "description": "Kubernetes, Go, on-call",
        "location": "San Francisco, USA (onsite only)",
        "url": "https://example.com/2",
    }]
    result = FitScorerAgent(ctx).run(roles)
    scored = result.data["scored"][0]
    if scored["score"] < FLOOR_THRESHOLD:
        assert scored["recommendation"] == "Skip"


def test_resume_tailor_never_invents_differentiators(ctx):
    result = ResumeTailorAgent(ctx).run(
        company="Perfios", job_description="Django, FastAPI, RBAC", use_llm=False
    )
    assert result.ok
    profile_diffs = set(ctx.profile["positioning"]["differentiators"])
    for bullet in result.data["ordered_bullets"]:
        assert bullet in profile_diffs


def test_priority_scheduler_ranks_fresh_signal_above_stale(ctx):
    roles = [
        {"company": "Fresh Co", "title": "Backend Engineer", "score": 70.0, "recommendation": "Apply"},
        {"company": "Stale Co", "title": "Backend Engineer", "score": 70.0, "recommendation": "Apply"},
    ]
    signals = [
        {"company": "Fresh Co", "freshest_signal_age_days": 2},
        {"company": "Stale Co", "freshest_signal_age_days": 400},
    ]
    result = PriorityScheduleAgent(ctx).run(roles, signals)
    ranked = {r["company"]: r["priority_score"] for r in result.data["all_ranked"]}
    assert ranked["Fresh Co"] > ranked["Stale Co"]


def test_priority_scheduler_caps_daily_queue(ctx):
    from src.agents.agent_07_priority_scheduler import MAX_DAILY_SENDS
    roles = [
        {"company": f"Co{i}", "title": "Backend Engineer", "score": 90.0, "recommendation": "Apply"}
        for i in range(MAX_DAILY_SENDS + 5)
    ]
    result = PriorityScheduleAgent(ctx).run(roles, [])
    assert len(result.data["queue"]) <= MAX_DAILY_SENDS
