#!/usr/bin/env python3
"""
Test script to verify the async pipeline event loop fix.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.async_pipeline.bounded_queue import BoundedQueue
from src.async_pipeline.worker_pool import AsyncWorkerPool
from src.async_pipeline.types import JobContext, ProcessingResult


async def simple_processor(job: JobContext) -> ProcessingResult:
    """Simple test processor."""
    await asyncio.sleep(0.1)  # Simulate work
    return ProcessingResult.success(
        job_id=job.job_id,
        data={"processed": True},
    )


async def test_event_loop_fix():
    """Test that the queue works properly across event loops."""
    print("🧪 Testing async pipeline event loop fix...")
    
    # Create queue and worker pool
    queue = BoundedQueue(maxsize=10)
    semaphore = asyncio.Semaphore(5)
    
    pool = AsyncWorkerPool(
        worker_count=3,
        processor=simple_processor,
        semaphore=semaphore,
        queue=queue,
    )
    
    # Start workers
    print("✓ Starting workers...")
    await pool.start()
    
    # Add jobs to queue
    print("✓ Adding test jobs...")
    for i in range(5):
        job = JobContext(
            job_id=f"test-job-{i}",
            title=f"Test Job {i}",
            company=f"Test Company {i}",
            location="Remote",
            description=f"Test description {i}",
            url=f"https://example.com/job/{i}",
            source="test",
        )
        await queue.put(job)
    
    # Wait for completion
    print("✓ Processing jobs...")
    results = await pool.wait_completion()
    
    # Stop workers
    print("✓ Stopping workers...")
    await pool.stop()
    
    # Check results
    print(f"\n📊 Results:")
    print(f"  - Jobs processed: {len(results)}")
    print(f"  - Success count: {sum(1 for r in results if r.is_success())}")
    print(f"  - Failure count: {sum(1 for r in results if not r.is_success())}")
    
    if len(results) == 5 and all(r.is_success() for r in results):
        print("\n✅ Event loop fix successful! Pipeline working correctly.")
        return True
    else:
        print("\n❌ Pipeline still has issues.")
        return False


async def main():
    """Run the test."""
    try:
        success = await test_event_loop_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
