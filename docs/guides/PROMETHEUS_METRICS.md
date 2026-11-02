# Prometheus Metrics Export

This document describes the Prometheus metrics export functionality added to the NEXUS job acquisition system.

## Overview

The `/metrics` endpoint exposes comprehensive pipeline metrics in Prometheus text format for monitoring and observability. The endpoint is designed to be scraped by Prometheus at regular intervals (typically 15-60 seconds).

## Endpoint

**URL:** `GET /metrics`

**Response Format:** `text/plain; version=0.0.4` (Prometheus exposition format)

**Requirements Coverage:**
- Requirement 6.1: Job processing metrics (throughput, latency)
- Requirement 6.2: Queue metrics (size, backpressure events)
- Requirement 6.3: Worker metrics (utilization, active count)
- Requirement 6.4: API metrics (rate limiter waits)
- Requirement 6.5: Error metrics (retry attempts, failure types)
- Requirement 9.1: DAG-based workflow metrics

## Exported Metrics

### Job Processing Metrics (Requirement 6.1)

These metrics track the overall job processing pipeline performance:

| Metric | Type | Description |
|--------|------|-------------|
| `pipeline_jobs_total` | counter | Total number of jobs processed |
| `pipeline_jobs_success` | counter | Number of successfully processed jobs |
| `pipeline_jobs_failed` | counter | Number of failed jobs |
| `pipeline_job_success_rate` | gauge | Job success rate (0-1) |
| `pipeline_processing_time_min_ms` | gauge | Minimum processing time in milliseconds |
| `pipeline_processing_time_avg_ms` | gauge | Average processing time in milliseconds |
| `pipeline_processing_time_max_ms` | gauge | Maximum processing time in milliseconds |
| `pipeline_processing_time_p50_ms` | gauge | Median (p50) processing time |
| `pipeline_processing_time_p95_ms` | gauge | 95th percentile processing time |
| `pipeline_processing_time_p99_ms` | gauge | 99th percentile processing time |
| `pipeline_throughput_jobs_per_sec` | gauge | Jobs processed per second |
| `pipeline_elapsed_seconds` | counter | Time since pipeline started |

### Queue Metrics (Requirement 6.2)

These metrics track the bounded queue state and backpressure:

| Metric | Type | Description |
|--------|------|-------------|
| `pipeline_queue_size_current` | gauge | Current queue size |
| `pipeline_queue_size_max` | gauge | Maximum queue size reached |
| `pipeline_queue_size_avg` | gauge | Average queue size over time |

**Note:** Backpressure events occur when `queue_size_current == queue_size_max` and are logged separately in structured logs.

### Worker Metrics (Requirement 6.3)

These metrics track worker pool utilization and performance:

| Metric | Type | Description |
|--------|------|-------------|
| `pipeline_workers_active` | gauge | Currently active workers |
| `pipeline_workers_total` | gauge | Total number of workers |
| `pipeline_worker_utilization` | gauge | Worker utilization rate (0-1) |
| `pipeline_worker_idle_rate` | gauge | Worker idle rate (0-1) |

**Utilization Calculation:**
```
utilization = active_workers / total_workers
idle_rate = 1.0 - utilization
```

### API Metrics (Requirement 6.4)

These metrics track rate limiting and API call performance:

#### Semaphore Contention
| Metric | Type | Description |
|--------|------|-------------|
| `pipeline_semaphore_available` | gauge | Available semaphore slots |
| `pipeline_semaphore_total` | gauge | Total semaphore slots |
| `pipeline_semaphore_contention` | gauge | Semaphore contention rate (0-1) |

**Contention Calculation:**
```
contention = 1.0 - (available / total)
```

#### Per-Service API Latency

For each service type (llm, email, scraping, database):

| Metric | Type | Description |
|--------|------|-------------|
| `pipeline_api_latency_count_{service}` | counter | Number of API calls |
| `pipeline_api_latency_total_ms_{service}` | counter | Total API latency in milliseconds |
| `pipeline_api_latency_avg_ms_{service}` | gauge | Average API latency |
| `pipeline_api_latency_min_ms_{service}` | gauge | Minimum API latency |
| `pipeline_api_latency_max_ms_{service}` | gauge | Maximum API latency |

**Example:**
```
pipeline_api_latency_count_llm 150
pipeline_api_latency_avg_ms_llm 180.5
pipeline_api_latency_max_ms_llm 450.2
```

### Error Metrics (Requirement 6.5)

These metrics track retry attempts and failure types:

For each error type (e.g., TimeoutError, ConnectionError):

| Metric | Type | Description |
|--------|------|-------------|
| `pipeline_retry_count_{error_type}` | counter | Number of retry attempts |
| `pipeline_retry_success_{error_type}` | counter | Successful retries |
| `pipeline_retry_failure_{error_type}` | counter | Failed retries |
| `pipeline_retry_success_rate_{error_type}` | gauge | Retry success rate (0-1) |

**Example:**
```
pipeline_retry_count_timeouterror 5
pipeline_retry_success_timeouterror 4
pipeline_retry_failure_timeouterror 1
pipeline_retry_success_rate_timeouterror 0.8
```

**Note:** Error types are sanitized for Prometheus (spaces and dots replaced with underscores, lowercased).

## Usage

### Manual Testing

```bash
# Start the FastAPI server
uvicorn main:app --reload

# Query the metrics endpoint
curl http://localhost:8000/metrics

# Or visit in browser
open http://localhost:8000/metrics
```

