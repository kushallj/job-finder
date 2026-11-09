import pytest
from src.autonomous_job_crawler import (
    extract_tech_tags_and_seniority,
    AutonomousJobCrawler,
    autonomous_crawler,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Job, fit_to_columns


def _isolated_session():
    """In-memory DB: tests must not write into whatever DATABASE_URL .env points at."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_fit_to_columns_clips_to_declared_lengths():
    row = fit_to_columns(Job, {"experience_level": "x" * 250, "salary_currency": "EURO-DOLLARS", "description": "y" * 5000})
    assert len(row["experience_level"]) == 100   # String(100)
    assert row["salary_currency"] == "EURO-DOLLA"  # String(10)
    assert len(row["description"]) == 5000      # Text: unlimited, untouched
    assert len("Lead / Staff / Principal") <= Job.__table__.c.experience_level.type.length


def test_tech_stack_and_seniority_extraction():
    title = "Staff Backend Engineer - Distributed Systems & Kafka"
    desc = "We build high-throughput microservices using Python, FastAPI, Golang, PostgreSQL, and AWS EC2 with Kubernetes."

    tags, seniority = extract_tech_tags_and_seniority(title, desc)
    assert seniority == "Lead / Staff / Principal"
    assert "Python" in tags
    assert "Go / Golang" in tags
    assert "Distributed Systems" in tags
    assert "Kafka / Event-Driven" in tags
    assert "AWS / Cloud" in tags
    assert "Kubernetes / Docker" in tags


def test_tech_stack_ai_and_mobile_extraction():
    title = "Senior GenAI & iOS Mobile Engineer"
    desc = "Develop LLM powered features using PyTorch, LangChain, RAG pipelines and Swift iOS apps."

    tags, seniority = extract_tech_tags_and_seniority(title, desc)
    assert seniority == "Senior"
    assert "GenAI & LLMs" in tags
    assert "AI / Machine Learning" in tags
    assert "Mobile (iOS / Android)" in tags


def test_crawler_upsert_job_record():
    db = _isolated_session()
    crawler = AutonomousJobCrawler()

    test_raw = {
        "id": "test_crawler_job_9988",
        "job_id": "test_crawler_job_9988",
        "title": "Lead Software Engineer - Core Switch",
        "company": "Top FinTech Corp",
        "location": "Bengaluru, India",
        "description": "Architect high availability payment switches using Python and Redis.",
        "url": "https://careers.topfintech.com/jobs/9988",
        "source": "autonomous_crawler_test",
        "has_remote": True,
        "salary_min": 5000000.0,
        "salary_max": 6500000.0,
        "salary_currency": "INR",
        "tags": ["Tier-1", "FinTech"],
    }

    try:
        # Clean existing test record if any
        db.query(Job).filter(Job.job_id == "test_crawler_job_9988").delete()
        db.commit()

        # Insert
        ins, upd = crawler.upsert_job_record(db, test_raw)
        assert ins is True
        assert upd is False

        # Verify DB
        job = db.query(Job).filter(Job.job_id == "test_crawler_job_9988").first()
        assert job is not None
        assert job.company == "Top FinTech Corp"
        assert job.experience_level == "Lead / Staff / Principal"
        assert "Python" in job.tags
        assert job.salary_min == 5000000.0

        # Update
        test_raw["title"] = "Principal Software Architect - Core Switch"
        ins, upd = crawler.upsert_job_record(db, test_raw)
        assert ins is False
        assert upd is True

        job = db.query(Job).filter(Job.job_id == "test_crawler_job_9988").first()
        assert job.title == "Principal Software Architect - Core Switch"
    finally:
        db.query(Job).filter(Job.job_id == "test_crawler_job_9988").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_crawler_lifecycle():
    crawler = AutonomousJobCrawler()
    assert crawler.is_running is False
    status = crawler.get_status()
    assert status["status"] == "stopped"

    # Start
    started = crawler.start_daemon(interval_seconds=1000)
    assert started is True
    assert crawler.is_running is True

    # Stop
    stopped = crawler.stop_daemon()
    assert stopped is True
    assert crawler.is_running is False
