"""
test_sprint3_features.py — Unit & Integration tests for Sprint 3:
1. Trojan-Horse Proof-of-Work Fabricator (Agent 17)
2. Anti-Ghosting SLA & Recruiter Escalation Engine (Agent 18)
3. Community Hiring Velocity Index
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from src.services.proof_of_work_fabricator import ProofOfWorkFabricatorService
from src.agents.agent_17_proof_of_work_fabricator import ProofOfWorkFabricatorAgent
from src.services.anti_ghosting_service import AntiGhostingService
from src.agents.agent_18_anti_ghosting_sla import AntiGhostingAgent

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Proof-of-Work Fabricator (Agent 17) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_pow_fabricator_templates():
    service = ProofOfWorkFabricatorService()
    templates = service.get_templates()
    assert len(templates) >= 4
    ids = [t["id"] for t in templates]
    assert "idempotent_webhook_engine" in ids
    assert "iot_telemetry_stream_pipeline" in ids


def test_pow_fabricator_fintech_generation():
    service = ProofOfWorkFabricatorService()
    res = service.fabricate(
        company_name="Pine Labs",
        role_title="Senior Backend Engineer",
    )
    assert res["status"] == "success"
    assert "Pine Labs" in res["project_title"]
    assert "app_code" in res
    assert "test_code" in res
    assert "dockerfile" in res
    assert "github_actions_ci" in res
    assert "pr_description_markdown" in res
    assert "mermaid" in res["pr_description_markdown"]
    assert res["benchmark_metrics"]["p99_latency_reduction_percent"] > 90


def test_pow_fabricator_iot_generation():
    service = ProofOfWorkFabricatorService()
    res = service.fabricate(
        company_name="Ather Energy",
        role_title="IoT Platform Engineer",
    )
    assert res["status"] == "success"
    assert "Ather Energy" in res["project_title"]
    assert "app_code_filename" in res


def test_agent_17_pow_fabricator_execution():
    agent = ProofOfWorkFabricatorAgent()
    result = agent.run(
        company_name="Cashfree Payments",
        role_title="Staff Systems Engineer",
    )
    assert result.ok is True
    assert result.agent == "proof_of_work_fabricator"
    assert "Cashfree Payments" in result.summary
    assert "app_code" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 2. Anti-Ghosting SLA & Recruiter Escalation (Agent 18) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_anti_ghosting_company_sla_lookup():
    service = AntiGhostingService()
    sla = service.get_company_sla("Pine Labs")
    assert sla["company_name"] == "Pine Labs"
    assert sla["is_verified_fast_track"] is True
    assert sla["avg_feedback_turnaround_hours"] <= 48.0


def test_anti_ghosting_risk_decay_curve():
    service = AntiGhostingService()
    sla = service.get_company_sla("Swiggy")

    # Day 1: Low risk
    low = service.calculate_ghosting_risk(1, "Technical Screen", sla)
    assert low["ghosting_risk_percent"] < 15.0
    assert "Within" in low["sla_status"]

    # Day 4: Nudge window
    med = service.calculate_ghosting_risk(4, "Technical Screen", sla)
    assert 15.0 <= med["ghosting_risk_percent"] <= 40.0

    # Day 9: Breached SLA
    high = service.calculate_ghosting_risk(9, "Technical Screen", sla)
    assert high["ghosting_risk_percent"] > 60.0
    assert "Breached" in high["sla_status"]


def test_anti_ghosting_escalation_synthesis():
    service = AntiGhostingService()
    res = service.synthesize_escalations(
        company_name="Razorpay",
        interview_stage="System Design / Round 2",
        days_elapsed=5,
        recruiter_name="Rahul",
        candidate_leverage="Has Competing Timelines",
        competing_company="CRED",
    )

    assert res["status"] == "success"
    assert len(res["escalation_tiers"]) == 3
    tiers = {t["tier_level"]: t for t in res["escalation_tiers"]}

    # Check Tier 1
    assert "Rahul" in tiers[1]["body"]
    assert "System Design / Round 2" in tiers[1]["subject"]

    # Check Tier 2 leverage trigger
    assert "CRED" in tiers[2]["body"]
    assert "competing" in tiers[2]["strategic_intent"].lower() or "scarcity" in tiers[2]["strategic_intent"].lower()

    # Check Tier 3 executive closeout
    assert "wrapping up" in tiers[3]["body"].lower() or "final scheduling" in tiers[3]["body"].lower()


def test_agent_18_anti_ghosting_execution():
    agent = AntiGhostingAgent()
    result = agent.run(
        company_name="CRED",
        interview_stage="Bar Raiser",
        days_elapsed=4,
    )
    assert result.ok is True
    assert result.agent == "anti_ghosting_sla"
    assert "CRED" in result.summary
    assert "escalation_tiers" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 3. FastAPI REST Endpoints Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_api_pow_templates_endpoint():
    response = client.get("/api/pow/templates")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["templates"]) >= 4


def test_api_pow_fabricate_endpoint():
    payload = {
        "company_name": "Pine Labs",
        "role_title": "Senior SRE",
        "archetype_id": "idempotent_webhook_engine",
    }
    response = client.post("/api/pow/fabricate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Pine Labs" in data["project_title"]
    assert "app_code" in data
    assert "pr_description_markdown" in data


def test_api_anti_ghosting_sla_index_endpoint():
    response = client.get("/api/anti-ghosting/sla-index")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["companies"]) >= 5


def test_api_anti_ghosting_escalate_endpoint():
    payload = {
        "company_name": "Ather Energy",
        "interview_stage": "Onsite System Architecture",
        "days_elapsed": 6,
        "recruiter_name": "Deepika",
        "candidate_leverage": "Final Round at Tier 1 Startup",
        "competing_company": "Ola Electric",
    }
    response = client.post("/api/anti-ghosting/escalate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["escalation_tiers"]) == 3
    assert data["risk_metrics"]["ghosting_risk_percent"] > 0
