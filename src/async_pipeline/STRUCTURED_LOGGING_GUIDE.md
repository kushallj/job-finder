# Structured Logging Guide

## Overview

The async job pipeline uses **structlog** for structured logging with JSON formatting. This provides:

- **Structured log entries** with consistent fields across all components
- **Correlation IDs** to trace individual jobs through the entire pipeline
- **Flexible output formats**: JSON for production, human-readable for development
- **Configurable log levels**: INFO for lifecycle, WARNING for retries, ERROR for failures
- **Rich context**: Every log entry includes job_id, status, timing, and error details

## Configuration

### Environment-Based Configuration

The logging system automatically configures itself based on environment variables:

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export LOG_LEVEL=INFO

# Set environment (production uses JSON, development uses colored console)
export ENVIRONMENT=production  # or "development"
```

### Manual Configuration

You can manually configure logging in your application:

```python
from src.async_pipeline import configure_structured_logging

# For production (JSON output)
configure_structured_logging(
    log_level="INFO",
    json_format=True,
    include_timestamp=True,
)

# For development (colored console output)
configure_structured_logging(
    log_level="DEBUG",
    json_format=False,
    include_timestamp=True,
)
```

## Using Structured Logging

### Get a Logger

```python
from src.async_pipeline import get_logger

logger = get_logger(__name__)
```

### Log with Structured Fields

Instead of string formatting, pass fields as keyword arguments:

```python
# ✅ Good: Structured logging
logger.info(
    "job_processing_started",
    job_id=job.job_id,
    company=job.company,
    title=job.title,
    status="PROCESSING",
    attempt_count=1,
)

# ❌ Bad: String formatting
logger.info(f"Processing job {job.job_id} at {job.company}")
```

## Correlation IDs

Correlation IDs allow you to trace a single job through the entire pipeline across all log entries.

### Setting Correlation ID

```python
from src.async_pipeline import set_correlation_id, generate_correlation_id

# Generate and set correlation ID for a job
correlation_id = f"job-{job.job_id}-{generate_correlation_id()[:8]}"
set_correlation_id(correlation_id)

# Now all log entries will include this correlation_id
logger.info("processing_started", job_id=job.job_id)
```

### Getting Correlation ID

```python
from src.async_pipeline import get_correlation_id

# Retrieve the current correlation ID
corr_id = get_correlation_id()
```

### Clearing Correlation ID

```python
from src.async_pipeline import clear_correlation_id

# Clean up after job processing
clear_correlation_id()
```

### Correlation ID in Async Context

Correlation IDs are stored in context variables, so they automatically persist across async operations:

```python
async def process_job(job):
    # Set correlation ID
    set_correlation_id(f"job-{job.job_id}")
    
    # Call async operations - correlation ID is preserved
    await extract_skills(job)
    await match_resume(job)
    await store_result(job)
    
    # Clear when done
    clear_correlation_id()
```

## Log Entry Format

### Standard Fields

Every log entry should include these standard fields where applicable:

- `event`: Event name (e.g., "job_processing_started", "job_completed", "job_failed")
- `job_id`: Unique job identifier
- `status`: Job status (PENDING, PROCESSING, COMPLETED, FAILED, RETRYING)
- `correlation_id`: Correlation ID for tracing
- `processing_time_ms`: Time taken in milliseconds
- `attempt_count`: Number of attempts made

### Job Lifecycle Logs (INFO Level)

```python
# Job started
logger.info(
    "job_processing_started",
    job_id=job.job_id,
    company=job.company,
    title=job.title,
    status=JobStatus.PROCESSING.value,
    attempt_count=1,
    correlation_id=correlation_id,
)

# Job completed
logger.info(
    "job_completed",
    job_id=job.job_id,
    status=JobStatus.COMPLETED.value,
    processing_time_ms=123.45,
    attempt_count=1,
    correlation_id=correlation_id,
)
```

### Retry Logs (WARNING Level)

```python
logger.warning(
    "job_retry",
    worker_id=worker_id,
    job_id=job.job_id,
    status=JobStatus.RETRYING.value,
    attempt_count=2,
    max_retries=3,
    delay_seconds=2.0,
    error_type="TimeoutError",
    error_message="LLM API timed out",
    correlation_id=correlation_id,
)
```

### Error Logs (ERROR Level)

```python
import traceback

try:
    # ... processing code ...
    pass
except Exception as e:
    error_traceback = traceback.format_exc()
    
    logger.error(
        "job_failed",
        job_id=job.job_id,
        status=JobStatus.FAILED.value,
        error_type=type(e).__name__,
        error_message=str(e),
        traceback=error_traceback,
        processing_time_ms=50.0,
        attempt_count=3,
        correlation_id=correlation_id,
    )
```

## Example Log Entries

### JSON Format (Production)

```json
{
  "event": "job_processing_started",
  "job_id": "job-12345",
  "company": "Tech Corp",
  "title": "Software Engineer",
  "status": "PROCESSING",
  "attempt_count": 1,
  "correlation_id": "job-12345-a7b3c9d2",
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "info",
  "logger": "src.async_pipeline.processor"
}

