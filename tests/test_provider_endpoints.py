import pytest
from datetime import datetime
from fastapi.testclient import TestClient


def test_provider_sync_endpoint_contract(monkeypatch, tmp_path):
    import main
    from src import config
    from src.database import engine

    async def fake_search_all(**kwargs):
        return {
            "jobdataapi": [{
                "job_id": "jobdataapi:1", "title": "Senior Python Engineer", "company": "Acme",
                "location": "India", "description": "Python FastAPI", "url": "https://example.com/1",
                "source": "jobdataapi", "posted_date": datetime.utcnow(), "provider_id": "1",
                "tags": ["Python"], "provider_payload": {"id": 1},
            }],
            "aidevboard": [{
                "job_id": "aidevboard:2", "title": "AI Engineer", "company": "Beta",
                "location": "Remote", "description": "LLM Python", "url": "https://example.com/2",
                "source": "aidevboard", "posted_date": datetime.utcnow(), "provider_id": "2",
                "tags": ["llm"], "provider_payload": {"id": 2},
            }],
        }
    monkeypatch.setattr(main, "search_all", fake_search_all)
    with TestClient(main.app) as client:
        response = client.post("/api/providers/sync", json={"query": "engineer", "location": "India", "limit": 10})
        assert response.status_code == 200
        body = response.json()
        assert body["total_fetched"] == 2
        assert body["total_inserted"] + body["total_updated"] == 2
        assert {x["provider"] for x in body["sources"]} == {"jobdataapi", "aidevboard"}
