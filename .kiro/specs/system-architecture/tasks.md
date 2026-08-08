# Implementation Plan: NEXUS Job Acquisition System

## Overview

This implementation plan focuses on completing the NEXUS system architecture by filling gaps in existing implementations, enhancing integration between components, adding comprehensive testing, and preparing for production deployment. Most core components are already operational (async pipeline, scrapers, AI services, email engine, outreach processor, resume engine, personalization, DAG orchestrator, contact intelligence, and feedback loop). This plan addresses remaining gaps, testing coverage, monitoring enhancements, and production hardening.

## Tasks

- [x] 1. Database schema validation and migration support
  - Verify all tables exist with proper indexes (jobs, applications, resumes, contacts, outreach_records, processing_results, pipeline_metrics)
  - Create compound indexes: (jobs.company, jobs.fetched_at), (contacts.email, contacts.company), (outreach_records.job_id, outreach_records.contact_id)
  - Create single indexes: (applications.match_score)
  - Add database migration utilities for schema updates
  - Implement PostgreSQL migration path for production scaling
  - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8, 21.9, 21.10, 21.11_

- [x] 1.1 Write unit tests for database schema validation
  - Test table existence and structure
  - Test index creation and performance
  - Test migration rollback functionality
  - _Requirements: 21.1-21.11_

- [x] 2. REST API enhancements and health checks
  - [x] 2.1 Implement comprehensive health check endpoints
    - Add `/api/health` with system component status
    - Check Ollama connectivity and model availability
    - Check database connectivity and table status
    - Check email service (SMTP) connectivity
    - Check external API status (GitHub, Cloudflare, Google Sheets)
    - Return structured health report with component statuses
    - _Requirements: 23.6, 22.1, 22.2, 22.3, 22.4, 22.5, 22.6_

  - [x] 2.2 Add request validation and error handling
    - Implement Pydantic request models for all endpoints
    - Add input validation for pipeline execution requests
    - Add comprehensive error responses with proper HTTP status codes
    - Implement request timeout handling
    - _Requirements: 23.2, 23.3_

  - [x] 2.3 Enhance request tracing and correlation IDs
    - Add X-Trace-ID header generation for all requests
    - Propagate trace IDs through all log entries
    - Add trace ID to response headers
    - Implement trace ID indexing for log searching
    - _Requirements: 23.5, 25.2, 33.1_

- [x] 2.4 Write integration tests for REST API endpoints
  - Test health check endpoint responses
  - Test async pipeline endpoint with various parameters
  - Test request validation and error responses
  - Test trace ID propagation
  - _Requirements: 23.1, 23.2, 23.3, 23.5, 23.6_

- [x] 3. Graceful shutdown and signal handling
  - [x] 3.1 Implement graceful shutdown for AsyncJobPipeline
    - Register SIGTERM and SIGINT signal handlers
    - Stop accepting new jobs on shutdown signal
    - Wait for in-flight jobs to complete (with configurable timeout)
    - Forcefully terminate remaining jobs after timeout
    - Clean up resources (database connections, file handles)
    - Log shutdown progress and completion
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 34.1_

  - [x] 3.2 Add shutdown support to FastAPI server
    - Implement lifespan context manager for cleanup
    - Close database connection pools on shutdown
    - Close async HTTP client sessions
    - Flush and close log handlers
    - _Requirements: 24.1, 24.2, 24.3, 24.4_

- [x] 3.3 Write tests for graceful shutdown
  - Test SIGTERM handling in AsyncJobPipeline
  - Test SIGINT handling in AsyncJobPipeline
  - Test timeout enforcement for shutdown
  - Test resource cleanup completeness
  - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6_

