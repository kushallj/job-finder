# Implementation Plan: Async Job Pipeline Refactor

## Overview

This implementation plan transforms the existing job automation pipeline into a high-performance, fully-async concurrent system using Python's asyncio. The refactor implements a producer-consumer pattern with bounded queues, async workers, semaphore-based concurrency control, and streaming generators for O(1) memory usage. The system will achieve 3.3+ jobs/second throughput while maintaining reliability through automatic retry logic, structured logging, and natural backpressure mechanisms.

## Tasks

- [x] 1. Set up core project structure and configuration
  - Review and enhance existing `src/async_pipeline/` structure
  - Define or update core data models in `src/async_pipeline/types.py`: JobContext (frozen dataclass), ProcessingResult, JobStatus enum
  - Define configuration dataclasses in `src/async_pipeline/config.py`: ProcessorConfig, RetryConfig, RateLimiterConfig
  - Set up structured logging with structlog in `src/async_pipeline/__init__.py`
  - Configure async SQLAlchemy engine with connection pooling in config module
  - _Requirements: 1.1, 1.2, 17.1, 17.2, 17.4, 12.1, 12.3, 12.5, 19.4_

- [x] 2. Implement and enhance streaming job producer
  - [x] 2.1 Create or update AsyncJobProducer in `src/async_pipeline/producer.py`
    - Implement `produce_jobs()` async generator that yields JobContext one at a time
    - Implement chunked database fetching with configurable chunk_size (default 100)
    - Implement proper database session lifecycle: open session per chunk, close after yielding
    - Convert ORM Job objects to immutable JobContext dataclasses using JobContext.from_orm()
    - Ensure memory usage is O(chunk_size) regardless of total job count
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 10.1, 10.2, 10.5_

  - [x] 2.2 Add job count method for progress tracking
    - Implement `get_job_count()` async method that returns total matching jobs
    - Use efficient COUNT(*) query without loading job data into memory
    - _Requirements: 1.5, 9.4_

- [x] 3. Implement bounded queue with backpressure
  - [x] 3.1 Create or update BoundedQueue in `src/async_pipeline/bounded_queue.py`
    - Initialize asyncio.Queue with configurable maxsize parameter
    - Implement async `put()` method that blocks when queue reaches capacity
    - Implement async `get()` method that blocks when queue is empty
    - Implement `put_poison_pills(count)` method for graceful shutdown signaling
    - Add queue statistics tracking: current size, total enqueued, total dequeued, wait times
    - Ensure queue size never exceeds maxsize
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 8.2_

- [x] 4. Implement retry manager with exponential backoff
  - [x] 4.1 Create or update RetryManager in `src/async_pipeline/retry.py`
    - Configure retry decorator using tenacity library with exponential backoff
    - Implement formula: delay = base_delay × (exponential_base ^ attempt)
    - Cap delay at max_delay when exponential calculation exceeds it
    - Configure retryable exception types: aiohttp.ClientError, asyncio.TimeoutError, httpx.RequestError
    - Add structured logging for retry attempts with error type, message, and attempt number
    - Implement jitter using tenacity's wait_random to prevent thundering herd
    - Create reusable `create_retry_decorator()` factory method
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 18.2, 18.4, 18.5_

- [x] 5. Implement rate limiter with token bucket algorithm
  - [x] 5.1 Create or update RateLimiter in `src/async_pipeline/rate_limiter.py`
    - Initialize with rate (tokens per second), capacity (max burst), and time_period parameters
    - Implement async `acquire(tokens=1)` method that blocks when insufficient tokens available
    - Implement token refill logic: refill at configured rate per second
    - Add `get_wait_time(tokens)` method for calculating when tokens will be available
    - Track rate limiter statistics: tokens consumed, requests blocked, average wait time
    - Ensure API call rate never exceeds configured limit in any sliding time window
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6. Implement async job processor with retry and rate limiting
  - [x] 6.1 Create AsyncJobProcessor in `src/async_pipeline/processor.py`
    - Initialize with LLM service, email service, scraper service, and database session factory
    - Implement async `process_job(job, semaphore)` method decorated with retry logic
    - Implement async `extract_skills(description)` method that calls LLM API with timeout
    - Implement async `match_resume(skills, job)` method with skill matching logic
    - Implement async `store_result(job, result)` using per-task database sessions with transactions
    - Acquire semaphore before each external API call (LLM, email, scraping)
    - Release semaphore in finally block to ensure cleanup even on exceptions
    - Add structured logging for each operation: job_id, operation type, status, duration_ms
    - Return ProcessingResult with status (COMPLETED/FAILED), data, error details, attempt count, processing time
    - Wrap all database operations in transactions with rollback on error
    - _Requirements: 4.4, 5.1, 7.1, 7.2, 7.3, 7.4, 7.5, 9.2, 11.1, 13.2, 13.4, 14.1, 14.2, 14.3, 14.4, 18.1, 18.2, 19.1, 19.2, 19.3_

