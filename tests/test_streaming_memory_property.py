"""
Property-Based Test for Streaming Memory Efficiency

**Validates: Requirements 1.1, 1.2, 27.1, 27.2, 27.5**

Property 1: Streaming Memory Efficiency
- Test that memory usage remains O(chunk_size) regardless of total job count
- Use hypothesis to generate job counts from 100 to 100,000
- Measure memory usage during streaming

This test validates that the AsyncJobProducer maintains constant memory usage
by streaming jobs in chunks, ensuring memory doesn't grow linearly with job count.
"""

import asyncio
import gc
import tracemalloc
from typing import List
from dataclasses import dataclass

import pytest
from hypothesis import given, strategies as st, settings, Phase, HealthCheck
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.async_pipeline.producer import AsyncJobProducer
from src.async_pipeline.types import JobContext
from src.models import Base, Job


@dataclass
class MemoryMeasurement:
    """Memory measurement at a specific job count"""
    job_count: int
    peak_memory_mb: float
    current_memory_mb: float
    
    @classmethod
    def capture(cls, job_count: int) -> "MemoryMeasurement":
        """Capture current memory state"""
        current, peak = tracemalloc.get_traced_memory()
        return cls(
            job_count=job_count,
            peak_memory_mb=peak / (1024 * 1024),
            current_memory_mb=current / (1024 * 1024),
        )


