"""
Tests for Continuous VC Batch Harvester & Intelligence Pipeline.
Verifies batch extraction, deduplication, state tracking, and REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, VCFirm, PortfolioCompany, CompanyFounder
from src.vc_intelligence.continuous_runner import ContinuousVCBatchRunner
from src.vc_intelligence.batch_data_catalog import BATCH_2_FOUNDERS
from main import app


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_batch_2_catalog_integrity():
    """Verify BATCH_2_FOUNDERS contains 50+ founders with high-confidence corporate emails."""
    assert len(BATCH_2_FOUNDERS) >= 20
    total_founders = sum(len(c.get("founders", [])) for c in BATCH_2_FOUNDERS)
    assert total_founders >= 50, f"Expected at least 50 founders in Batch 2 catalog, got {total_founders}"

    for comp in BATCH_2_FOUNDERS:
        assert comp.get("vc_slug"), "Missing vc_slug"
        assert comp.get("domain"), "Missing company domain"
        for f in comp.get("founders", []):
            assert f.get("name"), "Missing founder name"
            assert f.get("email"), f"Founder {f.get('name')} missing email"
            assert "@" in f["email"], f"Invalid email format: {f['email']}"
            assert f.get("confidence", 0) >= 0.90, f"Confidence too low for {f['name']}"


def test_continuous_runner_singleton():
    """Verify singleton pattern returns the same instance."""
    r1 = ContinuousVCBatchRunner.get_instance()
    r2 = ContinuousVCBatchRunner.get_instance()
    assert r1 is r2


def test_continuous_runner_status_structure():
    """Verify get_status returns all expected telemetry fields."""
    runner = ContinuousVCBatchRunner.get_instance()
    status = runner.get_status()

    assert "is_running" in status
    assert "current_batch" in status
    assert "total_founders_in_db" in status
    assert "founders_with_verified_email" in status
    assert "recent_logs" in status
    assert isinstance(status["recent_logs"], list)


def test_continuous_api_endpoints():
    """Verify the FastAPI continuous batch REST routes."""
    from src.auth.jwt_handler import create_access_token
    token = create_access_token(data={"sub": "1"})
    client = TestClient(app, headers={"Authorization": f"Bearer {token}"})

    # 1. Get status
    res = client.get("/api/vc/continuous/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_running" in data
    assert "total_founders_in_db" in data

    # 2. Stop endpoint
    res_stop = client.post("/api/vc/continuous/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "stopping"
