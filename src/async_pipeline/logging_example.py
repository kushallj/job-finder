"""
Example demonstrating structured logging with correlation IDs.

This script shows how to use the structured logging system in the async pipeline.
Run this to see how logs are formatted in development vs production mode.
"""

import asyncio
import time
from src.async_pipeline import (
    configure_structured_logging,
    get_logger,
    set_correlation_id,
    get_correlation_id,
    generate_correlation_id,
    clear_correlation_id,
    JobContext,
    JobStatus,
)


async def simulate_job_processing(job: JobContext) -> None:
    """
    Simulate processing a job with structured logging.
    
    This function demonstrates all the key logging points in the pipeline:
    - Job started (INFO)
    - Skills extracted (DEBUG)
    - Resume matched (DEBUG)
    - Result stored (INFO)
    - Job completed (INFO)
    - Retry (WARNING) if needed
    - Job failed (ERROR) with traceback
    """
    logger = get_logger(__name__)
    
    # Generate and set correlation ID for this job
    correlation_id = f"job-{job.job_id}-{generate_correlation_id()[:8]}"
    set_correlation_id(correlation_id)
    
    start_time = time.time()
    attempt = 1
    
    # Log job started
    logger.info(
        "job_processing_started",
        job_id=job.job_id,
        company=job.company,
        title=job.title,
        status=JobStatus.PROCESSING.value,
        attempt_count=attempt,
        correlation_id=correlation_id,
    )
    
    try:
        # Simulate skill extraction
        await asyncio.sleep(0.1)
        skills = ["Python", "Docker", "Kubernetes"]
        
        logger.debug(
            "skills_extracted",
            job_id=job.job_id,
            skills_count=len(skills),
            correlation_id=correlation_id,
        )
        
        # Simulate resume matching
        await asyncio.sleep(0.1)
        match_score = 85
        
        logger.debug(
            "resume_matched",
            job_id=job.job_id,
            match_score=match_score,
            correlation_id=correlation_id,
        )
        
        # Simulate storing result
        await asyncio.sleep(0.05)
        
        logger.debug(
            "db_store_result_complete",
            job_id=job.job_id,
            match_score=match_score,
            correlation_id=correlation_id,
        )
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Log job completed
        logger.info(
            "job_completed",
            job_id=job.job_id,
            status=JobStatus.COMPLETED.value,
            processing_time_ms=round(processing_time_ms, 2),
            attempt_count=attempt,
            correlation_id=correlation_id,
        )
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.error(
            "job_failed",
            job_id=job.job_id,
            status=JobStatus.FAILED.value,
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=error_traceback,
            processing_time_ms=round(processing_time_ms, 2),
            attempt_count=attempt,
            correlation_id=correlation_id,
        )
    
    finally:
        # Clear correlation ID
        clear_correlation_id()


async def simulate_retry_scenario(job: JobContext) -> None:
    """
    Simulate a job that requires retries.
    
    Demonstrates WARNING level logging for retry attempts.
    """
    logger = get_logger(__name__)
    
    correlation_id = f"job-{job.job_id}-{generate_correlation_id()[:8]}"
    set_correlation_id(correlation_id)
    
    max_retries = 3
    
    for attempt in range(1, max_retries + 1):
        logger.info(
            "job_processing_started",
            job_id=job.job_id,
            company=job.company,
            title=job.title,
            status=JobStatus.PROCESSING.value,
            attempt_count=attempt,
            correlation_id=correlation_id,
        )
        
        try:
            # Simulate a transient error on first two attempts
            if attempt < 3:
                await asyncio.sleep(0.05)
                raise TimeoutError(f"LLM API timeout on attempt {attempt}")
            
            # Success on third attempt
            await asyncio.sleep(0.1)
            
            logger.info(
                "job_completed",
                job_id=job.job_id,
                status=JobStatus.COMPLETED.value,
                processing_time_ms=100.0,
                attempt_count=attempt,
                correlation_id=correlation_id,
            )
            break
            
        except Exception as e:
            if attempt < max_retries:
                # Calculate backoff delay
                delay = 1.0 * (2 ** (attempt - 1))
                
                logger.warning(
                    "job_retry",
                    job_id=job.job_id,
                    status=JobStatus.RETRYING.value,
                    attempt_count=attempt,
                    max_retries=max_retries,
                    delay_seconds=delay,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    correlation_id=correlation_id,
                )
                
                await asyncio.sleep(delay)
            else:
                # All retries exhausted
                import traceback
                error_traceback = traceback.format_exc()
                
                logger.error(
                    "job_failed_after_retries",
                    job_id=job.job_id,
                    status=JobStatus.FAILED.value,
                    attempt_count=attempt,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    traceback=error_traceback,
                    correlation_id=correlation_id,
                )
    
    clear_correlation_id()


async def main():
    """Main function to run examples."""
    print("=" * 80)
    print("STRUCTURED LOGGING EXAMPLE - DEVELOPMENT MODE")
    print("=" * 80)
    print()
    
    # Configure for development (colored console output)
    configure_structured_logging(
        log_level="DEBUG",
        json_format=False,
        include_timestamp=True,
    )
    
    # Create sample jobs
    job1 = JobContext(
        job_id="job-001",
        title="Senior Backend Engineer",
        company="Tech Startup Inc",
        description="We're looking for a senior backend engineer with Python experience." * 10,
        url="https://example.com/job/001",
        source="example",
    )
    
    job2 = JobContext(
        job_id="job-002",
        title="DevOps Engineer",
        company="Cloud Solutions Ltd",
        description="Join our DevOps team to build scalable infrastructure." * 10,
        url="https://example.com/job/002",
        source="example",
    )
    
    print("Processing Job 1 (successful):")
    print("-" * 80)
    await simulate_job_processing(job1)
    
    print()
    print("Processing Job 2 (with retries):")
    print("-" * 80)
    await simulate_retry_scenario(job2)
    
    print()
    print("=" * 80)
    print("STRUCTURED LOGGING EXAMPLE - PRODUCTION MODE")
    print("=" * 80)
    print()
    
    # Reconfigure for production (JSON output)
    configure_structured_logging(
        log_level="INFO",
        json_format=True,
        include_timestamp=True,
    )
    
    job3 = JobContext(
        job_id="job-003",
        title="Full Stack Developer",
        company="Digital Agency",
        description="We need a full stack developer proficient in React and Node.js." * 10,
        url="https://example.com/job/003",
        source="example",
    )
    
    print("Processing Job 3 (JSON format):")
    print("-" * 80)
    await simulate_job_processing(job3)
    
    print()
    print("=" * 80)
    print("EXAMPLE COMPLETE")
    print("=" * 80)
    print()
    print("Key features demonstrated:")
    print("✓ Correlation IDs for job tracing")
    print("✓ Structured fields (job_id, status, processing_time_ms, attempt_count)")
    print("✓ Log levels: INFO (lifecycle), WARNING (retries), ERROR (failures)")
    print("✓ Error details: error_type, error_message, traceback")
    print("✓ Development mode: Colored console output")
    print("✓ Production mode: JSON formatted logs")


if __name__ == "__main__":
    asyncio.run(main())
