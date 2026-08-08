#!/usr/bin/env python3
"""
Pipeline Performance Benchmarking Script

This script benchmarks the async job pipeline with different configurations
to help identify optimal settings for your environment.

Usage:
    python scripts/benchmark_pipeline.py --jobs 1000 --workers 5
    python scripts/benchmark_pipeline.py --profile
    python scripts/benchmark_pipeline.py --compare-workers

Requirements Coverage: 16.1, 16.2, 16.3, 16.4, 16.5
"""
import argparse
import asyncio
import cProfile
import io
import os
import pstats
import sys
import time
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.pipeline import AsyncJobPipeline
from src.async_pipeline.types import JobContext, JobStatus, ProcessingResult
from src.models import Base, Job


async def create_test_database(num_jobs: int = 1000) -> str:
    """
    Create an in-memory test database with jobs.
    
    Args:
        num_jobs: Number of test jobs to create
        
    Returns:
        Database URL
    """
    print(f"Creating test database with {num_jobs} jobs...")
    
    db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(db_url, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Populate with test jobs
    async with async_session() as session:
        jobs = []
        for i in range(num_jobs):
            job = Job(
                job_id=f"bench_job_{i:05d}",
                title=f"Software Engineer {i}",
                company=f"Company {i % 100}",
                location="Remote",
                description=f"Job description for position {i}. Python, Django, FastAPI. 5+ years.",
                url=f"https://example.com/jobs/{i}",
                source="benchmark",
            )
            jobs.append(job)
        
        session.add_all(jobs)
        await session.commit()
    
    print(f"✓ Test database created with {num_jobs} jobs")
    return db_url, engine, async_session


async def mock_processor(job: JobContext) -> ProcessingResult:
    """
    Mock processor that simulates real work.
    
    Simulates 10ms of API call latency (typical for fast LLM APIs).
    """
    await asyncio.sleep(0.01)
    
    return ProcessingResult(
        job_id=job.job_id,
        status=JobStatus.COMPLETED,
        data={"processed": True},
        error=None,
        error_type=None,
        attempt_count=1,
        processing_time_ms=10.0,
        timestamp=time.time(),
        worker_id="benchmark",
    )


async def benchmark_configuration(
    config: ProcessorConfig,
    db_url: str,
    engine: Any,
    session_factory: Any,
    job_count: int,
) -> Dict[str, Any]:
    """
    Benchmark pipeline with given configuration.
    
    Args:
        config: Pipeline configuration
        db_url: Database URL
        engine: Database engine
        session_factory: Session factory
        job_count: Number of jobs to process
        
    Returns:
        Dictionary with benchmark results
    """
    pipeline = AsyncJobPipeline(config=config, db_url=db_url)
    
    # Inject test database
    pipeline._engine = engine
    pipeline._session_factory = session_factory
    
    pipeline.set_processor(mock_processor)
    
    start_time = time.time()
    
    try:
        results = await pipeline.run(query="", filters={})
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        successful = sum(1 for r in results if r.is_success())
        failed = len(results) - successful
        throughput = job_count / elapsed if elapsed > 0 else 0
        
        return {
            "config": {
                "worker_count": config.worker_count,
                "queue_size": config.queue_size,
                "max_concurrent_api_calls": config.max_concurrent_api_calls,
            },
            "results": {
                "total_jobs": job_count,
                "successful": successful,
                "failed": failed,
                "elapsed_seconds": round(elapsed, 2),
                "throughput_jobs_per_sec": round(throughput, 2),
                "avg_time_per_job_ms": round((elapsed * 1000) / job_count, 2) if job_count > 0 else 0,
            },
            "meets_requirements": {
                "under_300_seconds": elapsed < 300,
                "above_3_3_jobs_per_sec": throughput >= 3.3,
            }
        }
        
    finally:
        pipeline._engine = None
        await pipeline.close()


async def benchmark_worker_counts(
    worker_counts: List[int],
    job_count: int = 200,
) -> None:
    """
    Benchmark pipeline with different worker counts.
    
    Args:
        worker_counts: List of worker counts to test
        job_count: Number of jobs for each test
    """
    print(f"\n{'='*60}")
    print(f"Worker Count Comparison Benchmark")
    print(f"{'='*60}")
    print(f"Jobs per test: {job_count}")
    print(f"Worker counts: {worker_counts}")
    print()
    
    db_url, engine, session_factory = await create_test_database(job_count)
    
    results = []
    
    for worker_count in worker_counts:
        config = ProcessorConfig(
            worker_count=worker_count,
            queue_size=100,
            max_concurrent_api_calls=worker_count * 2,
            llm_rate_limit=1000.0,
            email_rate_limit=1000.0,
            scraper_rate_limit=1000.0,
            max_retries=0,
            enable_progress_bar=True,
        )
        
        print(f"Benchmarking with {worker_count} workers...")
        
        result = await benchmark_configuration(
            config, db_url, engine, session_factory, job_count
        )
        results.append(result)
        
        print(f"  Elapsed: {result['results']['elapsed_seconds']}s")
        print(f"  Throughput: {result['results']['throughput_jobs_per_sec']} jobs/s")
        print()
    
    # Print comparison table
    print(f"\n{'='*60}")
    print("Comparison Results")
    print(f"{'='*60}")
    print(f"{'Workers':<10} {'Elapsed (s)':<15} {'Throughput (jobs/s)':<20} {'Speedup':<10}")
    print(f"{'-'*60}")
    
    baseline_time = results[0]['results']['elapsed_seconds']
    
    for result in results:
        workers = result['config']['worker_count']
        elapsed = result['results']['elapsed_seconds']
        throughput = result['results']['throughput_jobs_per_sec']
        speedup = baseline_time / elapsed if elapsed > 0 else 0
        
        print(f"{workers:<10} {elapsed:<15.2f} {throughput:<20.2f} {speedup:<10.2f}x")
    
    # Find optimal worker count
    best_result = max(results, key=lambda r: r['results']['throughput_jobs_per_sec'])
    best_workers = best_result['config']['worker_count']
    best_throughput = best_result['results']['throughput_jobs_per_sec']
    
    print(f"\n✓ Optimal configuration: {best_workers} workers ({best_throughput} jobs/s)")
    
    await engine.dispose()


async def benchmark_with_profiling(job_count: int = 100) -> None:
    """
    Benchmark pipeline with cProfile to identify bottlenecks.
    
    Args:
        job_count: Number of jobs to process
    """
    print(f"\n{'='*60}")
    print(f"Profiling Benchmark")
    print(f"{'='*60}")
    print(f"Jobs: {job_count}")
    print()
    
    db_url, engine, session_factory = await create_test_database(job_count)
    
    config = ProcessorConfig(
        worker_count=5,
        queue_size=100,
        max_concurrent_api_calls=10,
        llm_rate_limit=1000.0,
        email_rate_limit=1000.0,
        scraper_rate_limit=1000.0,
        max_retries=0,
        enable_progress_bar=True,
    )
    
    # Profile the execution
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = await benchmark_configuration(
        config, db_url, engine, session_factory, job_count
    )
    
    profiler.disable()
    
    # Print results
    print(f"\n{'='*60}")
    print("Performance Results")
    print(f"{'='*60}")
    print(f"Total jobs: {result['results']['total_jobs']}")
    print(f"Elapsed time: {result['results']['elapsed_seconds']}s")
    print(f"Throughput: {result['results']['throughput_jobs_per_sec']} jobs/s")
    print(f"Avg time per job: {result['results']['avg_time_per_job_ms']}ms")
    
    # Print profiling report
    print(f"\n{'='*60}")
    print("Top 20 Functions by Cumulative Time")
    print(f"{'='*60}")
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())
    
    await engine.dispose()


