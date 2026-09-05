"""
test_sprint5_features.py — Unit & Integration tests for Sprint 5:
1. Feature 7: Reverse Headhunter Bounty Network (Agent 20)
2. Feature 8: Global Geo-Arbitrage & Cross-Border Engine (Agent 21)
3. Feature 9: Web3 & Open-Source Bounty Harvester (Agent 22)
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from src.services.reverse_headhunter_service import ReverseHeadhunterService
from src.agents.agent_20_reverse_headhunter import ReverseHeadhunterAgent
from src.services.geo_arbitrage_service import GeoArbitrageService
from src.agents.agent_21_geo_arbitrage import GeoArbitrageAgent
from src.services.web3_bounty_harvester import Web3BountyHarvesterService
from src.agents.agent_22_web3_bounty_harvester import Web3BountyHarvesterAgent

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Reverse Headhunter Bounty Network (Agent 20) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_headhunter_listings_directory():
    service = ReverseHeadhunterService()
    listings = service.get_listings()
    assert len(listings) >= 5
    companies = [l["company_name"] for l in listings]
    assert "Stripe" in companies
    assert "OpenAI" in companies
    assert "Razorpay" in companies
    assert "Mercari Japan" in companies

    for l in listings:
        assert l["bounty_amount_usd"] >= 1000
        assert l["escrow_status"] == "VERIFIED_ESCROW"


def test_headhunter_pitch_pack_generation():
    service = ReverseHeadhunterService()
    pack = service.generate_pitch_pack(
        candidate_name="Ujjwal",
        target_company="Stripe",
        role_title="Staff Distributed Systems Engineer",
        referrer_name="Alex",
        key_strengths=["Raft Consensus", "P99 Latency Reduction"],
        years_experience=6,
        github_portfolio="https://github.com/ujjwal-sovereign",
    )
    assert pack["status"] == "success"
    assert pack["candidate_name"] == "Ujjwal"
    assert pack["target_company"] == "Stripe"
    assert "Subject: Warm Referral: Ujjwal" in pack["hiring_manager_referral_email"]
    assert "Raft Consensus" in pack["hiring_manager_referral_email"]
    assert "Alex" in pack["peer_outreach_script"]
    assert pack["bounty_financials"]["total_bounty_usd"] == 5000
    assert pack["bounty_financials"]["milestone_1_payout_usd"] == 2500
    assert pack["bounty_financials"]["milestone_2_payout_usd"] == 2500


def test_agent_20_reverse_headhunter_execution():
    agent = ReverseHeadhunterAgent()
    result = agent.run(
        candidate_name="Ujjwal",
        target_company="OpenAI",
        role_title="Inference Systems Engineer",
    )
    assert result.ok is True
    assert result.agent == "reverse_headhunter"
    assert "Generated Referral Pitch Pack for Ujjwal" in result.summary
    assert "bounty_financials" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 2. Global Geo-Arbitrage & Cross-Border Engine (Agent 21) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_geo_arbitrage_markets_directory():
    service = GeoArbitrageService()
    markets = service.get_markets()
    assert len(markets) >= 5
    ids = [m["market_id"] for m in markets]
    assert "japan_tokyo" in ids
    assert "singapore_apac" in ids
    assert "netherlands_amsterdam" in ids
    assert "germany_berlin_munich" in ids
    assert "uk_london" in ids

    for m in markets:
        assert m["english_adoption_score"] >= 85
        assert m["pr_timeline_months"] > 0


def test_geo_arbitrage_ppp_tokyo_calculation():
    service = GeoArbitrageService()
    res = service.calculate_net_ppp(
        gross_annual_salary=18000000.0,  # 18M JPY
        market_id="japan_tokyo",
        current_inr_ctc_lpa=35.0,
    )
    assert res["status"] == "success"
    fin = res["financials"]
    assert fin["gross_salary_local"] == 18000000.0
    assert fin["effective_tax_percent"] == 28.5
    assert fin["gross_inr_lakhs"] > 90.0
    assert fin["net_inr_lakhs"] > 65.0
    assert fin["annual_savings_inr_lakhs"] > 40.0
    assert fin["savings_expansion_multiplier"] > 1.5
    assert "12 months" in res["visa_dossier"]["permanent_residence_timeline"]


def test_geo_arbitrage_ppp_amsterdam_calculation():
    service = GeoArbitrageService()
    res = service.calculate_net_ppp(
        gross_annual_salary=120000.0,  # 120k EUR
        market_id="netherlands_amsterdam",
        current_inr_ctc_lpa=30.0,
    )
    assert res["status"] == "success"
    assert res["financials"]["effective_tax_percent"] == 26.0  # 30% tax ruling
    assert res["financials"]["annual_savings_inr_lakhs"] > 45.0


def test_agent_21_geo_arbitrage_execution():
    agent = GeoArbitrageAgent()
    result = agent.run(
        gross_annual_salary=16000000.0,
        market_id="japan_tokyo",
        current_inr_ctc_lpa=35.0,
    )
    assert result.ok is True
    assert result.agent == "geo_arbitrage"
    assert "Geo-Arbitrage Analysis (Tokyo)" in result.summary
    assert "financials" in result.data
    assert "visa_dossier" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 3. Web3 & Open-Source Bounty Harvester (Agent 22) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_web3_bounties_directory():
    service = Web3BountyHarvesterService()
    bounties = service.get_bounties()
    assert len(bounties) >= 5
    ids = [b["bounty_id"] for b in bounties]
    assert "bounty_solana_blinks_01" in ids
    assert "bounty_eth_zk_02" in ids
    assert "bounty_arbitrum_nitro_03" in ids
    assert "bounty_oss_postgres_04" in ids

    for b in bounties:
        assert b["reward_usd"] >= 500
        assert b["escrow_verified"] is True


def test_web3_proposal_synthesis():
    service = Web3BountyHarvesterService()
    proposal = service.synthesize_proposal(
        bounty_id="bounty_solana_blinks_01",
        candidate_name="Ujjwal",
        proposed_architecture="Memory-bounded ring buffer with sub-10ms P99 latency.",
        timeline_days=12,
        github_profile="https://github.com/ujjwal-sovereign",
    )
    assert proposal["status"] == "success"
    assert proposal["reward_usd"] == 5000
    assert proposal["reward_inr_lakhs"] > 4.0
    assert "# 🛠️ RFC Proposal:" in proposal["proposal_markdown"]
    assert "Memory-bounded ring buffer" in proposal["proposal_markdown"]
    assert "Milestone 1" in proposal["proposal_markdown"]
    assert "Milestone 2" in proposal["proposal_markdown"]
    assert "Milestone 3" in proposal["proposal_markdown"]


def test_agent_22_web3_bounty_harvester_execution():
    agent = Web3BountyHarvesterAgent()
    result = agent.run(
        bounty_id="bounty_eth_zk_02",
        candidate_name="Ujjwal",
    )
    assert result.ok is True
    assert result.agent == "web3_bounty_harvester"
    assert "Synthesized Bounty RFC Proposal" in result.summary
    assert result.data["reward_usd"] == 12000
    assert "proposal_markdown" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 4. FastAPI REST Endpoints Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_api_headhunter_listings():
    response = client.get("/api/bounties/headhunter/listings")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["listings"]) >= 5


def test_api_headhunter_pitch_pack():
    payload = {
        "candidate_name": "Ujjwal",
        "target_company": "Stripe",
        "role_title": "Staff Engineer",
        "referrer_name": "Alex",
    }
    response = client.post("/api/bounties/headhunter/pitch-pack", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "hiring_manager_referral_email" in data
    assert "bounty_financials" in data


def test_api_geo_arbitrage_markets():
    response = client.get("/api/geo-arbitrage/markets")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["markets"]) >= 5


def test_api_geo_arbitrage_ppp_calc():
    payload = {
        "gross_annual_salary": 16000000.0,
        "market_id": "japan_tokyo",
        "current_inr_ctc_lpa": 35.0,
    }
    response = client.post("/api/geo-arbitrage/ppp-calc", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["financials"]["annual_savings_inr_lakhs"] > 0


def test_api_web3_bounties_listings():
    response = client.get("/api/web3-bounties/listings")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["bounties"]) >= 5


def test_api_web3_bounties_proposal():
    payload = {
        "bounty_id": "bounty_solana_blinks_01",
        "candidate_name": "Ujjwal",
        "proposed_architecture": "Async actor pool with sub-10ms P99 indexing.",
        "timeline_days": 10,
    }
    response = client.post("/api/web3-bounties/proposal", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "proposal_markdown" in data
    assert data["reward_usd"] == 5000