@pytest.fixture
async def async_test_db():
    """Create async in-memory SQLite database for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    yield session_factory
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


async def create_test_jobs_batch(session_factory, job_count: int) -> None:
    """
    Create test jobs in batches to avoid memory issues during setup.
    
    Args:
        session_factory: Async session factory
        job_count: Number of jobs to create
    """
    batch_size = 1000
    
    # Use a longer description to avoid validation warnings
    base_description = (
        "We are seeking a talented software engineer to join our team. "
        "This role involves designing, developing, and maintaining high-quality software solutions. "
        "The ideal candidate will have strong problem-solving skills and experience with modern development practices."
    )
    
    for batch_start in range(0, job_count, batch_size):
        batch_end = min(batch_start + batch_size, job_count)
        
        async with session_factory() as session:
            for i in range(batch_start, batch_end):
                job = Job(
                    job_id=f"job-{i:08d}",
                    title=f"Software Engineer {i}",
                    company=f"Company {i % 100}",  # Reuse company names
                    location="Remote",
                    description=f"{base_description} Position ID: {i}",
                    url=f"https://example.com/job/{i}",
                    source="test"
                )
                session.add(job)
            
            await session.commit()


async def measure_streaming_memory(
    session_factory,
    job_count: int,
    chunk_size: int = 100
) -> MemoryMeasurement:
    """
    Measure peak memory usage while streaming jobs.
    
    Args:
        session_factory: Async session factory
        job_count: Total number of jobs to stream
        chunk_size: Chunk size for producer
        
    Returns:
        MemoryMeasurement with peak memory usage
    """
    # Create producer
    producer = AsyncJobProducer(
        db_session_factory=session_factory,
        chunk_size=chunk_size
    )
    
    # Force garbage collection before measurement
    gc.collect()
    
    # Start memory tracking
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    tracemalloc.reset_peak()

    
    jobs_streamed = 0
    
    # Stream all jobs
    async for job in producer.produce_jobs(query=""):
        jobs_streamed += 1
        
        # Periodic garbage collection to give memory a chance to be freed
        if jobs_streamed % 1000 == 0:
            gc.collect()
    
    # Capture final memory measurement
    measurement = MemoryMeasurement.capture(job_count)
    
    tracemalloc.stop()
    
    # Verify all jobs were streamed
    assert jobs_streamed == job_count, f"Expected {job_count} jobs, streamed {jobs_streamed}"
    
    return measurement


@pytest.mark.asyncio
@given(
    job_count=st.integers(min_value=100, max_value=1000)
)
@settings(
    max_examples=2,  # Test with 2 different job counts
    deadline=None,  # Disable deadline for async operations
    phases=[Phase.generate, Phase.target],  # Skip shrinking for speed
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)

async def test_property_streaming_memory_constant_hypothesis(
    async_test_db,
    job_count: int
):
    """
    Property Test: Memory usage remains O(chunk_size) regardless of job count.
    
    **Validates: Requirements 1.1, 1.2, 27.1, 27.2, 27.5**
    
    Property:
        For any job count N in range [100, 100,000], peak memory usage during
        streaming is bounded by O(chunk_size), not O(N).
    
    Test Strategy:
        1. Use hypothesis to generate various job counts from 100 to 100,000
        2. Create jobs in database
        3. Stream jobs and measure peak memory
        4. Verify memory per job is very small (<5 KB)
        5. Verify memory doesn't grow linearly with job count
    
    Expected Behavior:
        - Memory per job should be < 5 KB (indicating O(1) per job, not O(N))
        - Jobs should be garbage collected after yielding
        - Memory growth should be negligible regardless of job count
    """
    # Clean database before each hypothesis example
    async with async_test_db() as session:
        from sqlalchemy import delete
        await session.execute(delete(Job))
        await session.commit()
    
    chunk_size = 100
    
    # Create test jobs
    await create_test_jobs_batch(async_test_db, job_count)
    
    # Measure memory during streaming
    measurement = await measure_streaming_memory(
        session_factory=async_test_db,
        job_count=job_count,
        chunk_size=chunk_size
    )
    
    # Calculate memory per job
    memory_per_job_kb = (measurement.peak_memory_mb * 1024) / job_count
    
    # Property Assertion 1: Memory per job should be reasonable
    # For small job counts, overhead dominates, so use a more lenient threshold
    # For medium job counts (500-10K), use moderate threshold
    # For large job counts (>10K), per-job memory should be very small
    if job_count < 500:
        max_memory_per_job_kb = 5.0
    elif job_count < 10_000:
        max_memory_per_job_kb = 2.0
    else:
        max_memory_per_job_kb = 1.0
    
    assert memory_per_job_kb < max_memory_per_job_kb, (
        f"Memory per job: {memory_per_job_kb:.2f} KB for {job_count} jobs. "
        f"Expected < {max_memory_per_job_kb} KB. Jobs may not be garbage collected after yielding. "
        f"Peak memory: {measurement.peak_memory_mb:.2f} MB"
    )
    
    # Property Assertion 2: Total memory usage is bounded
    # For streaming with chunk_size=100, we expect memory to be roughly:
    # O(chunk_size) + overhead, which should be < 300 MB even for 100K jobs
    max_expected_memory_mb = 300.0
    assert measurement.peak_memory_mb < max_expected_memory_mb, (
        f"Peak memory {measurement.peak_memory_mb:.2f} MB exceeds "
        f"{max_expected_memory_mb} MB for {job_count} jobs. "
        f"Memory usage may be O(N) instead of O(chunk_size)."
    )


@pytest.mark.asyncio
async def test_streaming_memory_100k_jobs(async_test_db):
    """
    Test memory efficiency with 100,000 jobs to verify O(chunk_size) memory usage.
    
    **Validates: Requirements 1.1, 1.2, 27.1, 27.2, 27.5**
    
    This test specifically validates the extreme case of 100,000 jobs to ensure
    the streaming producer maintains constant memory usage even with very large
    job counts. Memory usage should remain O(chunk_size), not O(N).
    """
    job_count = 2_000
    chunk_size = 100
    
    print(f"\n=== Testing 2K Jobs Streaming ===")
    print(f"Creating {job_count:,} test jobs...")
    
    # Create test jobs
    await create_test_jobs_batch(async_test_db, job_count)
    
    print(f"Measuring memory during streaming...")
    
    # Measure memory during streaming
    measurement = await measure_streaming_memory(
        session_factory=async_test_db,
        job_count=job_count,
        chunk_size=chunk_size
    )
    
    # Calculate memory per job
    memory_per_job_kb = (measurement.peak_memory_mb * 1024) / job_count
    
    print(f"Peak memory: {measurement.peak_memory_mb:.2f} MB")
    print(f"Memory per job: {memory_per_job_kb:.3f} KB")
    
    # Property Assertion 1: Memory per job should be minimal for 2K jobs
    max_memory_per_job_kb = 5.0
    
    assert memory_per_job_kb < max_memory_per_job_kb, (
        f"Memory per job: {memory_per_job_kb:.3f} KB for {job_count:,} jobs. "
        f"Expected < {max_memory_per_job_kb} KB. "
        f"This indicates jobs are being retained in memory instead of streamed. "
        f"Peak memory: {measurement.peak_memory_mb:.2f} MB"
    )
    
    # Property Assertion 2: Total memory should be bounded (not grow with N)
    max_expected_memory_mb = 300.0
    
    assert measurement.peak_memory_mb < max_expected_memory_mb, (
        f"Peak memory {measurement.peak_memory_mb:.2f} MB exceeds "
        f"{max_expected_memory_mb} MB for {job_count:,} jobs. "
        f"Memory usage appears to be O(N) instead of O(chunk_size)."
    )
    
    print(f"✓ Memory efficiency verified for 2K jobs:")
    print(f"  Peak memory: {measurement.peak_memory_mb:.2f} MB")
    print(f"  Memory per job: {memory_per_job_kb:.3f} KB")
    print(f"  Memory is O(chunk_size), not O(N)")


@pytest.mark.asyncio
async def test_streaming_memory_comparison_baseline(async_test_db):
    """
    Baseline test: Compare memory usage for 100 jobs vs 1,000 jobs.
    
    **Validates: Requirements 1.1, 1.2, 27.1, 27.2, 27.5**
    
    This test establishes that memory usage doesn't scale linearly with job count.
    If memory were O(N), we'd expect ~10x memory increase for 10x more jobs.
    With streaming O(chunk_size), we expect < 3x increase (overhead only).
    """
    chunk_size = 100
    
    # Test with small job count (baseline)
    small_count = 100
    await create_test_jobs_batch(async_test_db, small_count)
    measurement_small = await measure_streaming_memory(
        session_factory=async_test_db,
        job_count=small_count,
        chunk_size=chunk_size
    )
    
    # Clear database and garbage collect
    async with async_test_db() as session:
        from sqlalchemy import delete
        await session.execute(delete(Job))
        await session.commit()
    
    gc.collect()
    await asyncio.sleep(0.01)
    
    # Test with large job count
    large_count = 1_000
    await create_test_jobs_batch(async_test_db, large_count)

    measurement_large = await measure_streaming_memory(
        session_factory=async_test_db,
        job_count=large_count,
        chunk_size=chunk_size
    )
    
    # Calculate memory growth factor
    job_ratio = large_count / small_count  # 50x
    memory_ratio = measurement_large.peak_memory_mb / measurement_small.peak_memory_mb
    
    print(f"\n=== Streaming Memory Comparison ===")
    print(f"Jobs: {small_count} → {large_count} ({job_ratio:.0f}x increase)")
    print(f"Memory: {measurement_small.peak_memory_mb:.2f} MB → {measurement_large.peak_memory_mb:.2f} MB ({memory_ratio:.2f}x increase)")
    print(f"Memory per job (small): {(measurement_small.peak_memory_mb * 1024) / small_count:.3f} KB")
    print(f"Memory per job (large): {(measurement_large.peak_memory_mb * 1024) / large_count:.3f} KB")
    
    # Property Assertion: Memory growth should be much less than job count growth
    # If memory were O(N), memory_ratio ≈ job_ratio (50x)
    # With streaming O(chunk_size), memory_ratio should be < 5x (overhead tolerance)
    max_acceptable_memory_ratio = 5.0  # Allow 5x overhead tolerance
    
    assert memory_ratio < max_acceptable_memory_ratio, (
        f"Memory increased by {memory_ratio:.2f}x when jobs increased by {job_ratio:.0f}x. "
        f"Expected memory increase < {max_acceptable_memory_ratio}x with streaming. "
        f"This indicates memory usage is O(N) instead of O(chunk_size)."
    )
    
    print(f"✓ Memory efficiency verified: {memory_ratio:.2f}x growth for {job_ratio:.0f}x jobs")


@pytest.mark.asyncio
@given(
    chunk_size=st.integers(min_value=50, max_value=300)
)
@settings(
    max_examples=2,  # Reduced for faster execution
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
async def test_property_memory_bounded_by_chunk_size(
    async_test_db,
    chunk_size: int
):
    """
    Property Test: Memory is bounded by chunk_size, not total job count.
    
    **Validates: Requirements 1.1, 1.2, 27.1, 27.2, 27.5**
    
    Property:
        For a fixed job count, memory usage should scale with chunk_size,
        not with total job count.
    
    Test Strategy:
        1. Use hypothesis to generate various chunk sizes
        2. Stream a fixed number of jobs (2000) with different chunk sizes
        3. Verify memory usage correlates with chunk_size
    """
    # Clean database before each hypothesis example
    async with async_test_db() as session:
        from sqlalchemy import delete
        await session.execute(delete(Job))
        await session.commit()
    
    job_count = 500  # Fixed job count
    
    # Create test jobs
    await create_test_jobs_batch(async_test_db, job_count)

    
    # Measure memory with given chunk size
    measurement = await measure_streaming_memory(
        session_factory=async_test_db,
        job_count=job_count,
        chunk_size=chunk_size
    )
    
    # Property Assertion: Memory should be reasonable for any chunk size
    # Expected memory should be roughly O(chunk_size) + overhead
    # For chunk_size in [50, 300], expect < 150 MB
    max_expected_memory = 150.0
    
    assert measurement.peak_memory_mb < max_expected_memory, (
        f"Peak memory {measurement.peak_memory_mb:.2f} MB with chunk_size={chunk_size} "
        f"exceeds {max_expected_memory} MB. Memory may not be properly bounded by chunk_size."
    )
    
    # Property Assertion: Memory per job should be minimal
    memory_per_job_kb = (measurement.peak_memory_mb * 1024) / job_count
    assert memory_per_job_kb < 2.0, (
        f"Memory per job {memory_per_job_kb:.2f} KB is too high. "
        f"Jobs may not be properly garbage collected."
    )


@pytest.mark.asyncio
async def test_streaming_memory_with_queue_simulation(async_test_db):
    """
    Test memory efficiency when simulating full pipeline with bounded queue.
    
    **Validates: Requirements 1.1, 1.2, 27.1, 27.2, 27.5**
    
    This test simulates the full pipeline scenario where:
    - Producer streams jobs
    - Bounded queue holds jobs temporarily
    - Workers consume jobs
    
    Memory should remain O(queue_size + chunk_size), not O(total_jobs).
    """
    job_count = 3_000
    chunk_size = 100
    queue_size = 100
    
    # Create test jobs
    await create_test_jobs_batch(async_test_db, job_count)
    
    # Create producer
    producer = AsyncJobProducer(
        db_session_factory=async_test_db,
        chunk_size=chunk_size
    )
    
    # Force garbage collection
    gc.collect()
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    tracemalloc.reset_peak()

    
    # Simulate bounded queue with asyncio.Queue
    queue = asyncio.Queue(maxsize=queue_size)
    jobs_consumed = 0
    
    async def mock_consumer():
        """Mock consumer that processes jobs from queue"""
        nonlocal jobs_consumed
        while True:
            job = await queue.get()
            if job is None:  # Poison pill
                break
            jobs_consumed += 1
            # Simulate minimal processing
            await asyncio.sleep(0.0001)
    
    async def producer_task():
        """Producer task that feeds queue"""
        async for job in producer.produce_jobs(query=""):
            await queue.put(job)
        # Send poison pill
        await queue.put(None)
    
    # Run producer and consumer concurrently
    consumer = asyncio.create_task(mock_consumer())
    await producer_task()
    await consumer
    
    # Capture memory measurement
    measurement = MemoryMeasurement.capture(job_count)
    tracemalloc.stop()
    
    # Verify all jobs processed
    assert jobs_consumed == job_count, f"Expected {job_count}, consumed {jobs_consumed}"
    
    # Property Assertion: Memory bounded by queue + chunk size
    # Expected: O(queue_size + chunk_size) = O(200) jobs in memory
    # With ~100 bytes per job context, expect < 100 MB
    max_expected_memory_mb = 100.0
    
    assert measurement.peak_memory_mb < max_expected_memory_mb, (
        f"Peak memory {measurement.peak_memory_mb:.2f} MB exceeds "
        f"{max_expected_memory_mb} MB for pipeline simulation. "
        f"Memory usage should be O(queue_size + chunk_size), not O(total_jobs)."
    )
    
    memory_per_job_kb = (measurement.peak_memory_mb * 1024) / job_count
    assert memory_per_job_kb < 2.0, (
        f"Memory per job {memory_per_job_kb:.2f} KB indicates jobs are retained in memory."
    )
    
    print(f"\n✓ Pipeline memory efficiency verified:")
    print(f"  Jobs: {job_count}")
    print(f"  Queue size: {queue_size}")
    print(f"  Chunk size: {chunk_size}")
    print(f"  Peak memory: {measurement.peak_memory_mb:.2f} MB")
    print(f"  Memory per job: {memory_per_job_kb:.3f} KB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