async def benchmark_standard(
    job_count: int = 1000,
    worker_count: int = 5,
) -> None:
    """
    Standard benchmark with specified configuration.
    
    Args:
        job_count: Number of jobs to process
        worker_count: Number of concurrent workers
    """
    print(f"\n{'='*60}")
    print(f"Standard Benchmark")
    print(f"{'='*60}")
    print(f"Jobs: {job_count}")
    print(f"Workers: {worker_count}")
    print()
    
    db_url, engine, session_factory = await create_test_database(job_count)
    
    config = ProcessorConfig(
        worker_count=worker_count,
        queue_size=100,
        max_concurrent_api_calls=10,
        chunk_size=100,
        llm_rate_limit=1000.0,
        email_rate_limit=1000.0,
        scraper_rate_limit=1000.0,
        llm_timeout_seconds=5.0,
        email_timeout_seconds=5.0,
        scraper_timeout_seconds=5.0,
        db_timeout_seconds=5.0,
        max_retries=0,
        enable_progress_bar=True,
    )
    
    result = await benchmark_configuration(
        config, db_url, engine, session_factory, job_count
    )
    
    # Print results
    print(f"\n{'='*60}")
    print("Benchmark Results")
    print(f"{'='*60}")
    print(f"Total jobs: {result['results']['total_jobs']}")
    print(f"Successful: {result['results']['successful']}")
    print(f"Failed: {result['results']['failed']}")
    print(f"Elapsed time: {result['results']['elapsed_seconds']}s")
    print(f"Throughput: {result['results']['throughput_jobs_per_sec']} jobs/s")
    print(f"Avg time per job: {result['results']['avg_time_per_job_ms']}ms")
    print()
    print("Requirements Validation:")
    print(f"  ✓ Under 300 seconds: {result['meets_requirements']['under_300_seconds']}")
    print(f"  ✓ Above 3.3 jobs/s: {result['meets_requirements']['above_3_3_jobs_per_sec']}")
    
    if result['meets_requirements']['above_3_3_jobs_per_sec']:
        factor = result['results']['throughput_jobs_per_sec'] / 3.3
        print(f"\n✓ Throughput is {factor:.1f}x the minimum requirement!")
    
    await engine.dispose()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark async job pipeline performance"
    )
    
    parser.add_argument(
        "--jobs",
        type=int,
        default=1000,
        help="Number of jobs to process (default: 1000)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of workers (default: 5)"
    )
    
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run with profiling to identify bottlenecks"
    )
    
    parser.add_argument(
        "--compare-workers",
        action="store_true",
        help="Compare different worker counts"
    )
    
    args = parser.parse_args()
    
    if args.profile:
        asyncio.run(benchmark_with_profiling(args.jobs))
    elif args.compare_workers:
        asyncio.run(benchmark_worker_counts([1, 3, 5, 7, 10], args.jobs))
    else:
        asyncio.run(benchmark_standard(args.jobs, args.workers))


if __name__ == "__main__":
    main()
