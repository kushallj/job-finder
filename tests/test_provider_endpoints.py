import pytest
from datetime import datetime
from fastapi.testclient import TestClient


def test_provider_sync_endpoint_contract(monkeypatch, tmp_path):
    import main
    from src import config
    from src.database import engine

    from src.job_sources import FetchReport, JobRecord, SearchQuery, SourceReport, Tier

    async def fake_fetch_jobs(query, sources=None, **kwargs):
        rows = [
            ({"job_id": "jobdataapi:1", "title": "Senior Python Engineer", "company": "Acme", "location": "India",
              "description": "Python FastAPI", "url": "https://example.com/1", "posted_date": datetime.utcnow(),
              "provider_id": "1", "tags": ["Python"], "provider_payload": {"id": 1}}, "jobdataapi"),
            ({"job_id": "aidevboard:2", "title": "AI Engineer", "company": "Beta", "location": "Remote",
              "description": "LLM Python", "url": "https://example.com/2", "posted_date": datetime.utcnow(),
              "provider_id": "2", "tags": ["llm"], "provider_payload": {"id": 2}}, "aidevboard"),
        ]
        records = [JobRecord.from_dict(r, src) for r, src in rows]
        sources = [SourceReport("jobdataapi", Tier.OFFICIAL_API, "ok", 1), SourceReport("aidevboard", Tier.OFFICIAL_API, "ok", 1)]
        return FetchReport(query=query, records=records, sources=sources)
    monkeypatch.setattr(main, "fetch_jobs", fake_fetch_jobs)
    with TestClient(main.app) as client:
        response = client.post("/api/providers/sync", json={"query": "engineer", "location": "India", "limit": 10})
        assert response.status_code == 200
        body = response.json()
        assert body["total_fetched"] == 2
        assert body["total_inserted"] + body["total_updated"] == 2
        assert {x["provider"] for x in body["sources"]} == {"jobdataapi", "aidevboard"}
