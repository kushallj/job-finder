"""
Unit and Integration Tests for VC Intelligence Engine & Security Hardening
Tests SOLID principles, deduplication caching, scraper strategies, and security fixes.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, VCFirm, PortfolioCompany, CompanyFounder
from src.vc_intelligence.models import RawPortfolioCompany, RawFounder
from src.vc_intelligence.interfaces import IVCPortfolioScraper, IFounderEnricher
from src.vc_intelligence.scrapers.registry import VCScraperRegistry
from src.vc_intelligence.repository import VCIntelligenceRepository
from src.vc_intelligence.service import VCIntelligenceService
from src.auth.jwt_handler import create_access_token, decode_access_token
from main import app


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


# ─────────────────────────────────────────────────────────────────────────────
# 1. SOLID Architecture Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_registry_open_closed_principle():
    """
    Open/Closed Principle (OCP):
    Verify that a new VC scraper strategy can be added to the registry dynamically
    without changing existing orchestrators or registries.
    """
    class SequoiaScraper(IVCPortfolioScraper):
        @property
        def vc_name(self) -> str:
            return "Sequoia Capital"

        @property
        def slug(self) -> str:
            return "sequoia-capital"

        async def scrape_companies(self, max_companies: int = 50):
            return [
                RawPortfolioCompany(
                    name="Apple",
                    slug="apple",
                    domain="apple.com",
                    website="https://apple.com",
                    batch_or_year="1978",
                )
            ]

    VCScraperRegistry.register(SequoiaScraper)
    assert VCScraperRegistry.is_registered("sequoia-capital")
    instance = VCScraperRegistry.get("sequoia-capital")
    assert instance is not None
    assert instance.vc_name == "Sequoia Capital"


def test_liskov_substitution_principle():
    """
    Liskov Substitution Principle (LSP):
    Verify that all registered scrapers implement the IVCPortfolioScraper protocol.
    """
    for slug in VCScraperRegistry.list_available_slugs():
        scraper = VCScraperRegistry.get(slug)
        assert isinstance(scraper, IVCPortfolioScraper)
        assert hasattr(scraper, "vc_name")
        assert hasattr(scraper, "slug")
        assert hasattr(scraper, "scrape_companies")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Smart Deduplication & Caching Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_company_deduplication(in_memory_db):
    """
    Verify that syncing an existing company updates attributes rather than inserting duplicates.
    """
    repo = VCIntelligenceRepository(in_memory_db)
    firm = VCFirm(name="Test VC", slug="test-vc")
    in_memory_db.add(firm)
    in_memory_db.commit()

    raw_companies = [
        RawPortfolioCompany(
            name="Alpha Corp",
            slug="alpha-corp",
            domain="alpha.io",
            website="https://alpha.io",
            description="Initial description",
        )
    ]

    # First pass: creates company
    created, updated = repo.save_companies(firm.id, raw_companies)
    assert created == 1
    assert updated == 0
    assert in_memory_db.query(PortfolioCompany).count() == 1

    # Second pass with updated description: updates existing
    raw_companies[0].description = "Updated description"
    created2, updated2 = repo.save_companies(firm.id, raw_companies)
    assert created2 == 0
    assert updated2 == 1
    assert in_memory_db.query(PortfolioCompany).count() == 1

    company = in_memory_db.query(PortfolioCompany).first()
    assert company.description == "Updated description"


def test_founder_caching_and_30_day_deduplication(in_memory_db):
    """
    Verify that should_enrich_company skips enrichment if founders were cached recently (<30 days),
    minimizing external API costs (Firecrawl) and Playwright rate-limits.
    """
    repo = VCIntelligenceRepository(in_memory_db)
    firm = VCFirm(name="Test VC", slug="test-vc")
    in_memory_db.add(firm)
    in_memory_db.commit()

    company = PortfolioCompany(
        vc_firm_id=firm.id,
        name="Beta Corp",
        slug="beta-corp",
        domain="beta.com",
    )
    in_memory_db.add(company)
    in_memory_db.commit()

    # Brand new company has no founders -> should enrich
    assert repo.should_enrich_company(company.id, max_age_days=30) is True

    # Add enriched founder verified today
    repo.save_founders(
        company.id,
        [
            RawFounder(
                full_name="Jane Doe",
                title="Co-Founder & CEO",
                email="jane@beta.com",
                email_confidence=0.9,
            )
        ],
    )

    # After enrichment, should_enrich_company returns False (cached!)
    assert repo.should_enrich_company(company.id, max_age_days=30) is False

    # Simulate 31 days elapsed
    founder = in_memory_db.query(CompanyFounder).first()
    founder.last_verified_at = datetime.utcnow() - timedelta(days=31)
    in_memory_db.commit()

    # Now cache has expired -> should re-enrich
    assert repo.should_enrich_company(company.id, max_age_days=30) is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Security Hardening Tests (Evaluating Claude's Points)
# ─────────────────────────────────────────────────────────────────────────────

def test_jwt_alg_header_validation():
    """
    Verify that tokens forged with an unsupported algorithm (e.g. 'none' or 'RS256')
    are strictly rejected by decode_access_token.
    """
    import base64
    import json

    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "1", "exp": 9999999999}).encode()).decode().rstrip("=")
    forged_token = f"{header}.{payload}."

    with pytest.raises(ValueError, match="Unsupported JWT algorithm"):
        decode_access_token(forged_token)


def test_jwt_nbf_future_validation():
    """
    Verify that tokens with an 'nbf' (not before) claim in the future are rejected.
    """
    import time
    token = create_access_token(
        data={"sub": "1", "nbf": int(time.time()) + 1000},
        secret_key="test-secret-key-12345",
    )
    with pytest.raises(ValueError, match="Token is not valid yet"):
        decode_access_token(token, secret_key="test-secret-key-12345")


# ─────────────────────────────────────────────────────────────────────────────
# 4. API Endpoints Integration Test
# ─────────────────────────────────────────────────────────────────────────────

def test_vc_api_endpoints():
    """Verify VC FastAPI endpoints via TestClient with auth headers."""
    from src.auth.jwt_handler import create_access_token
    token = create_access_token(data={"sub": "1"})
    auth_headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)

    # 1. GET /api/vc/firms
    resp = client.get("/api/vc/firms", headers=auth_headers)
    assert resp.status_code == 200
    firms = resp.json()
    assert len(firms) >= 5
    firm_slugs = [f["slug"] for f in firms]
    assert "y-combinator" in firm_slugs
    assert "accel" in firm_slugs
    assert "blume-ventures" in firm_slugs
    assert "tiger-global" in firm_slugs
    assert "india-accelerator" in firm_slugs

    # 2. POST /api/vc/firms/{slug}/sync
    sync_resp = client.post("/api/vc/firms/accel/sync", json={"max_companies": 3, "enrich_contacts": True}, headers=auth_headers)
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["status"] == "success"
    assert sync_data["vc_slug"] == "accel"

    # 3. GET /api/vc/companies
    comp_resp = client.get("/api/vc/companies?vc_slug=accel", headers=auth_headers)
    assert comp_resp.status_code == 200
    companies = comp_resp.json()
    assert len(companies) > 0
    first_company = companies[0]
    assert "founders" in first_company

    # 4. GET /api/vc/export (CSV)
    export_csv = client.get("/api/vc/export?vc_slug=accel&format=csv", headers=auth_headers)
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers["content-type"]
    assert "founder_name" in export_csv.text
    assert "founder_email" in export_csv.text

    # 5. GET /api/vc/export (JSON)
    export_json = client.get("/api/vc/export?vc_slug=accel&format=json", headers=auth_headers)
    assert export_json.status_code == 200
    assert isinstance(export_json.json(), list)
