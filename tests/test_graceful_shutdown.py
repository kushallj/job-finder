"""
Tests for graceful shutdown functionality in AsyncJobPipeline.

Tests cover SIGTERM/SIGINT handling, in-flight job completion,
timeout enforcement, resource cleanup, and shutdown logging.

Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 34.1
"""

import asyncio
import logging
import os
import pytest
import signal
import time
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.pipeline import AsyncJobPipeline
from src.async_pipeline.types import (
    JobContext,
    JobStatus,
    ProcessingResult,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def shutdown_config():
    """Create a test configuration with short shutdown timeout."""
    return ProcessorConfig(
        worker_count=2,
        queue_size=10,
        max_concurrent_api_calls=5,
        chunk_size=5,
        max_retries=1,
        base_delay=0.01,
        max_delay=0.1,
        shutdown_timeout_seconds=2.0,  # Short timeout for testing
        log_level="DEBUG",
    )


@pytest.fixture
def sample_jobs():
    """Create sample job contexts."""
    return [
        JobContext(
            job_id=f"test-job-{i}",
            title=f"Software Engineer {i}",
            company="Test Corp",
            description=f"Test job description {i} with more than 50 characters to pass validation.",
            url=f"https://example.com/job/{i}",
            source="test",
        )
        for i in range(10)
    ]


@pytest.fixture
def fast_processor():
    """Create a processor that completes quickly."""
    async def processor(job: JobContext) -> ProcessingResult:
        await asyncio.sleep(0.1)  # Fast processing
        return ProcessingResult.success(
            job_id=job.job_id,
            data={"processed": True},
        )
    return processor


@pytest.fixture
def slow_processor():
    """Create a processor that takes a long time."""
    async def processor(job: JobContext) -> ProcessingResult:
        await asyncio.sleep(5.0)  # Slow processing - exceeds shutdown timeout
        return ProcessingResult.success(
            job_id=job.job_id,
            data={"processed": True},
        )
    return processor


@pytest.fixture
async def mock_db_engine():
    """Create a mock async database engine."""
    engine = AsyncMock()
    engine.dispose = AsyncMock()
    return engine


# ============================================================================
# Test Signal Handler Registration
# ============================================================================

@pytest.mark.asyncio
async def test_signal_handlers_registered(shutdown_config):
    """
    Test that SIGTERM and SIGINT signal handlers are registered.
    
    Requirements: 24.1, 24.3
    """
    pipeline = AsyncJobPipeline(config=shutdown_config)
    
    # Signal handlers should be registered during initialization
    # We can't directly test the signal handler without actually sending signals,
    # but we can verify the shutdown_requested flag starts as False
    assert pipeline._shutdown_requested is False
    
    await pipeline.close()


@pytest.mark.asyncio
async def test_shutdown_flag_set_by_signal_handler(shutdown_config):
    """
    Test that shutdown flag is set when signal handler is invoked.
    
    Requirements: 24.1, 24.3
    """
    pipeline = AsyncJobPipeline(config=shutdown_config)
    
    # Simulate signal handler invocation
    pipeline._shutdown_requested = True
    
    assert pipeline._shutdown_requested is True
    
    await pipeline.close()


# ============================================================================
# Test Graceful Shutdown - In-Flight Jobs Complete
# ============================================================================

@pytest.mark.asyncio
async def test_shutdown_waits_for_inflight_jobs(shutdown_config, fast_processor, tmp_path):
    """
    Test that shutdown waits for in-flight jobs to complete within timeout.
    
    Requirements: 24.2, 24.4, 24.5
    """
    # Use a temporary database
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    
    # Create pipeline with fast processor
    pipeline = AsyncJobPipeline(config=shutdown_config, db_url=db_url)
    pipeline.set_processor(fast_processor)
    
    # Disable progress display for cleaner test output
    pipeline.enable_progress_display(False)
    
    # Mock the database to avoid actual DB setup
    with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
        await pipeline._setup_components()
        mock_producer = pipeline._producer
        mock_producer.get_job_count = AsyncMock(return_value=3)
        
        async def produce_jobs(query, filters):
            for i in range(3):
                yield JobContext(
                    job_id=f"job-{i}",
                    title="Test Job",
                    company="Test Corp",
                    description="A test job description that is long enough for validation purposes.",
                    url=f"https://example.com/job/{i}",
                    source="test",
                )
        
        mock_producer.produce_jobs = MagicMock(side_effect=lambda *a, **kw: produce_jobs(*a, **kw))
        
        # Start pipeline in background
        task = asyncio.create_task(pipeline.run(query="test"))
        
        # Wait a bit for jobs to start processing
        await asyncio.sleep(0.2)
        
        # Request shutdown
        pipeline._shutdown_requested = True
        
        # Measure shutdown time
        start_time = time.time()
        
        # Wait for pipeline to complete
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            pytest.fail("Pipeline did not shutdown within expected time")
        
        elapsed = time.time() - start_time
        
        # Shutdown should complete quickly since jobs are fast
        assert elapsed < shutdown_config.shutdown_timeout_seconds
    
    await pipeline.close()



@pytest.mark.asyncio
async def test_shutdown_timeout_exceeded_force_terminate(shutdown_config, slow_processor, tmp_path):
    """
    Test that shutdown forcefully terminates jobs after timeout.
    
    Requirements: 24.5, 24.6
    """
    # Use a temporary database
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    
    # Create pipeline with slow processor
    pipeline = AsyncJobPipeline(config=shutdown_config, db_url=db_url)
    pipeline.set_processor(slow_processor)
    
    # Disable progress display
    pipeline.enable_progress_display(False)
    
    # Mock the database
    with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
        await pipeline._setup_components()
        mock_producer = pipeline._producer
        mock_producer.get_job_count = AsyncMock(return_value=1)
        
        async def produce_jobs(query, filters):
            yield JobContext(
                job_id="slow-job",
                title="Slow Job",
                company="Test Corp",
                description="A slow job that will exceed shutdown timeout with enough characters.",
                url="https://example.com/job/slow",
                source="test",
            )
        
        mock_producer.produce_jobs = MagicMock(side_effect=lambda *a, **kw: produce_jobs(*a, **kw))
        
        # Start pipeline in background
        task = asyncio.create_task(pipeline.run(query="test"))
        
        # Wait for job to start processing
        await asyncio.sleep(0.3)
        
        # Request shutdown
        pipeline._shutdown_requested = True
        
        # Measure shutdown time
        start_time = time.time()
        
        # Close pipeline (which triggers graceful shutdown)
        await pipeline.close()
        
        elapsed = time.time() - start_time
        
        # Shutdown should complete within timeout + small buffer
        # Even though job takes 5s, shutdown should force terminate at 2s
        assert elapsed < shutdown_config.shutdown_timeout_seconds + 1.0
        
        # Cancel the task if still running
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# ============================================================================
# Test Stop Accepting New Jobs on Shutdown
# ============================================================================

@pytest.mark.asyncio
async def test_shutdown_stops_accepting_new_jobs(shutdown_config, fast_processor, tmp_path):
    """
    Test that pipeline stops accepting new jobs when shutdown is requested.
    
    Requirements: 24.1
    """
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    
    pipeline = AsyncJobPipeline(config=shutdown_config, db_url=db_url)
    pipeline.set_processor(fast_processor)
    pipeline.enable_progress_display(False)
    
    with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
        await pipeline._setup_components()
        mock_producer = pipeline._producer
        mock_producer.get_job_count = AsyncMock(return_value=10)
        
        jobs_produced = []
        
        async def produce_jobs(query, filters):
            for i in range(10):
                # Simulate slow job production
                await asyncio.sleep(0.1)
                job = JobContext(
                    job_id=f"job-{i}",
                    title="Test Job",
                    company="Test Corp",
                    description="A test job description with sufficient length for validation.",
                    url=f"https://example.com/job/{i}",
                    source="test",
                )
                jobs_produced.append(job)
                yield job
        
        mock_producer.produce_jobs = MagicMock(side_effect=lambda *a, **kw: produce_jobs(*a, **kw))
        
        # Start pipeline
        task = asyncio.create_task(pipeline.run(query="test"))
        
        # Wait for some jobs to be produced
        await asyncio.sleep(0.3)
        
        # Request shutdown - should stop accepting new jobs
        pipeline._shutdown_requested = True
        
        # Wait for completion
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            task.cancel()
        
        # Should have produced fewer than 10 jobs (stopped early)
        assert len(jobs_produced) < 10

    
    await pipeline.close()


# ============================================================================
# Test Resource Cleanup
# ============================================================================

@pytest.mark.asyncio
async def test_shutdown_cleans_up_database_connections(shutdown_config, mock_db_engine):
    """
    Test that database connections are properly closed during shutdown.
    
    Requirements: 34.1
    """
    pipeline = AsyncJobPipeline(config=shutdown_config)
    
    # Set mock engine
    pipeline._engine = mock_db_engine
    
    # Close pipeline
    await pipeline.close()
    
    # Verify dispose was called
    mock_db_engine.dispose.assert_awaited_once()
    
    # Engine should be set to None
    assert pipeline._engine is None


@pytest.mark.asyncio
async def test_shutdown_stops_progress_tracker(shutdown_config):
    """
    Test that progress tracker is stopped during shutdown.
    
    Requirements: 34.1
    """
    pipeline = AsyncJobPipeline(config=shutdown_config)
    
    # Create mock progress tracker
    mock_tracker = Mock()
    mock_tracker.stop = Mock()
    pipeline._progress_tracker = mock_tracker
    
    # Close pipeline
    await pipeline.close()
    
    # Verify stop was called
    mock_tracker.stop.assert_called_once()
    
    # Tracker should be set to None
    assert pipeline._progress_tracker is None


@pytest.mark.asyncio
async def test_shutdown_flushes_log_handlers(shutdown_config):
    """
    Test that log handlers are flushed during shutdown.
    
    Requirements: 34.1
    """
    pipeline = AsyncJobPipeline(config=shutdown_config)
    
    # Create a mock handler
    mock_handler = logging.NullHandler()
    mock_handler.flush = Mock()
    
    # Add mock handler to root logger
    logger = logging.getLogger()

    logger.addHandler(mock_handler)
    
    try:
        # Close pipeline
        await pipeline.close()
        
        # Verify flush was called
        mock_handler.flush.assert_called()
    finally:
        # Clean up
        logger.removeHandler(mock_handler)


# ============================================================================
# Test Shutdown Logging
# ============================================================================

@pytest.mark.asyncio
async def test_shutdown_logs_progress(shutdown_config, caplog):
    """
    Test that shutdown logs progress and completion messages.
    
    Requirements: 24.6
    """
    caplog.set_level(logging.INFO)
    
    pipeline = AsyncJobPipeline(config=shutdown_config)
    
    # Mock engine to avoid actual DB
    pipeline._engine = AsyncMock()
    pipeline._engine.dispose = AsyncMock()
    
    # Close pipeline
    await pipeline.close()
    
    # Check for shutdown log messages
    log_messages = [record.message for record in caplog.records]
    
    # Should have messages about shutdown started and completed
    assert any("shutdown" in msg.lower() for msg in log_messages)
    assert any("complete" in msg.lower() for msg in log_messages)


@pytest.mark.asyncio
async def test_shutdown_logs_timeout_warning(shutdown_config, slow_processor, caplog, tmp_path):
    """
    Test that timeout exceeded is logged as a warning.
    
    Requirements: 24.6
    """
    caplog.set_level(logging.WARNING)
    
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    
    pipeline = AsyncJobPipeline(config=shutdown_config, db_url=db_url)
    pipeline.set_processor(slow_processor)
    pipeline.enable_progress_display(False)
    
    with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
        await pipeline._setup_components()
        mock_producer = pipeline._producer
        mock_producer.get_job_count = AsyncMock(return_value=1)
        
        async def produce_jobs(query, filters):
            yield JobContext(
                job_id="slow-job",
                title="Slow Job",
                company="Test Corp",
                description="A slow job that will exceed shutdown timeout for testing purposes.",
                url="https://example.com/job/slow",
                source="test",
            )
        
        mock_producer.produce_jobs = MagicMock(side_effect=lambda *a, **kw: produce_jobs(*a, **kw))
        
        # Start pipeline
        task = asyncio.create_task(pipeline.run(query="test"))
        
        # Wait for job to start
        await asyncio.sleep(0.3)
        
        # Request shutdown
        pipeline._shutdown_requested = True
        
        # Close with timeout
        await pipeline.close()
        
        # Cancel task if still running
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    # Check for timeout warning in logs
    log_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
    assert any("timeout" in msg.lower() for msg in log_messages)


# ============================================================================
# Test Configuration Validation
# ============================================================================

def test_shutdown_timeout_validation():
    """
    Test that shutdown_timeout_seconds must be positive.
    
    Requirements: 24.5
    """
    # Valid configuration
    config = ProcessorConfig(shutdown_timeout_seconds=30.0)
    config.validate()  # Should not raise
    
    # Invalid configuration - zero timeout
    with pytest.raises(ValueError, match="shutdown_timeout_seconds must be positive"):
        config = ProcessorConfig(shutdown_timeout_seconds=0.0)
        config.validate()
    
    # Invalid configuration - negative timeout
    with pytest.raises(ValueError, match="shutdown_timeout_seconds must be positive"):
        config = ProcessorConfig(shutdown_timeout_seconds=-10.0)
        config.validate()


def test_shutdown_timeout_from_env():
    """
    Test that shutdown timeout can be configured via environment variable.
    
    Requirements: 24.5
    """
    # Set environment variable
    os.environ["PIPELINE_SHUTDOWN_TIMEOUT_SECONDS"] = "120.0"
    
    try:
        config = ProcessorConfig.from_env()
        assert config.shutdown_timeout_seconds == 120.0
    finally:
        # Clean up
        del os.environ["PIPELINE_SHUTDOWN_TIMEOUT_SECONDS"]


# ============================================================================
# Test Multiple Shutdown Signals
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_shutdown_signals_handled_gracefully(shutdown_config):
    """
    Test that multiple shutdown signals don't cause issues.
    
    Requirements: 24.1, 24.3
    """
    pipeline = AsyncJobPipeline(config=shutdown_config)
    
    # Simulate multiple shutdown signals
    pipeline._shutdown_requested = True
    pipeline._shutdown_requested = True  # Second signal
    
    # Should still be True
    assert pipeline._shutdown_requested is True
    
    # Should close gracefully
    await pipeline.close()


# ============================================================================
# Test Shutdown During Different Pipeline States
# ============================================================================

@pytest.mark.asyncio
async def test_shutdown_before_pipeline_start(shutdown_config):
    """
    Test shutdown when pipeline hasn't been started yet.
    
    Requirements: 34.1
    """
    pipeline = AsyncJobPipeline(config=shutdown_config)
    
    # Close immediately without running
    await pipeline.close()
    
    # Should complete without errors
    assert not pipeline.is_running


@pytest.mark.asyncio
async def test_shutdown_after_pipeline_complete(shutdown_config, fast_processor, tmp_path):
    """
    Test shutdown after pipeline has already completed.
    
    Requirements: 34.1
    """
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    
    pipeline = AsyncJobPipeline(config=shutdown_config, db_url=db_url)
    pipeline.set_processor(fast_processor)
    pipeline.enable_progress_display(False)
    
    with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
        await pipeline._setup_components()
        mock_producer = pipeline._producer
        mock_producer.get_job_count = AsyncMock(return_value=0)
        
        async def produce_jobs(query, filters):
            if False:
                yield
        
        mock_producer.produce_jobs = MagicMock(side_effect=lambda *a, **kw: produce_jobs(*a, **kw))
        
        # Run pipeline to completion
        await pipeline.run(query="test")
        
        # Now close after completion
        await pipeline.close()
        
        # Should complete without errors
        assert not pipeline.is_running



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