- [ ] 4. Checkpoint - Verify core infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Enhanced observability and metrics
  - [x] 5.1 Add Prometheus metrics export endpoint
    - Create `/metrics` endpoint for Prometheus scraping
    - Export job processing metrics (throughput, latency, success rate)
    - Export queue metrics (size, backpressure events, wait times)
    - Export worker metrics (utilization, active count, idle time)
    - Export API metrics (rate limiter waits, semaphore contention)
    - Export error metrics (retry attempts, failure types, error rates)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 9.1_

  - [x] 5.2 Implement metrics dashboard data endpoint
    - Create `/api/metrics/snapshot` endpoint for real-time dashboard
    - Return current pipeline state (queue size, active workers, throughput)
    - Return time-series data for charts (last hour, last day)
    - Calculate and return latency percentiles (p50, p95, p99)
    - _Requirements: 6.6, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 5.3 Enhance structured logging with log aggregation support
    - Add JSON log formatter for log aggregation systems
    - Include standard fields in all logs (timestamp, level, component, correlation_id)
    - Add context fields (job_id, worker_id, status, processing_time_ms)
    - Implement log sampling for high-volume operations
    - Add log level configuration via environment variables
    - _Requirements: 6.7, 6.8, 25.1, 25.2, 25.3, 25.4, 25.5, 25.6, 25.7, 10.1_

- [ ] 5.4 Write unit tests for metrics collection
  - Test metrics calculation accuracy (throughput, latency percentiles)
  - Test time-series data aggregation
  - Test metrics snapshot generation
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 6. Configuration management and validation
  - [x] 6.1 Enhance ProcessorConfig validation
    - Validate worker_count is positive and within reasonable bounds (1-50)
    - Validate queue_size is positive and sufficient (≥10)
    - Validate rate_limits are positive for all API types
    - Validate timeout values are positive for all operation types
    - Validate retry parameters (max_attempts, backoff multiplier, max_delay)
    - Validate database parameters (chunk_size, pool_size)
    - Add descriptive error messages for each validation failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 26.1, 26.2, 26.3, 26.4, 26.5, 26.6, 12.1_

  - [x] 6.2 Add environment-specific configuration profiles
    - Create configuration profiles: development, staging, production
    - Support profile selection via environment variable
    - Add profile-specific defaults (worker count, timeouts, log levels)
    - Document configuration best practices
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 6.3 Write property tests for configuration validation
  - **Property 12: Configuration Validation**
  - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 26.1, 26.2, 26.3, 26.4, 26.5, 26.6**
  - Test that invalid configurations (negative values, zero values, extreme values) raise descriptive errors
  - Test that valid configurations are accepted
  - Test configuration boundary conditions

- [ ] 7. Property-based tests for async pipeline correctness
  - [ ] 7.1 Write property test for streaming memory efficiency
    - **Property 1: Streaming Memory Efficiency**
    - **Validates: Requirements 1.1, 1.2, 27.1, 27.2, 27.5**
    - Test that memory usage remains O(chunk_size) regardless of total job count
    - Use hypothesis to generate job counts from 100 to 100,000
    - Measure memory usage during streaming

  - [ ] 7.2 Write property test for bounded queue backpressure
    - **Property 2: Bounded Queue Backpressure**
    - **Validates: Requirements 1.3, 1.4, 1.5, 30.1, 30.2**
    - Test that put blocks when queue is full
    - Test that get blocks when queue is empty
    - Test poison pill pattern for shutdown

  - [ ] 7.3 Write property test for worker pool concurrency
    - **Property 3: Worker Pool Concurrency**
    - **Validates: Requirements 2.1, 2.3**
    - Test that exactly W workers are spawned for worker_count=W
    - Test that sum of per-worker processed counts equals total jobs processed
    - Test concurrent execution with hypothesis-generated job sets

  - [ ] 7.4 Write property test for error isolation
    - **Property 4: Error Isolation**
    - **Validates: Requirements 2.4, 3.6, 29.1, 29.2, 29.5**
    - Test that failing jobs don't affect other jobs
    - Test that no exceptions propagate to pipeline coordinator
    - Use hypothesis to generate mixed success/failure job sets

  - [ ] 7.5 Write property test for exponential backoff retry
    - **Property 7: Exponential Backoff Retry**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.6**
    - Test retry delay calculation: min(base × exponential^attempt, max)
    - Test that total attempts never exceed max_attempts
    - Test jitter addition to delays

  - [ ] 7.6 Write property test for rate limiting
    - **Property 8: Per-API Rate Limiting**
    - **Validates: Requirements 2.2, 5.2, 5.3, 5.5**
    - Test that API calls never exceed configured rate limits
    - Test that total concurrent calls never exceed semaphore limit
    - Use hypothesis to generate API call patterns

