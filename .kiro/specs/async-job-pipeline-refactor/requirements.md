# Requirements Document

## Introduction

This document specifies the business and functional requirements for refactoring the job automation pipeline from a partially-async, sequential processing model into a high-performance, fully-async concurrent system. The system must process job applications efficiently while maintaining reliability, preventing resource exhaustion, and providing visibility into processing status. The refactor addresses critical bottlenecks: sequential processing limiting throughput, blocking I/O operations causing delays, unbounded memory growth risking crashes, absence of rate limiting leading to API throttling, and insufficient error handling causing data loss.

## Glossary

- **Job_Producer**: Component that streams job records from the database using async generators
- **Job_Queue**: Bounded async queue (asyncio.Queue) that holds jobs awaiting processing
- **Worker_Pool**: Collection of N concurrent async workers that process jobs from the queue
- **Job_Processor**: Component that executes the full processing pipeline for a single job
- **Retry_Manager**: Component that implements exponential backoff retry logic for failed operations
- **Rate_Limiter**: Token bucket implementation that controls API request rates
- **External_API**: Third-party service (LLM, email, scraping) called during job processing
- **Processing_Result**: Data structure containing job processing outcome and metrics
- **Semaphore**: Async concurrency limiter that restricts simultaneous operations
- **Backpressure**: Mechanism that slows down producer when consumers cannot keep up
- **Poison_Pill**: Sentinel value (None) sent to signal worker shutdown
- **Job_Context**: Immutable data structure containing job information passed through pipeline

## Requirements

### Requirement 1: Streaming Job Production

**User Story:** As a system operator, I want jobs to be streamed from the database in chunks, so that memory usage remains constant regardless of the total number of jobs.

#### Acceptance Criteria

1. WHEN the Job_Producer fetches jobs from the database, THE Job_Producer SHALL retrieve jobs in configurable chunks
2. WHEN yielding jobs, THE Job_Producer SHALL yield one JobContext object at a time using async generators
3. WHEN a chunk is fully yielded, THE Job_Producer SHALL close the database session before fetching the next chunk
4. THE Job_Producer SHALL maintain memory usage of O(chunk_size) regardless of total job count
5. WHEN the database contains no more jobs matching the query, THE Job_Producer SHALL terminate the generator cleanly

### Requirement 2: Bounded Queue with Backpressure

**User Story:** As a system operator, I want a bounded queue that automatically prevents memory overflow, so that the system remains stable under high load.

#### Acceptance Criteria

1. THE Job_Queue SHALL have a configurable maximum size limit
2. WHEN the Job_Queue reaches maximum capacity, THE Job_Queue SHALL block the producer from adding new jobs
3. WHEN workers consume jobs from the Job_Queue, THE Job_Queue SHALL automatically unblock the producer
4. WHEN the Job_Queue is empty, THE Job_Queue SHALL block workers until new jobs are available
5. THE Job_Queue SHALL maintain queue size less than or equal to the configured maximum at all times

### Requirement 3: Concurrent Worker Pool

**User Story:** As a system operator, I want multiple concurrent workers processing jobs simultaneously, so that throughput is maximized for I/O-bound operations.

#### Acceptance Criteria

1. THE Worker_Pool SHALL spawn exactly the configured number of worker coroutines
2. WHEN a worker retrieves a job from the Job_Queue, THE Worker_Pool SHALL process the job asynchronously
3. WHEN a worker completes job processing, THE Worker_Pool SHALL immediately retrieve the next job from the queue
4. WHEN a worker encounters an error, THE Worker_Pool SHALL continue processing without terminating other workers
5. THE Worker_Pool SHALL maintain active worker count less than or equal to the configured worker count at all times

### Requirement 4: Exactly-Once Job Processing

**User Story:** As a business user, I want every job to be processed exactly once, so that no opportunities are missed or duplicated.

#### Acceptance Criteria

1. WHEN a job exists in the database, THE system SHALL produce exactly one ProcessingResult for that job
2. WHEN a job is retrieved from the Job_Queue, THE system SHALL process that job exactly once
3. WHEN job processing fails and retries are exhausted, THE system SHALL mark the job as FAILED with error details
4. WHEN job processing succeeds, THE system SHALL store exactly one result record in the database
5. THE system SHALL ensure no jobs are lost due to worker failure or system restart

### Requirement 5: Exponential Backoff Retry Logic

**User Story:** As a system operator, I want automatic retry with exponential backoff for transient failures, so that temporary issues don't cause permanent job failures.

#### Acceptance Criteria

1. WHEN an External_API call fails with a retryable error, THE Retry_Manager SHALL retry the operation
2. WHEN retrying an operation, THE Retry_Manager SHALL wait with exponential backoff between attempts
3. WHEN the retry count reaches the maximum configured retries, THE Retry_Manager SHALL mark the job as permanently failed
4. THE Retry_Manager SHALL calculate retry delay using the formula: base_delay × (exponential_base ^ attempt)
5. WHEN the calculated delay exceeds maximum delay, THE Retry_Manager SHALL cap the delay at the configured maximum