{
  "event": "job_completed",
  "job_id": "job-12345",
  "status": "COMPLETED",
  "processing_time_ms": 2345.67,
  "attempt_count": 1,
  "correlation_id": "job-12345-a7b3c9d2",
  "timestamp": "2024-01-15T10:30:47.469123",
  "level": "info",
  "logger": "src.async_pipeline.processor"
}
```

### Console Format (Development)

```
2024-01-15 10:30:45 [info     ] job_processing_started    job_id=job-12345 company=Tech Corp title=Software Engineer status=PROCESSING attempt_count=1 correlation_id=job-12345-a7b3c9d2
2024-01-15 10:30:47 [info     ] job_completed             job_id=job-12345 status=COMPLETED processing_time_ms=2345.67 attempt_count=1 correlation_id=job-12345-a7b3c9d2
```

## Querying Logs

### Find All Logs for a Job

Using `jq` with JSON logs:

```bash
# Find all logs for a specific job
cat logs/pipeline.log | jq 'select(.job_id == "job-12345")'

# Find all logs with a correlation ID
cat logs/pipeline.log | jq 'select(.correlation_id == "job-12345-a7b3c9d2")'
```

### Find Failed Jobs

```bash
# Find all failed jobs
cat logs/pipeline.log | jq 'select(.status == "FAILED")'

# Count failures by error type
cat logs/pipeline.log | jq 'select(.status == "FAILED") | .error_type' | sort | uniq -c
```

### Find Retried Jobs

```bash
# Find all retry events
cat logs/pipeline.log | jq 'select(.event == "job_retry")'

# Find jobs that required retries
cat logs/pipeline.log | jq 'select(.attempt_count > 1)'
```

## Best Practices

### 1. Always Use Structured Fields

```python
# ✅ Good
logger.info("user_action", user_id=user.id, action="login", status="success")

# ❌ Bad
logger.info(f"User {user.id} logged in successfully")
```

### 2. Include Correlation IDs for Tracing

```python
# ✅ Good
set_correlation_id(f"job-{job.job_id}")
logger.info("processing", job_id=job.job_id, correlation_id=get_correlation_id())

# ❌ Bad
logger.info("processing", job_id=job.job_id)  # Missing correlation_id
```

### 3. Use Consistent Event Names

```python
# ✅ Good: Descriptive, consistent naming
logger.info("job_processing_started", ...)
logger.info("job_completed", ...)
logger.warning("job_retry", ...)
logger.error("job_failed", ...)

# ❌ Bad: Inconsistent naming
logger.info("start_job", ...)
logger.info("done", ...)
logger.warning("retry_happening", ...)
```

### 4. Always Include Tracebacks for Errors

```python
import traceback

# ✅ Good
try:
    process_job(job)
except Exception as e:
    logger.error(
        "job_failed",
        job_id=job.job_id,
        error_type=type(e).__name__,
        error_message=str(e),
        traceback=traceback.format_exc(),  # Include full traceback
    )

# ❌ Bad
try:
    process_job(job)
except Exception as e:
    logger.error("job_failed", error=str(e))  # Missing traceback
```

### 5. Use Appropriate Log Levels

- **INFO**: Job lifecycle events (started, completed, stored)
- **WARNING**: Retries, recoverable errors, timeouts with retry
- **ERROR**: Permanent failures, unrecoverable errors, bugs
- **DEBUG**: Detailed operation info (skill extraction, API calls)

## Integration with Monitoring Tools

### Exporting to Elasticsearch/Logstash

Configure your log shipper (Filebeat, Fluentd, etc.) to parse JSON logs:

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/pipeline/*.log
    json.keys_under_root: true
    json.add_error_key: true
```

### Grafana Dashboards

Query examples for Loki or Elasticsearch:

```promql
# Failed jobs in the last hour
count_over_time({job="pipeline"} | json | status="FAILED" [1h])

# Average processing time by company
avg_over_time({job="pipeline"} | json | event="job_completed" | unwrap processing_time_ms [5m]) by (company)

# Jobs by correlation_id
{job="pipeline"} | json | correlation_id="job-12345-a7b3c9d2"
```

## Troubleshooting

### Logs Not Appearing

1. Check log level: `LOG_LEVEL` environment variable or `configure_structured_logging()`
2. Verify logger is obtained: `logger = get_logger(__name__)`
3. Check output destination: logs go to stdout by default

### Correlation IDs Not Persisting

1. Ensure you're using async context variables correctly
2. Call `set_correlation_id()` at the start of job processing
3. Verify correlation ID is passed through all async calls

### JSON Parsing Errors

1. Ensure `json_format=True` is set for production
2. Check for any print statements mixing with structured logs
3. Verify all logged values are JSON-serializable

## Summary

The structured logging system provides:

✅ **Consistent format** across all components  
✅ **Correlation IDs** for end-to-end tracing  
✅ **JSON output** for production parsing  
✅ **Rich context** (job_id, status, timing, errors)  
✅ **Flexible configuration** (environment-based or manual)  
✅ **Standard log levels** (INFO/WARNING/ERROR)

Use structured logging everywhere in the pipeline for maximum observability and troubleshooting capability.
