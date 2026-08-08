"""
Unit tests for async pipeline core structure and configuration.

Tests cover:
- JobContext creation and immutability
- ProcessingResult validation
- ProcessorConfig validation
- Structured logging setup
- Async database engine creation
"""

import pytest
import asyncio
from datetime import datetime
from src.async_pipeline import (
    JobContext,
    ProcessingResult,
    JobStatus,
    ProcessorConfig,
    RetryConfig,
    RateLimitConfig,
    configure_structured_logging,
    get_logger,
    create_async_db_engine,
    create_async_session_factory,
)


class TestJobContext:
    """Test JobContext immutability and validation."""
    
    def test_job_context_creation(self):
        """Test creating a valid JobContext."""
        job = JobContext(
            job_id="job-123",
            title="Software Engineer",
            company="Tech Corp",
            description="A" * 50,  # At least 50 chars
            url="https://example.com/job",
            source="indeed",
        )
        
        assert job.job_id == "job-123"
        assert job.title == "Software Engineer"
        assert job.company == "Tech Corp"
        assert job.source == "indeed"
    
    def test_job_context_immutability(self):
        """Test that JobContext is frozen and cannot be modified."""
        job = JobContext(
            job_id="job-123",
            title="Software Engineer",
            company="Tech Corp",
            description="A" * 50,
            url="https://example.com/job",
            source="indeed",
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            job.title = "New Title"
    
    def test_job_context_empty_id_validation(self):
        """Test that empty job_id raises ValueError."""
        with pytest.raises(ValueError, match="job_id cannot be empty"):
            JobContext(
                job_id="",
                title="Software Engineer",
                company="Tech Corp",
                description="A" * 50,
                url="https://example.com/job",
                source="indeed",
            )
    
    def test_job_context_empty_title_validation(self):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            JobContext(
                job_id="job-123",
                title="",
                company="Tech Corp",
                description="A" * 50,
                url="https://example.com/job",
                source="indeed",
            )
    
    def test_job_context_to_dict(self):
        """Test converting JobContext to dictionary."""
        job = JobContext(
            job_id="job-123",
            title="Software Engineer",
            company="Tech Corp",
            description="A" * 50,
            url="https://example.com/job",
            source="indeed",
        )
        
        job_dict = job.to_dict()
        assert job_dict["job_id"] == "job-123"
        assert job_dict["title"] == "Software Engineer"
        assert isinstance(job_dict, dict)


class TestProcessingResult:
    """Test ProcessingResult validation."""
    
    def test_processing_result_success(self):
        """Test creating a successful ProcessingResult."""
        result = ProcessingResult.success(
            job_id="job-123",
            data={"match_score": 85},
            attempt_count=1,
            processing_time_ms=1500.0,
            worker_id="worker-1",
        )
        
        assert result.status == JobStatus.COMPLETED
        assert result.is_success()
        assert result.data["match_score"] == 85
        assert result.error is None
    
    def test_processing_result_failure(self):
        """Test creating a failed ProcessingResult."""
        result = ProcessingResult.failure(
            job_id="job-123",
            error="API timeout",
            error_type="TimeoutError",
            attempt_count=3,
            worker_id="worker-1",
        )
        
        assert result.status == JobStatus.FAILED
        assert not result.is_success()
        assert result.error == "API timeout"
        assert result.error_type == "TimeoutError"
    
    def test_processing_result_failed_without_error(self):
        """Test that FAILED status requires an error message."""
        with pytest.raises(ValueError, match="Failed status requires an error message"):
            ProcessingResult(
                job_id="job-123",
                status=JobStatus.FAILED,
                data=None,
                error=None,
            )
    
    def test_processing_result_completed_without_data(self):
        """Test that COMPLETED status requires data."""
        with pytest.raises(ValueError, match="Completed status requires data"):
            ProcessingResult(
                job_id="job-123",
                status=JobStatus.COMPLETED,
                data=None,
            )
    
    def test_processing_result_to_dict(self):
        """Test converting ProcessingResult to dictionary."""
        result = ProcessingResult.success(
            job_id="job-123",
            data={"match_score": 85},
        )
        
        result_dict = result.to_dict()
        assert result_dict["job_id"] == "job-123"
        assert result_dict["status"] == "completed"
        assert isinstance(result_dict, dict)


class TestProcessorConfig:
    """Test ProcessorConfig validation."""
    
    def test_processor_config_defaults(self):
        """Test that ProcessorConfig has sensible defaults."""
        config = ProcessorConfig()
        
        assert config.worker_count == 5
        assert config.queue_size == 100
        assert config.max_retries == 3
        assert config.retry_base_delay == 1.0
        assert config.llm_rate_limit == 10.0
    
    def test_processor_config_custom_values(self):
        """Test creating ProcessorConfig with custom values."""
        config = ProcessorConfig(
            worker_count=10,
            queue_size=200,
            max_retries=5,
        )
        
        assert config.worker_count == 10
        assert config.queue_size == 200
        assert config.max_retries == 5
    
    def test_processor_config_validation(self):
        """Test ProcessorConfig validation."""
        config = ProcessorConfig(
            worker_count=5,
            queue_size=100,
            max_retries=3,
        )
        
        # Should not raise
        config.validate()
    
    def test_processor_config_invalid_worker_count(self):
        """Test that invalid worker_count fails validation."""
        config = ProcessorConfig(worker_count=0)
        
        with pytest.raises(ValueError, match="worker_count must be positive"):
            config.validate()
    
    def test_processor_config_invalid_retry_delays(self):
        """Test that invalid retry delays fail validation."""
        config = ProcessorConfig(
            base_delay=60.0,
            max_delay=30.0,  # max < base
        )
        
        with pytest.raises(ValueError, match="max_delay .* must be >= base_delay"):
            config.validate()


class TestRetryConfig:
    """Test RetryConfig validation."""
    
    def test_retry_config_defaults(self):
        """Test RetryConfig defaults."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_retry_config_validation(self):
        """Test RetryConfig validation."""
        config = RetryConfig()
        config.validate()  # Should not raise
    
    def test_retry_config_invalid_exponential_base(self):
        """Test that invalid exponential base fails validation."""
        config = RetryConfig(exponential_base=1.0)
        
        with pytest.raises(ValueError, match="exponential_base must be > 1.0"):
            config.validate()


class TestRateLimitConfig:
    """Test RateLimitConfig validation."""
    
    def test_rate_limit_config_validation(self):
        """Test RateLimitConfig validation."""
        config = RateLimitConfig(rate=10.0, capacity=1)
        config.validate()  # Should not raise
    
    def test_rate_limit_config_invalid_rate(self):
        """Test that invalid rate fails validation."""
        config = RateLimitConfig(rate=0.0, capacity=1)
        
        with pytest.raises(ValueError, match="rate must be positive"):
            config.validate()


class TestStructuredLogging:
    """Test structured logging setup."""
    
    def test_configure_structured_logging(self):
        """Test that structured logging can be configured."""
        # Should not raise
        configure_structured_logging(
            log_level="INFO",
            json_format=False,
            include_timestamp=True,
        )
    
    def test_get_logger(self):
        """Test getting a structured logger."""
        logger = get_logger(__name__)
        
        assert logger is not None
        # Logger should have structlog methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")


class TestAsyncDatabase:
    """Test async database engine creation."""
    
    def test_create_async_db_engine_sqlite(self):
        """Test creating async SQLite engine."""
        engine = create_async_db_engine(
            database_url="sqlite:///test.db",
            pool_size=5,
            max_overflow=10,
        )
        
        assert engine is not None
        assert "aiosqlite" in str(engine.url)
    
    def test_create_async_db_engine_postgresql(self):
        """Test creating async PostgreSQL engine."""
        engine = create_async_db_engine(
            database_url="postgresql://user:pass@localhost/db",
            pool_size=5,
            max_overflow=10,
        )
        
        assert engine is not None
        assert "asyncpg" in str(engine.url)
    
    def test_create_async_session_factory(self):
        """Test creating async session factory."""
        engine = create_async_db_engine(
            database_url="sqlite:///test.db",
        )
        
        session_factory = create_async_session_factory(engine)
        
        assert session_factory is not None
        assert callable(session_factory)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
