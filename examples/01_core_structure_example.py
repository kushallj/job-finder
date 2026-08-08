"""
Example: Core Structure and Configuration

This example demonstrates the core data models and configuration
of the async job pipeline.
"""

import asyncio
from datetime import datetime

from src.async_pipeline import (
    JobContext,
    ProcessingResult,
    JobStatus,
    ProcessorConfig,
    RetryConfig,
    RateLimitConfig,
    configure_structured_logging,
    get_logger,
    create_async_db_engine,
    create_async_session_factory,
)


def example_job_context():
    """Example: Creating and using JobContext."""
    print("\n=== JobContext Example ===")
    
    # Create an immutable job context
    job = JobContext(
        job_id="job-12345",
        title="Senior Software Engineer",
        company="Tech Corp",
        description="We are looking for an experienced software engineer to join our team. " * 5,
        url="https://example.com/jobs/12345",
        source="linkedin",
        location="San Francisco, CA",
        salary="$150k - $200k",
        metadata={
            "remote": True,
            "experience_years": 5,
            "tags": ["python", "async", "distributed-systems"]
        }
    )
    
    print(f"Job ID: {job.job_id}")
    print(f"Title: {job.title}")
    print(f"Company: {job.company}")
    print(f"Location: {job.location}")
    print(f"Remote: {job.metadata.get('remote')}")
    
    # Convert to dictionary
    job_dict = job.to_dict()
    print(f"\nJob as dict keys: {list(job_dict.keys())}")
    
    # Try to modify (will raise FrozenInstanceError)
    try:
        job.title = "Modified Title"
    except Exception as e:
        print(f"\n✓ Immutability enforced: {type(e).__name__}")
    
    return job


def example_processing_result():
    """Example: Creating processing results."""
    print("\n\n=== ProcessingResult Example ===")
    
    # Create a successful result
    success_result = ProcessingResult.success(
        job_id="job-12345",
        data={
            "match_score": 85,
            "skills_matched": ["Python", "Async", "Distributed Systems"],
            "email_sent": True,
            "contacts_found": 2,
        },
        attempt_count=1,
        processing_time_ms=1500.0,
        worker_id="worker-1",
    )
    
    print(f"Success result:")
    print(f"  Status: {success_result.status.value}")
    print(f"  Match Score: {success_result.data['match_score']}")
    print(f"  Processing Time: {success_result.processing_time_ms}ms")
    print(f"  Is Success: {success_result.is_success()}")
    
    # Create a failed result
    failure_result = ProcessingResult.failure(
        job_id="job-67890",
        error="LLM API timeout after 30 seconds",
        error_type="TimeoutError",
        attempt_count=3,
        worker_id="worker-2",
    )
    
    print(f"\nFailure result:")
    print(f"  Status: {failure_result.status.value}")
    print(f"  Error: {failure_result.error}")
    print(f"  Error Type: {failure_result.error_type}")
    print(f"  Attempts: {failure_result.attempt_count}")
    print(f"  Is Success: {failure_result.is_success()}")


def example_processor_config():
    """Example: Creating and validating configuration."""
    print("\n\n=== ProcessorConfig Example ===")
    
    # Create config with defaults
    config_default = ProcessorConfig()
    print("Default configuration:")
    print(f"  Worker Count: {config_default.worker_count}")
    print(f"  Queue Size: {config_default.queue_size}")
    print(f"  Max Retries: {config_default.max_retries}")
    print(f"  LLM Rate Limit: {config_default.llm_rate_limit} req/s")
    
    # Create config with custom values
    config_custom = ProcessorConfig(
        worker_count=10,
        queue_size=200,
        max_retries=5,
        llm_rate_limit=20.0,
        retry_base_delay=2.0,
        retry_max_delay=120.0,
    )
    
    print("\nCustom configuration:")
    print(f"  Worker Count: {config_custom.worker_count}")
    print(f"  Queue Size: {config_custom.queue_size}")
    print(f"  Max Retries: {config_custom.max_retries}")
    print(f"  LLM Rate Limit: {config_custom.llm_rate_limit} req/s")
    print(f"  Retry Base Delay: {config_custom.retry_base_delay}s")
    
    # Validate configuration
    try:
        config_custom.validate()
        print("\n✓ Configuration is valid")
    except AssertionError as e:
        print(f"\n✗ Configuration invalid: {e}")
    
    # Try invalid configuration
    config_invalid = ProcessorConfig(
        worker_count=0,  # Invalid!
    )
    
    try:
        config_invalid.validate()
    except AssertionError as e:
        print(f"\n✓ Invalid config detected: {e}")