### Prometheus Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'nexus-job-pipeline'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Example queries for Grafana panels:

**Throughput:**
```promql
rate(pipeline_jobs_total[5m])
```

**Success Rate:**
```promql
pipeline_job_success_rate
```

**P95 Latency:**
```promql
pipeline_processing_time_p95_ms
```

**Worker Utilization:**
```promql
pipeline_worker_utilization
```

**API Latency (LLM):**
```promql
pipeline_api_latency_avg_ms_llm
```

**Retry Rate by Error Type:**
```promql
sum(rate(pipeline_retry_count_timeouterror[5m]))
```

## Implementation Details

### MetricsCollector

The `MetricsCollector` class (`src/async_pipeline/metrics.py`) is the core metrics collection system:

- **Thread-safe:** Uses locks for concurrent access
- **Time-series storage:** Maintains queue snapshots for time-series data
- **Percentile calculation:** Calculates p50, p95, p99 latencies
- **Automatic aggregation:** Aggregates metrics per service and error type

### Pipeline Integration

The `AsyncJobPipeline` class exposes metrics via:

```python
pipeline = AsyncJobPipeline(config)
snapshot = pipeline.get_metrics_snapshot()
prometheus_text = snapshot.to_prometheus_format()
```

The `/metrics` endpoint in `main.py` calls this method to generate the response.

### Metric Types

- **Counter:** Monotonically increasing value (jobs_total, retry_count)
- **Gauge:** Value that can increase or decrease (queue_size, utilization)
- **Histogram:** Distribution of values (not used, percentiles calculated manually)

## Monitoring Best Practices

1. **Scrape Interval:** Use 15-30 second intervals for real-time monitoring
2. **Retention:** Store at least 15 days of metrics for trend analysis
3. **Alerting Rules:**
   - Alert if `pipeline_job_success_rate < 0.9` for 5 minutes
   - Alert if `pipeline_processing_time_p95_ms > 5000` for 5 minutes
   - Alert if `pipeline_worker_utilization > 0.95` for 10 minutes
   - Alert if `pipeline_queue_size_current == pipeline_queue_size_max` for 5 minutes

4. **Dashboard Panels:**
   - Throughput (jobs/sec) over time
   - Success rate over time
   - P95 latency over time
   - Worker utilization over time
   - Queue depth over time
   - API latency per service
   - Retry rate by error type

## Testing

### Unit Test

Run the unit test to verify metric generation:

```bash
python test_metrics_endpoint.py
```

This test:
1. Creates a MetricsCollector with sample data
2. Generates Prometheus format output
3. Verifies all required metrics are present

### Integration Test

Run the integration test to verify the API endpoint:

```bash
# Start server first
uvicorn main:app --reload

# In another terminal
python test_metrics_api_endpoint.py
```

This test:
1. Connects to the running FastAPI server
2. Calls the `/metrics` endpoint
3. Verifies the response format and content

## Example Output

```
# HELP pipeline_jobs_total Total number of jobs processed
# TYPE pipeline_jobs_total counter
pipeline_jobs_total 1523

# HELP pipeline_jobs_success Number of successful jobs
# TYPE pipeline_jobs_success counter
pipeline_jobs_success 1498

# HELP pipeline_job_success_rate Job success rate (0-1)
# TYPE pipeline_job_success_rate gauge
pipeline_job_success_rate 0.9836

# HELP pipeline_processing_time_avg_ms Average processing time in milliseconds
# TYPE pipeline_processing_time_avg_ms gauge
pipeline_processing_time_avg_ms 2341.5

# HELP pipeline_throughput_jobs_per_sec Jobs processed per second
# TYPE pipeline_throughput_jobs_per_sec gauge
pipeline_throughput_jobs_per_sec 12.5

# HELP pipeline_queue_size_current Current queue size
# TYPE pipeline_queue_size_current gauge
pipeline_queue_size_current 42

# HELP pipeline_workers_active Currently active workers
# TYPE pipeline_workers_active gauge
pipeline_workers_active 5

# HELP pipeline_worker_utilization Worker utilization rate (0-1)
# TYPE pipeline_worker_utilization gauge
pipeline_worker_utilization 1.0000
```

## Related Documentation

- [Design Document](.kiro/specs/system-architecture/design.md)
- [Requirements Document](.kiro/specs/system-architecture/requirements.md)
- [Async Pipeline Documentation](ASYNC_PIPELINE_QUICK_START.md)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Prometheus Exposition Format](https://prometheus.io/docs/instrumenting/exposition_formats/)

## Troubleshooting

### Metrics endpoint returns empty/minimal data

**Cause:** The async pipeline hasn't been initialized or hasn't processed any jobs yet.

**Solution:** 
1. Run a job processing request first: `POST /run-query-async`
2. Then check metrics: `GET /metrics`

### Metrics show zero values

**Cause:** The pipeline has been initialized but not run.

**Solution:** Process some jobs to populate metrics.

### "Async pipeline not initialized" message

**Cause:** The AsyncJobPipeline is not available (likely missing `aiosqlite`).

**Solution:**
```bash
pip install aiosqlite
# Restart the server
```

### High retry rates

**Cause:** External APIs are failing or timing out frequently.

**Solution:**
1. Check API connectivity
2. Increase timeout values in config
3. Review API rate limits

### Queue always at max size

**Cause:** Workers are slower than job production (backpressure).

**Solution:**
1. Increase worker count
2. Increase queue size
3. Optimize job processing logic
4. Check for API bottlenecks
