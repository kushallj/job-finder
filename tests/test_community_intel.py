import pytest
from fastapi.testclient import TestClient
from main import app
from src.community_intel.service import CommunityIntelService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_community_intel_service_harvest():
    service = CommunityIntelService()
    intel = await service.get_company_intel("Stripe", "Staff Backend Engineer")
    assert intel.company == "Stripe"
    assert len(intel.sources) >= 4
    assert len(intel.interview_debrief.rounds) >= 4
    assert len(intel.interview_debrief.common_questions) >= 2
    assert "Idempotent Payment" in str(intel.interview_debrief.system_design_topics)


def test_community_intel_api_endpoints(client):
    # 1. GET /api/community-intel/company/{company}
    res = client.get("/api/community-intel/company/OpenAI?role=Research%20Engineer")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["company"] == "OpenAI"
    assert "interview_debrief" in data
    assert len(data["sources"]) > 0

    # 2. POST /api/community-intel/harvest
    res_harvest = client.post("/api/community-intel/harvest", json={
        "company": "Figma",
        "role_category": "Frontend Systems",
        "force_refresh": True,
    })
    assert res_harvest.status_code == 200
    assert res_harvest.json()["company"] == "Figma"
