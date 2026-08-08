"""
Tests for the Scraper Orchestrator.

Tests:
- Unified scraper interface
- Parallel scraping across platforms
- Job deduplication based on job_id
- Result aggregation
- Error handling for scraper failures

Requirements: 10.1, 10.2, 10.3, 10.5
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.scrapers.orchestrator import (
    ScraperOrchestrator,
    ScraperConfig,
    ScraperResult,
    OrchestratorResult,
    ScraperStatus,
    NormalizedJob,
    JobDeduplicator,
    UnifiedScraperInterface,
    create_orchestrator,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_jobs():
    """Sample job data for testing."""
    return [
        {
            "job_id": "job1",
            "title": "Python Developer",
            "company": "TechCorp",
            "location": "Remote",
            "description": "Build Python applications",
            "url": "https://techcorp.com/jobs/1",
            "source": "test_scraper",
        },
        {
            "job_id": "job2",
            "title": "Backend Engineer",
            "company": "StartupXYZ",
            "location": "San Francisco",
            "description": "Backend development with Python",
            "url": "https://startupxyz.com/jobs/2",
            "source": "test_scraper",
        },
    ]


@pytest.fixture
def duplicate_jobs():
    """Jobs with duplicates for deduplication testing."""
    return [
        NormalizedJob(
            job_id="job1",
            title="Python Developer",
            company="TechCorp",
            location="Remote",
            description="Build Python apps",
            url="https://techcorp.com/jobs/1",
            source="scraper1",
        ),
        # Same job_id - duplicate
        NormalizedJob(
            job_id="job1",
            title="Python Developer",
            company="TechCorp",
            location="Remote",
            description="Build Python apps",
            url="https://techcorp.com/jobs/1",
            source="scraper2",
        ),
        # Different job_id but same title+company - duplicate
        NormalizedJob(
            job_id="job2",
            title="Python Developer",
            company="TechCorp",
            location="Remote",
            description="Build Python apps",
            url="https://techcorp.com/jobs/different",
            source="scraper3",
        ),
        # Unique job
        NormalizedJob(
            job_id="job3",
            title="Backend Engineer",
            company="StartupXYZ",
            location="San Francisco",
            description="Backend development",
            url="https://startupxyz.com/jobs/3",
            source="scraper1",
        ),
    ]


@pytest.fixture
def mock_scraper_config():
    """Test configuration with minimal settings."""
    return ScraperConfig(
        enabled_scrapers=["multi_platform", "ats"],
        max_concurrent_scrapers=2,
        scraper_timeout_seconds=10.0,
        max_jobs_per_scraper=20,
        enable_deduplication=True,
        parallel_execution=True,
    )


# =============================================================================
# Test JobDeduplicator
# =============================================================================

class TestJobDeduplicator:
    """Tests for job deduplication logic (Requirement 10.3)."""
    
    def test_deduplicator_removes_duplicate_job_ids(self, duplicate_jobs):
        """Test that duplicate job_ids are removed."""
        deduplicator = JobDeduplicator()
        unique, removed = deduplicator.deduplicate(duplicate_jobs)
        
        # Should have 2 unique jobs (job1 and job3), removed 2 duplicates
        assert len(unique) == 2
        assert removed == 2
        
        # Check that unique jobs have different job_ids or are genuinely unique
        job_ids = [j.job_id for j in unique]
        # job1 appears once, job3 appears once
        assert "job3" in job_ids
    
    def test_deduplicator_handles_url_duplicates(self):
        """Test URL-based deduplication."""
        deduplicator = JobDeduplicator()
        
        job1 = NormalizedJob(
            job_id="different1",
            title="Job A",
            company="Company A",
            location="Remote",
            description="Description",
            url="https://example.com/jobs/123",
            source="scraper1",
        )
        job2 = NormalizedJob(
            job_id="different2",
            title="Job B",
            company="Company B",
            location="Remote",
            description="Description",
            url="https://example.com/jobs/123?utm=test",  # Same URL with params
            source="scraper2",
        )
        
        unique, removed = deduplicator.deduplicate([job1, job2])
        assert len(unique) == 1
        assert removed == 1

    
    def test_deduplicator_preserves_unique_jobs(self):
        """Test that unique jobs are preserved."""
        deduplicator = JobDeduplicator()
        
        jobs = [
            NormalizedJob(
                job_id=f"unique_{i}",
                title=f"Job {i}",
                company=f"Company {i}",
                location="Remote",
                description="Description",
                url=f"https://example.com/jobs/{i}",
                source="scraper1",
            )
            for i in range(5)
        ]
        
        unique, removed = deduplicator.deduplicate(jobs)
        assert len(unique) == 5
        assert removed == 0
    
    def test_deduplicator_reset(self):
        """Test that reset clears all indexes."""
        deduplicator = JobDeduplicator()
        
        job = NormalizedJob(
            job_id="test1",
            title="Test Job",
            company="Test Company",
            location="Remote",
            description="Description",
            url="https://example.com/jobs/1",
            source="test",
        )
        
        deduplicator.add(job)
        assert deduplicator.is_duplicate(job)
        
        deduplicator.reset()
        assert not deduplicator.is_duplicate(job)


# =============================================================================
# Test ScraperOrchestrator
# =============================================================================

class TestScraperOrchestrator:
    """Tests for the unified scraper orchestrator."""
    
    def test_orchestrator_initialization(self, mock_scraper_config):
        """Test orchestrator initializes with correct scrapers."""
        orchestrator = ScraperOrchestrator(mock_scraper_config)
        
        enabled = orchestrator.get_enabled_scrapers()
        assert "multi_platform" in enabled
        assert "ats" in enabled
    
    def test_orchestrator_available_scrapers(self):
        """Test available scrapers list (Requirement 10.1)."""
        config = ScraperConfig(enabled_scrapers=[])
        orchestrator = ScraperOrchestrator(config)
        
        available = orchestrator.get_available_scrapers()
        assert "multi_platform" in available
        assert "ats" in available
        assert "jobspy" in available
        assert "google_careers" in available
        assert "foorilla" in available
    
    def test_orchestrator_enable_disable_scrapers(self):
        """Test enabling and disabling scrapers."""
        config = ScraperConfig(enabled_scrapers=[])
        orchestrator = ScraperOrchestrator(config)
        
        # Initially no scrapers enabled
        assert len(orchestrator.get_enabled_scrapers()) == 0
        
        # Enable a scraper
        assert orchestrator.enable_scraper("ats")
        assert "ats" in orchestrator.get_enabled_scrapers()
        
        # Disable the scraper
        assert orchestrator.disable_scraper("ats")
        assert "ats" not in orchestrator.get_enabled_scrapers()

    
    @pytest.mark.asyncio
    async def test_orchestrator_handles_scraper_failure(self):
        """Test graceful error handling (Requirement 10.5)."""
        config = ScraperConfig(
            enabled_scrapers=["ats"],
            scraper_timeout_seconds=1.0,
        )
        orchestrator = ScraperOrchestrator(config)
        
        # Mock the ATS scraper to fail
        class FailingScraper(UnifiedScraperInterface):
            @property
            def name(self):
                return "ats"
            
            async def search(self, query, location="", max_results=50):
                raise Exception("Simulated failure")
        
        orchestrator._scrapers["ats"] = FailingScraper()
        
        result = await orchestrator.search("Python Developer")
        
        # Should complete without raising exception
        assert isinstance(result, OrchestratorResult)
        assert len(result.errors) > 0
        assert any(sr.status == ScraperStatus.FAILED for sr in result.scraper_results)
    
    @pytest.mark.asyncio
    async def test_orchestrator_handles_timeout(self):
        """Test timeout handling (Requirement 10.5)."""
        config = ScraperConfig(
            enabled_scrapers=["ats"],
            scraper_timeout_seconds=0.1,  # Very short timeout
        )
        orchestrator = ScraperOrchestrator(config)
        
        # Mock a slow scraper
        class SlowScraper(UnifiedScraperInterface):
            @property
            def name(self):
                return "ats"
            
            async def search(self, query, location="", max_results=50):
                await asyncio.sleep(5)  # Way longer than timeout
                return []
        
        orchestrator._scrapers["ats"] = SlowScraper()
        
        result = await orchestrator.search("Python Developer")
        
        # Should complete with timeout status
        assert isinstance(result, OrchestratorResult)
        assert any(sr.status == ScraperStatus.TIMEOUT for sr in result.scraper_results)


# =============================================================================
# Test NormalizedJob
# =============================================================================

class TestNormalizedJob:
    """Tests for job normalization (Requirement 10.2)."""
    
    def test_normalized_job_creation(self):
        """Test creating a normalized job."""
        job = NormalizedJob(
            job_id="test123",
            title="Python Developer",
            company="TechCorp",
            location="Remote",
            description="Build Python applications",
            url="https://example.com/jobs/1",
            source="test_scraper",
        )
        
        assert job.job_id == "test123"
        assert job.title == "Python Developer"
        assert job.company == "TechCorp"
        assert job.source == "test_scraper"
    
    def test_normalized_job_to_dict(self):
        """Test converting normalized job to dictionary."""
        job = NormalizedJob(
            job_id="test123",
            title="Python Developer",
            company="TechCorp",
            location="Remote",
            description="Build Python applications",
            url="https://example.com/jobs/1",
            source="test_scraper",
            salary="$100k-150k",
            skills=["Python", "Django"],
        )
        
        job_dict = job.to_dict()
        
        assert isinstance(job_dict, dict)
        assert job_dict["job_id"] == "test123"
        assert job_dict["title"] == "Python Developer"
        assert job_dict["salary"] == "$100k-150k"
        assert job_dict["skills"] == ["Python", "Django"]


# =============================================================================
# Test Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for orchestrator factory functions."""
    
    def test_create_orchestrator_default(self):
        """Test default orchestrator creation."""
        orchestrator = create_orchestrator()
        
        assert isinstance(orchestrator, ScraperOrchestrator)
        assert orchestrator.config.parallel_execution is True
    
    def test_create_orchestrator_custom(self):
        """Test custom orchestrator creation."""
        orchestrator = create_orchestrator(
            enabled_scrapers=["ats", "jobspy"],
            parallel=False,
            timeout_seconds=30.0,
        )
        
        assert "ats" in orchestrator.get_enabled_scrapers()
        assert "jobspy" in orchestrator.get_enabled_scrapers()
        assert orchestrator.config.parallel_execution is False
        assert orchestrator.config.scraper_timeout_seconds == 30.0


