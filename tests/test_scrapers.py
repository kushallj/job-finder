"""Tests for the base scraper module."""

import pytest
from typing import Dict, List

from src.scrapers.base import BaseScraper


# ---------------------------------------------------------------------------
# Concrete test implementation of BaseScraper
# ---------------------------------------------------------------------------


class ConcreteScraperImpl(BaseScraper):
    """Concrete implementation of BaseScraper for testing purposes."""

    def __init__(self):
        super().__init__(source_name="test_source")

    async def fetch_jobs(self, **kwargs) -> List[Dict]:
        """Return a dummy list of jobs."""
        return [
            {
                "title": "Software Engineer",
                "company": "TestCorp",
                "location": "Remote",
                "url": "https://example.com/job/1",
                "date": "2026-07-30",
            }
        ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBaseScraperAbstract:
    """Tests for BaseScraper abstract behavior."""

    def test_base_scraper_is_abstract(self):
        """Cannot instantiate BaseScraper without implementing fetch_jobs."""
        with pytest.raises(TypeError):
            BaseScraper(source_name="invalid")


class TestGenerateJobId:
    """Tests for BaseScraper.generate_job_id."""

    def setup_method(self):
        """Set up a concrete scraper instance for each test."""
        self.scraper = ConcreteScraperImpl()

    def test_generate_job_id_deterministic(self):
        """Same input produces the same hash."""
        job = {
            "title": "Backend Developer",
            "company": "Acme Inc",
            "location": "New York",
            "url": "https://acme.com/jobs/42",
            "date": "2026-07-15",
        }
        id1 = self.scraper.generate_job_id(job)
        id2 = self.scraper.generate_job_id(job)
        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) == 32  # MD5 hex digest is 32 chars

    def test_generate_job_id_different_inputs(self):
        """Different inputs produce different hashes."""
        job1 = {
            "title": "Backend Developer",
            "company": "Acme Inc",
            "location": "New York",
            "url": "https://acme.com/jobs/42",
            "date": "2026-07-15",
        }
        job2 = {
            "title": "Frontend Developer",
            "company": "Acme Inc",
            "location": "New York",
            "url": "https://acme.com/jobs/43",
            "date": "2026-07-15",
        }
        id1 = self.scraper.generate_job_id(job1)
        id2 = self.scraper.generate_job_id(job2)
        assert id1 != id2

    def test_generate_job_id_handles_empty(self):
        """Empty dict still generates a valid MD5 hash."""
        job = {}
        job_id = self.scraper.generate_job_id(job)
        assert isinstance(job_id, str)
        assert len(job_id) == 32  # Valid MD5 hex digest


class TestNormalizeJob:
    """Tests for BaseScraper.normalize_job."""

    def setup_method(self):
        """Set up a concrete scraper instance for each test."""
        self.scraper = ConcreteScraperImpl()

    def test_normalize_job_sets_job_id(self):
        """Job without job_id gets one assigned."""
        job = {
            "title": "Data Scientist",
            "company": "DataCo",
            "location": "SF",
            "url": "https://dataco.com/jobs/1",
            "date": "2026-06-01",
        }
        normalized = self.scraper.normalize_job(job)
        assert "job_id" in normalized
        assert isinstance(normalized["job_id"], str)
        assert len(normalized["job_id"]) == 32

    def test_normalize_job_preserves_existing_id(self):
        """Job with existing job_id keeps it unchanged."""
        job = {
            "title": "Data Scientist",
            "company": "DataCo",
            "location": "SF",
            "url": "https://dataco.com/jobs/1",
            "date": "2026-06-01",
            "job_id": "custom_id_12345",
        }
        normalized = self.scraper.normalize_job(job)
        assert normalized["job_id"] == "custom_id_12345"

    def test_normalize_job_sets_source(self):
        """Job without source gets source_name assigned."""
        job = {
            "title": "ML Engineer",
            "company": "AILab",
            "location": "Remote",
            "url": "https://ailab.io/careers/5",
            "date": "2026-07-20",
        }
        normalized = self.scraper.normalize_job(job)
        assert normalized["source"] == "test_source"

    def test_normalize_job_preserves_source(self):
        """Job with existing source keeps it unchanged."""
        job = {
            "title": "ML Engineer",
            "company": "AILab",
            "location": "Remote",
            "url": "https://ailab.io/careers/5",
            "date": "2026-07-20",
            "source": "custom_source",
        }
        normalized = self.scraper.normalize_job(job)
        assert normalized["source"] == "custom_source"
