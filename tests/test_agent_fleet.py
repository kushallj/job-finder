import pytest
from fastapi.testclient import TestClient
from main import app
from src.agent_fleet.service import AgentFleetService
from src.agent_fleet.models import AgentFleetConfig


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_agent_fleet_service_cycle():
    service = AgentFleetService()
    cfg = AgentFleetConfig(
        google_gemini_api_key="AIzaSyDummyTestKey123456789",
        autonomous_mode=True,
        execution_interval_hours=4,
    )
    service.update_config(cfg)
    result = await service.run_cycle(cfg)

    assert result.has_api_key is True
    assert result.is_active is True
    assert result.total_actions_executed >= 4
    assert len(result.agent_runs) == 4
    agent_names = [a.agent_name for a in result.agent_runs]
    assert "signal_scout" in agent_names
    assert "resume_tailor" in agent_names


def test_agent_fleet_api_endpoints(client):
    # 1. GET /api/fleet/config
    res_get = client.get("/api/fleet/config")
    assert res_get.status_code == 200

    # 2. POST /api/fleet/config
    res_post = client.post("/api/fleet/config", json={
        "google_gemini_api_key": "AIzaSyTestApiKey987654321",
        "autonomous_mode": True,
        "execution_interval_hours": 8,
        "target_roles": ["Staff Backend Engineer"],
    })
    assert res_post.status_code == 200
    assert res_post.json()["execution_interval_hours"] == 8

    # 3. POST /api/fleet/run-cycle
    res_run = client.post("/api/fleet/run-cycle", json={
        "google_gemini_api_key": "AIzaSyTestApiKey987654321",
        "autonomous_mode": True,
    })
    assert res_run.status_code == 200
    data = res_run.json()
    assert data["status"] == "success"
    assert "cycle" in data
    assert data["cycle"]["total_actions_executed"] >= 4
