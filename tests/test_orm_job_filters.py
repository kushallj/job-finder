"""
Unit tests for ORM job queries and multi-facet filtering in /api/jobs
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_orm_get_jobs_basic():
    response = client.get("/api/jobs?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "jobs" in data
    assert "pagination" in data
    assert data["pagination"]["limit"] == 5
    assert data["pagination"]["total"] >= 1


def test_orm_filter_by_region():
    # Test India filter
    res_india = client.get("/api/jobs?region=india&limit=10")
    assert res_india.status_code == 200
    data_india = res_india.json()
    assert data_india["status"] == "success"

    # Test Remote filter
    res_remote = client.get("/api/jobs?region=remote&limit=10")
    assert res_remote.status_code == 200
    data_remote = res_remote.json()
    assert data_remote["status"] == "success"


def test_orm_filter_by_experience_and_yoe():
    # Test by Senior experience
    res_sr = client.get("/api/jobs?experience_level=senior&limit=10")
    assert res_sr.status_code == 200
    data_sr = res_sr.json()
    assert data_sr["status"] == "success"

    # Test by numeric YOE
    res_yoe = client.get("/api/jobs?years_of_experience=4&limit=10")
    assert res_yoe.status_code == 200
    data_yoe = res_yoe.json()
    assert data_yoe["status"] == "success"


def test_orm_filter_by_date_posted():
    res_24h = client.get("/api/jobs?date_posted=24h&limit=10")
    assert res_24h.status_code == 200
    data_24h = res_24h.json()
    assert data_24h["status"] == "success"

    res_7d = client.get("/api/jobs?date_posted=7d&limit=10")
    assert res_7d.status_code == 200
    data_7d = res_7d.json()
    assert data_7d["status"] == "success"


def test_orm_filter_by_tech_stack_and_source():
    res_tech = client.get("/api/jobs?tech_stack=Python&limit=10")
    assert res_tech.status_code == 200
    data_tech = res_tech.json()
    assert data_tech["status"] == "success"

    res_src = client.get("/api/jobs?source=greenhouse_direct&limit=10")
    assert res_src.status_code == 200
    data_src = res_src.json()
    assert data_src["status"] == "success"
