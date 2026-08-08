# Requirements Document

## Introduction

NEXUS is a fully automated job acquisition pipeline that orchestrates job scraping, job description analysis, resume tailoring, contact discovery, personalized outreach, email sending, and feedback learning. This document defines the formal requirements derived from the technical design to ensure correct implementation of all system components.

## Glossary

- **NEXUS**: The complete job acquisition system
- **AsyncJobPipeline**: High-performance concurrent job processing system with producer-consumer pattern
- **AsyncJobProducer**: Component that streams jobs from database in chunks
- **BoundedQueue**: Async queue with backpressure mechanism
- **AsyncWorkerPool**: Pool of N concurrent workers with semaphore-based rate limiting
- **AsyncJobProcessor**: Core processing logic for a single job
- **RetryManager**: Centralized retry logic with exponential backoff
- **RateLimiter**: Token bucket rate limiter for external APIs
- **MetricsCollector**: Component that tracks pipeline performance metrics
- **ProgressTracker**: Component that provides real-time progress visualization
- **DAGOrchestrator**: Component that manages workflow execution using directed acyclic graph
- **StateGraph**: Graph-based workflow representation
- **CompiledGraph**: Optimized graph ready for execution
- **JobScraper**: Component that fetches job listings from external sources
- **AIService**: Component that provides LLM capabilities
- **EmailEngine**: Component that discovers and verifies contact emails
- **ResumeEngine**: Component that tailors resumes to job descriptions
- **PersonalizationEngine**: Component that generates personalized outreach content
- **OutreachProcessor**: Component that orchestrates email sending
- **ContactIntelligence**: Component that ranks and prioritizes contacts
- **FeedbackLoop**: Component that learns from outreach results

## Requirements

### Requirement 1: Async Pipeline Core Architecture

**User Story:** As a system operator, I want the job processing pipeline to use streaming and bounded queues, so that memory usage remains constant regardless of job count.

#### Acceptance Criteria

1. THE AsyncJobProducer SHALL stream jobs from the database in configurable chunks
2. WHEN the AsyncJobProducer streams jobs, THE memory usage SHALL remain O(chunk_size) regardless of total job count
3. THE BoundedQueue SHALL have a configurable maximum size
4. WHEN the BoundedQueue is at maximum capacity, THE AsyncJobProducer SHALL block until space is available
5. WHEN the BoundedQueue is empty, THE AsyncWorkerPool SHALL block until jobs are available
6. THE AsyncJobPipeline SHALL support graceful shutdown via poison pill pattern

### Requirement 2: Concurrent Job Processing

**User Story:** As a system operator, I want jobs to be processed concurrently by multiple workers, so that throughput is maximized.

#### Acceptance Criteria

1. THE AsyncWorkerPool SHALL support a configurable number of concurrent workers
2. WHEN processing jobs, THE AsyncWorkerPool SHALL use semaphore-based rate limiting
3. THE AsyncWorkerPool SHALL track per-worker statistics including active count and processed count
4. WHEN a worker encounters an error, THE other workers SHALL continue processing, and IF only one worker is running, THE system SHALL automatically restart the failed worker to ensure continuous processing
5. THE AsyncWorkerPool SHALL support graceful shutdown of all workers

### Requirement 3: Job Processing Logic

**User Story:** As a system operator, I want each job to be processed through skill extraction and resume matching, so that job-resume fit is calculated.

#### Acceptance Criteria

1. WHEN processing a job, THE AsyncJobProcessor SHALL extract skills from the job description using an LLM
2. WHEN processing a job, THE AsyncJobProcessor SHALL match the resume to job requirements using an LLM
3. WHEN processing a job, THE AsyncJobProcessor SHALL store the processing result in the database
4. WHERE operations are read-only or simple, THE AsyncJobProcessor SHALL allow shared database sessions, and WHEN operations modify data or are complex, THE AsyncJobProcessor SHALL use per-task database sessions to avoid shared state
5. THE AsyncJobProcessor SHALL include timeout protection for all operations
6. WHEN a processing error occurs and an error result is returned, THE overall job processing SHALL be marked as successful

### Requirement 4: Retry and Error Handling

**User Story:** As a system operator, I want transient failures to be automatically retried with exponential backoff, so that temporary issues don't cause job processing failures.

#### Acceptance Criteria

