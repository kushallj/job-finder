"""
Tests for the AsyncJobPipeline coordinator.

Tests cover pipeline orchestration, component integration, graceful shutdown,
and statistics tracking as specified in task 10.1.
"""

import asyncio
import logging
import pytest
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.pipeline import (
    AsyncJobPipeline,
    AsyncJobPipelineBuilder,
    create_pipeline_and_run,
)
from src.async_pipeline.types import (
    JobContext,
    JobStatus,
    ProcessingResult,
    PipelineStats,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_job():
    """Create a sample job context for testing."""
    return JobContext(
        job_id="test-job-1",
        title="Software Engineer",
        company="Test Corp",
        description="This is a test job description that is longer than 50 characters for validation.",
        url="https://example.com/job/1",
        source="test",
        location="Remote",
        salary="$100k-$150k",
        metadata={"test": True},
    )


@pytest.fixture
def sample_jobs():
    """Create a list of sample job contexts."""
    return [
        JobContext(
            job_id=f"test-job-{i}",
            title=f"Software Engineer {i}",
            company="Test Corp",
            description=f"Test job description {i} with more than 50 characters to pass validation.",
            url=f"https://example.com/job/{i}",
            source="test",
        )
        for i in range(5)
    ]


@pytest.fixture
def mock_processor():
    """Create a mock job processor that returns success."""
    async def processor(job: JobContext) -> ProcessingResult:
        await asyncio.sleep(0.01)  # Simulate processing
        return ProcessingResult.success(
            job_id=job.job_id,
            data={"processed": True},
        )
    return processor


@pytest.fixture
def mock_failing_processor():
    """Create a mock processor that fails."""
    async def processor(job: JobContext) -> ProcessingResult:
        raise ValueError("Simulated processing error")
    return processor


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return ProcessorConfig(
        worker_count=2,
        queue_size=10,
        max_concurrent_api_calls=5,
        chunk_size=10,
        max_retries=2,
        base_delay=0.01,
        max_delay=0.1,
    )


# ============================================================================
# Test AsyncJobPipeline Initialization
# ============================================================================

class TestPipelineInitialization:
    """Test pipeline initialization and configuration."""
    
    def test_pipeline_init_with_defaults(self):
        """Test pipeline initializes with default configuration."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline()
            
            assert pipeline._config is not None
            assert pipeline._running is False
            assert pipeline._shutdown_requested is False
            assert pipeline._results == []
            assert pipeline.stats.jobs_queued == 0
    
    def test_pipeline_init_with_custom_config(self, test_config):
        """Test pipeline initializes with custom configuration."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            
            assert pipeline._config == test_config
            assert pipeline._config.worker_count == 2
            assert pipeline._config.queue_size == 10
    
    def test_pipeline_init_with_db_url(self):
        """Test pipeline initializes with custom database URL."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            db_url = "sqlite+aiosqlite:///test.db"
            pipeline = AsyncJobPipeline(db_url=db_url)
            
            assert pipeline._db_url == db_url
    
    def test_pipeline_properties(self):
        """Test pipeline properties."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline()
            
            assert pipeline.is_running is False
            assert isinstance(pipeline.stats, PipelineStats)


# ============================================================================
# Test Pipeline Component Setup
# ============================================================================

class TestPipelineComponentSetup:
    """Test pipeline component initialization."""
    
    @pytest.mark.asyncio
    async def test_setup_components(self, test_config):
        """Test that all pipeline components are initialized correctly."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            
            await pipeline._setup_components()
            
            # Check components are initialized
            assert pipeline._queue is not None
            assert pipeline._semaphore is not None
            assert pipeline._rate_limiter is not None
            assert pipeline._retry_manager is not None
            assert pipeline._producer is not None
            assert pipeline._worker_pool is not None
            
            # Check configuration
            assert pipeline._semaphore._value == test_config.max_concurrent_api_calls
            assert pipeline._worker_pool.worker_count == test_config.worker_count
    
    @pytest.mark.asyncio
    async def test_setup_components_twice(self, test_config):
        """Test that components can be set up multiple times."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            
            await pipeline._setup_components()
            queue1 = pipeline._queue
            
            await pipeline._setup_components()
            queue2 = pipeline._queue
            
            # Should create new instances
            assert queue1 is not queue2


# ============================================================================
# Test Pipeline Execution
# ============================================================================

class TestPipelineExecution:
    """Test pipeline execution and job processing."""
    
    @pytest.mark.asyncio
    async def test_pipeline_runs_with_no_jobs(self, test_config, mock_processor):
        """Test pipeline runs successfully with no jobs."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            
            # Mock database initialization
            with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
                # Mock producer after setup
                await pipeline._setup_components()
                
                with patch.object(pipeline._producer, 'get_job_count', new_callable=AsyncMock) as mock_count:
                    with patch.object(pipeline._producer, 'produce_jobs', new_callable=AsyncMock) as mock_produce:
                        mock_count.return_value = 0
                        mock_produce.return_value = async_generator([])
                        
                        results = await pipeline._run_pipeline(query="test", resume_text="", filters={})
                        
                        assert results == []
                        assert pipeline._running is False
    
    @pytest.mark.asyncio
    async def test_pipeline_processes_jobs(self, test_config, mock_processor, sample_jobs):
        """Test pipeline processes jobs successfully."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            
            with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
                await pipeline._setup_components()
                
                with patch.object(pipeline._producer, 'get_job_count', new_callable=AsyncMock) as mock_count:
                    with patch.object(pipeline._producer, 'produce_jobs', new_callable=AsyncMock) as mock_produce:
                        mock_count.return_value = len(sample_jobs)
                        mock_produce.return_value = async_generator(sample_jobs)
                        
                        results = await pipeline._run_pipeline(query="test", resume_text="", filters={})
                        
                        assert len(results) == len(sample_jobs)
                        assert all(r.is_success() for r in results)
    
    @pytest.mark.asyncio
    async def test_pipeline_handles_processing_errors(self, test_config, sample_jobs):
        """Test pipeline handles processing errors gracefully."""
        # Create a processor that fails
        async def failing_processor(job: JobContext) -> ProcessingResult:
            return ProcessingResult.failure(
                job_id=job.job_id,
                error="Simulated error",
                error_type="ValueError",
            )
        
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(failing_processor)
            
            with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
                await pipeline._setup_components()
                
                with patch.object(pipeline._producer, 'get_job_count', new_callable=AsyncMock) as mock_count:
                    with patch.object(pipeline._producer, 'produce_jobs', new_callable=AsyncMock) as mock_produce:
                        mock_count.return_value = len(sample_jobs)
                        mock_produce.return_value = async_generator(sample_jobs)
                        
                        results = await pipeline._run_pipeline(query="test", resume_text="", filters={})
                        
                        assert len(results) == len(sample_jobs)
                        assert all(not r.is_success() for r in results)
    
    @pytest.mark.asyncio
    async def test_pipeline_rejects_concurrent_runs(self, test_config, mock_processor):
        """Test pipeline rejects concurrent run attempts."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            pipeline._running = True
            
            with pytest.raises(RuntimeError, match="already running"):
                await pipeline.run(query="test")


# ============================================================================
# Test Pipeline Shutdown
# ============================================================================

class TestPipelineShutdown:
    """Test pipeline graceful shutdown."""
    
    @pytest.mark.asyncio
    async def test_pipeline_closes_cleanly(self, test_config):
        """Test pipeline cleanup."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config, db_url="sqlite+aiosqlite:///:memory:")
            
            # Initialize components
            await pipeline._init_database()
            await pipeline._setup_components()
            
            # Close pipeline
            await pipeline.close()
            
            assert pipeline._engine is None
    
    @pytest.mark.asyncio
    async def test_pipeline_shutdown_signal(self, test_config, sample_jobs):
        """Test pipeline respects shutdown signal."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            
            async def slow_processor(job: JobContext) -> ProcessingResult:
                await asyncio.sleep(1)  # Slow processing
                return ProcessingResult.success(job_id=job.job_id, data={})
            
            pipeline.set_processor(slow_processor)
            
            with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
                await pipeline._setup_components()
                
                with patch.object(pipeline._producer, 'get_job_count', new_callable=AsyncMock) as mock_count:
                    with patch.object(pipeline._producer, 'produce_jobs', new_callable=AsyncMock) as mock_produce:
                        mock_count.return_value = len(sample_jobs)
                        mock_produce.return_value = async_generator(sample_jobs)
                        
                        # Trigger shutdown after a short delay
                        async def trigger_shutdown():
                            await asyncio.sleep(0.1)
                            pipeline._shutdown_requested = True
                        
                        # Run both tasks
                        pipeline._running = True
                        await asyncio.gather(
                            pipeline._run_pipeline(query="test", resume_text="", filters={}),
                            trigger_shutdown(),
                        )
                        pipeline._running = False
                        
                        # Should have stopped production early
                        assert pipeline.stats.jobs_completed < len(sample_jobs)


# ============================================================================
# Test Pipeline Statistics
# ============================================================================

class TestPipelineStatistics:
    """Test pipeline statistics tracking."""
    
    @pytest.mark.asyncio
    async def test_pipeline_tracks_statistics(self, test_config, mock_processor, sample_jobs):
        """Test pipeline tracks processing statistics."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            
            with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
                await pipeline._setup_components()
                
                with patch.object(pipeline._producer, 'get_job_count', new_callable=AsyncMock) as mock_count:
                    with patch.object(pipeline._producer, 'produce_jobs', new_callable=AsyncMock) as mock_produce:
                        mock_count.return_value = len(sample_jobs)
                        mock_produce.return_value = async_generator(sample_jobs)
                        
                        await pipeline._run_pipeline(query="test", resume_text="", filters={})
                        
                        stats = pipeline.stats
                        assert stats.jobs_queued == len(sample_jobs)
                        assert stats.elapsed_seconds > 0
    
    def test_pipeline_stats_to_dict(self, test_config):
        """Test pipeline statistics serialization."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            
            stats_dict = pipeline.stats.to_dict()
            
            assert "jobs_queued" in stats_dict
            assert "jobs_completed" in stats_dict
            assert "jobs_failed" in stats_dict
            assert "elapsed_seconds" in stats_dict
            assert "throughput_jobs_per_second" in stats_dict


# ============================================================================
# Test Pipeline Builder
# ============================================================================

class TestPipelineBuilder:
    """Test AsyncJobPipelineBuilder."""
    
    def test_builder_creates_pipeline(self, test_config, mock_processor):
        """Test builder creates pipeline with configuration."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = (
                AsyncJobPipelineBuilder()
                .config(test_config)
                .processor(mock_processor)
                .build()
            )
            
            assert pipeline._config == test_config
            assert pipeline._processor == mock_processor
    
    def test_builder_with_progress_callback(self, test_config):
        """Test builder with progress callback."""
        callback = MagicMock()
        
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = (
                AsyncJobPipelineBuilder()
                .config(test_config)
                .on_progress(callback)
                .build()
            )
            
            assert pipeline._progress_callback == callback
    
    def test_builder_with_db_url(self):
        """Test builder with custom database URL."""
        db_url = "sqlite+aiosqlite:///test.db"
        
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = (
                AsyncJobPipelineBuilder()
                .db_url(db_url)
                .build()
            )
            
            assert pipeline._db_url == db_url


