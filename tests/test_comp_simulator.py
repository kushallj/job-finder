import pytest
from fastapi.testclient import TestClient
from main import app
from src.comp_simulator.models import OfferPackage
from src.comp_simulator.engine import CompensationSimulatorEngine


@pytest.fixture
def client():
    return TestClient(app)


def test_standard_4yr_simulation():
    engine = CompensationSimulatorEngine()
    offer = OfferPackage(
        company="Stripe",
        role_title="Staff Engineer",
        base_salary=220000,
        signon_bonus=30000,
        target_bonus_pct=15.0,
        equity_grant_usd=400000,
        vesting_schedule="standard_4yr_25",
        estimated_tax_rate=35.0,
    )
    res = engine.simulate_package(offer)
    assert res.four_year_total_pre_tax > 1200000
    assert len(res.yearly_breakdowns) == 4
    assert res.yearly_breakdowns[0].equity_vested == 100000.0
    assert res.negotiation_counter_target > res.average_annual_comp


def test_amazon_backloaded_simulation():
    engine = CompensationSimulatorEngine()
    offer = OfferPackage(
        company="Amazon",
        role_title="Senior SDE",
        base_salary=185000,
        signon_bonus=65000,
        target_bonus_pct=0.0,
        equity_grant_usd=300000,
        vesting_schedule="amazon_5_15_40_40",
    )
    res = engine.simulate_package(offer)
    assert res.yearly_breakdowns[0].equity_vested == 15000.0  # 5% of 300k
    assert res.yearly_breakdowns[2].equity_vested == 120000.0 # 40% of 300k
    assert "Backloaded Equity Warning" in res.negotiation_advice


def test_comp_api_endpoints(client):
    # 1. POST /api/comp/simulate
    res = client.post("/api/comp/simulate", json={
        "company": "OpenAI",
        "role_title": "Research Engineer",
        "base_salary": 250000,
        "signon_bonus": 50000,
        "equity_grant_usd": 600000,
        "startup_exit_multiple": 2.0,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["average_annual_comp"] > 400000

    # 2. POST /api/comp/compare
    res_cmp = client.post("/api/comp/compare", json={
        "offers": [
            {
                "company": "Figma",
                "role_title": "Staff Engineer",
                "base_salary": 230000,
                "equity_grant_usd": 400000,
            },
            {
                "company": "Stripe",
                "role_title": "Staff Engineer",
                "base_salary": 240000,
                "equity_grant_usd": 450000,
            }
        ]
    })
    assert res_cmp.status_code == 200
    assert len(res_cmp.json()) == 2