1. WHEN a transient error occurs, THE RetryManager SHALL retry the operation with exponential backoff
2. THE RetryManager SHALL support a configurable maximum number of retry attempts
3. THE RetryManager SHALL calculate retry delay using the formula: delay = min(base_delay × (exponential_base ^ attempt), max_delay), and WHERE max_delay equals base_delay, THE delays SHALL remain constant from the first retry
4. THE RetryManager SHALL add jitter to retry delays to prevent thundering herd
5. THE RetryManager SHALL log each retry attempt with structured logging
6. WHEN the maximum retry attempts is reached and actual retry attempts were made, THE RetryManager SHALL return a failure result

### Requirement 5: Rate Limiting

**User Story:** As a system operator, I want external API calls to be rate-limited per API type, so that API quotas are not exceeded.

#### Acceptance Criteria

1. THE RateLimiter SHALL implement the token bucket algorithm
2. THE RateLimiter SHALL support configurable rate limits per API type
3. WHEN a worker requests API access and insufficient tokens are available, THE RateLimiter SHALL block and wait for the next token refill
4. THE RateLimiter SHALL refill tokens at the configured rate
5. THE RateLimiter SHALL support burst capacity for API calls
6. THE RateLimiter SHALL track rate limiter statistics including wait times

### Requirement 6: Observability and Metrics

**User Story:** As a system operator, I want comprehensive metrics and logging, so that I can monitor pipeline health and debug issues.

#### Acceptance Criteria

1. THE MetricsCollector SHALL track job processing metrics including throughput and latency
2. THE MetricsCollector SHALL track queue metrics including size and backpressure events
3. THE MetricsCollector SHALL track worker metrics including utilization and active count
4. THE MetricsCollector SHALL track API metrics including rate limiter waits
5. THE MetricsCollector SHALL track error metrics including retry attempts and failure types
6. THE MetricsCollector SHALL calculate latency percentiles including p50, p95, and p99
7. THE AsyncJobPipeline SHALL use structured logging with correlation IDs for all log entries
8. WHEN logging, THE AsyncJobPipeline SHALL include job_id, worker_id, and status in each log entry

### Requirement 7: Progress Tracking

**User Story:** As a system operator, I want real-time progress visualization, so that I can see pipeline execution status.

#### Acceptance Criteria

1. THE ProgressTracker SHALL display job completion percentage
2. THE ProgressTracker SHALL calculate and display throughput in jobs per second
3. THE ProgressTracker SHALL calculate and display estimated time to completion
4. THE ProgressTracker SHALL display active worker count
5. THE ProgressTracker SHALL display current queue depth
6. THE ProgressTracker SHALL use rich terminal output with progress bars

### Requirement 8: Configuration Management

**User Story:** As a system operator, I want pipeline behavior to be configurable, so that I can tune performance for different environments.

#### Acceptance Criteria

1. THE ProcessorConfig SHALL support configurable worker count
2. THE ProcessorConfig SHALL support configurable queue size
3. THE ProcessorConfig SHALL support configurable rate limits per API type
4. THE ProcessorConfig SHALL support configurable retry parameters including max attempts and backoff multiplier
5. THE ProcessorConfig SHALL support configurable timeout values per operation type
6. THE ProcessorConfig SHALL support configurable database parameters including chunk size and pool size
7. THE ProcessorConfig SHALL validate all configuration values on initialization, and WHERE values pass basic type validation, THE system SHALL allow any numeric values

### Requirement 9: DAG-Based Workflow Orchestration

**User Story:** As a system architect, I want workflows to be represented as directed acyclic graphs, so that complex dependencies can be expressed clearly.

#### Acceptance Criteria

1. THE StateGraph SHALL represent workflows as nodes and edges
2. THE StateGraph SHALL support conditional routing between nodes
3. THE StateGraph SHALL support parallel execution of independent nodes
4. THE CompiledGraph SHALL use topological sorting for execution order
5. WHEN executing a workflow, THE DAGOrchestrator SHALL respect node dependencies
6. WHEN executing parallel nodes, THE DAGOrchestrator SHALL execute them concurrently

### Requirement 10: Job Scraping

**User Story:** As a job seeker, I want jobs to be scraped from multiple platforms, so that I have comprehensive job coverage.

#### Acceptance Criteria

1. THE JobScraper SHALL support scraping from at least 9 different platforms
2. WHEN scraping jobs, THE JobScraper SHALL normalize job data to a common schema
3. WHEN scraping jobs, THE JobScraper SHALL generate a unique job ID for deduplication
4. THE JobScraper SHALL support Cloudflare bypass for anti-bot protection
5. WHEN scraping fails, THE JobScraper SHALL return an empty result without raising exceptions
6. THE JobScraper SHALL store scraped jobs in the database

### Requirement 11: AI-Powered Analysis