- [ ] 8. Checkpoint - Verify async pipeline correctness
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Job scraping integration and testing
  - [x] 9.1 Add scraper orchestration and deduplication
    - Create unified scraper interface for all platforms
    - Implement parallel scraping across multiple platforms
    - Add job deduplication based on job_id generation
    - Add result aggregation across scrapers
    - Implement error handling for scraper failures
    - _Requirements: 10.1, 10.2, 10.3, 10.5_

  - [ ] 9.2 Write property tests for job scraping
    - **Property 15: Job Data Normalization**
    - **Validates: Requirements 10.2**
    - Test that all scraped jobs conform to common schema
    - Test that all required fields are present

    - **Property 16: Job ID Uniqueness**
    - **Validates: Requirements 10.3**
    - Test that generated job IDs are unique across all scrapers
    - Use hypothesis to generate job data from multiple platforms

    - **Property 17: Graceful Scraping Failure**
    - **Validates: Requirements 10.5**
    - Test that scraper errors return empty results without raising exceptions

- [ ] 10. AI service integration and fallback testing
  - [x] 10.1 Enhance LLM cascade fallback chain
    - Verify fallback chain: Ollama → Gemini → Keyword matching
    - Add health checks for each LLM provider
    - Implement automatic provider failover on errors
    - Add provider availability tracking and metrics
    - _Requirements: 11.2, 11.3, 11.4, 32.1_

  - [ ] 10.2 Write property tests for AI service
    - **Property 18: LLM Cascade Fallback**
    - **Validates: Requirements 11.2, 11.3, 11.4**
    - Test that provider P2 is tried when P1 fails
    - Test that keyword fallback is used when all LLMs fail

    - **Property 19: Match Score Range Validation**
    - **Validates: Requirements 11.7**
    - Test that match scores are between 0 and 100 inclusive
    - Use hypothesis to generate job descriptions and resumes

- [ ] 11. Email discovery engine validation and testing
  - [x] 11.1 Verify 5-layer discovery pipeline integration
    - Test concurrent collection from all 13+ providers
    - Verify pattern mining and SQLite persistence
    - Test candidate generation from mined patterns
    - Verify SMTP verification (20-thread pool)
    - Test multi-factor confidence scoring and ranking
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_

  - [ ] 11.2 Write property tests for email discovery
    - **Property 20: Email Pattern Learning and Application**
    - **Validates: Requirements 12.3, 12.4, 13.1, 13.2, 13.3**
    - Test that patterns are detected and stored
    - Test that learned patterns are applied to new contacts

    - **Property 21: Email Discovery Deduplication and Ranking**
    - **Validates: Requirements 12.7, 12.8**
    - Test that duplicates are removed
    - Test that results are ranked by descending confidence score

    - **Property 22: Multi-Factor Confidence Scoring**
    - **Validates: Requirements 12.6**
    - Test confidence score calculation based on multiple factors
    - Use hypothesis to generate discovered emails with various attributes

- [ ] 12. Resume engine integration and testing
  - [x] 12.1 Verify resume tailoring pipeline
    - Test JD analysis for requirement extraction
    - Test section optimization for job matching
    - Test ATS keyword optimization
    - Test PDF generation and storage
    - Verify resume versioning by job_id
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ] 12.2 Write property tests for resume engine
    - **Property 23: Resume Tailoring Pipeline**
    - **Validates: Requirements 14.1, 14.2, 14.3, 14.4**
    - Test that all pipeline steps complete successfully
    - Test that PDF is generated and is valid

    - **Property 24: Resume Versioning**
    - **Validates: Requirements 14.5**
    - Test that resume versions match job IDs
    - Test that multiple versions can coexist

- [ ] 13. Checkpoint - Verify component integration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Outreach processor enhancements and testing
  - [x] 14.1 Verify outreach orchestration components
    - Test Trie-based email deduplication (O(k) performance)
    - Test ContactGraph routing (O(1) lookups)
    - Test TaskDAG with Kahn's scheduling
    - Test timezone-aware send timing (09:00-11:00 local, Tue-Thu)
    - Test rate limiting (50/day global, 3/week per-domain, 1/week per-contact)
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8_

  - [ ] 14.2 Write property tests for outreach processor
    - **Property 26: Email Deduplication Efficiency**
    - **Validates: Requirements 16.1**
    - Test O(k) time complexity for Trie deduplication
    - Use hypothesis to generate email address sets with duplicates

    - **Property 27: Outreach Rate Limiting**
    - **Validates: Requirements 16.6, 16.7, 16.8**
    - Test global rate limit (≤50 emails/day)
    - Test per-domain rate limit (≤3 emails/week per domain)
    - Test per-contact rate limit (≤1 email/week per contact)

    - **Property 28: Timezone-Aware Send Timing**
    - **Validates: Requirements 16.4, 16.5**
    - Test send time is between 09:00-11:00 local time
    - Test preference for Tuesday through Thursday

