"""
test_sprint4_features.py — Unit & Integration tests for Sprint 4:
1. Feature 6: Frontier AI & RLHF High-Income Arbitrage Radar (Agent 19)
2. Feature 10: The Executive Decision Memo Closer (Agent 23)
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from src.services.frontier_ai_radar import FrontierAiRadarService
from src.agents.agent_19_frontier_ai_radar import FrontierAiRadarAgent
from src.services.executive_decision_memo import ExecutiveDecisionMemoService
from src.agents.agent_23_executive_decision_memo import ExecutiveDecisionMemoAgent

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Frontier AI & RLHF High-Income Arbitrage Radar (Agent 19) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_frontier_ai_platforms_directory():
    service = FrontierAiRadarService()
    platforms = service.get_platforms()
    assert len(platforms) >= 5
    ids = [p["id"] for p in platforms]
    assert "outlier_ai" in ids
    assert "alignerr" in ids
    assert "mercor" in ids
    assert "micro1" in ids
    assert "data_annotation" in ids

    for p in platforms:
        assert p["hourly_rate_usd"] >= 40.0
        assert p["direct_apply_url"].startswith("https://")


def test_frontier_ai_sample_challenge():
    service = FrontierAiRadarService()
    challenge = service.get_sample_challenge()
    assert challenge["challenge_id"] == "eval_py_01"
    assert "LRUCache" in challenge["buggy_code"]
    assert len(challenge["rubric_key_points"]) == 5


def test_frontier_ai_critique_evaluation_perfect():
    service = FrontierAiRadarService()
    perfect_critique = (
        "1. Big-O: self.order.remove(key) is O(N) linear scan. "
        "2. Eviction: self.order.pop(0) causes O(N) array shifting. "
        "3. OrderedDict / Doubly-Linked List with Hash Map must be used for O(1). "
        "4. Edge case: capacity <= 0 zero capacity validation. "
        "5. Concurrency: Thread safety / race condition lock is required."
    )
    result = service.evaluate_benchmark(perfect_critique, weekly_hours=20)
    assert result["status"] == "success"
    assert result["benchmark_score"] == 100
    assert result["projected_hourly_rate_usd"] >= 75.0
    assert "Tier 1" in result["tier_status"]
    assert len(result["rubric_breakdown"]) == 5
    assert all(r["passed"] for r in result["rubric_breakdown"])
    assert result["projections"]["monthly_usd"] > 5000
    assert result["projections"]["annual_inr_lakhs"] > 50


def test_frontier_ai_critique_evaluation_partial():
    service = FrontierAiRadarService()
    partial_critique = "The order list remove is O(N) and slow. We should use OrderedDict."
    result = service.evaluate_benchmark(partial_critique, weekly_hours=10)
    assert result["status"] == "success"
    assert 40 <= result["benchmark_score"] <= 60
    assert result["projected_hourly_rate_usd"] >= 40.0
    assert len(result["top_recommended_platforms"]) > 0


def test_agent_19_frontier_ai_radar_execution():
    agent = FrontierAiRadarAgent()
    result = agent.run(
        critique_text="self.order.remove(key) is O(N), self.order.pop(0) is O(N). Use OrderedDict and locks for thread safety.",
        weekly_hours=15,
    )
    assert result.ok is True
    assert result.agent == "frontier_ai_radar"
    assert "Frontier AI Score" in result.summary
    assert "projections" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 2. Executive Decision Memo Closer (Agent 23) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_executive_memo_cost_per_hire_calc():
    service = ExecutiveDecisionMemoService()
    costs = service.calculate_hiring_costs(target_comp_lpa=70.0)
    assert costs["total_hiring_investment_inr_lakhs"] >= 15.0
    assert costs["total_usd_equivalent"] >= 15000
    breakdown = costs["breakdown"]
    assert "₹12.6L" in breakdown["agency_recruiter_commission"]
    assert "₹3.8L" in breakdown["engineering_team_interview_hours"]
    assert "₹1.4L" in breakdown["ats_sourcing_infrastructure"]
    assert "₹17.5L" in breakdown["cost_of_empty_seat_per_month"]


def test_executive_memo_synthesis():
    service = ExecutiveDecisionMemoService()
    memo_pkg = service.synthesize_memo(
        candidate_name="Ujjwal",
        company_name="Stripe",
        role_title="Staff Distributed Systems Engineer",
        interview_stage="Final Round",
        key_technical_topics=["Raft Consensus", "Distributed Lock Sharding"],
        p99_impact_metric="Reduced P99 tail latency by 64% and saved k/yr",
        competing_offer_anchor="Competing offer at ₹75 LPA",
        target_compensation_lpa=70.0,
    )
    assert memo_pkg["status"] == "success"
    assert memo_pkg["candidate_name"] == "Ujjwal"
    assert memo_pkg["company_name"] == "Stripe"
    assert "Internal Debrief & Candidate Recommendation Memo" in memo_pkg["executive_memo_markdown"]
    assert "Raft Consensus" in memo_pkg["executive_memo_markdown"]
    assert "Reduced P99 tail latency by 64%" in memo_pkg["executive_memo_markdown"]
    assert "Subject: Follow-up & architecture debrief notes" in memo_pkg["followup_email"]
    assert len(memo_pkg["strategic_leverage_summary"]) > 20


def test_agent_23_executive_memo_execution():
    agent = ExecutiveDecisionMemoAgent()
    result = agent.run(
        candidate_name="Ujjwal",
        company_name="Acme Corp",
        role_title="Principal Architect",
        target_compensation_lpa=65.0,
    )
    assert result.ok is True
    assert result.agent == "executive_decision_memo"
    assert "Synthesized Executive Decision Memo" in result.summary
    assert "cost_analysis" in result.data
    assert "executive_memo_markdown" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 3. FastAPI REST Endpoints Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_api_frontier_ai_platforms_endpoint():
    response = client.get("/api/frontier-ai/platforms")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["platforms"]) >= 5


def test_api_frontier_ai_challenge_endpoint():
    response = client.get("/api/frontier-ai/challenge")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "challenge_id" in data["challenge"]


def test_api_frontier_ai_benchmark_endpoint():
    payload = {
        "critique_text": "self.order.remove is O(N), self.order.pop(0) is O(N). Must use OrderedDict or doubly linked list with lock.",
        "weekly_hours_available": 15,
        "usd_to_inr_rate": 86.5,
    }
    response = client.post("/api/frontier-ai/benchmark", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["benchmark_score"] > 0
    assert data["projections"]["monthly_usd"] > 0


def test_api_executive_memo_synthesize_endpoint():
    payload = {
        "candidate_name": "Ujjwal",
        "company_name": "Acme AI",
        "role_title": "Staff Engineer",
        "target_compensation_lpa": 68.0,
        "p99_impact_metric": "P99 latency down 50%",
    }
    response = client.post("/api/executive-memo/synthesize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["candidate_name"] == "Ujjwal"
    assert "executive_memo_markdown" in data
    assert "cost_analysis" in data
