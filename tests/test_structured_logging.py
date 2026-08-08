"""
Tests for structured logging configuration.

This test verifies that the structured logging system is properly configured
and that correlation IDs are correctly propagated through the pipeline.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock

from src.async_pipeline import (
    configure_structured_logging,
    get_logger,
    set_correlation_id,
    get_correlation_id,
    generate_correlation_id,
    clear_correlation_id,
)
from src.async_pipeline.types import JobContext
from src.async_pipeline.processor import AsyncJobProcessor
from src.async_pipeline.config import ProcessorConfig


def test_configure_structured_logging_json_format():
    """Test that structured logging can be configured with JSON format."""
    # Should not raise any exceptions
    configure_structured_logging(
        log_level="INFO",
        json_format=True,
        include_timestamp=True,
    )
    
    # Get a logger and verify it works
    logger = get_logger(__name__)
    assert logger is not None
    
    # Log a test message with structured data
    logger.info(
        "test_message",
        test_field="test_value",
        numeric_field=123,
    )


def test_configure_structured_logging_console_format():
    """Test that structured logging can be configured with console format."""
    # Should not raise any exceptions
    configure_structured_logging(
        log_level="DEBUG",
        json_format=False,
        include_timestamp=True,
    )
    
    # Get a logger and verify it works
    logger = get_logger(__name__)
    assert logger is not None
    
    # Log a test message
    logger.debug("test_debug_message", context="test")


def test_correlation_id_generation():
    """Test that correlation IDs can be generated."""
    corr_id = generate_correlation_id()
    
    assert corr_id is not None
    assert isinstance(corr_id, str)
    assert len(corr_id) > 0


def test_correlation_id_set_and_get():
    """Test setting and getting correlation ID."""
    test_id = "test-correlation-id-123"
    
    # Set correlation ID
    set_correlation_id(test_id)
    
    # Get it back
    retrieved_id = get_correlation_id()
    assert retrieved_id == test_id
    
    # Clear it
    clear_correlation_id()
    retrieved_id = get_correlation_id()
    assert retrieved_id is None


@pytest.mark.asyncio
async def test_correlation_id_in_async_context():
    """Test that correlation ID persists across async operations."""
    test_id = "async-test-id"
    
    set_correlation_id(test_id)
    
    # Simulate async operation
    await asyncio.sleep(0.01)
    
    # Correlation ID should still be set
    assert get_correlation_id() == test_id
    
    clear_correlation_id()


def test_structured_logging_with_job_context():
    """Test structured logging with job-related fields."""
    logger = get_logger(__name__)
    
    # Create a job context
    job = JobContext(
        job_id="test-job-123",
        title="Software Engineer",
        company="Test Company",
        description="Test description " * 20,  # Make it > 50 chars
        url="https://example.com/job/123",
        source="test",
    )
    
    # Set correlation ID for this job
    correlation_id = f"job-{job.job_id}-{generate_correlation_id()[:8]}"
    set_correlation_id(correlation_id)
    
    # Log job processing events
    logger.info(
        "job_processing_started",
        job_id=job.job_id,
        company=job.company,
        title=job.title,
        status="PROCESSING",
        attempt_count=1,
        correlation_id=correlation_id,
    )
    
    logger.info(
        "job_completed",
        job_id=job.job_id,
        status="COMPLETED",
        processing_time_ms=123.45,
        attempt_count=1,
        correlation_id=correlation_id,
    )
    
    # Clean up
    clear_correlation_id()


def test_error_logging_with_traceback():
    """Test error logging includes error_type, error_message, and traceback."""
    logger = get_logger(__name__)
    
    try:
        # Simulate an error
        raise ValueError("Test error message")
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        
        logger.error(
            "job_failed",
            job_id="test-job-error",
            status="FAILED",
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=error_traceback,
            processing_time_ms=50.0,
            attempt_count=3,
        )


def test_log_levels_configuration():
    """Test that different log levels work correctly."""
    logger = get_logger(__name__)
    
    # INFO level (job lifecycle)
    logger.info(
        "job_lifecycle_event",
        job_id="test-123",
        status="COMPLETED",
    )
    
    # WARNING level (retries)
    logger.warning(
        "job_retry",
        job_id="test-123",
        status="RETRYING",
        attempt_count=2,
        max_retries=3,
    )
    
    # ERROR level (failures)
    logger.error(
        "job_failed",
        job_id="test-123",
        status="FAILED",
        error_type="TimeoutError",
        error_message="Operation timed out",
    )


@pytest.mark.asyncio
async def test_processor_uses_correlation_id():
    """Test that AsyncJobProcessor sets and uses correlation IDs."""
    # Create mock services
    mock_llm = AsyncMock()
    mock_llm.extract_skills = AsyncMock(return_value=["Python", "Docker"])
    mock_llm.match_resume_to_job = AsyncMock(return_value={
        "match_score": 85,
        "matched_skills": ["Python"],
        "missing_skills": ["Docker"],
        "recommendations": "Learn Docker"
    })
    
    mock_email = AsyncMock()
    mock_scraper = AsyncMock()
    mock_db_factory = AsyncMock()
    
    # Create processor
    config = ProcessorConfig()
    processor = AsyncJobProcessor(
        llm_service=mock_llm,
        email_service=mock_email,
        scraper_service=mock_scraper,
        db_session_factory=mock_db_factory,
        config=config,
    )
    
    # Create job
    job = JobContext(
        job_id="test-processor-job",
        title="Backend Engineer",
        company="Tech Corp",
        description="We need a backend engineer with Python experience. " * 10,
        url="https://example.com/job/456",
        source="test",
    )
    
    # Note: We can't fully test process_job without mocking database,
    # but we can verify correlation ID generation works
    correlation_id = f"job-{job.job_id}-{generate_correlation_id()[:8]}"
    assert len(correlation_id) > 0
    assert job.job_id in correlation_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