- [ ] 15. Reply detection and follow-up testing
  - [x] 15.1 Implement reply detection and classification
    - Test IMAP polling at 30-minute intervals
    - Test reply detection and status updates
    - Test sentiment classification (positive, negative, neutral, referral, unsubscribe)
    - Test unsubscribe handling (mark do-not-contact)
    - _Requirements: 17.1, 17.2, 17.3, 17.4_

  - [x] 15.2 Implement follow-up scheduling
    - Test first follow-up scheduling (day 5)
    - Test second follow-up scheduling (day 12)
    - Test third follow-up scheduling (day 21)
    - Test follow-up cancellation on reply
    - Test different follow-up content generation
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_

  - [ ] 15.3 Write property test for follow-up cancellation
    - **Property 29: Follow-Up Cancellation on Reply**
    - **Validates: Requirements 18.4**
    - Test that all pending follow-ups are cancelled when reply is received
    - Use hypothesis to generate reply timing scenarios

- [ ] 16. Contact intelligence and ranking
  - [x] 16.1 Verify contact graph and ranking
    - Test ContactGraph relationship building
    - Test PageRank-style ranking algorithm
    - Test role hierarchy prioritization
    - Test hiring manager prioritization over recruiters
    - Test engineering manager prioritization for technical roles
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_

  - [ ] 16.2 Write property test for contact role prioritization
    - **Property 30: Contact Role Prioritization**
    - **Validates: Requirements 19.4, 19.5**
    - Test that hiring managers rank higher than recruiters
    - Test that engineering managers rank high for technical roles
    - Use hypothesis to generate contact sets with various roles

- [ ] 17. DAG orchestrator validation and testing
  - [x] 17.1 Verify DAG workflow execution
    - Test StateGraph node and edge representation
    - Test conditional routing between nodes
    - Test parallel execution of independent nodes
    - Test topological sorting for execution order
    - Test dependency enforcement during execution
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ] 17.2 Write property tests for DAG orchestrator
    - **Property 13: DAG Dependency Enforcement**
    - **Validates: Requirements 9.4, 9.5**
    - Test that execution order is a valid topological sort
    - Test that no node executes before its dependencies complete

    - **Property 14: Conditional Routing**
    - **Validates: Requirements 9.2**
    - Test that next node selection follows condition evaluation
    - Use hypothesis to generate workflow graphs with conditions

- [ ] 18. Checkpoint - Verify workflow orchestration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Feedback loop implementation and testing
  - [x] 19.1 Implement feedback collection and optimization
    - Test nightly metrics collection
    - Test pattern mining from successful/unsuccessful outreach
    - Test adaptive optimization based on patterns
    - Test daily digest report generation
    - Test metric tracking (open rate, reply rate, positive reply rate)
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

  - [ ] 19.2 Write unit tests for feedback loop components
    - Test metrics calculation accuracy
    - Test pattern detection from historical data
    - Test strategy optimization recommendations
    - Test digest report formatting
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

- [ ] 20. Personalization engine validation
  - [x] 20.1 Verify personalization pipeline
    - Test company research data collection
    - Test contact research data collection
    - Test personalized hook generation
    - Test email composition with hook integration
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [ ] 20.2 Write property test for personalization completeness
    - **Property 25: Personalization Pipeline Completeness**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.4**
    - Test that all pipeline steps produce non-empty results
    - Test that final email includes all components (hook, body, signature)
    - Use hypothesis to generate company and contact data

