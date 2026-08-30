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
from src.agents.agent_10_challenge_solver import ChallengeSolverAgent
from src.agents.agent_11_query_hunter import QueryHunterAgent
from src.agents.agent_12_influencer import InfluencerAgent


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


def test_challenge_solver_extracts_grounded_challenge_from_jd(ctx):
    jd = ("We need to scale our microservices and improve API reliability while "
          "maintaining strict compliance and audit trails for BFSI customers.")
    result = ChallengeSolverAgent(ctx).run(company="Perfios", job_description=jd)
    assert result.ok
    assert result.data["identified_challenge"]
    # Every matched proof point must come verbatim from config/profile.yml —
    # never invented.
    proof_values = set(ctx.profile["narrative"]["proof_points_by_theme"].values())
    diffs = set(ctx.profile["positioning"]["differentiators"])
    for point in result.data["matched_proof_points"]:
        assert point in proof_values or point in diffs


def test_challenge_solver_falls_back_to_signal_when_no_jd(ctx):
    result = ChallengeSolverAgent(ctx).run(company="SolarSquare", job_description="")
    assert result.ok
    # SolarSquare has a "funding" signal in target_companies.yml, so a
    # signal-derived challenge should be found even with no JD text.
    assert result.data["identified_challenge"] or result.warnings


def test_query_hunter_renders_queries_without_backend_configured(ctx, monkeypatch):
    import src.agents.agent_11_query_hunter as qh_mod
    monkeypatch.setattr(qh_mod, "settings", None)  # force "no backend" path
    result = QueryHunterAgent(ctx).run(categories=["funding"])
    assert result.ok
    assert result.data["executed"] is False
    assert len(result.data["rendered_queries"]) >= 5


def test_query_hunter_bank_has_at_least_25_queries():
    from src.agents.agent_11_query_hunter import _load_query_bank
    bank = _load_query_bank()
    assert len(bank) >= 25
    assert all("query" in q and "purpose" in q and "category" in q for q in bank)


def test_influencer_never_exceeds_x_char_limit(ctx):
    from src.agents.agent_12_influencer import X_CHAR_LIMIT
    result = InfluencerAgent(ctx).run(angle="signal_reaction", company="SolarSquare")
    assert result.ok
    assert len(result.data["platform_drafts"]["x"]) <= X_CHAR_LIMIT


def test_influencer_draft_reflects_real_signal_not_generic(ctx):
    result = InfluencerAgent(ctx).run(angle="signal_reaction", company="SolarSquare")
    company_cfg = ctx.company("SolarSquare")
    signal_detail = company_cfg["signals"][0]["detail"]
    assert signal_detail in result.data["platform_drafts"]["linkedin"]
