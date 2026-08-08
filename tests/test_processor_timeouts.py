"""
Unit tests for AsyncJobProcessor timeout enforcement.

Tests cover:
- LLM timeout wrappers for extract_skills
- LLM timeout wrappers for match_resume
- Database timeout wrappers for store_result
- Email timeout wrappers for send_outreach_email
- Scraping timeout wrappers for scrape_job_details
- Timeout errors are caught and handled by retry logic

Requirements Coverage: 18.1, 18.2, 18.3, 18.4, 18.5
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.async_pipeline.processor import AsyncJobProcessor
from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.types import JobContext


@pytest.fixture
def processor_config():
    """Create test configuration with short timeouts for testing."""
    return ProcessorConfig(
        llm_timeout_seconds=0.5,
        email_timeout_seconds=0.5,
        scraper_timeout_seconds=0.5,
        db_timeout_seconds=0.5,
        max_retries=1,  # Reduce retries for faster tests
    )


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    llm_service = AsyncMock()
    email_service = AsyncMock()
    scraper_service = AsyncMock()
    return llm_service, email_service, scraper_service


@pytest.fixture
def mock_db_session_factory():
    """Create mock database session factory."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    
    # Create a proper async context manager for begin()
    class BeginContextManager:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
    
    session.begin = MagicMock(return_value=BeginContextManager())
    
    # Make session work as async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    
    # Make factory work as async context manager
    class AsyncSessionFactory:
        def __call__(self):
            return session
        
        async def __aenter__(self):
            return session
        
        async def __aexit__(self, *args):
            pass
    
    return AsyncSessionFactory()


@pytest.fixture
def sample_job():
    """Create a sample job context for testing."""
    return JobContext(
        job_id="test-job-123",
        title="Software Engineer",
        company="Tech Corp",
        description="A" * 100,
        url="https://example.com/job",
        source="indeed",
    )


@pytest.fixture
def processor(processor_config, mock_services, mock_db_session_factory):
    """Create AsyncJobProcessor instance for testing."""
    llm_service, email_service, scraper_service = mock_services
    
    processor = AsyncJobProcessor(
        llm_service=llm_service,
        email_service=email_service,
        scraper_service=scraper_service,
        db_session_factory=mock_db_session_factory,
        config=processor_config,
    )
    
    return processor


class TestLLMTimeouts:
    """Test timeout enforcement for LLM operations."""
    
    @pytest.mark.asyncio
    async def test_extract_skills_timeout(self, processor, sample_job):
        """Test that extract_skills times out when LLM takes too long.
        
        Requirements Coverage: 18.1, 18.2, 18.3
        """
        # Configure LLM service to take longer than timeout
        async def slow_extract(description):
            await asyncio.sleep(2.0)  # Longer than 0.5s timeout
            return ["Python", "SQL"]
        
        processor.llm_service.extract_skills = slow_extract
        
        # Should raise TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await processor.extract_skills(sample_job.description)
    
    @pytest.mark.asyncio
    async def test_extract_skills_success_within_timeout(self, processor, sample_job):
        """Test that extract_skills succeeds when LLM responds quickly.
        
        Requirements Coverage: 18.1
        """
        # Configure LLM service to respond quickly
        async def fast_extract(description):
            await asyncio.sleep(0.1)  # Well within timeout
            return ["Python", "SQL", "AWS"]
        
        processor.llm_service.extract_skills = fast_extract
        
        # Should succeed
        skills = await processor.extract_skills(sample_job.description)
        assert len(skills) == 3
        assert "Python" in skills
    
    @pytest.mark.asyncio
    async def test_match_resume_timeout(self, processor, sample_job):
        """Test that match_resume times out when LLM takes too long.
        
        Requirements Coverage: 18.1, 18.2, 18.3
        """
        # Configure LLM service to take longer than timeout
        async def slow_match(resume, skills):
            await asyncio.sleep(2.0)  # Longer than 0.5s timeout
            return {"match_score": 85}
        
        processor.llm_service.match_resume_to_job = slow_match
        
        # Should raise TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await processor.match_resume(["Python", "SQL"], sample_job)
    
    @pytest.mark.asyncio
    async def test_match_resume_success_within_timeout(self, processor, sample_job):
        """Test that match_resume succeeds when LLM responds quickly.
        
        Requirements Coverage: 18.1
        """
        # Configure LLM service to respond quickly
        async def fast_match(resume, skills):
            await asyncio.sleep(0.1)
            return {
                "match_score": 85,
                "matched_skills": ["Python", "SQL"],
                "missing_skills": ["AWS"],
                "recommendations": "Learn AWS",
            }
        
        processor.llm_service.match_resume_to_job = fast_match
        
        # Should succeed
        result = await processor.match_resume(["Python", "SQL", "AWS"], sample_job)
        assert result["match_score"] == 85
        assert result["job_id"] == sample_job.job_id


