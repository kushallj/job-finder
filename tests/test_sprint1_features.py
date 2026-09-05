"""
Unit tests for Sprint 1 Category-Defining Features:
1. Interviewer Cognitive Profiler & Bias Radar (Service + Agent 16).
2. Multi-Offer Arbitrage & Negotiation War-Room Engine.
3. REST API endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from src.services.interviewer_profiler import InterviewerProfilerService
from src.services.offer_arbitrage import OfferArbitrageService, CompensationOffer
from src.agents.agent_16_interviewer_profiler import InterviewerProfilerAgent
from src.agents.base import AgentContext


def test_interviewer_profiler_service_fintech():
    service = InterviewerProfilerService()
    dossier = service.profile_interviewer(
        name="Ankit Sharma",
        company="CRED",
        role="Director of Engineering",
    )
    assert dossier["status"] == "success"
    assert "ACID" in dossier["architectural_biases"][0] or "consistency" in dossier["architectural_biases"][0]
    assert len(dossier["green_lights_to_highlight"]) >= 3
    assert len(dossier["red_lines_to_avoid"]) >= 3
    assert "Ankit" in dossier["personalized_conversation_opener"]
    assert len(dossier["recommended_questions_to_ask_them"]) >= 3


def test_interviewer_profiler_agent_run():
    ctx = AgentContext.load()
    agent = InterviewerProfilerAgent(context=ctx)
    result = agent.run(interviewer_name="Sarah Jenkins", company_name="Walmart Global Tech", role="VP of Engineering")
    assert result.ok is True
    assert result.agent == "interviewer_profiler"
    assert "Walmart" in result.data["interviewer"]["company"]


def test_offer_arbitrage_simulation():
    service = OfferArbitrageService()
    offers = [
        CompensationOffer(
            id="offer_cred",
            company_name="CRED",
            role_title="Senior Backend Engineer",
            currency="LPA (INR)",
            base_salary=42.0,
            annual_bonus=5.0,
            joining_bonus=4.0,
            equity_total_grant=40.0,
            equity_type="ESOP",
            company_stage="Series D",
        ),
        CompensationOffer(
            id="offer_walmart",
            company_name="Walmart Global Tech",
            role_title="Senior Software Engineer",
            currency="LPA (INR)",
            base_salary=38.0,
            annual_bonus=6.0,
            joining_bonus=3.0,
            equity_total_grant=48.0,
            equity_type="RSU",
            company_stage="Public",
        ),
    ]

    res = service.simulate_arbitrage(offers)
    assert res["status"] == "success"
    assert res["total_offers_analyzed"] == 2
    assert len(res["ranked_offers"]) == 2
    # Walmart RSU (95% multiplier) should outrank or closely rival CRED ESOP (60% multiplier)
    assert len(res["leverage_insights"]) >= 1


def test_counter_offer_script_generation():
    service = OfferArbitrageService()
    script = service.generate_counter_script(
        target_company="CRED",
        competing_company="Walmart Global Tech",
        current_base=42.0,
        target_base=48.0,
        currency="LPA (INR)",
    )
    assert script["status"] == "success"
    assert "Subject:" in script["email_script"]
    assert "48.0" in script["email_script"]
    assert "Walmart Global Tech" in script["email_script"]
    assert "Rescission Risk" in script["rescission_risk_score"] or "%" in script["rescission_risk_score"]


def test_deadline_defuser_generation():
    service = OfferArbitrageService()
    defuser = service.generate_deadline_defuser(
        company_name="CRED",
        current_deadline="Friday, Sept 12",
        extension_days=5,
    )
    assert defuser["status"] == "success"
    assert "CRED" in defuser["defuser_email_script"]
    assert "extension" in defuser["tactical_rule"].lower() or "committed" in defuser["tactical_rule"].lower()


def test_sprint1_fastapi_endpoints():
    client = TestClient(app)

    # 1. Interviewer Profiler Endpoint
    prof_res = client.post("/api/interviewer/profile", json={
        "name": "Vikram Seth",
        "company": "Razorpay",
        "role": "Staff Engineer",
    })
    assert prof_res.status_code == 200
    assert prof_res.json()["status"] == "success"

    # 2. Offer Arbitrage Endpoint
    arb_res = client.post("/api/negotiation/arbitrage", json={
        "offers": [
            {
                "id": "off_1",
                "company_name": "CRED",
                "base_salary": 45.0,
                "annual_bonus": 5.0,
                "joining_bonus": 5.0,
                "equity_total_grant": 20.0,
                "equity_type": "ESOP",
                "company_stage": "Series D",
                "currency": "LPA",
            }
        ]
    })
    assert arb_res.status_code == 200
    assert arb_res.json()["status"] == "success"

    # 3. Counter Script Endpoint
    counter_res = client.post("/api/negotiation/counter-script", json={
        "target_company": "Razorpay",
        "competing_company": "CRED",
        "current_base": 40.0,
        "target_base": 46.0,
    })
    assert counter_res.status_code == 200
    assert "Razorpay" in counter_res.json()["email_script"]

    # 4. Defuse Deadline Endpoint
    defuse_res = client.post("/api/negotiation/defuse-deadline", json={
        "company_name": "Razorpay",
        "current_deadline": "Sept 10",
        "extension_days": 4,
    })
    assert defuse_res.status_code == 200
    assert "Razorpay" in defuse_res.json()["defuser_email_script"]
