"""
Example: Using the async job pipeline.

This file demonstrates how to use the new AsyncJobPipeline with
the existing job processing system.
"""

import asyncio
import logging
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


async def example_basic_usage():
    """
    Basic usage example - process jobs with default settings.
    """
    from src.async_pipeline import (
        AsyncJobPipeline,
        ProcessorConfig,
        JobContext,
        ProcessingResult,
    )
    
    # Configure pipeline
    config = ProcessorConfig(
        worker_count=5,
        max_concurrent_api_calls=10,
        queue_size=100,
        max_retries=3,
    )
    
    # Simple processor function
    async def process_job(job: JobContext) -> ProcessingResult:
        """Process a single job."""
        logger.info(f"Processing job: {job.title} at {job.company}")
        
        # Simulate processing work
        await asyncio.sleep(0.1)
        
        return ProcessingResult.success(
            job_id=job.job_id,
            data={"title": job.title, "company": job.company},
            processing_time_ms=100.0,
        )
    
    # Create and run pipeline
    pipeline = AsyncJobPipeline(config)
    pipeline.set_processor(process_job)
    
    try:
        results = await pipeline.run(query="software engineer")
        
        # Print results
        success = sum(1 for r in results if r.is_success())
        failed = sum(1 for r in results if not r.is_success())
        
        print(f"\n{'='*50}")
        print(f"Pipeline completed!")
        print(f"Total jobs: {len(results)}")
        print(f"Successful: {success}")
        print(f"Failed: {failed}")
        print(f"{'='*50}\n")
        
    finally:
        await pipeline.close()