**User Story:** As a job seeker, I want AI to analyze job descriptions and match them to my resume, so that I can identify the best opportunities.

#### Acceptance Criteria

1. THE AIService SHALL support multiple LLM backends including Ollama and Gemini
2. THE AIService SHALL implement a cascade fallback chain for LLM calls
3. WHEN an LLM call fails, THE AIService SHALL try the next provider in the cascade, and WHERE the next provider is the same as the current failing provider, THE system SHALL retry the same provider as specified by the cascade order
4. WHEN all LLM providers fail, THE AIService SHALL use keyword-based fallback matching
5. THE AIService SHALL support async LLM calls with timeout protection
6. THE AIService SHALL extract skills from job descriptions
7. THE AIService SHALL calculate job-resume match scores from 0 to 100

### Requirement 12: Email Discovery

**User Story:** As a job seeker, I want to discover hiring manager email addresses, so that I can send personalized outreach.

#### Acceptance Criteria

1. THE EmailEngine SHALL implement a 5-layer discovery pipeline
2. THE EmailEngine SHALL support at least 13 email discovery providers
3. THE EmailEngine SHALL mine email patterns from discovered emails and store them in SQLite
4. THE EmailEngine SHALL generate email candidates from mined patterns
5. THE EmailEngine SHALL verify email candidates using SMTP RCPT TO verification
6. THE EmailEngine SHALL calculate multi-factor confidence scores for discovered emails
7. THE EmailEngine SHALL deduplicate discovered emails before returning results
8. THE EmailEngine SHALL rank discovered emails by confidence score
9. WHEN no API keys are configured, THE EmailEngine SHALL use free fallback methods including DNS MX lookups and web scraping, and WHERE API keys are configured, THE system SHALL allow fallback methods to be used

### Requirement 13: Pattern Mining

**User Story:** As a system operator, I want email patterns to be learned from discovered emails, so that future discovery is more accurate.

#### Acceptance Criteria

1. THE PatternMiner SHALL detect email format patterns using dynamic programming
2. THE PatternMiner SHALL store detected patterns in SQLite with company association
3. WHEN generating email candidates, THE PatternMiner SHALL apply learned patterns to contact names
4. THE PatternMiner SHALL support common patterns including firstname@domain and firstnamelastname@domain
5. THE PatternMiner SHALL persist patterns across system restarts

### Requirement 14: Resume Tailoring

**User Story:** As a job seeker, I want my resume to be tailored to each job description, so that I maximize my chances of getting interviews.

#### Acceptance Criteria

1. WHEN tailoring a resume, THE ResumeEngine SHALL analyze the job description to extract key requirements
2. WHEN tailoring a resume, THE ResumeEngine SHALL optimize resume sections to match job requirements
3. WHEN tailoring a resume, THE ResumeEngine SHALL optimize for ATS keyword matching
4. WHEN tailoring a resume, THE ResumeEngine SHALL generate a PDF version of the tailored resume
5. THE ResumeEngine SHALL store tailored resumes with versioning by job ID

### Requirement 15: Personalized Outreach

**User Story:** As a job seeker, I want personalized outreach emails, so that my applications stand out.

#### Acceptance Criteria

1. WHEN generating outreach, THE PersonalizationEngine SHALL research the target company
2. WHEN generating outreach, THE PersonalizationEngine SHALL research the target contact
3. WHEN generating outreach, THE PersonalizationEngine SHALL generate a personalized hook based on research
4. WHEN generating outreach, THE PersonalizationEngine SHALL compose a complete email with the hook
5. THE PersonalizationEngine SHALL include the tailored resume in the outreach email

### Requirement 16: Outreach Orchestration

**User Story:** As a job seeker, I want outreach to be sent with smart timing and deduplication, so that I don't spam companies.

#### Acceptance Criteria

1. THE OutreachProcessor SHALL use a Trie index for O(k) email deduplication
2. THE OutreachProcessor SHALL use a ContactGraph for O(1) relationship lookups
3. THE OutreachProcessor SHALL use a TaskDAG for workflow scheduling
4. THE OutreachProcessor SHALL support timezone-aware send timing between 09:00 and 11:00 local time
5. THE OutreachProcessor SHALL prefer Tuesday through Thursday for sending
6. THE OutreachProcessor SHALL implement rate limiting of 50 emails per day globally
7. THE OutreachProcessor SHALL implement rate limiting of 3 emails per week per domain
8. THE OutreachProcessor SHALL implement rate limiting of 1 email per week per contact
9. THE OutreachProcessor SHALL support A/B testing of subject lines
10. THE OutreachProcessor SHALL store all sent emails in the database