- [ ] 7. Checkpoint - Verify core components
  - Run unit tests for producer, queue, retry manager, rate limiter, and processor
  - Verify each component works independently before integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement async worker pool
  - [x] 8.1 Create or update AsyncWorkerPool in `src/async_pipeline/worker_pool.py`
    - Initialize with worker_count, processor instance, semaphore, and bounded queue
    - Implement `start()` method that spawns exactly worker_count coroutines using asyncio.create_task()
    - Implement worker loop: continuously get job from queue, process with semaphore, handle poison pills (None)
    - When worker receives poison pill (None), complete current job and terminate gracefully
    - Implement error isolation: catch exceptions in worker, log error, continue processing next job
    - Implement `wait_completion()` method that awaits all worker tasks and collects ProcessingResults
    - Add `get_stats()` method returning active worker count, jobs processed, success/failure counts
    - Ensure failed worker doesn't terminate other workers
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 8.3, 13.1, 13.2, 13.3_

- [ ] 9. Configure HTTP session pooling and async I/O
  - [ ] 9.1 Update LLM service to use async HTTP client
    - Refactor `src/ai/gemini_service.py` or relevant LLM service to use aiohttp or httpx
    - Create shared ClientSession with connection pooling (max connections, timeouts)
    - Ensure all HTTP requests are async (no blocking calls)
    - Implement proper session cleanup on shutdown
    - _Requirements: 11.1, 11.2, 11.4, 12.2, 12.4_

  - [ ] 9.2 Update email service to use async HTTP client
    - Refactor `src/email_outreach.py` or email service to use async HTTP client
    - Replace synchronous requests with aiohttp/httpx async calls
    - Configure connection pooling and timeouts
    - _Requirements: 11.2, 11.4, 12.2, 12.4_

  - [x] 9.3 Update scraper service to use async HTTP client
    - Refactor scrapers in `src/scrapers/` to use async HTTP client (httpx or aiohttp)
    - Replace blocking I/O with async I/O operations
    - Configure connection pooling for efficient resource reuse
    - _Requirements: 11.2, 11.4, 12.2, 12.4_

- [ ] 10. Implement main pipeline orchestration
  - [ ] 10.1 Create main async pipeline coordinator in `src/async_pipeline/pipeline.py`
    - Create `run_async_pipeline(query, config)` async function
    - Initialize all components: producer, bounded queue (with maxsize), semaphore (max concurrent API calls), rate limiters per service
    - Create producer task using asyncio.create_task(producer.produce_jobs())
    - Create worker pool and start workers
    - Await producer task completion
    - Send poison pills to queue (one per worker) to signal shutdown
    - Await all worker tasks completion and collect results
    - Close all database connections, HTTP sessions, and async resources
    - Return aggregated ProcessingResults with summary statistics
    - _Requirements: 4.1, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ] 10.2 Add progress tracking with rich library
    - Install and configure rich library for terminal progress display
    - Create progress bar showing: jobs processed / total jobs, completion percentage
    - Display real-time metrics: current throughput (jobs/sec), average processing time
    - Show queue size (current items in queue) and active worker count
    - Display success count and failure count with color coding
    - Update progress bar in real-time as jobs complete
    - _Requirements: 9.4, 9.5, 16.5, 20.1, 20.3_

- [x] 11. Implement configuration management
  - [x] 11.1 Create configuration loader in `src/async_pipeline/config.py`
    - Define ProcessorConfig dataclass with fields: worker_count, queue_size, max_concurrent_api_calls, chunk_size
    - Add retry configuration: max_retries, base_delay, max_delay, exponential_base
    - Add rate limit configuration per service: llm_rate_limit, email_rate_limit, scraper_rate_limit
    - Add timeout configuration per operation: llm_timeout_seconds, email_timeout_seconds, scraper_timeout_seconds, db_timeout_seconds
    - Load configuration from environment variables (with defaults) or YAML/JSON config file
    - Validate all parameters: worker_count > 0, queue_size > 0, max_retries >= 0, timeouts > 0
    - Validate rate limits are positive, delays are positive, exponential_base > 1.0
    - Raise ValueError with clear message for invalid configuration values
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [ ] 12. Implement timeout enforcement for all operations
  - [ ] 12.1 Add timeout wrappers in AsyncJobProcessor
    - Wrap LLM API calls with asyncio.timeout(llm_timeout_seconds) context manager
    - Wrap email API calls with asyncio.timeout(email_timeout_seconds)
    - Wrap scraping operations with asyncio.timeout(scraper_timeout_seconds)
    - Wrap database queries with asyncio.timeout(db_timeout_seconds)
    - Configure different timeout values for each operation type in config
    - When timeout occurs, raise asyncio.TimeoutError to trigger retry logic
    - If all retries exhausted due to timeouts, mark job as FAILED with timeout error
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_