### Requirement 6: Rate Limiting for External APIs

**User Story:** As a system operator, I want automatic rate limiting for external API calls, so that the system respects API quotas and avoids throttling.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL implement token bucket algorithm for rate control
2. WHEN an External_API call is requested, THE Rate_Limiter SHALL acquire a token before proceeding
3. WHEN tokens are insufficient, THE Rate_Limiter SHALL block the caller until tokens become available
4. THE Rate_Limiter SHALL refill tokens at the configured rate per second
5. THE Rate_Limiter SHALL maintain API call rate less than or equal to configured limit in any time window

### Requirement 7: Concurrency Control with Semaphores

**User Story:** As a system operator, I want to limit concurrent external API calls, so that services are not overwhelmed and resource exhaustion is prevented.

#### Acceptance Criteria

1. THE system SHALL use a Semaphore to limit concurrent External_API calls
2. WHEN a worker attempts an External_API call, THE worker SHALL acquire the Semaphore before proceeding
3. WHEN the Semaphore limit is reached, THE system SHALL block additional API calls until a slot becomes available
4. WHEN an External_API call completes, THE worker SHALL release the Semaphore immediately
5. IF an External_API call raises an exception, THE worker SHALL release the Semaphore in a finally block

### Requirement 8: Graceful Shutdown

**User Story:** As a system operator, I want the system to shut down gracefully without losing in-progress jobs, so that processing can resume cleanly after restart.

#### Acceptance Criteria

1. WHEN a shutdown signal is received, THE Job_Producer SHALL stop yielding new jobs immediately
2. WHEN shutdown is initiated, THE system SHALL send one Poison_Pill to the Job_Queue for each worker
3. WHEN a worker receives a Poison_Pill, THE worker SHALL complete the current job and then terminate
4. WHEN all workers terminate, THE system SHALL close all database connections and HTTP sessions
5. THE system SHALL ensure all in-progress jobs complete successfully before final shutdown

### Requirement 9: Structured Logging and Progress Tracking

**User Story:** As a system operator, I want detailed structured logs and real-time progress tracking, so that I can monitor system health and troubleshoot issues.

#### Acceptance Criteria

1. THE system SHALL use structured logging with JSON-formatted log entries
2. WHEN processing a job, THE system SHALL log job_id, status, processing time, and attempt count
3. WHEN an error occurs, THE system SHALL log the error type, message, and full traceback
4. THE system SHALL display a real-time progress bar showing jobs processed and estimated completion time
5. THE system SHALL track and log throughput metrics (jobs per second, average processing time)

### Requirement 10: Memory Efficiency Through Streaming

**User Story:** As a system operator, I want memory usage to remain constant regardless of job count, so that the system can handle large job volumes without crashing.

#### Acceptance Criteria

1. THE Job_Producer SHALL use async generators to yield jobs one at a time
2. WHEN a job is yielded by the Job_Producer, THE previous job SHALL be eligible for garbage collection
3. THE system SHALL maintain total memory usage of O(queue_size + worker_count), not O(total_jobs)
4. WHEN processing 10,000 jobs, THE system SHALL use the same peak memory as processing 100 jobs
5. THE system SHALL close database sessions immediately after fetching each chunk to release connection resources

### Requirement 11: Async I/O for All External Operations

**User Story:** As a developer, I want all I/O operations to be non-blocking async, so that the event loop remains responsive and throughput is maximized.

#### Acceptance Criteria

1. THE system SHALL use async HTTP clients (aiohttp or httpx) for all External_API calls
2. THE system SHALL use async SQLAlchemy for all database operations
3. THE system SHALL never block the event loop with synchronous I/O operations
4. WHEN waiting for I/O, THE system SHALL allow other coroutines to execute concurrently
5. WHERE CPU-intensive operations are required, THE system SHALL use ProcessPoolExecutor to avoid blocking

### Requirement 12: Connection Pooling

**User Story:** As a system operator, I want connection pooling for databases and HTTP clients, so that connection overhead is minimized and resources are reused efficiently.

#### Acceptance Criteria

1. THE system SHALL maintain a database connection pool with configurable size and overflow limits
2. THE system SHALL reuse HTTP sessions across multiple API calls instead of creating new connections
3. WHEN a database operation completes, THE system SHALL return the connection to the pool for reuse
4. WHEN a worker terminates, THE system SHALL close all HTTP sessions properly
5. THE system SHALL configure connection pool timeouts to prevent resource leaks

### Requirement 13: Error Isolation

**User Story:** As a business user, I want errors in one job to not affect other jobs, so that partial failures don't stop the entire pipeline.