- [ ] 21. End-to-end integration testing
  - [ ] 21.1 Implement complete workflow integration test
    - Test full pipeline: scrape → analyze → tailor → discover → personalize → outreach
    - Test parallel execution paths (tailor_resume ∥ contact_intel)
    - Test error recovery and graceful degradation
    - Test metrics collection throughout workflow
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ] 21.2 Write integration test for DAG workflow
    - Test NEXUS DAG execution with all nodes
    - Test conditional routing (feedback only after real sends)
    - Test parallel node execution
    - Test workflow state persistence
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [ ] 22. Production hardening and deployment preparation
  - [ ] 22.1 Add error tracking and alerting
    - Integrate Sentry for error tracking
    - Add error grouping and deduplication
    - Configure alert thresholds for critical errors
    - Add error context (user, request, environment)
    - _Requirements: 4.5, 6.5_

  - [ ] 22.2 Implement secrets management
    - Move secrets from .env to secure secrets manager (Vault/AWS Secrets Manager)
    - Add secrets rotation support
    - Implement secrets encryption at rest
    - Add audit logging for secrets access
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5, 22.6_

  - [ ] 22.3 Create Docker containerization
    - Write Dockerfile for application
    - Create docker-compose.yml for local development
    - Add multi-stage builds for optimization
    - Configure container health checks
    - Add volume mounts for data persistence
    - _Requirements: 24.1, 24.2_

  - [ ] 22.4 Document deployment procedures
    - Write deployment runbook
    - Document environment setup steps
    - Add troubleshooting guide
    - Create monitoring dashboard setup guide
    - Document rollback procedures
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 23. Performance optimization and load testing
  - [ ] 23.1 Implement database query optimization
    - Add database query profiling
    - Optimize slow queries with proper indexes
    - Implement connection pooling tuning
    - Add query result caching for frequent queries
    - _Requirements: 21.8, 21.9, 21.10, 21.11, 28.1, 28.3_

  - [ ] 23.2 Conduct load testing
    - Test async pipeline with 10,000+ jobs
    - Test concurrent API request handling
    - Test database performance under load
    - Measure throughput and latency under load
    - Identify bottlenecks and optimization opportunities
    - _Requirements: 27.1, 27.2, 27.3, 27.4, 27.5, 28.1, 28.2, 28.3, 28.4, 28.5_

  - [ ] 23.3 Write performance benchmarks
    - Benchmark async pipeline throughput
    - Benchmark email deduplication performance
    - Benchmark contact graph lookup performance
    - Benchmark AI service response times
    - _Requirements: 16.1, 16.2, 28.1, 28.2, 28.3_

- [ ] 24. Documentation and API reference
  - [ ] 24.1 Generate OpenAPI documentation
    - Add OpenAPI spec generation to FastAPI
    - Document all REST endpoints with examples
    - Add request/response schemas
    - Include authentication and authorization details
    - _Requirements: 23.1, 23.2, 23.3_

  - [ ] 24.2 Write architecture documentation
    - Document system architecture and component interactions
    - Create sequence diagrams for key workflows
    - Document data flow and state transitions
    - Add scaling and deployment architecture diagrams
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ] 24.3 Create developer onboarding guide
    - Write setup instructions for local development
    - Document development workflow and best practices
    - Add code contribution guidelines
    - Create testing guidelines
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 25. Final checkpoint and production readiness review
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 26. Property test implementation for correctness properties
  - [ ] 26.1 Write property test for timeout enforcement
    - **Property 6: Timeout Enforcement**
    - **Validates: Requirements 3.5, 11.5**
    - Test that operations exceeding timeout T are cancelled
    - Use hypothesis to generate operation durations

  - [ ] 26.2 Write property test for job processing pipeline
    - **Property 5: Job Processing Pipeline**
    - **Validates: Requirements 3.1, 3.2, 3.3**
    - Test that skill extraction produces non-empty results
    - Test that match score is 0-100 inclusive
    - Test that results are stored in database

  - [ ] 26.3 Write property test for metrics collection
    - **Property 9: Comprehensive Metrics Collection**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
    - Test accuracy of throughput calculation
    - Test accuracy of latency percentiles (p50, p95, p99)
    - Test queue, worker, and error metrics tracking

  - [ ] 26.4 Write property test for structured logging
    - **Property 10: Structured Logging Completeness**
    - **Validates: Requirements 6.7, 6.8, 25.1, 25.2, 25.3, 25.4, 25.5, 25.6**
    - Test that all logs include correlation_id
    - Test that job logs include job_id, worker_id, status
    - Use hypothesis to generate log scenarios

  - [ ] 26.5 Write property test for progress tracking accuracy
    - **Property 11: Progress Tracking Accuracy**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
    - Test completion percentage calculation
    - Test throughput calculation (jobs/second)
    - Test ETA calculation accuracy
    - Test display of active workers and queue depth

  - [ ] 26.6 Write property test for graceful service degradation
    - **Property 32: Graceful Service Degradation**
    - **Validates: Requirements 22.7**
    - Test system continues functioning when external services fail
    - Test fallback mechanisms are used appropriately
    - Use hypothesis to simulate service failure scenarios

  - [ ] 26.7 Write property test for request tracing
    - **Property 33: Request Tracing Completeness**
    - **Validates: Requirements 23.5**
    - Test that all requests get X-Trace-ID headers
    - Test trace ID propagation through logs
    - Use hypothesis to generate request scenarios

  - [ ] 26.8 Write property test for backpressure event logging
    - **Property 35: Backpressure Event Logging**
    - **Validates: Requirements 30.4**
    - Test that sustained backpressure (>30s) logs warnings
    - Test warning includes duration and queue statistics
    - Use hypothesis to generate backpressure scenarios

  - [ ] 26.9 Write property test for database schema integrity
    - **Property 31: Database Schema Integrity**
    - **Validates: Requirements 21.1-21.11**
    - Test that all required tables exist
    - Test that all required indexes exist
    - Test compound and single indexes

