import pytest
import httpx

from src.job_data_providers import JobDataAPIClient, AIDevBoardClient, normalize_job


def test_normalize_job_preserves_provider_intelligence():
    row = normalize_job({
        "id": 123,
        "ext_id": "abc",
        "title": "Senior Backend Engineer",
        "company": {"name": "Acme", "website": "https://acme.example"},
        "location": "Bengaluru",
        "application_url": "https://jobs.example/apply",
        "published": "2026-08-29T10:00:00Z",
        "salary_min": 1800000,
        "salary_max": 2600000,
        "salary_currency": "INR",
        "has_remote": True,
        "experience_level": "SE",
        "tags": [{"name": "Backend"}, "Python"],
    }, "jobdataapi")
    assert row["job_id"] == "jobdataapi:abc"
    assert row["company"] == "Acme"
    assert row["salary_min"] == 1800000
    assert row["has_remote"] is True
    assert row["tags"] == ["Backend", "Python"]


@pytest.mark.asyncio
async def test_jobdata_client_builds_documented_request():
    seen = {}
    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"results": [{"id": 1, "title": "Python Engineer", "company": {"name": "Acme"}}]})
    client = JobDataAPIClient(api_key="secret", transport=httpx.MockTransport(handler))
    rows = await client.search(query="Python Engineer", location="India", max_age=14, page_size=5)
    assert len(rows) == 1
    assert "Python" in seen["url"] and "Engineer" in seen["url"]
    assert "location=India" in seen["url"]
    assert "max_age=14" in seen["url"]
    assert seen["auth"] == "Api-Key secret"


@pytest.mark.asyncio
async def test_aidevboard_match_uses_candidate_profile():
    seen = {}
    async def handler(request: httpx.Request):
        seen["json"] = request.content.decode()
        return httpx.Response(200, json={"matches": [], "total": 0})
    client = AIDevBoardClient(api_key="aidv", transport=httpx.MockTransport(handler))
    result = await client.match(skills=["python", "fastapi"], salary_min=120000, workplace="remote", level="senior")
    assert result["total"] == 0
    import json
    parsed = json.loads(seen["json"])
    assert parsed["skills"] == ["python", "fastapi"]
    assert parsed["workplace"] == "remote"