class TestDatabaseTimeouts:
    """Test timeout enforcement for database operations."""
    
    @pytest.mark.asyncio
    async def test_store_result_timeout(self, processor, sample_job):
        """Test that store_result times out when database takes too long.
        
        Requirements Coverage: 18.1, 18.2, 18.3, 18.4
        """
        # Create a session that simulates slow database operations
        class SlowSession:
            def __init__(self):
                self._begin_context = self
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
            
            def begin(self):
                return self
            
            async def execute(self, *args, **kwargs):
                await asyncio.sleep(2.0)  # Longer than 0.5s timeout
                return AsyncMock()
            
            async def commit(self):
                pass
            
            async def flush(self):
                pass
            
            def add(self, obj):
                pass
        
        # Replace the session factory with slow session
        class SlowSessionFactory:
            def __call__(self):
                return SlowSession()
            
            async def __aenter__(self):
                return SlowSession()
            
            async def __aexit__(self, *args):
                pass
        
        processor.db_session_factory = SlowSessionFactory()
        
        result_data = {
            "match_score": 85,
            "matched_skills": ["Python"],
            "missing_skills": ["AWS"],
        }
        
        # Should raise TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await processor.store_result(sample_job, result_data)
    
    @pytest.mark.asyncio
    async def test_store_result_success_within_timeout(self, processor, sample_job, mock_db_session_factory):
        """Test that store_result succeeds when database responds quickly.
        
        Requirements Coverage: 18.1
        """
        # Configure database to respond quickly
        async def fast_execute(*args, **kwargs):
            await asyncio.sleep(0.1)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=None)
            return mock_result
        
        mock_db_session_factory().execute = fast_execute
        
        result_data = {
            "match_score": 85,
            "matched_skills": ["Python"],
            "missing_skills": ["AWS"],
        }
        
        # Should succeed
        await processor.store_result(sample_job, result_data)


