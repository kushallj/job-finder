# Metrics Collection Guide

## Overview

The async pipeline includes a comprehensive metrics collection system that tracks all aspects of job processing. Metrics are collected in a structured format suitable for export to monitoring tools like Prometheus, Datadog, or CloudWatch.

## Features

The metrics system tracks:

1. **Job Processing Counts** (Requirement 20.1)
   - Total jobs processed
   - Successful jobs
   - Failed jobs
   - Jobs currently in progress

2. **Processing Time Statistics** (Requirement 20.2)
   - Minimum processing time
   - Average (mean) processing time
   - Maximum processing time
   - Percentiles (p50, p95, p99)

3. **Queue and Worker Metrics** (Requirement 20.3)
   - Current queue size
   - Maximum queue size reached
   - Average queue size over time
   - Active worker count
   - Total worker count
   - Available semaphore slots

4. **API Latency per Service** (Requirement 20.4)
   - LLM service latency (min, max, avg)
   - Email service latency
   - Scraping service latency
   - Database operation latency

5. **Retry Statistics per Error Type** (Requirement 20.5)
   - Number of retries per error type
   - Successful retries
   - Failed retries after exhausting attempts
   - Success rate

## Usage

### Basic Usage

The metrics collector is automatically integrated into the pipeline:

```python
from src.async_pipeline.pipeline import AsyncJobPipeline
from src.async_pipeline.config import ProcessorConfig

# Create pipeline (metrics collector is initialized automatically)
config = ProcessorConfig(worker_count=5, queue_size=100)
pipeline = AsyncJobPipeline(config=config)

# Run pipeline
results = await pipeline.run(query="software engineer")

# Get metrics snapshot
snapshot = pipeline.get_metrics_snapshot()

# Print metrics summary
print(f"Total jobs: {snapshot.jobs_total}")
print(f"Success rate: {snapshot.jobs_success / snapshot.jobs_total * 100:.1f}%")
print(f"Avg processing time: {snapshot.processing_time_avg_ms:.2f}ms")
print(f"Throughput: {snapshot.throughput_jobs_per_sec:.2f} jobs/sec")
```

### Accessing Detailed Metrics

```python
# Get complete metrics snapshot
snapshot = pipeline.get_metrics_snapshot()

# Job metrics
print(f"Jobs processed: {snapshot.jobs_total}")
print(f"Successful: {snapshot.jobs_success}")
print(f"Failed: {snapshot.jobs_failed}")

# Processing time metrics
print(f"Min: {snapshot.processing_time_min_ms}ms")
print(f"Avg: {snapshot.processing_time_avg_ms}ms")
print(f"Max: {snapshot.processing_time_max_ms}ms")
print(f"P50: {snapshot.processing_time_p50_ms}ms")
print(f"P95: {snapshot.processing_time_p95_ms}ms")
print(f"P99: {snapshot.processing_time_p99_ms}ms")

# Queue metrics
print(f"Current queue size: {snapshot.queue_size_current}")
print(f"Max queue size: {snapshot.queue_size_max}")
print(f"Avg queue size: {snapshot.queue_size_avg}")

# Worker metrics
print(f"Active workers: {snapshot.workers_active}/{snapshot.workers_total}")
print(f"Semaphore: {snapshot.semaphore_available}/{snapshot.semaphore_total} available")

# API latencies
print(f"LLM latency: {snapshot.llm_latency}")
print(f"Email latency: {snapshot.email_latency}")
print(f"Scraping latency: {snapshot.scraping_latency}")
print(f"Database latency: {snapshot.database_latency}")

# Retry metrics
print(f"Retry metrics: {snapshot.retry_metrics}")
```

### Exporting Metrics

#### JSON Format

```python
import json

snapshot = pipeline.get_metrics_snapshot()
metrics_json = json.dumps(snapshot.to_dict(), indent=2)
print(metrics_json)
```

#### Prometheus Format

```python
snapshot = pipeline.get_metrics_snapshot()
prometheus_text = snapshot.to_prometheus_format()
print(prometheus_text)

# Example output:
# # HELP pipeline_jobs_total Total number of jobs processed
# # TYPE pipeline_jobs_total counter
# pipeline_jobs_total 1000
# 
# # HELP pipeline_jobs_success Number of successful jobs
# # TYPE pipeline_jobs_success counter
# pipeline_jobs_success 950
# ...
```

### Periodic Metrics Logging

The pipeline automatically logs metrics periodically during execution. You can also log metrics manually:

```python
# Log metrics summary
pipeline.log_metrics_summary()
```

### Queue State History

Get historical queue state data for time-series analysis:

```python
# Get last 100 queue snapshots
collector = pipeline.metrics_collector
history = collector.get_queue_history(limit=100)

for snapshot in history:
    print(f"{snapshot['timestamp']}: queue_size={snapshot['size']}, "
          f"active_workers={snapshot['active_workers']}")
```

### Custom Metrics Collection

You can access the metrics collector directly for custom tracking:

```python
from src.async_pipeline.metrics import MetricsCollector, ServiceType

# Create standalone collector
collector = MetricsCollector(
    semaphore_total=10,
    workers_total=5
)

# Track job lifecycle
collector.record_job_start("job-123")
# ... process job ...
collector.record_job_success("job-123", duration_ms=250.5)

# Track API latencies
collector.record_api_latency(ServiceType.LLM, duration_ms=180.2)

# Track retries
collector.record_retry_attempt("TimeoutError")
collector.record_retry_success("TimeoutError")

# Track queue state
collector.record_queue_state(
    size=15,
    active_workers=3,
    semaphore_available=7
)

# Get snapshot
snapshot = collector.get_snapshot()
```