### Requirement 17: Reply Detection

**User Story:** As a job seeker, I want replies to my outreach to be detected automatically, so that I can track engagement.

#### Acceptance Criteria

1. THE ReplyDetector SHALL poll IMAP for new replies at 30-minute intervals
2. WHEN a reply is detected, THE ReplyDetector SHALL update the outreach record status
3. THE ReplyDetector SHALL classify reply sentiment as positive, negative, neutral, referral, or unsubscribe
4. WHEN an unsubscribe reply is detected, THE ReplyDetector SHALL mark the contact as do-not-contact

### Requirement 18: Follow-Up Scheduling

**User Story:** As a job seeker, I want automatic follow-ups to be scheduled for non-responders, so that I maximize response rates.

#### Acceptance Criteria

1. THE FollowUpScheduler SHALL schedule first follow-up on day 5 after initial send
2. THE FollowUpScheduler SHALL schedule second follow-up on day 12 after initial send
3. THE FollowUpScheduler SHALL schedule third follow-up on day 21 after initial send
4. WHEN a reply is received, THE FollowUpScheduler SHALL cancel all pending follow-ups
5. THE FollowUpScheduler SHALL generate different follow-up content for each attempt

### Requirement 19: Contact Ranking

**User Story:** As a job seeker, I want contacts to be ranked by likelihood of response, so that I prioritize outreach effectively.

#### Acceptance Criteria

1. THE ContactIntelligence SHALL build a ContactGraph of relationships between contacts
2. THE ContactIntelligence SHALL use PageRank-style algorithm for contact ranking
3. THE ContactIntelligence SHALL use role hierarchy for contact prioritization
4. THE ContactIntelligence SHALL prioritize hiring managers over recruiters
5. THE ContactIntelligence SHALL prioritize engineering managers for technical roles

### Requirement 20: Feedback Learning

**User Story:** As a system operator, I want the system to learn from outreach results, so that performance improves over time.

#### Acceptance Criteria

1. THE FeedbackLoop SHALL collect metrics on outreach performance nightly
2. THE FeedbackLoop SHALL mine patterns from successful and unsuccessful outreach
3. THE FeedbackLoop SHALL adaptively optimize outreach strategies based on patterns
4. THE FeedbackLoop SHALL generate daily digest reports with performance insights
5. THE FeedbackLoop SHALL track metrics including open rate, reply rate, and positive reply rate

### Requirement 21: Database Schema

**User Story:** As a system operator, I want a well-structured database schema, so that data is stored consistently and efficiently.

#### Acceptance Criteria

1. THE Database SHALL include a jobs table for scraped job listings
2. THE Database SHALL include an applications table for job matching results
3. THE Database SHALL include a resumes table for resume versions
4. THE Database SHALL include a contacts table for discovered contacts
5. THE Database SHALL include an outreach_records table for email lifecycle tracking
6. THE Database SHALL include a processing_results table for async pipeline results
7. THE Database SHALL include a pipeline_metrics table for performance metrics
8. THE Database SHALL create compound indexes on jobs(company, fetched_at)
9. THE Database SHALL create compound indexes on contacts(email, company)
10. THE Database SHALL create compound indexes on outreach_records(job_id, contact_id)
11. THE Database SHALL create indexes on applications(match_score)

### Requirement 22: External Service Integration

**User Story:** As a system operator, I want the system to integrate with external services, so that functionality can be extended.

#### Acceptance Criteria

1. THE NEXUS SHALL integrate with Ollama for local LLM processing
2. THE NEXUS SHALL integrate with Google Gemini for cloud LLM processing as fallback
3. THE NEXUS SHALL integrate with Gmail SMTP for email sending
4. THE NEXUS SHALL integrate with GitHub API for commit email mining
5. THE NEXUS SHALL integrate with Cloudflare for browser rendering
6. THE NEXUS SHALL integrate with Google Sheets API for data export
7. WHEN external service integration fails, THE NEXUS SHALL gracefully degrade functionality

### Requirement 23: REST API

**User Story:** As an API consumer, I want REST endpoints for pipeline execution, so that I can trigger jobs programmatically.

#### Acceptance Criteria

1. THE REST API SHALL provide a POST endpoint for async job pipeline execution
2. WHEN receiving a pipeline execution request, THE REST API SHALL validate request parameters
3. WHEN executing a pipeline, THE REST API SHALL return processing statistics in the response
4. THE REST API SHALL include CORS middleware for cross-origin requests
5. THE REST API SHALL include request tracing with X-Trace-ID headers
6. THE REST API SHALL provide health check endpoints

