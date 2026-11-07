"""
tests/test_startups_gallery_miner.py — Unit Tests for startups.gallery Registry, Miner, and API
"""
import pytest
from unittest.mock import AsyncMock, patch

from src.database import SessionLocal, init_db
from src.models import Contact, StartupsGalleryCompanyRecord
from src.company_sources.miners.startups_gallery_miner import (
    StartupsGalleryMiner,
    startups_gallery_miner,
)
from src.company_sources.registries.startups_gallery_registry import (
    filter_by_category,
    filter_by_location,
    get_all_startups_gallery_companies,
    get_category_breakdown,
    get_company_by_slug,
    search_startups,
)


def test_registry_loads_1369_companies():
    companies = get_all_startups_gallery_companies()
    assert len(companies) >= 1300, f"Expected ~1,369 companies, got {len(companies)}"

    # Check prominent startups
    slugs = {c.slug for c in companies}
    assert "doppel" in slugs
    assert "toma" in slugs
    assert "pulley" in slugs


def test_search_and_filter_helpers():
    doppel = get_company_by_slug("doppel")
    assert doppel is not None
    assert doppel.name == "Doppel"
    assert "doppel.com" in doppel.domain

    ai_companies = filter_by_category("AI")
    assert len(ai_companies) >= 50

    sf_companies = filter_by_location("San Francisco")
    assert len(sf_companies) >= 50

    search_res = search_startups("pulley")
    assert any(c.slug == "pulley" for c in search_res)

    breakdown = get_category_breakdown()
    assert "AI" in breakdown
    assert sum(breakdown.values()) >= 1300


def test_compose_startups_gallery_outreach():
    miner = StartupsGalleryMiner()
    contact = {
        "name": "Kevin Tian",
        "title": "Co-Founder & CEO",
        "company": "Doppel",
        "category": "AI",
        "funding": "Raised $70M Series C",
    }
    subj, text, html = miner.compose_startups_gallery_outreach(contact)
    assert "Doppel" in subj
    assert "Kevin" in text
    assert "Co-Founder & CEO" in text
    assert "$70M Series C" in text
    assert "Python, FastAPI, React" in text
    assert "<html>" in html


def test_miner_status_and_database_seeding():
    init_db()
    status = startups_gallery_miner.get_status()
    assert status["total_companies"] >= 1300
    assert status["pending_companies"] >= 0
    assert "completion_percentage" in status


@pytest.mark.asyncio
async def test_batch_mining_advances_unmined_companies():
    init_db()
    miner = StartupsGalleryMiner()

    mock_contacts = [
        {
            "name": "Jane Founder",
            "title": "Founder & CEO",
            "company": "TestCo",
            "email": "jane@testco.com",
            "linkedin_url": "https://linkedin.com/in/janefounder",
        }
    ]

    with patch.object(miner, "search_linkedin_decision_makers", new=AsyncMock(return_value=mock_contacts)):
        with patch.object(miner, "search_twitter_handle", new=AsyncMock(return_value="https://x.com/janefounder")):
            # Batch 1
            res1 = await miner.batch_mine(batch_size=2, extract_twitter=True)
            assert res1["companies_processed"] == 2
            assert res1["founders_mined"] == 2

            # Check that database recorded X (Twitter) URL
            with SessionLocal() as db:
                c = db.query(Contact).filter(Contact.email == "jane@testco.com").first()
                assert c is not None
                assert c.twitter_url == "https://x.com/janefounder"

            # Batch 2: Should advance to the NEXT unmined companies
            res2 = await miner.batch_mine(batch_size=2, extract_twitter=False)
            assert res2["companies_processed"] == 2


def test_fastapi_endpoints():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Status endpoint
    resp = client.get("/api/startups-gallery/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_companies"] >= 1300

    # Categories breakdown
    resp = client.get("/api/startups-gallery/categories")
    assert resp.status_code == 200
    cats = resp.json()
    assert "AI" in cats

    # Companies paginated list
    resp = client.get("/api/startups-gallery/companies?page=1&limit=10")
    assert resp.status_code == 200
    comps = resp.json()
    assert comps["total"] >= 1300
    assert len(comps["companies"]) == 10