# ============================================================================
# Test Convenience Functions
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.asyncio
    async def test_create_pipeline_and_run(self, test_config, mock_processor, sample_jobs):
        """Test create_pipeline_and_run convenience function."""
        with patch('src.async_pipeline.pipeline.AsyncJobPipeline') as MockPipeline:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(return_value=[])
            mock_instance.close = AsyncMock()
            MockPipeline.return_value = mock_instance
            
            results = await create_pipeline_and_run(
                query="test",
                processor=mock_processor,
                config=test_config,
            )
            
            mock_instance.run.assert_called_once()
            mock_instance.close.assert_called_once()


# ============================================================================
# Test Progress Tracking
# ============================================================================

class TestProgressTracking:
    """Test progress tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_progress_callback_called(self, test_config, mock_processor, sample_jobs):
        """Test progress callback is called during processing."""
        progress_updates = []
        
        def progress_callback(data):
            progress_updates.append(data)
        
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            pipeline.set_progress_callback(progress_callback)
            
            # Create more jobs to trigger progress updates (updates every 10 jobs)
            many_jobs = [
                JobContext(
                    job_id=f"job-{i}",
                    title=f"Job {i}",
                    company="Test",
                    description="Test description with more than 50 chars for validation",
                    url=f"https://example.com/{i}",
                    source="test",
                )
                for i in range(25)
            ]
            
            with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
                await pipeline._setup_components()
                
                with patch.object(pipeline._producer, 'get_job_count', new_callable=AsyncMock) as mock_count:
                    with patch.object(pipeline._producer, 'produce_jobs', new_callable=AsyncMock) as mock_produce:
                        mock_count.return_value = len(many_jobs)
                        mock_produce.return_value = async_generator(many_jobs)
                        
                        await pipeline._run_pipeline(query="test", resume_text="", filters={})
                        
                        # Should have received progress updates
                        assert len(progress_updates) > 0


# ============================================================================
# Test Integration with Components
# ============================================================================

class TestComponentIntegration:
    """Test pipeline integration with components."""
    
    @pytest.mark.asyncio
    async def test_pipeline_integrates_with_queue(self, test_config, mock_processor, sample_jobs):
        """Test pipeline correctly integrates with bounded queue."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            
            with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
                await pipeline._setup_components()
                
                with patch.object(pipeline._producer, 'get_job_count', new_callable=AsyncMock) as mock_count:
                    with patch.object(pipeline._producer, 'produce_jobs', new_callable=AsyncMock) as mock_produce:
                        mock_count.return_value = len(sample_jobs)
                        mock_produce.return_value = async_generator(sample_jobs)
                        
                        await pipeline._run_pipeline(query="test", resume_text="", filters={})
                        
                        # Queue should be empty after processing
                        assert pipeline.queue.empty()
    
    @pytest.mark.asyncio
    async def test_pipeline_uses_rate_limiter(self, test_config, mock_processor):
        """Test pipeline integrates rate limiter."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            
            await pipeline._setup_components()
            
            assert pipeline.rate_limiter is not None
            assert pipeline._rate_limiter is not None


# ============================================================================
# Helper Functions
# ============================================================================

async def async_generator(items):
    """Helper to create an async generator from a list."""
    for item in items:
        yield item


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in pipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_handles_database_errors(self, test_config, mock_processor):
        """Test pipeline handles database initialization errors."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            
            with patch.object(pipeline, '_init_database', side_effect=Exception("DB Error")):
                with pytest.raises(Exception, match="DB Error"):
                    await pipeline.run(query="test")
    
    @pytest.mark.asyncio
    async def test_pipeline_handles_producer_errors(self, test_config, mock_processor):
        """Test pipeline handles producer errors."""
        with patch.object(AsyncJobPipeline, '_setup_signal_handlers'):
            pipeline = AsyncJobPipeline(config=test_config)
            pipeline.set_processor(mock_processor)
            
            async def failing_generator():
                yield JobContext(
                    job_id="1",
                    title="Test",
                    company="Test",
                    description="Test description longer than 50 chars for validation",
                    url="https://test.com",
                    source="test",
                )
                raise ValueError("Producer error")
            
            with patch.object(pipeline, '_init_database', new_callable=AsyncMock):
                await pipeline._setup_components()
                
                with patch.object(pipeline._producer, 'get_job_count', new_callable=AsyncMock) as mock_count:
                    with patch.object(pipeline._producer, 'produce_jobs', new_callable=AsyncMock) as mock_produce:
                        mock_count.return_value = 2
                        mock_produce.return_value = failing_generator()
                        
                        with pytest.raises(ValueError, match="Producer error"):
                            await pipeline._run_pipeline(query="test", resume_text="", filters={})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