### Requirement 24: Graceful Shutdown

**User Story:** As a system operator, I want graceful shutdown, so that in-flight jobs are not lost during deployment.

#### Acceptance Criteria

1. WHEN SIGTERM is received, THE AsyncJobPipeline SHALL stop accepting new jobs
2. WHEN SIGTERM is received, THE AsyncJobPipeline SHALL wait for in-flight jobs to complete
3. WHEN SIGINT is received, THE AsyncJobPipeline SHALL stop accepting new jobs
4. WHEN SIGINT is received, THE AsyncJobPipeline SHALL wait for in-flight jobs to complete
5. THE AsyncJobPipeline SHALL support a configurable shutdown timeout
6. WHEN the shutdown timeout is exceeded, THE AsyncJobPipeline SHALL forcefully terminate remaining jobs

### Requirement 25: Structured Logging

**User Story:** As a system operator, I want structured logging, so that I can trace requests and debug issues.

#### Acceptance Criteria

1. THE NEXUS SHALL use structured logging throughout all components
2. THE NEXUS SHALL include correlation_id in all log entries for request tracing
3. THE NEXUS SHALL include job_id in all job-related log entries
4. THE NEXUS SHALL include worker_id in all worker-related log entries
5. THE NEXUS SHALL include status in all processing log entries
6. THE NEXUS SHALL include processing_time_ms in completed job log entries
7. THE NEXUS SHALL rotate log files at 5MB with 5 backup files

### Requirement 26: Configuration Validation

**User Story:** As a system operator, I want configuration to be validated on startup, so that misconfigurations are caught early.

#### Acceptance Criteria

1. THE ProcessorConfig SHALL validate that worker_count is positive
2. THE ProcessorConfig SHALL validate that queue_size is positive
3. THE ProcessorConfig SHALL validate that rate_limits are positive
4. THE ProcessorConfig SHALL validate that timeout values are positive
5. THE ProcessorConfig SHALL validate that retry parameters are positive
6. WHEN configuration validation fails, THE ProcessorConfig SHALL raise a descriptive error

### Requirement 27: Memory Efficiency

**User Story:** As a system operator, I want the pipeline to maintain constant memory usage, so that it can scale to millions of jobs.

#### Acceptance Criteria

1. THE AsyncJobPipeline SHALL maintain O(1) memory usage regardless of total job count
2. THE AsyncJobProducer SHALL load jobs in chunks and discard them after yielding
3. THE BoundedQueue SHALL never exceed the configured maximum size
4. THE AsyncJobPipeline SHALL not accumulate results in memory during processing
5. WHEN processing 1 million jobs, THE memory usage SHALL remain within O(queue_size + chunk_size)

### Requirement 28: Throughput Optimization

**User Story:** As a system operator, I want high throughput, so that large job batches complete quickly.

#### Acceptance Criteria

1. THE AsyncJobPipeline SHALL scale throughput linearly with worker count up to external API bottlenecks
2. THE AsyncJobPipeline SHALL achieve at least 10 jobs per second with 5 workers
3. THE AsyncJobPipeline SHALL minimize worker idle time through queue pre-filling
4. THE AsyncWorkerPool SHALL process jobs concurrently without blocking each other
5. THE RateLimiter SHALL allow burst capacity for improved throughput

### Requirement 29: Error Isolation

**User Story:** As a system operator, I want job failures to be isolated, so that one bad job doesn't crash the entire pipeline.

#### Acceptance Criteria

1. WHEN a job processing error occurs, THE error SHALL be isolated to that job only
2. WHEN a job fails, THE other workers SHALL continue processing remaining jobs
3. WHEN a job fails, THE failure SHALL be logged with full error details
4. WHEN a job fails, THE failure result SHALL be stored in the database
5. THE AsyncJobPipeline SHALL never propagate exceptions from individual jobs to the main pipeline

### Requirement 30: Backpressure Management

**User Story:** As a system operator, I want automatic backpressure, so that the producer doesn't overwhelm the workers.

#### Acceptance Criteria

1. WHEN the BoundedQueue is full, THE AsyncJobProducer SHALL block until space becomes available
2. WHEN the BoundedQueue is empty, THE AsyncWorkerPool SHALL block until jobs become available
3. THE BoundedQueue SHALL track backpressure events in metrics
4. THE BoundedQueue SHALL log warnings when backpressure is sustained for over 30 seconds
5. THE queue size SHALL be tunable to balance memory usage and throughput