- [x] 13. Implement monitoring and observability
  - [x] 13.1 Add comprehensive metrics collection in pipeline and worker pool
    - Track total jobs processed, success count, failure count (atomic counters)
    - Track processing times for all jobs and calculate min, avg (mean), max
    - Track queue size over time (log periodically or on significant changes)
    - Track active worker count and semaphore availability (remaining slots)
    - Track API call latencies per external service: LLM, email, scraping
    - Track retry rates: count of retries per error type (timeout, client error, etc.)
    - Store metrics in structured format suitable for export to monitoring tools
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

  - [x] 13.2 Configure structured logging with context
    - Use structlog for JSON-formatted structured log entries
    - For each job, log: job_id, status (PENDING/PROCESSING/COMPLETED/FAILED), processing_time_ms, attempt_count
    - For errors, log: job_id, error_type (class name), error_message, full traceback (formatted)
    - Add correlation_id to trace jobs through entire pipeline
    - Configure log levels: INFO for job lifecycle, WARNING for retries, ERROR for failures
    - Configure log output format: JSON for production, human-readable for development
    - _Requirements: 9.1, 9.2, 9.3_

- [ ] 14. Checkpoint - Integration testing
  - Test end-to-end pipeline with small job set (10-50 jobs)
  - Verify all components integrate correctly: producer → queue → workers → processor → database
  - Verify backpressure mechanism works when queue fills
  - Verify graceful shutdown with poison pills
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Implement error isolation and transaction management
  - [x] 15.1 Enhance database session management in AsyncJobProcessor
    - Create new async database session for each job (per-task sessions)
    - Wrap all store_result() operations in explicit database transactions (begin/commit)
    - Implement rollback on any database error (catch exceptions, call session.rollback())
    - Ensure session cleanup in finally block: await session.close()
    - Verify workers use separate sessions: no shared session state between workers
    - Test that one worker's database failure doesn't affect other workers
    - _Requirements: 13.3, 13.4, 13.5, 19.1, 19.2, 19.3, 19.4, 19.5_

- [x] 16. Performance optimization and throughput validation
  - [x] 16.1 Optimize pipeline for throughput target
    - Configure pipeline with 5 workers, queue size 100, appropriate rate limits
    - Test processing 1000 jobs end-to-end and measure total execution time
    - Verify completion time is under 5 minutes (300 seconds)
    - Verify minimum sustained throughput of 3.3 jobs/second
    - Profile with cProfile or py-spy to identify bottlenecks if throughput is below target
    - Optimize identified bottlenecks: increase concurrency, adjust batch sizes, tune rate limits
    - Verify throughput remains steady without degradation over full test duration
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 17. Integration with existing codebase
  - [x] 17.1 Update main entry points to use async pipeline
    - Update `main.py` to import and use new async pipeline coordinator
    - Replace synchronous job processing loops with `asyncio.run(run_async_pipeline(...))`
    - Update CLI commands in `src/cli.py` to support async pipeline execution
    - Migrate existing job processing logic from `src/job_processor.py` to AsyncJobProcessor
    - Update database models in `src/models.py` for async SQLAlchemy 2.0+ compatibility (use async sessions)
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 17.2 Add backward compatibility or migration utilities
    - If synchronous interface required by other modules, create sync wrapper using asyncio.run()
    - Document migration path: what changed, how to update calling code, configuration differences
    - Create migration guide: `docs/async_pipeline_migration.md` with examples
    - _Requirements: 4.1_

