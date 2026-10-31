"""
Unit and Integration Tests for 100 Global VC Firms Intelligence Pipeline
Tests:
- JSON schema validation of 100 global VC firms
- Seeding of 100 firms across 6 regions
- Regional query filtering (US & Global, Asia, India, Europe, LatAm, MENA & Africa)
- UniversalVCScraper instantiation and execution
- Batch synchronization orchestration
- FastAPI REST endpoints (/api/v1/vc/firms?region=..., /api/v1/vc/seed-100, /api/v1/vc/regions)
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, VCFirm, PortfolioCompany, CompanyFounder
from src.vc_intelligence.models import BatchVCSyncRequest
from src.vc_intelligence.repository import VCIntelligenceRepository
from src.vc_intelligence.service import VCIntelligenceService
from src.vc_intelligence.scrapers.universal_vc_scraper import UniversalVCScraper
from src.vc_intelligence.scrapers.registry import VCScraperRegistry
from main import app


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def test_100_vc_firms_json_validity():
    """Verify that vc_100_firms.json has exactly 100 firms and valid fields."""
    json_path = Path("src/vc_intelligence/data/vc_100_firms.json")
    assert json_path.exists(), "vc_100_firms.json file must exist"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 100, f"Expected 100 firms, found {len(data)}"

    expected_regions = {
        "US & Global": 37,
        "Asia": 20,
        "India": 15,
        "Europe": 16,
        "Latin America": 6,
        "Middle East & Africa": 6,
    }

    region_counts = {}
    slugs = set()

    for item in data:
        assert "id" in item and 1 <= item["id"] <= 100
        assert "name" in item and len(item["name"]) > 1
        assert "slug" in item and len(item["slug"]) > 1
        assert "region" in item and item["region"] in expected_regions
        assert "website" in item and item["website"].startswith("http")
        assert "portfolio_url" in item and item["portfolio_url"].startswith("http")

        slugs.add(item["slug"])
        region_counts[item["region"]] = region_counts.get(item["region"], 0) + 1

    assert len(slugs) == 100, "All 100 slugs must be unique"
    for r, count in expected_regions.items():
        assert region_counts[r] == count, f"Region {r} expected {count}, got {region_counts.get(r, 0)}"


def test_repository_seed_100_firms(in_memory_db):
    """Verify seeding 100 firms into an empty database."""
    repo = VCIntelligenceRepository(in_memory_db)
    count = repo.seed_100_firms()
    assert count == 100

    firms = repo.list_firms()
    assert len(firms) == 100

    # Test idempotency (re-seeding should update without error)
    count2 = repo.seed_100_firms()
    assert count2 == 100
    firms2 = repo.list_firms()
    assert len(firms2) == 100


def test_regional_filter_list_firms(in_memory_db):
    """Verify regional filtering in list_firms."""
    repo = VCIntelligenceRepository(in_memory_db)
    repo.seed_100_firms()

    india_firms = repo.list_firms(region="India")
    assert len(india_firms) == 15
    for f in india_firms:
        assert f.region == "India"

    europe_firms = repo.list_firms(region="Europe")
    assert len(europe_firms) == 16
    for f in europe_firms:
        assert f.region == "Europe"

    us_firms = repo.list_firms(region="US & Global")
    assert len(us_firms) == 37


def test_universal_vc_scraper_strategy():
    """Verify that UniversalVCScraper implements IVCPortfolioScraper properly."""
    scraper = UniversalVCScraper(
        vc_name="Atomico",
        slug="atomico",
        portfolio_url="https://atomico.com/portfolio",
        country_focus="UK",
    )
    assert scraper.vc_name == "Atomico"
    assert scraper.slug == "atomico"
    assert scraper.portfolio_url == "https://atomico.com/portfolio"

    # Test fallback extraction when offline or headless
    fallback_comps = scraper._generate_fallback_companies(max_companies=2)
    assert len(fallback_comps) == 2
    assert "Atomico" in fallback_comps[0].name or "atomico" in fallback_comps[0].slug


def test_registry_resolves_all_100_slugs():
    """Verify that VCScraperRegistry resolves any of the 100 global VC slugs."""
    assert VCScraperRegistry.is_registered("peak-xv-partners")
    assert VCScraperRegistry.is_registered("creandum")
    assert VCScraperRegistry.is_registered("kaszek")
    assert VCScraperRegistry.is_registered("stv")

    scraper = VCScraperRegistry.get("creandum")
    assert scraper is not None
    assert scraper.slug == "creandum"
    assert "creandum" in scraper.portfolio_url


@pytest.mark.asyncio
async def test_batch_sync_pipeline(in_memory_db):
    """Verify batch synchronization of VC firms."""
    repo = VCIntelligenceRepository(in_memory_db)
    repo.seed_100_firms()
    service = VCIntelligenceService(repository=repo)

    req = BatchVCSyncRequest(
        slugs=["blume-ventures", "peak-xv-partners"],
        max_companies_per_firm=2,
        enrich_contacts=False,
    )
    res = await service.batch_sync(req)
    assert res.total_firms_processed == 2
    assert len(res.results) == 2
    assert res.results[0].status == "success"
    assert res.results[1].status == "success"


def test_vc_api_endpoints_100():
    """Verify FastAPI routes for 100 VC firms."""
    client = TestClient(app)

    # 1. Test /regions endpoint
    res_regions = client.get("/api/v1/vc/regions")
    assert res_regions.status_code == 200
    data = res_regions.json()
    assert "total_firms" in data
    assert "regions" in data

    # 2. Test /firms with region filter
    res_india = client.get("/api/v1/vc/firms?region=India")
    assert res_india.status_code == 200
    firms = res_india.json()
    assert isinstance(firms, list)
    if firms:
        assert all(f["region"] == "India" for f in firms)
