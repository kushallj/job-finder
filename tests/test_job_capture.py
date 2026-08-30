import uuid
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_job_capture_endpoint(client):
    unique_suffix = uuid.uuid4().hex[:8]
    test_url = f"https://www.linkedin.com/jobs/view/test-unique-{unique_suffix}"
    
    # 1. First capture: creates new Job
    req = {
        "title": "Principal Python Systems Architect",
        "company": f"CaptureCorp-{unique_suffix}",
        "location": "Remote",
        "description": "Architect high-performance distributed pipelines with Python, FastAPI, and Redis.",
        "url": test_url,
        "source": "linkedin_extension",
        "score": False,
    }
    
    res = client.post("/api/jobs/capture", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["job"]["title"] == "Principal Python Systems Architect"
    assert data["job"]["company"] == f"CaptureCorp-{unique_suffix}"
    assert data["already_existed"] is False

    # 2. Second capture: deduplicates by URL
    res2 = client.post("/api/jobs/capture", json=req)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "success"
    assert data2["already_existed"] is True
    assert data2["job"]["id"] == data["job"]["id"]


def test_job_capture_validation(client):
    # Missing required title or url
    bad_req = {
        "company": "NoTitleCorp",
    }
    res = client.post("/api/jobs/capture", json=bad_req)
    assert res.status_code == 422