async def example_with_ai_services():
    """
    Example with AI services integration.
    """
    from src.async_pipeline import (
        AsyncJobPipelineBuilder,
        ProcessorConfig,
        JobContext,
        ProcessingResult,
    )
    from src.ai.unified_ai_service import UnifiedAIService
    from src.email_discovery import EmailDiscoveryService
    from src.email_outreach import EmailOutreach
    
    # Create AI service
    ai_service = UnifiedAIService()
    
    # Create processor function with AI
    async def process_job_with_ai(job: JobContext, resume_text: str) -> ProcessingResult:
        """Process job with AI analysis."""
        import time
        start_time = time.time()
        
        try:
            # Extract skills from job description
            skills = await ai_service.extract_skills(job.description)
            
            # Match resume to job
            match_result = await ai_service.match_resume_to_job(
                resume_text, skills
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            return ProcessingResult.success(
                job_id=job.job_id,
                data={
                    "skills": skills,
                    "match_result": match_result,
                },
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            return ProcessingResult.failure(
                job_id=job.job_id,
                error=str(e),
            )
    
    # Resume text
    resume_text = open("data/resume.txt").read() if __name__ == "__main__" else ""
    
    # Build pipeline with builder
    config = ProcessorConfig(
        worker_count=5,
        max_concurrent_api_calls=10,
        max_retries=3,
    )
    
    pipeline = (
        AsyncJobPipelineBuilder()
        .config(config)
        .processor(lambda job: process_job_with_ai(job, resume_text))
        .on_progress(lambda p: logger.info(f"Progress: {p}"))
        .build()
    )
    
    try:
        results = await pipeline.run(query="software engineer")
        
        print(f"\nProcessed {len(results)} jobs")
        
    finally:
        await pipeline.close()
        await ai_service.close()


async def example_with_rate_limiting():
    """
    Example demonstrating rate limiting.
    """
    from src.async_pipeline import (
        AsyncJobPipelineBuilder,
        ProcessorConfig,
        JobContext,
        ProcessingResult,
        MultiRateLimiter,
    )
    import aiohttp
    
    # Setup rate limiter
    rate_limiter = MultiRateLimiter(
        llm_rate=10.0,  # 10 requests per second
        email_rate=1.0,  # 1 request per second
        scraper_rate=5.0,  # 5 requests per second
    )
    
    # Processor with rate limiting
    async def process_with_rate_limit(job: JobContext) -> ProcessingResult:
        """Process job with API rate limiting."""
        # Acquire rate limit token before API call
        await rate_limiter.acquire_llm()
        
        try:
            # Make API call (would be actual LLM API call)
            # async with aiohttp.ClientSession() as session:
            #     async with session.post(LLM_URL, json={"text": job.description}) as resp:
            #         data = await resp.json()
            
            await asyncio.sleep(0.05)  # Simulate API call
            
            return ProcessingResult.success(
                job_id=job.job_id,
                data={"processed": True},
            )
        except Exception as e:
            return ProcessingResult.failure(
                job_id=job.job_id,
                error=str(e),
            )
    
    # Build pipeline
    config = ProcessorConfig(
        worker_count=3,
        max_concurrent_api_calls=5,
        llm_rate_limit=10.0,
    )
    
    pipeline = (
        AsyncJobPipelineBuilder()
        .config(config)
        .processor(process_with_rate_limit)
        .build()
    )
    
    try:
        results = await pipeline.run(query="engineer")
        
        # Print rate limiter stats
        stats = rate_limiter.get_stats()
        print(f"Rate limiter stats: {stats}")
        
    finally:
        await pipeline.close()


async def example_streaming_producer():
    """
    Example demonstrating the streaming producer directly.
    """
    from src.async_pipeline import AsyncJobProducer
    from src.database import engine, async_session_maker
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    
    # Note: This requires async database setup
    # For demo, we'll just show the concept
    
    # Create producer (would need actual async session maker)
    # producer = AsyncJobProducer(
    #     db_session_factory=async_session_maker,
    #     chunk_size=100
    # )
    
    # Count jobs
    # count = await producer.get_job_count("software engineer")
    # print(f"Total matching jobs: {count}")
    
    # Stream jobs
    # async for job in producer.produce_jobs("software engineer"):
    #     print(f"Got job: {job.title}")
    #     # Process job...
    
    print("Streaming producer example (see code for usage)")


async def example_worker_pool():
    """
    Example demonstrating direct worker pool usage.
    """
    from src.async_pipeline import (
        AsyncWorkerPool,
        BoundedQueue,
        ProcessorConfig,
        JobContext,
        ProcessingResult,
    )
    import asyncio
    
    # Create components
    queue = BoundedQueue(maxsize=50)
    semaphore = asyncio.Semaphore(5)
    config = ProcessorConfig(max_retries=3)
    
    # Simple processor
    async def processor(job: JobContext) -> ProcessingResult:
        await asyncio.sleep(0.1)  # Simulate work
        return ProcessingResult.success(
            job_id=job.job_id,
            data={"processed": True},
        )
    
    # Create worker pool
    pool = AsyncWorkerPool(
        worker_count=5,
        processor=processor,
        semaphore=semaphore,
        queue=queue,
        config=config,
    )
    
    # Add some jobs
    for i in range(10):
        job = JobContext(
            job_id=f"job-{i}",
            title=f"Software Engineer {i}",
            company=f"Company {i}",
            description="Job description here",
            url="https://example.com",
            source="api",
        )
        await queue.put(job)
    
    # Add poison pills
    await queue.put_poison_pills(5)
    
    # Start workers
    await pool.start()
    
    # Wait for completion
    results = await pool.wait_completion()
    
    print(f"Worker pool processed {len(results)} jobs")
    
    await pool.stop()


async def example_backpressure():
    """
    Example demonstrating backpressure mechanism.
    """
    from src.async_pipeline import BoundedQueue
    import asyncio
    
    # Create bounded queue with small size
    queue = BoundedQueue(maxsize=5)
    
    async def producer():
        """Producer that tries to push faster than consumer."""
        for i in range(20):
            # This will block when queue is full
            await queue.put(f"job-{i}")
            print(f"Produced job-{i}, queue size: {queue.qsize()}")
    
    async def consumer(slow: bool = False):
        """Consumer that processes slowly."""
        while True:
            job = await queue.get()
            if job is None:
                break
            
            if slow:
                await asyncio.sleep(0.2)  # Slow processing
            else:
                await asyncio.sleep(0.05)
            
            print(f"Consumed {job}")
    
    # Run with slow consumer to demonstrate backpressure
    print("\n=== Backpressure Demo (slow consumer) ===")
    
    # Start producer and consumer
    await asyncio.gather(
        producer(),
        consumer(slow=True),
    )
    
    print(f"Final queue size: {queue.qsize()}")


async def example_retry_logic():
    """
    Example demonstrating retry logic.
    """
    from src.async_pipeline import (
        retry_with_backoff,
        retry_on_api_error,
        RetryManager,
    )
    import asyncio
    
    # Using decorator
    attempt_count = 0
    
    @retry_with_backoff(max_attempts=3, base_delay=0.5)
    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count < 3:
            raise ValueError("Temporary failure")
        
        return "Success!"
    
    result = await flaky_operation()
    print(f"Result: {result}, attempts: {attempt_count}")
    
    # Using RetryManager
    manager = RetryManager()
    
    call_count = 0
    
    async def operation():
        nonlocal call_count
        call_count += 1
        
        if call_count < 2:
            raise ValueError("Failed")
        
        return "Done"
    
    result = await manager.execute_with_retry(operation)
    print(f"Manager result: {result}")


async def example_rate_limiter():
    """
    Example demonstrating token bucket rate limiter.
    """
    from src.async_pipeline import TokenBucket
    import asyncio
    import time
    
    # Create rate limiter: 5 requests per second
    bucket = TokenBucket(rate=5.0)
    
    async def make_request(i: int):
        """Make a rate-limited request."""
        await bucket.acquire()
        print(f"Request {i} at {time.time():.3f}")
    
    # Make 10 requests
    print("\n=== Rate Limiter Demo ===")
    start = time.time()
    
    tasks = [make_request(i) for i in range(10)]
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f"Completed 10 requests in {elapsed:.2f}s")
    print(f"Expected: ~2.0s (10 requests / 5 req/s)")


async def main():
    """Run all examples."""
    print("="*60)
    print("Async Job Pipeline Examples")
    print("="*60)
    
    # Run examples
    # await example_basic_usage()
    # await example_with_ai_services()
    # await example_with_rate_limiting()
    # await example_streaming_producer()
    # await example_worker_pool()
    # await example_backpressure()
    # await example_retry_logic()
    await example_rate_limiter()
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