class TestEmailTimeouts:
    """Test timeout enforcement for email operations."""
    
    @pytest.mark.asyncio
    async def test_send_outreach_email_timeout(self, processor, sample_job):
        """Test that send_outreach_email times out when email API takes too long.
        
        Requirements Coverage: 18.1, 18.2, 18.3
        """
        # Configure email service to take longer than timeout
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(2.0)  # Longer than 0.5s timeout
            return {"status": "sent"}
        
        processor.email_service.send_email = slow_send
        
        # Should raise TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await processor.send_outreach_email(
                job=sample_job,
                contact_email="hiring@example.com",
                email_content="Test email content",
            )
    
    @pytest.mark.asyncio
    async def test_send_outreach_email_success_within_timeout(self, processor, sample_job):
        """Test that send_outreach_email succeeds when email API responds quickly.
        
        Requirements Coverage: 18.1
        """
        # Configure email service to respond quickly
        async def fast_send(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {"status": "sent", "message_id": "msg-123"}
        
        processor.email_service.send_email = fast_send
        
        # Should succeed
        result = await processor.send_outreach_email(
            job=sample_job,
            contact_email="hiring@example.com",
            email_content="Test email content",
        )
        assert result["status"] == "sent"


class TestScrapingTimeouts:
    """Test timeout enforcement for scraping operations."""
    
    @pytest.mark.asyncio
    async def test_scrape_job_details_timeout(self, processor):
        """Test that scrape_job_details times out when scraping takes too long.
        
        Requirements Coverage: 18.1, 18.2, 18.3
        """
        # Configure scraper to take longer than timeout
        async def slow_scrape(*args, **kwargs):
            await asyncio.sleep(2.0)  # Longer than 0.5s timeout
            return {"company_size": "500+"}
        
        processor.scraper_service.scrape_job = slow_scrape
        
        # Should raise TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await processor.scrape_job_details("https://example.com/job")
    
    @pytest.mark.asyncio
    async def test_scrape_job_details_success_within_timeout(self, processor):
        """Test that scrape_job_details succeeds when scraping responds quickly.
        
        Requirements Coverage: 18.1
        """
        # Configure scraper to respond quickly
        async def fast_scrape(url):
            await asyncio.sleep(0.1)
            return {
                "company_size": "500+",
                "tech_stack": ["Python", "AWS"],
            }
        
        processor.scraper_service.scrape_job = fast_scrape
        
        # Should succeed
        result = await processor.scrape_job_details("https://example.com/job")
        assert result["company_size"] == "500+"


class TestSemaphoreIntegration:
    """Test that timeout enforcement works correctly with semaphore rate limiting."""
    
    @pytest.mark.asyncio
    async def test_timeout_with_semaphore_releases_properly(self, processor, sample_job):
        """Test that semaphore is released even when timeout occurs.
        
        Requirements Coverage: 18.3, 18.5
        """
        semaphore = asyncio.Semaphore(2)
        
        # Verify initial semaphore state
        initial_value = semaphore._value
        
        # Configure LLM to timeout
        async def slow_extract(description):
            await asyncio.sleep(2.0)
            return ["Python"]
        
        processor.llm_service.extract_skills = slow_extract
        
        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await processor.extract_skills(sample_job.description, semaphore)
        
        # Semaphore should be released despite timeout
        assert semaphore._value == initial_value
    
    @pytest.mark.asyncio
    async def test_timeout_with_semaphore_email(self, processor, sample_job):
        """Test that email operations release semaphore on timeout.
        
        Requirements Coverage: 18.3, 18.5
        """
        semaphore = asyncio.Semaphore(1)
        initial_value = semaphore._value
        
        # Configure email to timeout
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(2.0)
            return {"status": "sent"}
        
        processor.email_service.send_email = slow_send
        
        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await processor.send_outreach_email(
                job=sample_job,
                contact_email="test@example.com",
                email_content="content",
                semaphore=semaphore,
            )
        
        # Semaphore should be released
        assert semaphore._value == initial_value


class TestTimeoutConfiguration:
    """Test that different timeout values are properly configured."""
    
    def test_default_timeouts(self):
        """Test that default timeout values are reasonable.
        
        Requirements Coverage: 18.1
        """
        config = ProcessorConfig()
        
        assert config.llm_timeout_seconds == 30.0
        assert config.email_timeout_seconds == 15.0
        assert config.scraper_timeout_seconds == 20.0
        assert config.db_timeout_seconds == 10.0
    
    def test_custom_timeouts(self):
        """Test that custom timeout values can be configured.
        
        Requirements Coverage: 18.1
        """
        config = ProcessorConfig(
            llm_timeout_seconds=60.0,
            email_timeout_seconds=30.0,
            scraper_timeout_seconds=45.0,
            db_timeout_seconds=20.0,
        )
        
        assert config.llm_timeout_seconds == 60.0
        assert config.email_timeout_seconds == 30.0
        assert config.scraper_timeout_seconds == 45.0
        assert config.db_timeout_seconds == 20.0
    
    def test_timeout_validation(self):
        """Test that invalid timeout values are rejected.
        
        Requirements Coverage: 18.1
        """
        config = ProcessorConfig(llm_timeout_seconds=0.0)
        
        with pytest.raises(ValueError, match="llm_timeout_seconds must be positive"):
            config.validate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