- [ ] 18. Final verification and documentation
  - [ ] 18.1 Memory efficiency verification with large job volumes
    - Test pipeline with 10,000 jobs and monitor memory usage (use memory_profiler or tracemalloc)
    - Test pipeline with 100 jobs and monitor memory usage
    - Compare peak memory usage: verify it's O(queue_size + worker_count), not O(total_jobs)
    - Confirm memory usage is similar for 100 jobs and 10,000 jobs (within 10-20% variance)
    - Verify database sessions are properly closed (no connection leaks)
    - _Requirements: 10.3, 10.4_

  - [ ] 18.2 Create operational documentation
    - Document all configuration parameters in `docs/async_pipeline_config.md`: purpose, valid ranges, recommended values
    - Document monitoring metrics and recommended alerting thresholds: failure rate, throughput, queue size, processing time percentiles
    - Create troubleshooting guide: common issues (timeouts, rate limiting, memory), diagnostic steps, solutions
    - Document performance tuning guidelines: how to adjust worker_count, queue_size, rate limits for different workloads
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 20.5_

- [ ] 19. Final checkpoint - Production readiness validation
  - Run full test suite including unit tests, integration tests, and load tests
  - Verify all 20 requirements are met through testing and code review
  - Conduct final code review focusing on error handling, resource cleanup, and edge cases
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- **Incremental Implementation**: Each task builds on previous tasks, allowing for incremental validation
- **Requirement Traceability**: Every task explicitly references specific requirement acceptance criteria (e.g., 1.1, 2.3, 5.4)
- **Existing Code Leverage**: Tasks reference existing `src/async_pipeline/` directory, building on work already done
- **Checkpoints**: Four checkpoint tasks ensure validation at key milestones before proceeding
- **No Optional Test Tasks**: Testing is integrated into implementation tasks due to critical nature of async correctness
- **Memory Efficiency Focus**: Explicit verification tasks ensure O(1) memory usage through streaming
- **Production-Grade**: Comprehensive error handling, retry logic, monitoring, and observability built-in
- **Configuration-Driven**: All tunable parameters configurable without code changes
- **Graceful Degradation**: Error isolation ensures single job failures don't crash entire pipeline

## Requirements Coverage Summary

**Streaming & Memory (Req 1, 10)**: Tasks 2.1, 2.2, 18.1  
**Queue & Backpressure (Req 2)**: Task 3.1  
**Concurrency (Req 3, 7)**: Tasks 6.1, 8.1  
**Exactly-Once Processing (Req 4)**: Tasks 6.1, 8.1, 10.1  
**Retry Logic (Req 5, 18)**: Tasks 4.1, 6.1, 12.1  
**Rate Limiting (Req 6)**: Task 5.1  
**Graceful Shutdown (Req 8)**: Tasks 3.1, 8.1, 10.1  
**Logging & Progress (Req 9)**: Tasks 10.2, 13.2  
**Async I/O (Req 11)**: Tasks 9.1, 9.2, 9.3, 17.1  
**Connection Pooling (Req 12)**: Tasks 1, 9.1, 9.2, 9.3  
**Error Isolation (Req 13, 19)**: Tasks 8.1, 15.1  
**Result Storage (Req 14)**: Task 6.1  
**Configuration (Req 15)**: Task 11.1  
**Throughput (Req 16)**: Task 16.1  
**Immutability (Req 17)**: Task 1  
**Monitoring (Req 20)**: Tasks 13.1, 13.2

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "3.1", "4.1", "5.1"] },
    { "id": 2, "tasks": ["6.1", "11.1"] },
    { "id": 3, "tasks": ["8.1"] },
    { "id": 4, "tasks": ["9.1", "9.2", "9.3"] },
    { "id": 5, "tasks": ["10.1", "10.2", "12.1"] },
    { "id": 6, "tasks": ["13.1", "13.2"] },
    { "id": 7, "tasks": ["15.1"] },
    { "id": 8, "tasks": ["16.1"] },
    { "id": 9, "tasks": ["17.1", "17.2"] },
    { "id": 10, "tasks": ["18.1", "18.2"] }
  ]
}
```

**Dependency Rationale**:
- **Wave 0**: Foundation - core structure and types
- **Wave 1**: Independent components can be built in parallel (producer, queue, retry, rate limiter)
- **Wave 2**: Processor depends on retry/rate limiter; config can be built in parallel
- **Wave 3**: Worker pool depends on processor and queue
- **Wave 4**: HTTP client updates can be done in parallel (LLM, email, scraper services)
- **Wave 5**: Pipeline orchestration depends on all core components; progress tracking and timeouts can be added in parallel
- **Wave 6**: Monitoring/logging can be added in parallel after pipeline exists
- **Wave 7**: Transaction management enhances existing processor
- **Wave 8**: Performance optimization requires complete pipeline
- **Wave 9**: Integration requires all async components complete
- **Wave 10**: Final verification and documentation

This dependency graph enables maximum parallelization: wave 1 has 5 independent tasks, wave 4 has 3 independent tasks, wave 5 has 3 independent tasks, and wave 6 has 2 independent tasks.
