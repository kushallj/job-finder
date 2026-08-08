# Async Pipeline Operations Guide

## Table of Contents

1. [Overview](#overview)
2. [Deployment](#deployment)
3. [Configuration](#configuration)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Maintenance](#maintenance)
7. [Performance Tuning](#performance-tuning)
8. [Security](#security)
9. [Backup and Recovery](#backup-and-recovery)
10. [Incident Response](#incident-response)

---

## Overview

### System Architecture

The async job pipeline is a high-performance, fully-async concurrent system that processes job applications through a producer-consumer pattern with bounded queues, async workers, and automatic retry logic.

**Key Components:**
- **Job Producer**: Streams jobs from database in chunks (O(1) memory)
- **Bounded Queue**: Provides natural backpressure (default: 100 jobs)
- **Worker Pool**: N concurrent async workers (configurable, default: 5)
- **Retry Manager**: Exponential backoff for transient failures
- **Rate Limiter**: Token bucket algorithm for API rate control
- **Progress Tracker**: Real-time monitoring and metrics

### Performance Characteristics

- **Throughput**: 3.3+ jobs/second (target: 1000 jobs in <5 minutes)
- **Memory**: O(queue_size + worker_count), not O(total_jobs)
- **Concurrency**: Fully async, non-blocking I/O
- **Reliability**: Automatic retry with exponential backoff

---

## Deployment

### Prerequisites

#### System Requirements

```yaml
Minimum:
  CPU: 2 cores
  RAM: 2GB
  Disk: 10GB
  Python: 3.9+

Recommended:
  CPU: 4+ cores
  RAM: 4GB+
  Disk: 50GB+
  Python: 3.10+
```

#### Required Dependencies

```bash
# Core dependencies
pip install aiosqlite>=0.17.0
pip install httpx>=0.24.0
pip install structlog>=23.1.0
pip install tenacity>=8.2.0
pip install rich>=13.0.0

# Optional monitoring
pip install prometheus-client>=0.16.0
```

### Installation Steps

#### 1. Clone and Install

```bash
# Clone repository
git clone <repository-url>
cd job-finder

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Database Setup

```bash
# Initialize database
python migrate_database.py

# Verify database connection
python -c "from src.async_pipeline.producer import AsyncJobProducer; print('Database OK')"
```

#### 3. Configuration

```bash
# Copy example configuration
cp src/async_pipeline/example_config.json config/pipeline_config.json

# Edit configuration (see Configuration section)
nano config/pipeline_config.json
```

#### 4. Environment Variables

```bash
# Create .env file
cat > .env << EOF
# Database
DATABASE_URL=sqlite+aiosqlite:///./jobs.db

# API Keys
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here

# Email API
EMAIL_API_KEY=your_email_key_here

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Performance
WORKER_COUNT=5
QUEUE_SIZE=100
MAX_CONCURRENT_API_CALLS=3
EOF

# Load environment variables
source .env  # On Windows: use set command or edit manually
```

#### 5. Verification

```bash
# Test basic functionality
python -m src.cli process-async "test query" --workers 2 --log-level DEBUG

# Expected output: Processing starts, jobs processed, summary displayed
```

### Deployment Environments

#### Development Environment

```bash
# Use minimal resources
python -m src.cli process-async "query" \
  --workers 2 \
  --queue-size 50 \
  --log-level DEBUG
```

#### Staging Environment

```bash
# Medium resources, full logging
python -m src.cli process-async "query" \
  --workers 5 \
  --queue-size 100 \
  --log-level INFO
```

#### Production Environment

```bash
# Full resources, optimized settings
python -m src.cli process-async "query" \
  --workers 8 \
  --queue-size 200 \
  --max-concurrent 5 \
  --log-level WARNING
```

### Docker Deployment (Optional)

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "src.cli", "process-async", "software engineer"]
```

```bash
# Build and run
docker build -t job-pipeline .
docker run -e DATABASE_URL="..." -e GEMINI_API_KEY="..." job-pipeline
```

---

## Configuration

### Configuration File Structure

**Location**: `config/pipeline_config.json` or `src/async_pipeline/example_config.json`


```json
{
  "worker_count": 5,
  "queue_size": 100,
  "max_concurrent_api_calls": 3,
  "chunk_size": 100,
  "retry": {
    "max_retries": 3,
    "base_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2.0,
    "jitter": true
  },
  "rate_limits": {
    "llm_api": 10,
    "email_api": 2,
    "scraper": 30
  },
  "timeouts": {
    "llm_api": 30,
    "email_api": 15,
    "scraper": 10,
    "database": 5
  },
  "logging": {
    "level": "INFO",
    "format": "json",
    "file": "logs/pipeline.log"
  }
}
```

### Configuration Parameters

#### Worker Pool Configuration

| Parameter | Description | Default | Range | Impact |
|-----------|-------------|---------|-------|--------|
| `worker_count` | Number of concurrent workers | 5 | 1-20 | Higher = more throughput, more resources |
| `queue_size` | Bounded queue capacity | 100 | 10-500 | Higher = less backpressure, more memory |
| `max_concurrent_api_calls` | Semaphore limit for API calls | 3 | 1-10 | Higher = more API load |

| `chunk_size` | Jobs fetched per database query | 100 | 10-1000 | Higher = fewer queries, more memory |

#### Retry Configuration

| Parameter | Description | Default | Impact |
|-----------|-------------|---------|--------|
| `max_retries` | Maximum retry attempts | 3 | Higher = more resilient, slower on failures |
| `base_delay` | Initial retry delay (seconds) | 1.0 | Higher = slower retry, less API pressure |
| `max_delay` | Maximum retry delay (seconds) | 60.0 | Caps exponential backoff |
| `exponential_base` | Backoff multiplier | 2.0 | Higher = faster backoff growth |
| `jitter` | Add random jitter to backoff | true | Prevents thundering herd |

#### Rate Limit Configuration

| Parameter | Description | Default (req/sec) | Typical Range |
|-----------|-------------|-------------------|---------------|
| `llm_api` | LLM API rate limit | 10 | 5-20 |
| `email_api` | Email API rate limit | 2 | 1-5 |
| `scraper` | Web scraper rate limit | 30 | 10-50 |

#### Timeout Configuration

| Parameter | Description | Default (seconds) | Range |
|-----------|-------------|-------------------|-------|
| `llm_api` | LLM API timeout | 30 | 10-60 |
| `email_api` | Email API timeout | 15 | 5-30 |
| `scraper` | Scraper timeout | 10 | 5-20 |
| `database` | Database query timeout | 5 | 1-10 |

### Configuration Best Practices

#### Small Job Volumes (<100 jobs)
```json
{
  "worker_count": 3,
  "queue_size": 50,
  "max_concurrent_api_calls": 2
}
```

#### Large Job Volumes (1000+ jobs)
```json
{
  "worker_count": 8,
  "queue_size": 200,
  "max_concurrent_api_calls": 5,
  "chunk_size": 200
}
```

#### Rate-Limited APIs
```json
{
  "worker_count": 3,
  "max_concurrent_api_calls": 2,
  "rate_limits": {
    "llm_api": 5,
    "email_api": 1,
    "scraper": 20
  }
}
```

#### High-Reliability Mode
```json
{
  "retry": {
    "max_retries": 5,
    "base_delay": 2.0,
    "max_delay": 120.0
  },
  "timeouts": {
    "llm_api": 45,
    "email_api": 25,
    "scraper": 15
  }
}
```

---

## Monitoring


### Real-Time Monitoring

#### Progress Tracker Output

The system displays real-time progress during execution:

```
Starting async pipeline for: 'software engineer'
  Workers: 5
  Queue size: 100
  Min score: 50

Processing Jobs ━━━━━━━━━━━━━━━━━━━━━ 142/150 (95%) 0:00:43
  Completed: 142 | Failed: 8
  Throughput: 3.2 jobs/sec | Avg time: 2.1s/job
  Queue: 12/100 | Active workers: 5/5

============================================================
Pipeline Complete
============================================================
  Total jobs: 150
  Completed: 142
  Failed: 8
  Success rate: 94.67%
  Time: 45.23s
  Throughput: 3.32 jobs/sec
  Avg processing time: 2.15s/job
============================================================
```

### Structured Logging

#### Log Format

Logs are written in JSON format for easy parsing:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "event": "job_processed",
  "job_id": "job-12345",
  "status": "completed",
  "processing_time_ms": 2150.5,
  "attempt_count": 1,
  "worker_id": "worker-3"
}
```

#### Log Levels

| Level | Usage | Example Events |
|-------|-------|----------------|
| `DEBUG` | Development, troubleshooting | Queue operations, semaphore acquire/release |
| `INFO` | Normal operations | Job processed, pipeline started/completed |
| `WARNING` | Recoverable errors | Retry attempts, rate limit approached |
| `ERROR` | Failures | Job failed after retries, API errors |
| `CRITICAL` | System failures | Database connection lost, pipeline crash |

#### Viewing Logs

```bash
# Real-time log monitoring
tail -f logs/pipeline.log

# Filter by level
grep '"level":"ERROR"' logs/pipeline.log | jq .

# Filter by job_id
grep '"job_id":"job-12345"' logs/pipeline.log | jq .

# Count errors in last hour
grep '"level":"ERROR"' logs/pipeline.log | grep "$(date -u -d '1 hour ago' +%Y-%m-%dT%H)" | wc -l
```

### Key Metrics

#### System Metrics


| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|-----------------|
| Throughput | Jobs processed per second | >3.3 | <2.0 |
| Success Rate | Percentage of successful jobs | >90% | <80% |
| Avg Processing Time | Average time per job (seconds) | <3.0 | >5.0 |
| Queue Utilization | Percentage of queue filled | 30-70% | >90% or <10% |
| Active Workers | Number of busy workers | 60-100% | <30% |
| Memory Usage | System memory consumption | <2GB | >3GB |

#### API Metrics

| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|-----------------|
| API Response Time | Average API latency (ms) | <1000 | >3000 |
| API Error Rate | Percentage of API failures | <5% | >15% |
| Retry Rate | Percentage of jobs requiring retry | <10% | >25% |
| Rate Limit Hit | Times rate limit was reached | 0 | >10/hour |

### Health Checks

#### Manual Health Check

```bash
# Check pipeline health
python -c "
from src.async_pipeline.metrics import PipelineMetrics
metrics = PipelineMetrics()
print(f'Status: {metrics.get_health_status()}')
"

```

#### Automated Health Monitoring

```python
# health_check.py
import asyncio
from src.async_pipeline.pipeline import AsyncJobPipeline
from src.async_pipeline.config import PipelineConfig

async def health_check():
    """Perform system health check"""
    checks = {
        "database": await check_database(),
        "llm_api": await check_llm_api(),
        "email_api": await check_email_api(),
        "disk_space": check_disk_space(),
        "memory": check_memory()
    }
    
    all_healthy = all(checks.values())
    return {"status": "healthy" if all_healthy else "unhealthy", "checks": checks}

# Run periodically (e.g., via cron)
# */5 * * * * python health_check.py
```

### Alerting

#### Alert Conditions

| Condition | Severity | Action |
|-----------|----------|--------|
| Success rate <80% | HIGH | Investigate immediately |
| Throughput <2.0 jobs/sec | MEDIUM | Check resource usage |
| Memory >3GB | HIGH | Reduce workers/queue |
| API error rate >15% | HIGH | Check API status |
| Disk space <10% | CRITICAL | Clear logs, expand disk |
| Database connection failed | CRITICAL | Restart pipeline |


#### Alert Notification Script

```bash
#!/bin/bash
# alert.sh - Send alerts when conditions are met

LOG_FILE="logs/pipeline.log"
ERROR_THRESHOLD=10

# Count errors in last hour
ERROR_COUNT=$(grep '"level":"ERROR"' "$LOG_FILE" | grep "$(date -u -d '1 hour ago' +%Y-%m-%dT%H)" | wc -l)

if [ "$ERROR_COUNT" -gt "$ERROR_THRESHOLD" ]; then
    # Send alert (example: email)
    echo "High error rate: $ERROR_COUNT errors in last hour" | mail -s "Pipeline Alert" ops@example.com
fi
```

---

## Troubleshooting

### Common Issues

#### Issue 1: High Memory Usage

**Symptoms:**
- System memory >3GB
- Out of memory errors
- System slowdown

**Diagnosis:**
```bash
# Check memory usage
ps aux | grep python | awk '{print $6}'  # Memory in KB

# Check Python process memory
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```


**Solutions:**
1. Reduce worker count: `--workers 3`
2. Reduce queue size: `--queue-size 50`
3. Reduce chunk size in config: `"chunk_size": 50`
4. Check for memory leaks in custom code

**Prevention:**
- Monitor memory usage continuously
- Use appropriate configuration for system resources
- Ensure database sessions are properly closed

---

#### Issue 2: Low Throughput

**Symptoms:**
- Processing <2 jobs/second
- Long processing times
- Workers idle

**Diagnosis:**
```bash
# Check active workers
grep '"event":"worker_' logs/pipeline.log | tail -20

# Check queue utilization
grep '"queue_size":' logs/pipeline.log | tail -20

# Check API response times
grep '"api_latency_ms":' logs/pipeline.log | jq '.api_latency_ms' | awk '{sum+=$1; count++} END {print sum/count}'
```

**Solutions:**
1. Increase worker count: `--workers 8`
2. Increase max concurrent: `--max-concurrent 5`
3. Check API rate limits are not too restrictive
4. Verify network connectivity
5. Check database query performance

**Prevention:**
- Start with recommended configuration
- Monitor throughput metrics
- Tune configuration based on results

---

#### Issue 3: High API Error Rate

**Symptoms:**
- >15% API failures
- Frequent retry attempts
- Jobs failing after max retries

**Diagnosis:**
```bash
# Count API errors
grep '"error_type":"API' logs/pipeline.log | wc -l

# Show recent API errors
grep '"error_type":"API' logs/pipeline.log | tail -10 | jq .

# Check rate limit errors
grep 'rate_limit' logs/pipeline.log | wc -l
```

**Solutions:**
1. Reduce API rate: `--llm-rate 5 --email-rate 1`
2. Increase retry attempts in config
3. Check API key validity: verify credentials
4. Verify API service status: check provider status page
5. Increase API timeouts if responses are slow

**Prevention:**
- Monitor API error rates
- Use conservative rate limits initially
- Set up API status monitoring
- Rotate API keys if approaching quota

---

#### Issue 4: Database Connection Errors

**Symptoms:**
- "Database connection failed" errors
- Jobs not being fetched
- Pipeline crashes on startup

**Diagnosis:**
```bash
# Test database connection
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test_db():
    engine = create_async_engine('sqlite+aiosqlite:///./jobs.db')
    async with engine.connect() as conn:
        print('Database connection OK')

asyncio.run(test_db())
"
```

**Solutions:**
1. Verify DATABASE_URL in .env file
2. Check file permissions: `ls -l jobs.db`
3. Run database migrations: `python migrate_database.py`
4. Check disk space: `df -h`
5. Restart database service if using external DB

**Prevention:**
- Use connection pooling (configured by default)
- Set appropriate connection timeouts
- Monitor database health
- Regular database backups

---

#### Issue 5: Queue Backpressure Issues

**Symptoms:**
- Queue always full (>90%)
- Producer blocked frequently
- Or queue always empty (<10%)

**Diagnosis:**
```bash
# Monitor queue size over time
grep '"queue_size":' logs/pipeline.log | jq '.queue_size' | tail -50
```

**Solutions for Full Queue:**
1. Increase worker count: more consumers
2. Increase max concurrent API calls
3. Check if workers are blocked on slow operations
4. Reduce producer chunk size

**Solutions for Empty Queue:**
1. Reduce worker count: too many consumers
2. Increase producer chunk size
3. Check database query performance

**Prevention:**
- Target queue utilization: 30-70%
- Monitor queue metrics continuously
- Adjust worker count based on load

---

#### Issue 6: Jobs Failing After Retries

**Symptoms:**
- Multiple jobs with status=FAILED
- "Max retries exceeded" errors
- High retry rate (>25%)

**Diagnosis:**
```bash
# Show failed jobs
grep '"status":"failed"' logs/pipeline.log | jq '{job_id, error, attempt_count}'

# Count retry attempts
grep '"event":"retry_attempt"' logs/pipeline.log | wc -l

# Analyze failure patterns
grep '"status":"failed"' logs/pipeline.log | jq '.error_type' | sort | uniq -c
```

**Solutions:**
1. Increase max_retries in config: `"max_retries": 5`
2. Increase max_delay for more patience: `"max_delay": 120`
3. Check root cause of failures (API errors, timeouts, etc.)
4. Verify API credentials and quotas
5. Add specific error handling for common failures

**Prevention:**
- Start with conservative retry settings
- Monitor retry rates
- Implement circuit breaker for persistent failures
- Set up alerts for high retry rates

---

### Debugging Techniques

#### Enable Debug Logging


```bash
# Run with debug logging
python -m src.cli process-async "query" --log-level DEBUG

# Debug specific job
grep '"job_id":"job-12345"' logs/pipeline.log | jq .
```

#### Trace Job Processing

```python
# trace_job.py - Track a specific job through the pipeline
import json

def trace_job(job_id, log_file="logs/pipeline.log"):
    """Trace all events for a specific job"""
    with open(log_file) as f:
        events = [json.loads(line) for line in f if job_id in line]
    
    for event in sorted(events, key=lambda x: x['timestamp']):
        print(f"{event['timestamp']} - {event['event']} - {event.get('status', 'N/A')}")
    
    return events

# Usage
events = trace_job("job-12345")
```

#### Profile Performance

```python
# profile_pipeline.py - Profile pipeline performance
import cProfile
import pstats
from src.cli import main

# Run with profiling
cProfile.run('main(["process-async", "query"])', 'profile_stats')

# Analyze results
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative')
stats.print_stats(20)
```

#### Memory Profiling

```bash
# Install memory profiler
pip install memory_profiler


# Profile memory usage
python -m memory_profiler -m src.cli process-async "query" --workers 2
```

---

## Maintenance

### Daily Maintenance

#### Log Rotation

```bash
# Rotate logs daily
# Add to cron: 0 0 * * * /path/to/rotate_logs.sh

#!/bin/bash
# rotate_logs.sh
LOG_DIR="logs"
DATE=$(date +%Y%m%d)

# Compress yesterday's logs
gzip "$LOG_DIR/pipeline.log.1"

# Rotate logs
mv "$LOG_DIR/pipeline.log" "$LOG_DIR/pipeline.log.1"

# Remove logs older than 30 days
find "$LOG_DIR" -name "pipeline.log.*.gz" -mtime +30 -delete
```

#### Health Check

```bash
# Daily health check
# Add to cron: 0 8 * * * /path/to/daily_health_check.sh

#!/bin/bash
# daily_health_check.sh

echo "=== Daily Health Check ===" >> health_check.log
date >> health_check.log

# Check disk space
df -h | grep -E 'Filesystem|/dev/' >> health_check.log

# Check error rate (last 24 hours)
ERROR_COUNT=$(grep '"level":"ERROR"' logs/pipeline.log | wc -l)
echo "Errors in last 24h: $ERROR_COUNT" >> health_check.log

# Check database size
ls -lh jobs.db >> health_check.log

```

### Weekly Maintenance

#### Database Optimization

```bash
# Weekly database maintenance
# Add to cron: 0 2 * * 0 /path/to/weekly_db_maintenance.sh

#!/bin/bash
# weekly_db_maintenance.sh

echo "Starting database maintenance..."

# Vacuum database (SQLite)
sqlite3 jobs.db "VACUUM;"

# Analyze query performance
sqlite3 jobs.db "ANALYZE;"

# Check database integrity
sqlite3 jobs.db "PRAGMA integrity_check;"

echo "Database maintenance complete"
```

#### Log Analysis

```bash
# Weekly log analysis
python analyze_logs.py --start-date "7 days ago" --end-date "now"
```

```python
# analyze_logs.py
import json
from datetime import datetime, timedelta
from collections import Counter

def analyze_logs(log_file, start_date, end_date):
    """Analyze logs for weekly report"""
    stats = {
        "total_jobs": 0,
        "completed": 0,
        "failed": 0,
        "avg_processing_time": 0,
        "error_types": Counter(),
        "retry_count": 0
    }
    
    processing_times = []
    
    with open(log_file) as f:
        for line in f:
            try:
                event = json.loads(line)
                timestamp = datetime.fromisoformat(event['timestamp'])
                
                if start_date <= timestamp <= end_date:
                    if event.get('event') == 'job_processed':
                        stats['total_jobs'] += 1
                        if event.get('status') == 'completed':
                            stats['completed'] += 1
                        else:
                            stats['failed'] += 1
                            stats['error_types'][event.get('error_type', 'unknown')] += 1
                        
                        processing_times.append(event.get('processing_time_ms', 0))
                    
                    if event.get('event') == 'retry_attempt':
                        stats['retry_count'] += 1
            except:
                continue
    
    if processing_times:
        stats['avg_processing_time'] = sum(processing_times) / len(processing_times)
    
    # Print report
    print("\n=== Weekly Pipeline Report ===")
    print(f"Period: {start_date} to {end_date}")
    print(f"Total jobs: {stats['total_jobs']}")
    print(f"Completed: {stats['completed']} ({stats['completed']/max(stats['total_jobs'],1)*100:.1f}%)")
    print(f"Failed: {stats['failed']} ({stats['failed']/max(stats['total_jobs'],1)*100:.1f}%)")
    print(f"Avg processing time: {stats['avg_processing_time']:.2f}ms")
    print(f"Retry attempts: {stats['retry_count']}")
    print(f"\nTop error types:")
    for error_type, count in stats['error_types'].most_common(5):
        print(f"  {error_type}: {count}")
    
    return stats
```

### Monthly Maintenance


#### Dependency Updates

```bash
# Check for outdated dependencies
pip list --outdated

# Update dependencies (test in staging first!)
pip install --upgrade aiosqlite httpx structlog tenacity rich

# Freeze new versions
pip freeze > requirements.txt
```

#### Performance Review

```bash
# Generate monthly performance report
python generate_monthly_report.py --month $(date +%Y-%m)
```

#### Configuration Review

- Review and adjust worker_count based on load patterns
- Review and adjust rate_limits based on API usage
- Review and adjust retry settings based on failure patterns
- Review and adjust timeouts based on API latencies

### Backup Procedures

#### Database Backup

```bash
# Daily database backup
# Add to cron: 0 3 * * * /path/to/backup_database.sh

#!/bin/bash
# backup_database.sh
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="jobs.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/jobs_$DATE.db'"

# Compress backup
gzip "$BACKUP_DIR/jobs_$DATE.db"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "jobs_*.db.gz" -mtime +30 -delete

echo "Database backup complete: jobs_$DATE.db.gz"
```

#### Configuration Backup

```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/ .env src/async_pipeline/example_config.json
```

#### Restore Procedures

```bash
# Restore database from backup
gunzip -c backups/jobs_20240115_030000.db.gz > jobs_restored.db

# Verify restored database
sqlite3 jobs_restored.db "PRAGMA integrity_check;"

# Replace current database (after verification)
mv jobs.db jobs.db.old
mv jobs_restored.db jobs.db
```

---

## Performance Tuning

### Optimization Strategies

#### 1. Worker Count Optimization

```bash
# Benchmark different worker counts
for workers in 2 4 6 8 10; do
    echo "Testing with $workers workers..."
    time python -m src.cli process-async "test query" --workers $workers
done

# Choose optimal based on results
```

**Guidelines:**
- Start with `workers = CPU_count`
- For I/O-bound: `workers = 2 * CPU_count`
- For API-limited: `workers = rate_limit / avg_requests_per_job`
- Maximum recommended: 20 workers

#### 2. Queue Size Tuning

```bash
# Monitor queue utilization
grep '"queue_size":' logs/pipeline.log | jq '.queue_size' | awk '{sum+=$1; count++} END {print sum/count}'
```

**Guidelines:**
- Target: 30-70% average utilization
- Too high (>90%): Increase workers or max_concurrent
- Too low (<10%): Reduce workers or increase chunk_size
- Memory constraint: `queue_size * avg_job_size < available_memory`

#### 3. Rate Limit Optimization

```python
# Calculate optimal rate limits
def calculate_optimal_rate(
    target_throughput_jobs_per_sec: float,
    avg_api_calls_per_job: int
) -> float:
    """Calculate required API rate limit"""
    return target_throughput_jobs_per_sec * avg_api_calls_per_job

# Example: 3.3 jobs/sec * 3 API calls/job = 10 req/sec
```

**Guidelines:**
- Start conservative (50% of API limit)
- Monitor for rate limit errors
- Gradually increase if no errors
- Leave 20% headroom for bursts

#### 4. Database Query Optimization

```python
# Optimize chunk size
# Too small: Many queries, overhead
# Too large: Memory usage, slow queries

# Benchmark
for chunk_size in [50, 100, 200, 500]:
    # Measure query time and memory
    pass

# Optimal: Balance between query overhead and memory
```

**Guidelines:**
- Small datasets (<1000): chunk_size = 50-100
- Large datasets (>10000): chunk_size = 200-500
- Monitor query times and adjust

#### 5. Timeout Optimization

```bash
# Analyze API latencies
grep '"api_latency_ms":' logs/pipeline.log | jq '.api_latency_ms' | \
  awk '{
    sum+=$1; count++;
    if ($1 > max) max=$1;
    if (min == 0 || $1 < min) min=$1
  } END {
    print "Avg:", sum/count, "Min:", min, "Max:", max
  }'

# Set timeout = P95 latency + buffer
```

**Guidelines:**
- timeout = P95_latency * 1.5 + safety_margin
- Too low: Unnecessary timeouts and retries
- Too high: Slow failure detection
- Monitor timeout rate (<1% ideal)

### Performance Benchmarks

#### Baseline Performance

| Configuration | Throughput | Memory | Use Case |
|---------------|------------|--------|----------|
| 2 workers, queue=50 | 1.5 jobs/sec | 500MB | Development |
| 5 workers, queue=100 | 3.3 jobs/sec | 1GB | Production (default) |
| 8 workers, queue=200 | 5.0 jobs/sec | 1.5GB | High-volume |
| 10 workers, queue=500 | 6.5 jobs/sec | 2GB | Maximum throughput |

#### Optimization Checklist

- [ ] Workers optimized for CPU/API limits
- [ ] Queue size balanced (30-70% utilization)
- [ ] Rate limits configured conservatively
- [ ] Timeouts set based on actual latencies
- [ ] Chunk size optimized for dataset
- [ ] Database queries indexed
- [ ] Connection pooling configured
- [ ] Memory usage within limits
- [ ] Monitoring and alerts configured

---

## Security

### API Key Management

#### Secure Storage


```bash
# Store API keys in .env file (never commit!)
echo ".env" >> .gitignore

# Set restrictive permissions
chmod 600 .env

# Use environment variables
export GEMINI_API_KEY="..."
export OPENAI_API_KEY="..."
```

#### Key Rotation

```bash
# Rotate API keys quarterly
# 1. Generate new keys in API provider console
# 2. Update .env file
# 3. Restart pipeline
# 4. Verify functionality
# 5. Revoke old keys after 24 hours
```

### Access Control

```bash
# Restrict file permissions
chmod 600 .env
chmod 600 config/pipeline_config.json
chmod 600 jobs.db

# Restrict directory access
chmod 700 logs/
chmod 700 backups/
```

### Network Security

```bash
# Use HTTPS for all API calls (configured by default)
# Verify SSL certificates (configured by default)

# For production: Use firewall rules
# Allow only necessary outbound connections
```

### Audit Logging

```python
# Enable audit logging for sensitive operations
# Log: API key usage, configuration changes, database access

# Example: audit.log
{
  "timestamp": "2024-01-15T10:30:45Z",
  "event": "config_changed",
  "user": "admin",
  "changes": {"worker_count": {"old": 5, "new": 8}}
}
```

### Security Checklist

- [ ] API keys stored securely in .env
- [ ] .env file not committed to git
- [ ] File permissions set correctly (600 for sensitive files)
- [ ] API keys rotated regularly (quarterly)
- [ ] HTTPS used for all external connections
- [ ] Logs sanitized (no API keys in logs)
- [ ] Access control implemented
- [ ] Audit logging enabled
- [ ] Database encrypted at rest (if required)
- [ ] Network firewall configured

---

## Backup and Recovery

### Backup Strategy

#### What to Backup

1. **Database** (Critical)
   - `jobs.db`
   - Daily backups, 30-day retention

2. **Configuration** (Important)
   - `.env` file
   - `config/pipeline_config.json`
   - Weekly backups, 90-day retention

3. **Logs** (Optional)
   - `logs/pipeline.log`
   - Daily rotation, 30-day retention

#### Backup Schedule

```bash
# Add to crontab: crontab -e

# Daily database backup at 3 AM
0 3 * * * /path/to/backup_database.sh

# Daily log rotation at midnight
0 0 * * * /path/to/rotate_logs.sh

# Weekly config backup on Sundays at 2 AM
0 2 * * 0 tar -czf config_backup_$(date +\%Y\%m\%d).tar.gz config/ .env
```

### Recovery Procedures

#### Database Recovery

```bash
# 1. Stop pipeline
pkill -f "python -m src.cli"

# 2. Backup current database (in case recovery fails)
cp jobs.db jobs.db.before_recovery

# 3. Restore from backup
gunzip -c backups/jobs_20240115_030000.db.gz > jobs.db

# 4. Verify integrity
sqlite3 jobs.db "PRAGMA integrity_check;"

# 5. Test with small query
python -m src.cli process-async "test" --workers 1

# 6. Resume normal operations
```

#### Configuration Recovery

```bash
# 1. Restore configuration from backup
tar -xzf config_backup_20240115.tar.gz

# 2. Verify configuration
python -c "
from src.async_pipeline.config import load_config
config = load_config('config/pipeline_config.json')
print('Config OK')
"

# 3. Test pipeline
python -m src.cli process-async "test" --workers 1
```

#### Disaster Recovery Plan

**Scenario 1: Complete System Failure**

```bash
# 1. Provision new system
# 2. Install dependencies
pip install -r requirements.txt

# 3. Restore database
gunzip -c backups/latest.db.gz > jobs.db

# 4. Restore configuration
tar -xzf config_backup_latest.tar.gz

# 5. Verify and test
python -m src.cli process-async "test" --workers 1

# 6. Resume operations
```

**Scenario 2: Database Corruption**

```bash
# 1. Stop pipeline immediately
pkill -f "python -m src.cli"

# 2. Attempt repair
sqlite3 jobs.db "PRAGMA integrity_check;"
sqlite3 jobs.db ".recover" | sqlite3 jobs_recovered.db

# 3. If repair fails, restore from backup
gunzip -c backups/latest.db.gz > jobs.db

# 4. Resume operations
```

**Scenario 3: API Key Compromise**

```bash
# 1. Revoke compromised keys immediately in provider console
# 2. Generate new keys
# 3. Update .env file with new keys
# 4. Restart pipeline
# 5. Monitor for unusual activity
# 6. Review audit logs
```

### Recovery Time Objectives (RTO)

| Scenario | Target RTO | Steps |
|----------|-----------|-------|
| Database corruption | <30 minutes | Restore from backup |
| Configuration loss | <15 minutes | Restore config files |
| Complete system failure | <2 hours | Rebuild and restore |
| API key compromise | <10 minutes | Rotate keys |

---

## Incident Response

### Incident Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| **P1 - Critical** | Complete system outage | Immediate | Pipeline crashed, database lost |
| **P2 - High** | Major degradation | <1 hour | Success rate <50%, high error rate |
| **P3 - Medium** | Minor degradation | <4 hours | Throughput low, some errors |
| **P4 - Low** | Cosmetic issues | <24 hours | Log formatting, minor bugs |


### Incident Response Workflow

#### 1. Detection

```bash
# Automated monitoring detects issue
# OR manual report from user/operator

# Check system status
python health_check.py

# Review recent logs
tail -100 logs/pipeline.log | grep ERROR
```

#### 2. Assessment

```bash
# Determine severity
# Identify affected components
# Estimate impact (jobs affected, time lost)

# Quick assessment script
python assess_incident.py
```

#### 3. Containment

```bash
# Stop pipeline if necessary
pkill -f "python -m src.cli"

# Preserve evidence
cp logs/pipeline.log logs/incident_$(date +%Y%m%d_%H%M%S).log
cp jobs.db jobs_incident_$(date +%Y%m%d_%H%M%S).db
```

#### 4. Resolution

```bash
# Apply fix based on issue type
# Restore from backup if needed
# Restart pipeline with monitoring

# Test fix
python -m src.cli process-async "test" --workers 1

# Resume operations
python -m src.cli process-async "query" --workers 5
```

#### 5. Documentation

```bash
# Create incident report
cat > incidents/incident_$(date +%Y%m%d).md << EOF
# Incident Report: $(date)

## Summary
[Brief description]

## Timeline
- Detection: [time]
- Containment: [time]
- Resolution: [time]

## Root Cause
[Analysis]

## Impact
[Jobs affected, downtime]

## Resolution
[Steps taken]

## Prevention
[Future improvements]
EOF
```

#### 6. Post-Mortem

- Review incident timeline
- Identify root cause
- Document lessons learned
- Implement preventive measures
- Update runbooks and documentation

### Common Incident Scenarios

#### Scenario: Pipeline Crash

```bash
# 1. Check if process is running
ps aux | grep "python -m src.cli"

# 2. Check crash logs
tail -100 logs/pipeline.log | grep -E "ERROR|CRITICAL"

# 3. Identify crash reason (OOM, exception, etc.)

# 4. Apply fix:
# - If OOM: Reduce workers/queue
# - If exception: Fix code bug
# - If API error: Check credentials

# 5. Restart with monitoring
python -m src.cli process-async "query" --workers 3 --log-level DEBUG
```

#### Scenario: High Error Rate

```bash
# 1. Check error distribution
grep '"level":"ERROR"' logs/pipeline.log | jq '.error_type' | sort | uniq -c

# 2. Identify pattern (API errors, timeouts, etc.)

# 3. Apply fix:
# - API errors: Check API status, credentials
# - Timeouts: Increase timeout values
# - Rate limits: Reduce rate limits

# 4. Monitor recovery
watch -n 5 'grep '"'"'"level":"ERROR"'"'"' logs/pipeline.log | tail -5'
```

#### Scenario: Performance Degradation

```bash
# 1. Check current throughput
grep '"event":"pipeline_complete"' logs/pipeline.log | tail -1 | jq '.throughput_jobs_per_sec'

# 2. Compare with baseline (3.3 jobs/sec)

# 3. Identify bottleneck:
# - Check worker utilization
# - Check queue size
# - Check API latencies
# - Check database query times

# 4. Apply fix:
# - Increase workers if underutilized
# - Increase max_concurrent if API-bound
# - Optimize database queries
# - Check network connectivity

# 5. Verify improvement
# Monitor throughput for 10 minutes
```

### Escalation Path

```
P1 Critical → Immediate alert → On-call engineer → Manager (if not resolved in 30 min)
P2 High     → Alert within 15 min → On-call engineer → Manager (if not resolved in 4 hours)
P3 Medium   → Alert within 1 hour → Regular engineer → Next business day
P4 Low      → Ticket created → Regular engineer → Within week
```

### Contact Information

```yaml
# Update with your team's information
Operations Team:
  Primary: ops@example.com
  Phone: +1-555-0100
  Slack: #pipeline-ops

On-Call Engineer:
  Schedule: PagerDuty rotation
  Phone: +1-555-0200

Manager:
  Email: manager@example.com
  Phone: +1-555-0300

External Services:
  Gemini API Support: support.google.com
  Database Support: (if external)
```

---

## Appendix

### Quick Reference Commands

```bash
# Start pipeline
python -m src.cli process-async "query" --workers 5

# Stop pipeline
pkill -f "python -m src.cli"

# Check status
ps aux | grep "python -m src.cli"

# View logs
tail -f logs/pipeline.log

# Health check
python health_check.py

# Backup database
sqlite3 jobs.db ".backup 'backup.db'"

# Restore database
gunzip -c backup.db.gz > jobs.db

# Rotate logs
mv logs/pipeline.log logs/pipeline.log.1

# Check disk space
df -h

# Check memory
free -h

# Check errors
grep ERROR logs/pipeline.log | wc -l

# Analyze performance
grep '"event":"pipeline_complete"' logs/pipeline.log | tail -5 | jq .
```

### Configuration Templates

#### Development
```json
{
  "worker_count": 2,
  "queue_size": 50,
  "max_concurrent_api_calls": 2,
  "logging": {"level": "DEBUG"}
}
```

#### Production
```json
{
  "worker_count": 8,
  "queue_size": 200,
  "max_concurrent_api_calls": 5,
  "logging": {"level": "WARNING"}
}
```

#### High-Reliability
```json
{
  "worker_count": 5,
  "queue_size": 100,
  "retry": {
    "max_retries": 5,
    "base_delay": 2.0,
    "max_delay": 120.0
  },
  "logging": {"level": "INFO"}
}
```

### Troubleshooting Flowchart

```
Issue Detected
    ↓
Is pipeline running?
    NO → Check crash logs → Fix and restart
    YES ↓
Is throughput low?
    YES → Check workers, queue, API latency → Tune config
    NO ↓
Is error rate high?
    YES → Check error types → Fix root cause
    NO ↓
Is memory high?
    YES → Reduce workers/queue → Restart
    NO ↓
Check specific component logs
```

### Glossary

| Term | Definition |
|------|------------|
| **Backpressure** | Mechanism that slows producer when queue is full |
| **Bounded Queue** | Queue with maximum size limit |
| **Chunk Size** | Number of jobs fetched per database query |
| **Exponential Backoff** | Retry strategy with increasing delays |
| **Job Context** | Immutable data structure for job information |
| **Poison Pill** | Sentinel value (None) signaling worker shutdown |
| **Rate Limiter** | Token bucket algorithm controlling API request rate |
| **Semaphore** | Concurrency limiter for simultaneous operations |
| **Throughput** | Jobs processed per second |
| **Worker Pool** | Collection of concurrent async workers |

### Related Documentation

- **Quick Start Guide**: `ASYNC_PIPELINE_QUICK_START.md`
- **Design Document**: `.kiro/specs/async-job-pipeline-refactor/design.md`
- **Requirements**: `.kiro/specs/async-job-pipeline-refactor/requirements.md`
- **Metrics Guide**: `src/async_pipeline/METRICS_GUIDE.md`
- **Structured Logging**: `src/async_pipeline/STRUCTURED_LOGGING_GUIDE.md`
- **Rate Limiter Implementation**: `src/async_pipeline/RATE_LIMITER_IMPLEMENTATION.md`
- **Config Implementation**: `src/async_pipeline/CONFIG_IMPLEMENTATION_SUMMARY.md`

### Support and Resources

#### Documentation
- System architecture diagrams in design.md
- API documentation in source code docstrings
- Configuration examples in example_config.json

#### Tools
- Health check script: `health_check.py`
- Log analyzer: `analyze_logs.py`
- Performance profiler: `profile_pipeline.py`

#### Community
- GitHub Issues: [repository]/issues
- Internal Wiki: [wiki-url]
- Team Slack: #pipeline-ops

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | Operations Team | Initial operational documentation |

---

**Document Status**: ✅ Complete

**Last Updated**: 2024-01-15

**Next Review**: 2024-04-15 (Quarterly)