def example_retry_config():
    """Example: Retry configuration."""
    print("\n\n=== RetryConfig Example ===")
    
    retry_config = RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
    )
    
    print(f"Retry configuration:")
    print(f"  Max Attempts: {retry_config.max_attempts}")
    print(f"  Base Delay: {retry_config.base_delay}s")
    print(f"  Max Delay: {retry_config.max_delay}s")
    print(f"  Exponential Base: {retry_config.exponential_base}")
    print(f"  Jitter Enabled: {retry_config.jitter}")
    
    # Calculate expected delays
    print(f"\nExpected delays (without jitter):")
    for attempt in range(1, retry_config.max_attempts + 1):
        delay = min(
            retry_config.base_delay * (retry_config.exponential_base ** attempt),
            retry_config.max_delay
        )
        print(f"  Attempt {attempt}: {delay:.2f}s")


def example_rate_limit_config():
    """Example: Rate limit configuration."""
    print("\n\n=== RateLimitConfig Example ===")
    
    # LLM rate limit: 10 requests per second
    llm_rate_config = RateLimitConfig(
        rate=10.0,
        capacity=10,
        time_period=1.0,
    )
    
    print("LLM Rate Limit:")
    print(f"  Rate: {llm_rate_config.rate} requests/{llm_rate_config.time_period}s")
    print(f"  Capacity: {llm_rate_config.capacity} tokens")
    
    # Email rate limit: 1 request per second
    email_rate_config = RateLimitConfig(
        rate=1.0,
        capacity=1,
        time_period=1.0,
    )
    
    print("\nEmail Rate Limit:")
    print(f"  Rate: {email_rate_config.rate} requests/{email_rate_config.time_period}s")
    print(f"  Capacity: {email_rate_config.capacity} tokens")


def example_structured_logging():
    """Example: Structured logging setup."""
    print("\n\n=== Structured Logging Example ===")
    
    # Configure structured logging
    configure_structured_logging(
        log_level="INFO",
        json_format=False,  # Use colored console for this example
        include_timestamp=True,
    )
    
    # Get logger instance
    logger = get_logger(__name__)
    
    print("Logging examples:")
    
    # Log with context
    logger.info(
        "job_processing_started",
        job_id="job-12345",
        worker_id="worker-1",
        attempt=1,
    )
    
    logger.info(
        "llm_api_call",
        job_id="job-12345",
        operation="extract_skills",
        processing_time_ms=1500.0,
    )
    
    logger.warning(
        "retry_attempt",
        job_id="job-12345",
        error_type="TimeoutError",
        attempt=2,
        delay_seconds=2.0,
    )
    
    logger.info(
        "job_completed",
        job_id="job-12345",
        status="completed",
        match_score=85,
        total_time_ms=3500.0,
    )


async def example_async_database():
    """Example: Async database setup."""
    print("\n\n=== Async Database Example ===")
    
    # Create async engine for SQLite
    engine = create_async_db_engine(
        database_url="sqlite:///example_jobs.db",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    
    print(f"Created async engine:")
    print(f"  URL: {engine.url}")
    print(f"  Pool Size: 5")
    print(f"  Max Overflow: 10")
    
    # Create session factory
    async_session = create_async_session_factory(engine)
    
    print(f"\n✓ Session factory created")
    print(f"  Factory callable: {callable(async_session)}")
    
    # Example usage (would need actual tables)
    print("\nExample usage:")
    print("  async with async_session() as session:")
    print("      result = await session.execute(select(Job))")
    print("      jobs = result.scalars().all()")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Async Job Pipeline - Core Structure Examples")
    print("=" * 60)
    
    # Run synchronous examples
    example_job_context()
    example_processing_result()
    example_processor_config()
    example_retry_config()
    example_rate_limit_config()
    example_structured_logging()
    
    # Run async examples
    asyncio.run(example_async_database())
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
