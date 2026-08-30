import pytest
from fastapi.testclient import TestClient
from main import app
from src.market_radar.service import MarketRadarService


@pytest.fixture
def client():
    return TestClient(app)


def test_market_radar_service():
    service = MarketRadarService()
    radar = service.get_market_radar()
    assert radar.usd_to_inr_rate > 80.0
    assert len(radar.remote_global_roles) >= 3
    assert len(radar.top_gcc_hubs) >= 3
    assert "Bangalore" in str(radar.top_gcc_hubs)


def test_market_radar_api_endpoint(client):
    res = client.get("/api/market-radar/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["usd_to_inr_rate"] > 80.0
    assert len(data["remote_global_roles"]) >= 2
    assert len(data["top_gcc_hubs"]) >= 2
