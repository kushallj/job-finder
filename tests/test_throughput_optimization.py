"""
Throughput optimization test for the async job pipeline.

This test validates Requirements 16.1, 16.2, 16.3, 16.4, 16.5:
- Configure pipeline with 5 workers, queue size 100, appropriate rate limits
- Test processing 1000 jobs end-to-end and measure total execution time
- Verify completion time is under 5 minutes (300 seconds)
- Verify minimum sustained throughput of 3.3 jobs/second
- Profile with cProfile to identify bottlenecks if throughput is below target
- Optimize identified bottlenecks
- Verify throughput remains steady without degradation over full test duration
"""
import asyncio
import cProfile
import io
import pstats
import time
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.pipeline import AsyncJobPipeline
from src.async_pipeline.types import JobContext, JobStatus, ProcessingResult
from src.models import Base, Job


class TestThroughputOptimization:
    """
    Test suite for throughput optimization validation.
    
    Requirements Coverage: 16.1, 16.2, 16.3, 16.4, 16.5
    """

    @pytest.fixture
    async def async_db_engine(self):
        """Create async SQLite engine for testing."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield engine
        
        # Cleanup
        await engine.dispose()

    @pytest.fixture
    async def async_session_factory(self, async_db_engine):
        """Create async session factory."""
        return async_sessionmaker(
            async_db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @pytest.fixture
    async def populate_jobs(self, async_session_factory, job_count: int = 1000):
        """Populate database with test jobs."""
        async with async_session_factory() as session:
            jobs = []
            for i in range(job_count):
                job = Job(
                    job_id=f"test_job_{i:05d}",
                    title=f"Software Engineer {i}",
                    company=f"Company {i % 100}",
                    location="Remote",
                    description=f"Job description for position {i}. Python, Django, FastAPI. 5+ years experience.",
                    url=f"https://example.com/jobs/{i}",
                    source="test",
                )
                jobs.append(job)
            
            session.add_all(jobs)
            await session.commit()
        
        return job_count

    @pytest.mark.asyncio
    async def test_throughput_with_1000_jobs(self, async_db_engine, async_session_factory):
        """
        Test pipeline throughput with 1000 jobs.
        
        Requirements:
        - 16.1: Configure pipeline with 5 workers, queue size 100
        - 16.2: Test processing 1000 jobs end-to-end
        - 16.3: Verify completion time under 5 minutes (300 seconds)
        - 16.4: Verify minimum sustained throughput of 3.3 jobs/second
        """
        # Populate database with 1000 jobs
        job_count = 1000
        async with async_session_factory() as session:
            jobs = []
            for i in range(job_count):
                job = Job(
                    job_id=f"test_job_{i:05d}",
                    title=f"Software Engineer {i}",
                    company=f"Company {i % 100}",
                    location="Remote",
                    description=f"Job description for position {i}. Python, Django, FastAPI.",
                    url=f"https://example.com/jobs/{i}",
                    source="test",
                )
                jobs.append(job)
            
            session.add_all(jobs)
            await session.commit()
        
        # Configure pipeline (Requirement 16.1)
        config = ProcessorConfig(
            worker_count=5,
            queue_size=100,
            max_concurrent_api_calls=10,
            chunk_size=100,
            # Disable rate limiting for tests to measure pure pipeline throughput
            llm_rate_limit=1000.0,
            email_rate_limit=1000.0,
            scraper_rate_limit=1000.0,
            # Short timeouts for fast tests
            llm_timeout_seconds=5.0,
            email_timeout_seconds=5.0,
            scraper_timeout_seconds=5.0,
            db_timeout_seconds=5.0,
            # Retry settings
            max_retries=0,  # Disable retries for predictable timing
            enable_progress_bar=False,  # Disable for clean test output
        )
        config.validate()
        
        # Create mock processor that simulates real work
        async def mock_processor(job: JobContext) -> ProcessingResult:
            """Mock processor that simulates LLM and API calls."""
            # Simulate async I/O operations (LLM, email, scraping)
            # Using short delays to simulate fast API responses
            await asyncio.sleep(0.01)  # Simulate 10ms API call
            
            return ProcessingResult(
                job_id=job.job_id,
                status=JobStatus.COMPLETED,
                data={"mock": "data"},
                error=None,
                error_type=None,
                attempt_count=1,
                processing_time_ms=10.0,
                timestamp=time.time(),
                worker_id="test_worker",
            )
        
        # Create pipeline and inject the test engine
        pipeline = AsyncJobPipeline(
            config=config,
            db_url=async_db_engine.url.render_as_string(hide_password=False),
        )
        
        # Inject the test engine and session factory to avoid creating a new connection
        pipeline._engine = async_db_engine
        pipeline._session_factory = async_session_factory
        
        pipeline.set_processor(mock_processor)
        
        # Measure execution time (Requirement 16.2)
        start_time = time.time()
        
        try:
            results = await pipeline.run(query="", filters={})
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Verify all jobs were processed
            assert len(results) == job_count, f"Expected {job_count} results, got {len(results)}"
            
            # Count successful jobs
            successful = sum(1 for r in results if r.is_success())
            
            # Calculate throughput
            throughput = job_count / elapsed_time if elapsed_time > 0 else 0
            
            # Log results
            print(f"\n=== Throughput Test Results ===")
            print(f"Total jobs: {job_count}")
            print(f"Successful: {successful}")
            print(f"Failed: {job_count - successful}")
            print(f"Elapsed time: {elapsed_time:.2f} seconds")
            print(f"Throughput: {throughput:.2f} jobs/second")
            print(f"Worker count: {config.worker_count}")
            print(f"Queue size: {config.queue_size}")
            
            # Requirement 16.3: Verify completion time under 5 minutes (300 seconds)
            assert elapsed_time < 300, (
                f"Pipeline took {elapsed_time:.2f}s, exceeding 300s limit"
            )
            
            # Requirement 16.4: Verify minimum sustained throughput of 3.3 jobs/second
            min_throughput = 3.3
            assert throughput >= min_throughput, (
                f"Throughput {throughput:.2f} jobs/s is below minimum {min_throughput} jobs/s"
            )
            
            print(f"✓ Throughput test PASSED")
            print(f"✓ Completed in {elapsed_time:.2f}s (< 300s requirement)")
            print(f"✓ Achieved {throughput:.2f} jobs/s (>= 3.3 jobs/s requirement)")
            
        finally:
            # Don't dispose the engine since it's shared with the fixture
            pipeline._engine = None
            await pipeline.close()

    @pytest.mark.asyncio
    async def test_throughput_profiling(self, async_db_engine, async_session_factory):
        """
        Test pipeline throughput with profiling to identify bottlenecks.
        
        Requirement 16.5: Profile with cProfile to identify bottlenecks if throughput is below target.
        """
        # Populate database with 100 jobs for faster profiling
        job_count = 100
        async with async_session_factory() as session:
            jobs = []
            for i in range(job_count):
                job = Job(
                    job_id=f"test_job_{i:05d}",
                    title=f"Software Engineer {i}",
                    company=f"Company {i % 10}",
                    location="Remote",
                    description=f"Job description {i}. Python, Django.",
                    url=f"https://example.com/jobs/{i}",
                    source="test",
                )
                jobs.append(job)
            
            session.add_all(jobs)
            await session.commit()
        
        # Configure pipeline
        config = ProcessorConfig(
            worker_count=5,
            queue_size=100,
            max_concurrent_api_calls=10,
            llm_rate_limit=1000.0,
            email_rate_limit=1000.0,
            scraper_rate_limit=1000.0,
            max_retries=0,
            enable_progress_bar=False,
        )
        
        # Mock processor
        async def mock_processor(job: JobContext) -> ProcessingResult:
            await asyncio.sleep(0.01)
            return ProcessingResult(
                job_id=job.job_id,
                status=JobStatus.COMPLETED,
                data={},
                error=None,
                error_type=None,
                attempt_count=1,
                processing_time_ms=10.0,
                timestamp=time.time(),
                worker_id="test",
            )
        
        # Create pipeline and inject the test engine
        pipeline = AsyncJobPipeline(
            config=config,
            db_url=async_db_engine.url.render_as_string(hide_password=False),
        )
        
        # Inject the test engine and session factory
        pipeline._engine = async_db_engine
        pipeline._session_factory = async_session_factory
        
        pipeline.set_processor(mock_processor)
        
        # Profile the execution
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.time()
        
        try:
            results = await pipeline.run(query="", filters={})
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            profiler.disable()
            
            # Calculate throughput
            throughput = job_count / elapsed_time if elapsed_time > 0 else 0
            
            # Generate profiling report
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
            ps.print_stats(20)  # Top 20 functions
            
            print(f"\n=== Profiling Results ===")
            print(f"Jobs: {job_count}")
            print(f"Elapsed time: {elapsed_time:.2f}s")
            print(f"Throughput: {throughput:.2f} jobs/s")
            print(f"\n=== Top 20 Functions by Cumulative Time ===")
            print(s.getvalue())
            
            # Verify throughput is reasonable
            assert throughput >= 3.3, (
                f"Throughput {throughput:.2f} jobs/s below minimum 3.3 jobs/s. "
                f"Check profiling output above for bottlenecks."
            )
            
            print(f"✓ Profiling test PASSED")
            
        finally:
            # Don't dispose the engine since it's shared with the fixture
            pipeline._engine = None
            await pipeline.close()

    @pytest.mark.asyncio
    async def test_throughput_steady_over_duration(self, async_db_engine, async_session_factory):
        """
        Test that throughput remains steady without degradation over full test duration.
        
        Requirement 16.5: Verify throughput remains steady without degradation.
        """
        # Populate database with 500 jobs for reasonable test duration
        job_count = 500
        async with async_session_factory() as session:
            jobs = []
            for i in range(job_count):
                job = Job(
                    job_id=f"test_job_{i:05d}",
                    title=f"Software Engineer {i}",
                    company=f"Company {i % 50}",
                    location="Remote",
                    description=f"Job description {i}.",
                    url=f"https://example.com/jobs/{i}",
                    source="test",
                )
                jobs.append(job)
            
            session.add_all(jobs)
            await session.commit()
        
        # Configure pipeline
        config = ProcessorConfig(
            worker_count=5,
            queue_size=100,
            max_concurrent_api_calls=10,
            llm_rate_limit=1000.0,
            email_rate_limit=1000.0,
            scraper_rate_limit=1000.0,
            max_retries=0,
            enable_progress_bar=False,
        )
        
        # Track throughput over time
        throughput_samples = []
        sample_interval = 50  # Sample every 50 jobs
        
        processed_count = 0
        start_time = time.time()
        last_sample_time = start_time
        last_sample_count = 0
        
        async def tracking_processor(job: JobContext) -> ProcessingResult:
            """Processor that tracks throughput over time."""
            nonlocal processed_count, last_sample_time, last_sample_count
            
            await asyncio.sleep(0.01)
            
            processed_count += 1
            
            # Sample throughput every N jobs
            if processed_count % sample_interval == 0:
                current_time = time.time()
                interval_duration = current_time - last_sample_time
                interval_jobs = processed_count - last_sample_count
                
                if interval_duration > 0:
                    interval_throughput = interval_jobs / interval_duration
                    throughput_samples.append({
                        "jobs_processed": processed_count,
                        "throughput": interval_throughput,
                        "elapsed": current_time - start_time,
                    })
                
                last_sample_time = current_time
                last_sample_count = processed_count
            
            return ProcessingResult(
                job_id=job.job_id,
                status=JobStatus.COMPLETED,
                data={},
                error=None,
                error_type=None,
                attempt_count=1,
                processing_time_ms=10.0,
                timestamp=time.time(),
                worker_id="test",
            )
        
        # Create pipeline and inject the test engine
        pipeline = AsyncJobPipeline(
            config=config,
            db_url=async_db_engine.url.render_as_string(hide_password=False),
        )
        
        # Inject the test engine and session factory
        pipeline._engine = async_db_engine
        pipeline._session_factory = async_session_factory
        
        pipeline.set_processor(tracking_processor)
        
        try:
            results = await pipeline.run(query="", filters={})
            
            end_time = time.time()
            total_elapsed = end_time - start_time
            overall_throughput = job_count / total_elapsed if total_elapsed > 0 else 0
            
            print(f"\n=== Throughput Stability Test Results ===")
            print(f"Total jobs: {job_count}")
            print(f"Total elapsed: {total_elapsed:.2f}s")
            print(f"Overall throughput: {overall_throughput:.2f} jobs/s")
            print(f"\n=== Throughput Samples ===")
            
            # Analyze throughput samples
            if len(throughput_samples) >= 2:
                first_half = throughput_samples[:len(throughput_samples)//2]
                second_half = throughput_samples[len(throughput_samples)//2:]
                
                avg_first_half = sum(s["throughput"] for s in first_half) / len(first_half)
                avg_second_half = sum(s["throughput"] for s in second_half) / len(second_half)
                
                degradation = (avg_first_half - avg_second_half) / avg_first_half * 100
                
                print(f"First half avg throughput: {avg_first_half:.2f} jobs/s")
                print(f"Second half avg throughput: {avg_second_half:.2f} jobs/s")
                print(f"Degradation: {degradation:.2f}%")
                
                # Print all samples
                for i, sample in enumerate(throughput_samples):
                    print(
                        f"  Sample {i+1}: {sample['jobs_processed']} jobs, "
                        f"{sample['throughput']:.2f} jobs/s, "
                        f"elapsed: {sample['elapsed']:.1f}s"
                    )
                
                # Verify throughput doesn't degrade significantly
                # Allow up to 20% degradation due to test variance
                max_allowed_degradation = 20.0
                assert degradation < max_allowed_degradation, (
                    f"Throughput degraded by {degradation:.2f}%, "
                    f"exceeding {max_allowed_degradation}% threshold"
                )
                
                print(f"\n✓ Throughput stability test PASSED")
                print(f"✓ Degradation {degradation:.2f}% is within {max_allowed_degradation}% threshold")
            else:
                print("Not enough samples to analyze throughput stability")
            
        finally:
            # Don't dispose the engine since it's shared with the fixture
            pipeline._engine = None
            await pipeline.close()

    @pytest.mark.asyncio
    async def test_throughput_with_different_worker_counts(self, async_db_engine, async_session_factory):
        """
        Test throughput with different worker counts to find optimal configuration.
        
        This helps optimize the pipeline by comparing different concurrency levels.
        """
        job_count = 200
        worker_counts = [1, 3, 5, 10]
        results_by_workers = {}
        
        # Populate database
        async with async_session_factory() as session:
            jobs = []
            for i in range(job_count):
                job = Job(
                    job_id=f"test_job_{i:05d}",
                    title=f"Software Engineer {i}",
                    company=f"Company {i % 20}",
                    location="Remote",
                    description=f"Job description {i}.",
                    url=f"https://example.com/jobs/{i}",
                    source="test",
                )
                jobs.append(job)
            
            session.add_all(jobs)
            await session.commit()
        
        # Mock processor
        async def mock_processor(job: JobContext) -> ProcessingResult:
            await asyncio.sleep(0.01)
            return ProcessingResult(
                job_id=job.job_id,
                status=JobStatus.COMPLETED,
                data={},
                error=None,
                error_type=None,
                attempt_count=1,
                processing_time_ms=10.0,
                timestamp=time.time(),
                worker_id="test",
            )
        
        print(f"\n=== Worker Count Optimization Test ===")
        print(f"Testing {job_count} jobs with different worker counts")
        
        for worker_count in worker_counts:
            # Configure pipeline
            config = ProcessorConfig(
                worker_count=worker_count,
                queue_size=100,
                max_concurrent_api_calls=worker_count * 2,
                llm_rate_limit=1000.0,
                email_rate_limit=1000.0,
                scraper_rate_limit=1000.0,
                max_retries=0,
                enable_progress_bar=False,
            )
            
            # Create pipeline and inject the test engine
            pipeline = AsyncJobPipeline(
                config=config,
                db_url=async_db_engine.url.render_as_string(hide_password=False),
            )
            
            # Inject the test engine and session factory
            pipeline._engine = async_db_engine
            pipeline._session_factory = async_session_factory
            
            pipeline.set_processor(mock_processor)
            
            # Measure throughput
            start_time = time.time()
            
            try:
                results = await pipeline.run(query="", filters={})
                
                end_time = time.time()
                elapsed = end_time - start_time
                throughput = job_count / elapsed if elapsed > 0 else 0
                
                results_by_workers[worker_count] = {
                    "elapsed": elapsed,
                    "throughput": throughput,
                }
                
                print(f"Workers: {worker_count:2d} | "
                      f"Elapsed: {elapsed:6.2f}s | "
                      f"Throughput: {throughput:6.2f} jobs/s")
                
            finally:
                # Don't dispose the engine since it's shared with the fixture
                pipeline._engine = None
                await pipeline.close()
        
        # Verify 5 workers meets the requirement
        if 5 in results_by_workers:
            throughput_5_workers = results_by_workers[5]["throughput"]
            assert throughput_5_workers >= 3.3, (
                f"5 workers achieved {throughput_5_workers:.2f} jobs/s, "
                f"below 3.3 jobs/s requirement"
            )
        
        print(f"\n✓ Worker count optimization test PASSED")


if __name__ == "__main__":
    # Run tests manually
    pytest.main([__file__, "-v", "-s"])