- [ ] 27. CI/CD pipeline implementation
  - [ ] 27.1 Set up GitHub Actions workflow
    - Create CI workflow for automated testing
    - Add linting and code quality checks (pylint, mypy, black)
    - Add test coverage reporting
    - Add security scanning (bandit, safety)
    - Configure automated test execution on PR
    - _Requirements: 8.7, 26.1, 26.2, 26.3, 26.4, 26.5, 26.6_

  - [ ] 27.2 Create CD pipeline for deployment
    - Add Docker image building and pushing
    - Configure deployment to staging environment
    - Add smoke tests for deployed application
    - Implement blue-green deployment strategy
    - Add rollback automation on deployment failure
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6_

- [ ] 28. Final integration and system verification
  - [ ] 28.1 Run complete system integration test
    - Execute full workflow from job scraping to outreach sending
    - Verify all components interact correctly
    - Test error recovery and resilience
    - Validate metrics collection throughout execution
    - _Requirements: All requirements_

  - [ ] 28.2 Perform production readiness checklist
    - Verify all health checks pass
    - Verify graceful shutdown works correctly
    - Verify metrics and logging are comprehensive
    - Verify database schema and indexes are optimal
    - Verify secrets management is secure
    - Verify Docker container works correctly
    - Verify load testing results are acceptable
    - _Requirements: All requirements_

  - [ ] 28.3 Generate system status report
    - Document current system capabilities
    - List all operational components
    - Document known limitations
    - Create performance benchmark report
    - Document deployment readiness status
    - _Requirements: All requirements_

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property-based tests validate universal correctness properties from the design
- Unit tests and integration tests validate specific examples and workflows
- Checkpoints ensure incremental validation throughout implementation
- Most core components are already implemented (✅ in design), focus is on gaps, testing, and production hardening
- The async pipeline is already operational, tasks focus on enhancing observability and testing
- Email discovery, outreach processing, and AI services are operational, tasks focus on validation and edge case handling
- Database schema exists, tasks focus on index optimization and migration support
- DAG orchestrator is operational, tasks focus on testing and workflow validation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "3.1", "6.1"] },
    { "id": 1, "tasks": ["2.2", "2.3", "3.2", "5.1", "6.2", "9.1", "10.1", "11.1", "12.1", "14.1", "15.1", "15.2", "16.1", "17.1", "19.1", "20.1"] },
    { "id": 2, "tasks": ["2.4", "3.3", "5.2", "5.3", "6.3", "7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "9.2", "10.2", "11.2", "12.2", "14.2", "15.3", "16.2", "17.2", "19.2", "20.2"] },
    { "id": 3, "tasks": ["5.4", "21.1", "21.2", "23.1", "24.1", "24.2", "24.3"] },
    { "id": 4, "tasks": ["22.1", "22.2", "22.3", "22.4", "23.2", "23.3", "26.1", "26.2", "26.3", "26.4", "26.5", "26.6", "26.7", "26.8", "26.9"] },
    { "id": 5, "tasks": ["27.1", "27.2"] },
    { "id": 6, "tasks": ["28.1", "28.2", "28.3"] }
  ]
}
```
