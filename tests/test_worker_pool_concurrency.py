"""
Property-based tests for AsyncWorkerPool concurrency mechanism.

**Validates: Requirements 2.1, 2.3**

This test suite uses hypothesis to verify worker pool concurrency properties:
- Exactly W workers are spawned for worker_count=W
- Sum of per-worker processed counts equals total jobs processed
- Concurrent execution with hypothesis-generated job sets
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import List

from src.async_pipeline.worker_pool import AsyncWorkerPool
from src.async_pipeline.bounded_queue import BoundedQueue
from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.types import JobContext, ProcessingResult, JobStatus


# Test strategies
worker_counts = st.integers(min_value=1, max_value=10)
job_counts = st.integers(min_value=1, max_value=100)
queue_sizes = st.integers(min_value=10, max_value=200)


def generate_test_job(job_id: str) -> JobContext:
    """Generate a test job context."""
    return JobContext(
        job_id=job_id,
        title=f"Software Engineer {job_id}",
        company=f"Company {job_id}",
        description="A" * 50,  # Minimum 50 chars
        url=f"https://example.com/job/{job_id}",
        source="test",
    )


async def simple_processor(job: JobContext) -> ProcessingResult:
    """Simple test processor that simulates work."""
    # Simulate some work
    await asyncio.sleep(0.01)
    
    return ProcessingResult.success(
        job_id=job.job_id,
        data={"processed": True},
        attempt_count=1,
    )


class TestWorkerPoolConcurrency:
    """Property-based tests for worker pool concurrency."""
    
    @pytest.mark.asyncio
    @given(worker_count=worker_counts)
    @settings(max_examples=3, deadline=10000)  # Reduced for faster execution
    async def test_property_exactly_w_workers_spawned(self, worker_count: int):
        """
        **Property 3: Worker Pool Concurrency - Exactly W Workers**
        **Validates: Requirements 2.1, 2.3**
        
        Test that exactly W workers are spawned for worker_count=W.
        """
        # Create worker pool
        queue = BoundedQueue(maxsize=100)
        semaphore = asyncio.Semaphore(10)
        config = ProcessorConfig(worker_count=worker_count)
        
        pool = AsyncWorkerPool(
            worker_count=worker_count,
            processor=simple_processor,
            semaphore=semaphore,
            queue=queue,
            config=config,
        )
        
        # Start the pool
        await pool.start()
        
        try:
            # Verify exactly W workers were created
            assert len(pool._workers) == worker_count, \
                f"Expected {worker_count} workers, got {len(pool._workers)}"
            
            # Verify workers_total stat is correct
            assert pool.stats.workers_total == worker_count, \
                f"Expected workers_total={worker_count}, got {pool.stats.workers_total}"
            
        finally:
            # Clean shutdown
            await pool.stop()
    
    @pytest.mark.asyncio
    @given(
        worker_count=worker_counts,
        job_count=job_counts,
    )
    @settings(max_examples=2, deadline=15000)  # Reduced for faster execution
    async def test_property_sum_of_per_worker_counts_equals_total(
        self, 
        worker_count: int, 
        job_count: int
    ):
        """
        **Property 3: Worker Pool Concurrency - Per-Worker Counts**
        **Validates: Requirements 2.1, 2.3**
        
        Test that sum of per-worker processed counts equals total jobs processed.
        """
        # Track per-worker job counts
        worker_job_counts = {}
        lock = asyncio.Lock()
        
        async def tracking_processor(job: JobContext) -> ProcessingResult:
            """Processor that tracks which worker processes each job."""
            # Simulate work
            await asyncio.sleep(0.001)
            
            # Get current task name to identify worker
            current_task = asyncio.current_task()
            worker_name = current_task.get_name() if current_task else "unknown"
            
            # Track this worker's count
            async with lock:
                worker_job_counts[worker_name] = worker_job_counts.get(worker_name, 0) + 1
            
            return ProcessingResult.success(
                job_id=job.job_id,
                data={"processed": True},
                attempt_count=1,
            )
        
        # Create worker pool
        queue = BoundedQueue(maxsize=max(100, job_count + 10))
        semaphore = asyncio.Semaphore(worker_count)
        config = ProcessorConfig(worker_count=worker_count)
        
        pool = AsyncWorkerPool(
            worker_count=worker_count,
            processor=tracking_processor,
            semaphore=semaphore,
            queue=queue,
            config=config,
        )
        
        # Start the pool
        await pool.start()
        
        try:
            # Queue all jobs
            jobs = [generate_test_job(f"job-{i}") for i in range(job_count)]
            for job in jobs:
                await queue.put(job)
            
            # Wait for all jobs to be processed
            await pool.wait_completion()
            
            # Verify sum of per-worker counts equals total jobs
            total_processed_by_workers = sum(worker_job_counts.values())
            assert total_processed_by_workers == job_count, \
                f"Sum of per-worker counts ({total_processed_by_workers}) != total jobs ({job_count})"
            
            # Verify pool stats match
            assert pool.stats.jobs_processed == job_count, \
                f"Pool stats jobs_processed ({pool.stats.jobs_processed}) != total jobs ({job_count})"
            
        finally:
            # Clean shutdown
            await pool.stop()
    
    @pytest.mark.asyncio
    @given(
        worker_count=st.integers(min_value=2, max_value=8),
        job_count=st.integers(min_value=10, max_value=50),
    )
    @settings(max_examples=2, deadline=20000)  # Reduced for faster execution
    async def test_property_concurrent_execution(
        self, 
        worker_count: int, 
        job_count: int
    ):
        """
        **Property 3: Worker Pool Concurrency - Concurrent Execution**
        **Validates: Requirements 2.1, 2.3**
        
        Test that multiple workers execute concurrently.
        """
        # Track concurrent execution
        active_workers = []
        max_concurrent = 0
        lock = asyncio.Lock()
        
        async def concurrent_processor(job: JobContext) -> ProcessingResult:
            """Processor that tracks concurrent execution."""
            nonlocal max_concurrent
            
            current_task = asyncio.current_task()
            worker_name = current_task.get_name() if current_task else "unknown"
            
            # Mark this worker as active
            async with lock:
                active_workers.append(worker_name)
                current_concurrent = len(set(active_workers))
                max_concurrent = max(max_concurrent, current_concurrent)
            
            # Simulate work
            await asyncio.sleep(0.05)
            
            # Mark this worker as done
            async with lock:
                if worker_name in active_workers:
                    active_workers.remove(worker_name)
            
            return ProcessingResult.success(
                job_id=job.job_id,
                data={"processed": True},
                attempt_count=1,
            )
        
        # Create worker pool
        queue = BoundedQueue(maxsize=max(100, job_count + 10))
        # Semaphore large enough to not block concurrency
        semaphore = asyncio.Semaphore(worker_count)
        config = ProcessorConfig(worker_count=worker_count)
        
        pool = AsyncWorkerPool(
            worker_count=worker_count,
            processor=concurrent_processor,
            semaphore=semaphore,
            queue=queue,
            config=config,
        )
        
        # Start the pool
        await pool.start()
        
        try:
            # Queue all jobs
            jobs = [generate_test_job(f"job-{i}") for i in range(job_count)]
            for job in jobs:
                await queue.put(job)
            
            # Wait for all jobs to be processed
            await pool.wait_completion()
            
            # Verify that we had concurrent execution
            # With worker_count >= 2 and job_count >= 10, we should see concurrency
            expected_min_concurrent = min(2, worker_count)
            assert max_concurrent >= expected_min_concurrent, \
                f"Max concurrent workers ({max_concurrent}) < expected min ({expected_min_concurrent})"
            
            # Verify we never exceeded worker_count
            assert max_concurrent <= worker_count, \
                f"Max concurrent workers ({max_concurrent}) > worker_count ({worker_count})"
            
        finally:
            # Clean shutdown
            await pool.stop()
    
    @pytest.mark.asyncio
    @given(
        worker_count=worker_counts,
        job_count=st.integers(min_value=5, max_value=50),
    )
    @settings(max_examples=2, deadline=15000)  # Reduced for faster execution
    async def test_property_worker_statistics_consistency(
        self, 
        worker_count: int, 
        job_count: int
    ):
        """
        **Property 3: Worker Pool Concurrency - Statistics Consistency**
        **Validates: Requirements 2.1, 2.3**
        
        Test that worker pool statistics are consistent and correct.
        """
        # Create worker pool
        queue = BoundedQueue(maxsize=max(100, job_count + 10))
        semaphore = asyncio.Semaphore(worker_count)
        config = ProcessorConfig(worker_count=worker_count)
        
        pool = AsyncWorkerPool(
            worker_count=worker_count,
            processor=simple_processor,
            semaphore=semaphore,
            queue=queue,
            config=config,
        )
        
        # Start the pool
        await pool.start()
        
        try:
            # Queue all jobs
            jobs = [generate_test_job(f"job-{i}") for i in range(job_count)]
            for job in jobs:
                await queue.put(job)
            
            # Wait for all jobs to be processed
            results = await pool.wait_completion()
            
            # Verify statistics
            stats = pool.get_stats()
            
            # Total workers should match configuration
            assert stats.workers_total == worker_count
            
            # All jobs should be accounted for (processed or failed)
            assert stats.jobs_processed + stats.jobs_failed == job_count, \
                f"jobs_processed ({stats.jobs_processed}) + jobs_failed ({stats.jobs_failed}) != total ({job_count})"
            
            # Number of results should match job count
            assert len(results) == job_count, \
                f"Results count ({len(results)}) != job count ({job_count})"
            
            # No active workers after completion
            assert stats.workers_active == 0, \
                f"Active workers should be 0 after completion, got {stats.workers_active}"
            
            # All jobs should have succeeded (our simple processor doesn't fail)
            assert stats.jobs_processed == job_count
            assert stats.jobs_failed == 0
            
        finally:
            # Clean shutdown
            await pool.stop()
    
    @pytest.mark.asyncio
    @given(
        worker_count=st.integers(min_value=1, max_value=5),
        job_count=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=2, deadline=10000)  # Reduced for faster execution
    async def test_property_all_jobs_processed_exactly_once(
        self, 
        worker_count: int, 
        job_count: int
    ):
        """
        **Property 3: Worker Pool Concurrency - No Duplicate Processing**
        **Validates: Requirements 2.1, 2.3**
        
        Test that each job is processed exactly once, not duplicated or skipped.
        """
        processed_jobs = set()
        lock = asyncio.Lock()
        
        async def tracking_processor(job: JobContext) -> ProcessingResult:
            """Processor that tracks which jobs have been processed."""
            async with lock:
                # Check if this job was already processed
                if job.job_id in processed_jobs:
                    raise ValueError(f"Job {job.job_id} processed twice!")
                processed_jobs.add(job.job_id)
            
            # Simulate work
            await asyncio.sleep(0.001)
            
            return ProcessingResult.success(
                job_id=job.job_id,
                data={"processed": True},
                attempt_count=1,
            )
        
        # Create worker pool
        queue = BoundedQueue(maxsize=max(100, job_count + 10))
        semaphore = asyncio.Semaphore(worker_count)
        config = ProcessorConfig(worker_count=worker_count)
        
        pool = AsyncWorkerPool(
            worker_count=worker_count,
            processor=tracking_processor,
            semaphore=semaphore,
            queue=queue,
            config=config,
        )
        
        # Start the pool
        await pool.start()
        
        try:
            # Create unique jobs
            job_ids = [f"job-{i}" for i in range(job_count)]
            jobs = [generate_test_job(job_id) for job_id in job_ids]
            
            # Queue all jobs
            for job in jobs:
                await queue.put(job)
            
            # Wait for all jobs to be processed
            await pool.wait_completion()
            
            # Verify all jobs were processed exactly once
            assert len(processed_jobs) == job_count, \
                f"Processed jobs count ({len(processed_jobs)}) != job count ({job_count})"
            
            # Verify all expected job IDs were processed
            expected_ids = set(job_ids)
            assert processed_jobs == expected_ids, \
                f"Processed jobs {processed_jobs} != expected {expected_ids}"
            
        finally:
            # Clean shutdown
            await pool.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