#### Acceptance Criteria

1. WHEN a job processing fails, THE system SHALL continue processing other jobs without interruption
2. WHEN a worker encounters an unhandled exception, THE worker SHALL log the error and process the next job
3. WHEN an External_API call times out, THE system SHALL only fail that specific job, not all jobs
4. THE system SHALL use per-task database sessions to ensure failure isolation
5. WHEN a database transaction fails, THE system SHALL roll back only that transaction, not affect other workers

### Requirement 14: Processing Result Storage

**User Story:** As a business user, I want detailed processing results stored for every job, so that I can review outcomes and investigate failures.

#### Acceptance Criteria

1. WHEN a job is processed, THE system SHALL create a ProcessingResult with status, data, error, and metrics
2. WHEN processing succeeds, THE ProcessingResult SHALL contain status=COMPLETED and the extracted data
3. WHEN processing fails after all retries, THE ProcessingResult SHALL contain status=FAILED and error details
4. THE ProcessingResult SHALL include attempt count, processing time in milliseconds, and timestamp
5. THE system SHALL store all ProcessingResults in the database for audit and analysis

### Requirement 15: Configurable Pipeline Parameters

**User Story:** As a system operator, I want to configure key pipeline parameters without code changes, so that I can tune performance for different environments.

#### Acceptance Criteria

1. THE system SHALL accept configuration for worker_count, queue_size, and max_concurrent_api_calls
2. THE system SHALL accept configuration for retry parameters (max_retries, base_delay, max_delay, exponential_base)
3. THE system SHALL accept configuration for rate limits per external service (LLM, email, scraping)
4. THE system SHALL accept configuration for timeouts per operation type (LLM, email, scraping, database)
5. THE system SHALL validate all configuration values and raise errors for invalid settings

### Requirement 16: Throughput Target

**User Story:** As a business user, I want the system to process at least 1000 jobs in under 5 minutes, so that job application campaigns complete in a reasonable timeframe.

#### Acceptance Criteria

1. WHEN processing 1000 jobs with 5 workers, THE system SHALL complete in less than 5 minutes
2. THE system SHALL achieve minimum throughput of 3.3 jobs per second under normal conditions
3. WHEN External_APIs respond within expected latency, THE system SHALL maintain steady throughput without degradation
4. THE system SHALL use concurrent workers to maximize throughput for I/O-bound operations
5. THE system SHALL provide throughput metrics (jobs/sec, avg processing time) in logs

### Requirement 17: Job Context Immutability

**User Story:** As a developer, I want job context to be immutable, so that concurrent workers cannot cause race conditions by modifying shared state.

#### Acceptance Criteria

1. THE JobContext dataclass SHALL be declared as frozen to prevent mutations
2. WHEN a JobContext is created, THE system SHALL not allow modification of its fields
3. WHEN passing JobContext between components, THE system SHALL ensure the same immutable object is used
4. THE system SHALL use dataclasses or NamedTuples for all data passed between workers
5. THE system SHALL avoid shared mutable state that could cause race conditions

### Requirement 18: Timeout Enforcement

**User Story:** As a system operator, I want configurable timeouts for all external operations, so that slow or hung operations don't block the pipeline indefinitely.

#### Acceptance Criteria

1. THE system SHALL enforce timeout for all External_API calls using async timeout mechanisms
2. WHEN an External_API call exceeds its configured timeout, THE system SHALL raise asyncio.TimeoutError
3. THE system SHALL configure separate timeouts for LLM calls, email operations, scraping, and database queries
4. WHEN a timeout occurs, THE Retry_Manager SHALL attempt to retry the operation with exponential backoff
5. IF retries are exhausted due to repeated timeouts, THE system SHALL mark the job as FAILED

### Requirement 19: Database Transaction Atomicity

**User Story:** As a developer, I want each job's database operations to be atomic, so that partial writes don't corrupt data on failures.

#### Acceptance Criteria

1. THE system SHALL use database transactions for all write operations
2. WHEN storing a ProcessingResult, THE system SHALL commit all related records in a single transaction
3. WHEN a database error occurs, THE system SHALL roll back the entire transaction
4. THE system SHALL use per-task database sessions to ensure transaction isolation
5. WHEN a transaction is rolled back, THE system SHALL release the database connection to the pool

### Requirement 20: Monitoring and Observability

**User Story:** As a system operator, I want comprehensive metrics and logs, so that I can monitor performance, detect issues, and optimize the pipeline.

#### Acceptance Criteria

1. THE system SHALL track and log total jobs processed, success count, and failure count
2. THE system SHALL track and log average processing time, minimum time, and maximum time
3. THE system SHALL track and log queue size, active workers, and semaphore availability
4. THE system SHALL track and log API call latencies and retry rates per external service
5. THE system SHALL expose metrics in structured format suitable for monitoring tools