# =============================================================================
# Integration Tests
# =============================================================================

class TestOrchestratorIntegration:
    """Integration tests for the orchestrator with mock scrapers."""
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel scraping across platforms (Requirement 10.1)."""
        config = ScraperConfig(
            enabled_scrapers=[],
            parallel_execution=True,
            max_concurrent_scrapers=3,
        )
        orchestrator = ScraperOrchestrator(config)
        
        # Create mock scrapers that track execution
        execution_order = []
        
        class MockScraper(UnifiedScraperInterface):
            def __init__(self, name: str, delay: float):
                self._name = name
                self._delay = delay
            
            @property
            def name(self):
                return self._name
            
            async def search(self, query, location="", max_results=50):
                execution_order.append(f"{self._name}_start")
                await asyncio.sleep(self._delay)
                execution_order.append(f"{self._name}_end")
                return [{"title": f"Job from {self._name}", "company": self._name, 
                        "job_id": f"{self._name}_1"}]
        
        orchestrator._scrapers = {
            "scraper1": MockScraper("scraper1", 0.1),
            "scraper2": MockScraper("scraper2", 0.1),
            "scraper3": MockScraper("scraper3", 0.1),
        }
        
        result = await orchestrator.search("Python")
        
        # All scrapers should have run
        assert len(result.scraper_results) == 3
        assert all(sr.status == ScraperStatus.SUCCESS for sr in result.scraper_results)

    
    @pytest.mark.asyncio
    async def test_result_aggregation(self):
        """Test result aggregation across scrapers."""
        config = ScraperConfig(
            enabled_scrapers=[],
            enable_deduplication=True,
        )
        orchestrator = ScraperOrchestrator(config)
        
        class MockScraper(UnifiedScraperInterface):
            def __init__(self, name: str, jobs: list):
                self._name = name
                self._jobs = jobs
            
            @property
            def name(self):
                return self._name
            
            async def search(self, query, location="", max_results=50):
                return self._jobs
        
        orchestrator._scrapers = {
            "scraper1": MockScraper("scraper1", [
                {"title": "Job A", "company": "Company A", "job_id": "a1"},
                {"title": "Job B", "company": "Company B", "job_id": "b1"},
            ]),
            "scraper2": MockScraper("scraper2", [
                {"title": "Job C", "company": "Company C", "job_id": "c1"},
                {"title": "Job A", "company": "Company A", "job_id": "a1"},  # Duplicate
            ]),
        }
        
        result = await orchestrator.search("Python")
        
        # Should have 4 total, 3 unique (1 duplicate removed)
        assert result.total_jobs == 4
        assert result.unique_jobs == 3
        assert result.duplicates_removed == 1
    
    @pytest.mark.asyncio
    async def test_scraper_stats(self):
        """Test orchestrator statistics."""
        orchestrator = create_orchestrator(enabled_scrapers=["ats"])
        
        stats = orchestrator.stats
        
        assert "enabled_scrapers" in stats
        assert "available_scrapers" in stats
        assert "deduplication_stats" in stats
        assert "config" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
