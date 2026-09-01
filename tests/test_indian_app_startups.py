import pytest
import httpx
from src.indian_app_startups import (
    INDIAN_APP_STARTUPS,
    get_indian_app_startup,
    filter_indian_startups,
)
from src.scrapers.indian_app_startups_scraper import IndianAppStartupsScraper


def test_catalog_contains_top_startups():
    assert len(INDIAN_APP_STARTUPS) >= 50

    phonepe = get_indian_app_startup("phonepe")
    assert phonepe is not None
    assert phonepe.category == "Fintech"
    assert "500M+" in phonepe.metrics_summary

    zepto = get_indian_app_startup("zepto")
    assert zepto is not None
    assert zepto.category == "Quick-Commerce"
    assert zepto.ats_platform == "lever"

    dream11 = get_indian_app_startup("dream11")
    assert dream11 is not None
    assert dream11.category == "Gaming"

    postman = get_indian_app_startup("postman")
    assert postman is not None
    assert postman.category == "SaaS & B2B"


def test_filter_indian_startups():
    fintechs = filter_indian_startups(category="Fintech")
    assert len(fintechs) >= 15
    assert any(f.name == "CRED" for f in fintechs)
    assert any(f.name == "Groww" for f in fintechs)

    top_downloads = filter_indian_startups(tier_category="top_downloads")
    assert len(top_downloads) >= 20

    top_revenue = filter_indian_startups(tier_category="top_revenue")
    assert len(top_revenue) >= 20


@pytest.mark.asyncio
async def test_indian_app_startups_scraper_greenhouse():
    async def handler(request: httpx.Request):
        if "boards-api.greenhouse.io/v1/boards/cred/jobs" in str(request.url):
            return httpx.Response(200, json={
                "jobs": [
                    {
                        "id": 998811,
                        "title": "Backend Engineer - High Throughput Ledger",
                        "content": "Work with Python, Go, and Redis clusters.",
                        "location": {"name": "Bengaluru, India"},
                        "absolute_url": "https://boards.greenhouse.io/cred/jobs/998811",
                        "updated_at": "2026-08-28T12:00:00Z"
                    }
                ]
            })
        return httpx.Response(404)

    scraper = IndianAppStartupsScraper(transport=httpx.MockTransport(handler))
    jobs = await scraper.scrape_all_startups(startup_ids=["cred"], keywords=["Backend"])
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Backend Engineer - High Throughput Ledger"
    assert jobs[0]["company"] == "CRED"
    assert "Indian-App-Startup" in jobs[0]["tags"]
    assert jobs[0]["startup_info"]["category"] == "Fintech"


@pytest.mark.asyncio
async def test_indian_app_startups_scraper_lever():
    async def handler(request: httpx.Request):
        if "api.lever.co/v0/postings/zepto" in str(request.url):
            return httpx.Response(200, json=[
                {
                    "id": "zp-101",
                    "text": "SDE II - Dispatch Engine",
                    "description": "Build real-time routing algorithms using Python & Kafka.",
                    "categories": {"location": "Bengaluru, India"},
                    "hostedUrl": "https://jobs.lever.co/zepto/zp-101",
                    "createdAt": 1724000000000
                }
            ])
        return httpx.Response(404)

    scraper = IndianAppStartupsScraper(transport=httpx.MockTransport(handler))
    jobs = await scraper.scrape_all_startups(startup_ids=["zepto"], keywords=["Dispatch"])
    assert len(jobs) == 1
    assert jobs[0]["title"] == "SDE II - Dispatch Engine"
    assert jobs[0]["company"] == "Zepto"
    assert jobs[0]["startup_info"]["category"] == "Quick-Commerce"