### Using MetricsTimer

For automatically timing operations:

```python
from src.async_pipeline.metrics import MetricsTimer, ServiceType

# Async context manager
async with MetricsTimer(collector, ServiceType.LLM):
    result = await llm_service.call_api()
    # Latency automatically recorded when context exits

# Sync context manager
with MetricsTimer(collector, ServiceType.DATABASE):
    result = db.query()
    # Latency automatically recorded
```

## Monitoring Integration

### Prometheus

Expose metrics via HTTP endpoint:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/metrics")
async def metrics():
    snapshot = pipeline.get_metrics_snapshot()
    return Response(
        content=snapshot.to_prometheus_format(),
        media_type="text/plain"
    )
```

### Datadog

Send metrics to Datadog:

```python
from datadog import statsd

snapshot = pipeline.get_metrics_snapshot()

# Send metrics
statsd.gauge('pipeline.jobs.total', snapshot.jobs_total)
statsd.gauge('pipeline.jobs.success', snapshot.jobs_success)
statsd.gauge('pipeline.jobs.failed', snapshot.jobs_failed)
statsd.gauge('pipeline.processing_time.avg', snapshot.processing_time_avg_ms)
statsd.gauge('pipeline.queue.size', snapshot.queue_size_current)
statsd.gauge('pipeline.workers.active', snapshot.workers_active)
```

### CloudWatch

Send metrics to AWS CloudWatch:

```python
import boto3

cloudwatch = boto3.client('cloudwatch')
snapshot = pipeline.get_metrics_snapshot()

cloudwatch.put_metric_data(
    Namespace='AsyncPipeline',
    MetricData=[
        {
            'MetricName': 'JobsTotal',
            'Value': snapshot.jobs_total,
            'Unit': 'Count'
        },
        {
            'MetricName': 'JobsSuccess',
            'Value': snapshot.jobs_success,
            'Unit': 'Count'
        },
        {
            'MetricName': 'ProcessingTimeAvg',
            'Value': snapshot.processing_time_avg_ms,
            'Unit': 'Milliseconds'
        },
        # ... more metrics
    ]
)
```

## Metrics Reference

### MetricsSnapshot Fields

| Field | Type | Description |
|-------|------|-------------|
| `jobs_total` | int | Total jobs processed |
| `jobs_success` | int | Successfully completed jobs |
| `jobs_failed` | int | Failed jobs |
| `processing_time_min_ms` | float | Minimum processing time |
| `processing_time_avg_ms` | float | Average processing time |
| `processing_time_max_ms` | float | Maximum processing time |
| `processing_time_p50_ms` | float | 50th percentile (median) |
| `processing_time_p95_ms` | float | 95th percentile |
| `processing_time_p99_ms` | float | 99th percentile |
| `queue_size_current` | int | Current queue size |
| `queue_size_max` | int | Maximum queue size reached |
| `queue_size_avg` | float | Average queue size |
| `workers_active` | int | Currently active workers |
| `workers_total` | int | Total worker count |
| `semaphore_available` | int | Available semaphore slots |
| `semaphore_total` | int | Total semaphore slots |
| `llm_latency` | dict | LLM API latency stats |
| `email_latency` | dict | Email API latency stats |
| `scraping_latency` | dict | Scraping API latency stats |
| `database_latency` | dict | Database operation latency stats |
| `retry_metrics` | dict | Retry statistics per error type |
| `elapsed_seconds` | float | Total elapsed time |
| `throughput_jobs_per_sec` | float | Jobs processed per second |

### Latency Metrics Format

```json
{
  "count": 150,
  "total_ms": 27000.0,
  "min_ms": 50.0,
  "max_ms": 500.0,
  "avg_ms": 180.0
}
```

### Retry Metrics Format

```json
{
  "TimeoutError": {
    "retry_count": 25,
    "success_after_retry": 20,
    "failed_after_retry": 5,
    "success_rate": 0.8
  },
  "ClientError": {
    "retry_count": 10,
    "success_after_retry": 8,
    "failed_after_retry": 2,
    "success_rate": 0.8
  }
}
```

## Best Practices

1. **Regular Snapshots**: Take metrics snapshots at regular intervals (e.g., every minute) for trend analysis

2. **Alert Thresholds**: Set up alerts based on:
   - High failure rate (> 10%)
   - High queue size (> 80% of max)
   - Low throughput (< target)
   - High processing times (p95 > threshold)
   - High retry rates

3. **Performance Monitoring**: Track these key metrics:
   - Throughput (jobs/sec)
   - P95 processing time
   - Queue size trend
   - Worker utilization

4. **Capacity Planning**: Use metrics to:
   - Determine optimal worker count
   - Adjust queue size
   - Tune rate limits
   - Scale infrastructure

## Thread Safety

The `MetricsCollector` is thread-safe and can be used from multiple threads/workers concurrently. All operations use locks to ensure data consistency.

## Performance Impact

The metrics collection system has minimal performance impact:
- Lock contention is minimized by using separate locks for different metric types
- Queue history is limited to last 1000 snapshots to prevent memory growth
- Percentile calculations are done only when snapshot is requested, not on every update

## Testing

See `tests/test_metrics.py` for comprehensive test coverage of the metrics system.
