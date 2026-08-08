# Async Job Pipeline Operations Guide

## Table of Contents

1. [Deployment Procedures](#deployment-procedures)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Troubleshooting Guide](#troubleshooting-guide)
4. [Performance Tuning](#performance-tuning)
5. [Backup and Recovery](#backup-and-recovery)
6. [Maintenance Procedures](#maintenance-procedures)
7. [Common Failure Modes](#common-failure-modes)
8. [Metrics Interpretation](#metrics-interpretation)
9. [Decision Trees](#decision-trees)

---

## 1. Deployment Procedures

### 1.1 Initial Deployment

#### Prerequisites

Before deploying the async pipeline, ensure:

- Python 3.8 or higher is installed
- PostgreSQL or SQLite database is configured
- Required API keys are available (LLM, Email, Scraping services)
- Sufficient system resources (see Resource Requirements below)

#### Resource Requirements

| Job Volume | Workers | Memory (RAM) | CPU Cores | Disk Space |
|-----------|---------|--------------|-----------|------------|
| < 100 jobs | 3 | 512 MB | 2 | 1 GB |
| 100-1000 jobs | 5 | 1 GB | 4 | 5 GB |
| 1000-5000 jobs | 8 | 2 GB | 8 | 10 GB |
| 5000+ jobs | 10-15 | 4 GB | 16 | 20 GB |

#### Installation Steps

```bash
# 1. Clone repository
git clone <repository-url>
cd job-finder

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your configuration

# 5. Initialize database
python migrate_database.py

# 6. Verify installation
python -m src.cli --help
```

#### Environment Configuration

Create or update `.env` file:

```bash
# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///job_automation.db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# API Keys
GEMINI_API_KEY=your_gemini_key_here
EMAIL_DISCOVERY_API_KEY=your_email_key_here

# Pipeline Configuration
WORKER_COUNT=5
QUEUE_SIZE=100
MAX_CONCURRENT_API=3

# Rate Limits (requests per second)
LLM_RATE_LIMIT=10
EMAIL_RATE_LIMIT=2
SCRAPER_RATE_LIMIT=30

# Retry Configuration
MAX_RETRIES=3
RETRY_BASE_DELAY=1.0
RETRY_MAX_DELAY=60.0

# Timeout Configuration (seconds)
LLM_TIMEOUT=30
EMAIL_TIMEOUT=10
SCRAPER_TIMEOUT=30
DB_TIMEOUT=5

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/async_pipeline.log
```

#### Verification Steps

```bash
# 1. Test database connection
python -c "from src.async_pipeline import AsyncJobPipeline; print('✓ Imports successful')"

# 2. Test configuration loading
python test_config.py

# 3. Run small test batch (10 jobs)
python -m src.cli process-async "test query" --workers 2 --limit 10

# 4. Check logs
tail -f logs/async_pipeline.log
```

### 1.2 Production Deployment

#### Docker Deployment (Recommended)

```dockerfile
# Dockerfile already provided in project root

# Build image
docker build -t job-pipeline:latest .

# Run container
docker run -d \
  --name job-pipeline \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -p 8000:8000 \
  job-pipeline:latest

# Check logs
docker logs -f job-pipeline

# Stop container
docker stop job-pipeline
```

#### Systemd Service (Linux)

Create `/etc/systemd/system/job-pipeline.service`:

```ini
[Unit]
Description=Async Job Pipeline Service
After=network.target

[Service]
Type=simple
User=jobuser
WorkingDirectory=/opt/job-finder
Environment="PATH=/opt/job-finder/.venv/bin"
ExecStart=/opt/job-finder/.venv/bin/python -m src.cli process-async "default query"
Restart=on-failure
RestartSec=10

StandardOutput=append:/var/log/job-pipeline/output.log
StandardError=append:/var/log/job-pipeline/error.log

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable job-pipeline
sudo systemctl start job-pipeline
sudo systemctl status job-pipeline
```

### 1.3 Configuration Management

#### Configuration Files

The pipeline supports three configuration methods (in priority order):

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Configuration file** (`config/pipeline_config.json`)

#### Example Configuration File

```json
{
  "worker_count": 5,
  "queue_size": 100,
  "max_concurrent_api_calls": 3,
  "db_chunk_size": 100,
  "llm_rate_limit": 10,
  "email_rate_limit": 2,
  "scraper_rate_limit": 30,
  "max_retries": 3,
  "retry_base_delay": 1.0,
  "retry_max_delay": 60.0,
  "retry_exponential_base": 2.0,
  "llm_timeout": 30,
  "email_timeout": 10,
  "scraper_timeout": 30,
  "db_timeout": 5,
  "log_level": "INFO"
}
```

#### Validating Configuration

```python
from src.async_pipeline.config import ProcessorConfig

# Load and validate
config = ProcessorConfig.from_file("config/pipeline_config.json")
config.validate()  # Raises ValueError if invalid
```

---

## 2. Monitoring and Alerting

### 2.1 Key Metrics to Monitor

#### Pipeline Health Metrics

| Metric | Normal Range | Warning Threshold | Critical Threshold |
|--------|--------------|-------------------|-------------------|
| Throughput (jobs/sec) | 3.0 - 5.0 | < 2.0 | < 1.0 |
| Success Rate (%) | 90 - 100 | < 85 | < 75 |
| Memory Usage (MB) | 500 - 2000 | > 3000 | > 4000 |
| Queue Size | 0 - 100 | > 80 | > 95 |
| Active Workers | = worker_count | < 50% | < 25% |
| Avg Processing Time (ms) | 500 - 2000 | > 3000 | > 5000 |

#### API Health Metrics

| Metric | Normal Range | Warning Threshold | Critical Threshold |
|--------|--------------|-------------------|-------------------|
| LLM API Latency (ms) | 200 - 1000 | > 2000 | > 5000 |
| Email API Latency (ms) | 100 - 500 | > 1000 | > 2000 |
| Scraper Latency (ms) | 500 - 2000 | > 4000 | > 8000 |
| LLM Error Rate (%) | 0 - 5 | > 10 | > 25 |
| Email Error Rate (%) | 0 - 5 | > 10 | > 25 |
| Retry Rate (%) | 0 - 10 | > 20 | > 40 |

### 2.2 Real-Time Monitoring

#### Using Built-in Metrics

```python
from src.async_pipeline import AsyncJobPipeline

pipeline = AsyncJobPipeline(config=config)

# Enable progress display
pipeline.enable_progress_display(True)

# Custom progress callback
def on_progress(metrics):
    throughput = metrics.get('throughput', 0)
    success_rate = metrics.get('success_rate', 0)
    
    # Alert if throughput drops
    if throughput < 2.0:
        send_alert(f"Low throughput: {throughput:.2f} jobs/sec")
    
    # Alert if success rate drops
    if success_rate < 85:
        send_alert(f"Low success rate: {success_rate:.1f}%")

pipeline.set_progress_callback(on_progress)
```

#### Accessing Metrics Snapshot

```python
# After pipeline run
results = await pipeline.run(query="software engineer")
metrics = pipeline.get_metrics_snapshot()

if metrics:
    print(f"Total processed: {metrics.total_processed}")
    print(f"Success count: {metrics.success_count}")
    print(f"Failure count: {metrics.failure_count}")
    print(f"Success rate: {metrics.success_rate:.1f}%")
    print(f"Throughput: {metrics.throughput:.2f} jobs/sec")
    print(f"Avg processing time: {metrics.avg_processing_time_ms:.1f}ms")
    print(f"Min/Max time: {metrics.min_processing_time_ms:.1f} / {metrics.max_processing_time_ms:.1f}ms")
```

### 2.3 Log-Based Monitoring

#### Log Locations

- **Application logs**: `logs/async_pipeline.log`
- **Error logs**: Check for `"level": "error"` in structured logs
- **Retry logs**: Check for `"level": "warning"` and `"event": "retry_attempt"`

#### Important Log Patterns

```bash
# Monitor error rate
grep '"level":"error"' logs/async_pipeline.log | wc -l

# Monitor retry attempts
grep '"event":"retry_attempt"' logs/async_pipeline.log | wc -l

# Check timeout errors
grep '"error_type":"TimeoutError"' logs/async_pipeline.log

# Monitor queue backpressure
grep '"queue_size":' logs/async_pipeline.log | tail -20

# Check throughput over time
grep '"throughput":' logs/async_pipeline.log | tail -10
```

#### Structured Log Format

Logs are in JSON format for easy parsing:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "job_completed",
  "job_id": "job_12345",
  "status": "completed",
  "processing_time_ms": 1234.5,
  "attempt_count": 1,
  "worker_id": "worker_2"
}
```

### 2.4 Setting Up Alerts

#### Alert Conditions

```yaml
alerts:
  # Critical: Pipeline stalled
  - name: pipeline_stalled
    condition: throughput < 0.5 jobs/sec for 5 minutes
    severity: critical
    action: restart pipeline
  
  # Warning: High error rate
  - name: high_error_rate
    condition: error_rate > 15% for 10 minutes
    severity: warning
    action: investigate logs
  
  # Warning: Memory growth
  - name: memory_leak
    condition: memory_usage increasing steadily
    severity: warning
    action: check for connection leaks
  
  # Critical: Database errors
  - name: database_errors
    condition: db_error_rate > 10%
    severity: critical
    action: check database connection
  
  # Warning: API rate limiting
  - name: api_rate_limited
    condition: rate_limit_error_count > 10 in 5 minutes
    severity: warning
    action: reduce rate limits
```

#### Example Alert Script

```python
#!/usr/bin/env python
import json
import sys
from datetime import datetime, timedelta

def check_metrics(log_file):
    """Parse logs and check for alert conditions."""
    errors = []
    recent_throughput = []
    
    with open(log_file) as f:
        for line in f:
            try:
                log = json.loads(line)
                
                # Collect errors
                if log.get('level') == 'error':
                    errors.append(log)
                
                # Collect throughput
                if 'throughput' in log:
                    recent_throughput.append(log['throughput'])
            except:
                continue
    
    # Check alert conditions
    alerts = []
    
    if len(recent_throughput) > 0:
        avg_throughput = sum(recent_throughput[-10:]) / len(recent_throughput[-10:])
        if avg_throughput < 1.0:
            alerts.append({
                'severity': 'critical',
                'message': f'Low throughput: {avg_throughput:.2f} jobs/sec'
            })
    
    error_rate = len(errors) / max(len(recent_throughput), 1) * 100
    if error_rate > 15:
        alerts.append({
            'severity': 'warning',
            'message': f'High error rate: {error_rate:.1f}%'
        })
    
    return alerts

if __name__ == '__main__':
    alerts = check_metrics('logs/async_pipeline.log')
    for alert in alerts:
        print(f"[{alert['severity'].upper()}] {alert['message']}")
        # Send to alerting system (PagerDuty, Slack, etc.)
```

---

## 3. Troubleshooting Guide

### 3.1 Pipeline Not Starting

#### Symptoms
- Pipeline exits immediately
- "RuntimeError: Event loop is closed"
- Import errors

#### Diagnosis Steps

```bash
# 1. Check Python version
python --version  # Should be 3.8+

# 2. Verify dependencies
pip list | grep -E "aiosqlite|httpx|structlog|tenacity"

# 3. Test imports
python -c "from src.async_pipeline import AsyncJobPipeline"

# 4. Check configuration
python -c "from src.async_pipeline.config import ProcessorConfig; c = ProcessorConfig(); c.validate()"

# 5. Check database
python -c "from sqlalchemy import create_engine; engine = create_engine('sqlite:///job_automation.db'); print('DB OK')"
```

#### Solutions

| Issue | Solution |
|-------|----------|
| Missing dependencies | `pip install -r requirements.txt` |
| Wrong Python version | Use Python 3.8+ |
| Database not found | Run `python migrate_database.py` |
| Invalid configuration | Check `.env` file and validate config |
| Event loop error | Use `asyncio.run()` or sync wrapper |

### 3.2 Low Throughput

#### Symptoms
- Processing < 2 jobs/sec
- Long queue wait times
- Workers idle

#### Diagnosis Steps

```bash
# 1. Check active workers
grep '"worker_id"' logs/async_pipeline.log | sort -u | wc -l

# 2. Check queue backpressure
grep '"queue_size"' logs/async_pipeline.log | tail -10

# 3. Check API latencies
grep '"processing_time_ms"' logs/async_pipeline.log | \
  jq '.processing_time_ms' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'

# 4. Check rate limiting
grep 'rate_limit' logs/async_pipeline.log

# 5. Monitor CPU and memory
top -p $(pgrep -f "python.*async_pipeline")
```

#### Solutions

| Cause | Solution | Configuration |
|-------|----------|---------------|
| Too few workers | Increase worker count | `WORKER_COUNT=8` |
| Rate limits too low | Increase rate limits | `LLM_RATE_LIMIT=15` |
| Small queue size | Increase queue size | `QUEUE_SIZE=200` |
| Low concurrency limit | Increase concurrent calls | `MAX_CONCURRENT_API=5` |
| Slow APIs | Increase timeouts, check API health | `LLM_TIMEOUT=60` |
| CPU bottleneck | Add more CPU cores | Scale horizontally |

### 3.3 High Memory Usage

#### Symptoms
- Memory usage > 3 GB
- Out of memory errors
- System swap usage increasing

#### Diagnosis Steps

```bash
# 1. Check memory usage
ps aux | grep python | grep async_pipeline

# 2. Check queue size
# Should remain constant, not grow indefinitely
grep '"queue_size"' logs/async_pipeline.log | tail -20

# 3. Check for connection leaks
# Count open database connections
lsof -p $(pgrep -f python.*async) | grep -c ".db"

# 4. Profile memory usage
python -m memory_profiler main.py
```

#### Solutions

| Cause | Solution | Configuration |
|-------|----------|---------------|
| Queue too large | Reduce queue size | `QUEUE_SIZE=50` |
| Too many workers | Reduce worker count | `WORKER_COUNT=3` |
| Connection leak | Check session cleanup in code | Verify `finally` blocks |
| Large job objects | Reduce data stored in memory | Use streaming |
| Memory leak in code | Profile and fix leak | Use `tracemalloc` |

#### Memory Leak Detection

```python
import tracemalloc
import asyncio

tracemalloc.start()

# Run pipeline
await pipeline.run(query="test")

# Get memory snapshot
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

# Print top 10 memory allocations
for stat in top_stats[:10]:
    print(stat)
```

### 3.4 Database Connection Errors

#### Symptoms
- "Connection pool exhausted"
- "Database locked" (SQLite)
- Timeout errors on database operations

#### Diagnosis Steps

```bash
# 1. Check database connection pool
grep 'pool' logs/async_pipeline.log

# 2. Check for long-running queries
grep 'db_timeout' logs/async_pipeline.log

# 3. Verify database health (PostgreSQL)
psql -U user -d jobs -c "SELECT count(*) FROM pg_stat_activity;"

# 4. Check SQLite locks
fuser job_automation.db
```

#### Solutions

| Cause | Solution | Configuration |
|-------|----------|---------------|
| Pool size too small | Increase pool size | `DB_POOL_SIZE=10` |
| Pool overflow reached | Increase overflow | `DB_MAX_OVERFLOW=20` |
| SQLite contention | Switch to PostgreSQL | Use PostgreSQL for production |
| Long transactions | Optimize queries | Add indexes, reduce transaction scope |
| Connection leaks | Fix session cleanup | Ensure `session.close()` in `finally` |

#### PostgreSQL Configuration

```python
# Recommended for production
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/jobs"
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_TIMEOUT = 30  # seconds
```

### 3.5 API Rate Limiting Errors

#### Symptoms
- "429 Too Many Requests" errors
- Frequent retry attempts
- Rate limit warnings in logs

#### Diagnosis Steps

```bash
# 1. Count rate limit errors
grep '429\|rate.limit' logs/async_pipeline.log | wc -l

# 2. Check retry attempts
grep '"event":"retry_attempt"' logs/async_pipeline.log | \
  jq '.attempt_count' | sort | uniq -c

# 3. Measure actual request rate
grep '"api_call"' logs/async_pipeline.log | \
  awk '{print $1}' | uniq -c

# 4. Check rate limiter stats
grep 'rate_limiter' logs/async_pipeline.log | tail -10
```

#### Solutions

| API | Typical Limit | Recommended Setting |
|-----|---------------|---------------------|
| LLM (Gemini) | 60 req/min | `LLM_RATE_LIMIT=8` (10 req/min with buffer) |
| Email Discovery | 100 req/hour | `EMAIL_RATE_LIMIT=1` (60 req/hour with buffer) |
| Scraping | Variable | `SCRAPER_RATE_LIMIT=20` |

#### Configuration Adjustment

```python
# Conservative settings for API quota compliance
config = ProcessorConfig(
    llm_rate_limit=5,      # 300 req/hour
    email_rate_limit=1,    # 60 req/hour
    scraper_rate_limit=10, # 600 req/hour
    max_retries=5,         # More retries for rate limits
    retry_max_delay=120,   # Longer max delay
)
```

### 3.6 Jobs Timing Out

#### Symptoms
- Many "TimeoutError" in logs
- Jobs marked as FAILED with timeout errors
- High retry rates

#### Diagnosis Steps

```bash
# 1. Count timeout errors
grep 'TimeoutError' logs/async_pipeline.log | wc -l

# 2. Check which operation times out
grep 'TimeoutError' logs/async_pipeline.log | jq '.operation'

# 3. Measure actual operation times
grep '"processing_time_ms"' logs/async_pipeline.log | \
  jq '.processing_time_ms' | \
  awk '{if($1>max)max=$1} END {print "Max:", max, "ms"}'

# 4. Check timeout configuration
grep 'timeout' .env
```

#### Solutions

| Operation | Default Timeout | Recommended Increase |
|-----------|----------------|----------------------|
| LLM API | 30s | 60s for complex prompts |
| Email API | 10s | 20s for slow networks |
| Scraping | 30s | 60s for slow sites |
| Database | 5s | 10s for complex queries |

```python
# Adjust timeouts
config = ProcessorConfig(
    llm_timeout=60,      # Increase for slow LLM
    email_timeout=20,    # Increase for network issues
    scraper_timeout=60,  # Increase for slow sites
    db_timeout=10,       # Increase for complex queries
)
```

### 3.7 Workers Not Processing

#### Symptoms
- Active worker count < configured count
- Queue filling up but jobs not processed
- No progress for extended period

#### Diagnosis Steps

```bash
# 1. Check active workers
grep '"worker_id"' logs/async_pipeline.log | \
  tail -100 | \
  jq -r '.worker_id' | \
  sort -u | wc -l

# 2. Check for worker crashes
grep 'worker.*error\|worker.*exception' logs/async_pipeline.log

# 3. Check if workers are blocked
grep 'semaphore\|blocked' logs/async_pipeline.log

# 4. Check system resources
top -H -p $(pgrep -f python.*async)
```

#### Solutions

| Cause | Solution |
|-------|----------|
| Worker crash | Check error logs, fix bug in processor |
| Semaphore exhaustion | Increase `max_concurrent_api_calls` |
| Deadlock | Check for circular dependencies in code |
| Resource exhaustion | Reduce worker count or add resources |
| Event loop blocked | Find and fix blocking operations |

---

## 4. Performance Tuning

### 4.1 Baseline Configuration

Start with this baseline and adjust:

```python
# Baseline configuration for 1000 jobs
baseline_config = ProcessorConfig(
    worker_count=5,
    queue_size=100,
    max_concurrent_api_calls=3,
    llm_rate_limit=10,
    email_rate_limit=2,
    scraper_rate_limit=30,
)
```

### 4.2 Tuning for Throughput

**Goal**: Maximize jobs/sec while respecting API limits

#### Step 1: Increase Workers

```python
# Test with 8 workers
config = ProcessorConfig(worker_count=8)
# Measure: throughput should increase proportionally
```

#### Step 2: Increase Concurrency

```python
# Allow more concurrent API calls
config = ProcessorConfig(
    worker_count=8,
    max_concurrent_api_calls=5,
)
# Measure: throughput should increase further
```

#### Step 3: Optimize Queue Size

```python
# Larger queue = more buffering
config = ProcessorConfig(
    worker_count=8,
    max_concurrent_api_calls=5,
    queue_size=200,
)
# Measure: should reduce producer wait time
```

#### Step 4: Increase Rate Limits (Carefully)

```python
# Only if API quotas allow
config = ProcessorConfig(
    worker_count=8,
    max_concurrent_api_calls=5,
    queue_size=200,
    llm_rate_limit=15,   # Monitor for 429 errors
    email_rate_limit=3,
)
# Measure: monitor error rate closely
```

### 4.3 Tuning for Memory Efficiency

**Goal**: Minimize memory usage for large job volumes

```python
# Memory-optimized configuration
memory_config = ProcessorConfig(
    worker_count=3,        # Fewer workers
    queue_size=50,         # Smaller queue
    db_chunk_size=50,      # Smaller chunks
    max_concurrent_api_calls=2,
)
```

### 4.4 Tuning for API Quota Compliance

**Goal**: Stay under API limits at all times

```python
# Conservative configuration
conservative_config = ProcessorConfig(
    worker_count=3,
    max_concurrent_api_calls=2,
    llm_rate_limit=5,      # Well under quota
    email_rate_limit=1,
    scraper_rate_limit=10,
    max_retries=5,         # More retries for rate limits
)
```

### 4.5 Performance Testing

#### Benchmark Script

```python
import time
import asyncio
from src.async_pipeline import AsyncJobPipeline, ProcessorConfig

async def benchmark(config, job_count=1000):
    """Benchmark pipeline configuration."""
    pipeline = AsyncJobPipeline(config=config)
    
    start = time.time()
    results = await pipeline.run(query="test", limit=job_count)
    elapsed = time.time() - start
    
    metrics = pipeline.get_metrics_snapshot()
    
    print(f"\n{'='*60}")
    print(f"Configuration: {config.worker_count} workers, queue={config.queue_size}")
    print(f"{'='*60}")
    print(f"Jobs processed: {len(results)}")
    print(f"Time elapsed: {elapsed:.2f}s")
    print(f"Throughput: {metrics.throughput:.2f} jobs/sec")
    print(f"Success rate: {metrics.success_rate:.1f}%")
    print(f"Avg processing time: {metrics.avg_processing_time_ms:.1f}ms")
    print(f"Memory (peak): {metrics.peak_memory_mb:.1f} MB")
    print(f"{'='*60}\n")
    
    await pipeline.close()
    return metrics

# Test different configurations
configs = [
    ProcessorConfig(worker_count=3, queue_size=50),
    ProcessorConfig(worker_count=5, queue_size=100),
    ProcessorConfig(worker_count=8, queue_size=200),
    ProcessorConfig(worker_count=10, queue_size=200, max_concurrent_api_calls=5),
]

for config in configs:
    await benchmark(config)
```

### 4.6 Recommended Configurations by Use Case

#### Small Batches (< 100 jobs)

```python
small_batch_config = ProcessorConfig(
    worker_count=3,
    queue_size=50,
    max_concurrent_api_calls=2,
)
```

#### Medium Batches (100-1000 jobs)

```python
medium_batch_config = ProcessorConfig(
    worker_count=5,
    queue_size=100,
    max_concurrent_api_calls=3,
    llm_rate_limit=10,
)
```

#### Large Batches (1000-5000 jobs)

```python
large_batch_config = ProcessorConfig(
    worker_count=8,
    queue_size=200,
    max_concurrent_api_calls=5,
    llm_rate_limit=15,
    db_pool_size=10,
)
```

#### Very Large Batches (5000+ jobs)

```python
very_large_batch_config = ProcessorConfig(
    worker_count=10,
    queue_size=200,
    max_concurrent_api_calls=8,
    llm_rate_limit=20,
    db_pool_size=15,
    db_max_overflow=30,
)
```

---

## 5. Backup and Recovery

### 5.1 Database Backup

#### Automated Backup Script

```bash
#!/bin/bash
# backup_db.sh

BACKUP_DIR="/var/backups/job-pipeline"
DB_FILE="job_automation.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
cp "$DB_FILE" "$BACKUP_DIR/${DB_FILE}.${TIMESTAMP}.bak"

# Compress backup
gzip "$BACKUP_DIR/${DB_FILE}.${TIMESTAMP}.bak"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "Backup completed: ${DB_FILE}.${TIMESTAMP}.bak.gz"
```

#### Scheduled Backups (Cron)

```cron
# Daily backup at 2 AM
0 2 * * * /opt/job-finder/backup_db.sh

# Hourly backup during business hours
0 9-17 * * 1-5 /opt/job-finder/backup_db.sh
```

### 5.2 Database Recovery

#### Restore from Backup

```bash
#!/bin/bash
# restore_db.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.gz>"
    exit 1
fi

# Stop pipeline
systemctl stop job-pipeline

# Decompress backup
gunzip -c "$BACKUP_FILE" > job_automation.db.restored

# Replace current database
mv job_automation.db job_automation.db.old
mv job_automation.db.restored job_automation.db

# Verify database
sqlite3 job_automation.db "PRAGMA integrity_check;"

# Restart pipeline
systemctl start job-pipeline

echo "Database restored from $BACKUP_FILE"
```

### 5.3 Configuration Backup

```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
    .env \
    config/ \
    logs/
```

### 5.4 Disaster Recovery Plan

#### Recovery Time Objectives (RTO)

| Scenario | Target RTO | Steps |
|----------|-----------|-------|
| Database corruption | 15 minutes | Restore from backup |
| Configuration loss | 5 minutes | Restore from config backup |
| Complete system failure | 1 hour | Redeploy from scratch |
| Data center failure | 4 hours | Failover to backup region |

#### Recovery Procedure

```bash
# 1. Stop all pipeline processes
systemctl stop job-pipeline
# or
docker stop job-pipeline

# 2. Restore database
./restore_db.sh /var/backups/job-pipeline/job_automation.db.20240115_020000.bak.gz

# 3. Restore configuration
tar -xzf config_backup_20240115.tar.gz

# 4. Verify configuration
python -c "from src.async_pipeline.config import ProcessorConfig; ProcessorConfig().validate()"

# 5. Restart pipeline
systemctl start job-pipeline
# or
docker start job-pipeline

# 6. Verify operation
tail -f logs/async_pipeline.log

# 7. Check metrics
python -c "from src.async_pipeline import AsyncJobPipeline; print('Pipeline OK')"
```

---

## 6. Maintenance Procedures

### 6.1 Regular Maintenance Tasks

#### Daily Tasks

```bash
# Check logs for errors
grep -i error logs/async_pipeline.log | tail -20

# Verify pipeline is running
systemctl status job-pipeline

# Check disk space
df -h | grep -E "/$|/var"

# Monitor memory usage
free -h
```

#### Weekly Tasks

```bash
# Rotate logs
logrotate /etc/logrotate.d/job-pipeline

# Clean old logs (keep 30 days)
find logs/ -name "*.log.*" -mtime +30 -delete

# Vacuum database (SQLite)
sqlite3 job_automation.db "VACUUM;"

# Check for updates
pip list --outdated

# Review metrics trends
python scripts/metrics_report.py --last-7-days
```

#### Monthly Tasks

```bash
# Full database backup
./backup_db.sh

# Performance benchmark
python scripts/benchmark.py

# Review and optimize configuration
python scripts/config_recommendations.py

# Update dependencies
pip install --upgrade -r requirements.txt

# Security audit
pip-audit
```

### 6.2 Log Rotation

Create `/etc/logrotate.d/job-pipeline`:

```
/opt/job-finder/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 jobuser jobuser
    sharedscripts
    postrotate
        systemctl reload job-pipeline > /dev/null 2>&1 || true
    endscript
}
```

### 6.3 Database Maintenance

#### SQLite Maintenance

```bash
# Vacuum to reclaim space
sqlite3 job_automation.db "VACUUM;"

# Analyze for query optimization
sqlite3 job_automation.db "ANALYZE;"

# Check integrity
sqlite3 job_automation.db "PRAGMA integrity_check;"

# Check foreign keys
sqlite3 job_automation.db "PRAGMA foreign_key_check;"
```

#### PostgreSQL Maintenance

```sql
-- Vacuum analyze
VACUUM ANALYZE jobs;

-- Reindex
REINDEX DATABASE jobs;

-- Check for bloat
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 6.4 Dependency Updates

```bash
# Check for security vulnerabilities
pip-audit

# Update packages
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# Test after updates
python -m pytest tests/

# Verify pipeline still works
python -m src.cli process-async "test" --workers 2 --limit 10
```

---

## 7. Common Failure Modes

### 7.1 Queue Deadlock

**Symptoms**: Queue full, workers idle, no progress

**Cause**: Producer blocked, workers waiting for producer

**Resolution**:
```python
# Fix: Ensure queue has sufficient size
config = ProcessorConfig(
    queue_size=max(100, worker_count * 20)  # Rule of thumb
)
```

### 7.2 Memory Leak

**Symptoms**: Memory usage grows over time, eventual OOM

**Cause**: Unclosed connections, circular references

**Resolution**:
```bash
# 1. Identify leak source
python -m memory_profiler main.py

# 2. Check for unclosed sessions
grep 'session.*not.*closed' logs/async_pipeline.log

# 3. Restart pipeline as temporary fix
systemctl restart job-pipeline

# 4. Fix code and redeploy
```

### 7.3 API Quota Exhaustion

**Symptoms**: Many 429 errors, all jobs failing

**Cause**: Rate limits exceeded API quota

**Resolution**:
```python
# Immediate: Reduce rate limits
config = ProcessorConfig(
    llm_rate_limit=5,      # Cut in half
    email_rate_limit=1,
    max_retries=5,         # More retries
    retry_max_delay=300,   # Longer backoff
)

# Long-term: Request quota increase from API provider
```

### 7.4 Database Lock Contention

**Symptoms**: Many database timeout errors, slow writes

**Cause**: SQLite write contention with many workers

**Resolution**:
```python
# Short-term: Reduce workers
config = ProcessorConfig(worker_count=3)

# Long-term: Migrate to PostgreSQL
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/jobs"
```

### 7.5 Worker Starvation

**Symptoms**: Some workers idle while others busy

**Cause**: Uneven work distribution, blocking operations

**Resolution**:
```python
# Check for blocking operations in processor
# Ensure all I/O is async
# Use asyncio.TimeoutError to prevent indefinite blocking

# Increase worker count to compensate
config = ProcessorConfig(worker_count=8)
```

### 7.6 Cascading Failures

**Symptoms**: One API failure causes all jobs to fail

**Cause**: No circuit breaker, retries exhaust quickly

**Resolution**:
```python
# Increase retry attempts and delays
config = ProcessorConfig(
    max_retries=5,
    retry_base_delay=2.0,
    retry_max_delay=300,  # 5 minutes
    retry_exponential_base=2.5,
)

# Implement circuit breaker pattern (future enhancement)
```

---

## 8. Metrics Interpretation

### 8.1 Understanding Throughput

**Throughput** = Jobs completed per second

| Throughput | Status | Action |
|------------|--------|--------|
| > 4.0 | Excellent | Maintain configuration |
| 3.0 - 4.0 | Good | Optimal for most cases |
| 2.0 - 3.0 | Acceptable | Consider tuning if consistent |
| 1.0 - 2.0 | Poor | Investigate bottlenecks |
| < 1.0 | Critical | Immediate action required |

**Throughput Calculation**:
```python
throughput = total_jobs_completed / total_time_seconds
```

**Factors Affecting Throughput**:
- Worker count
- API latency
- Rate limits
- Queue backpressure
- Database performance

### 8.2 Understanding Success Rate

**Success Rate** = (Completed jobs / Total jobs) × 100

| Success Rate | Status | Action |
|--------------|--------|--------|
| > 95% | Excellent | Normal operation |
| 85-95% | Good | Monitor for trends |
| 75-85% | Concerning | Investigate failures |
| 60-75% | Poor | Immediate investigation |
| < 60% | Critical | Stop and fix issues |

**Common Failure Patterns**:
```bash
# Analyze failure types
grep '"status":"failed"' logs/async_pipeline.log | \
  jq '.error_type' | \
  sort | uniq -c | sort -rn
```

### 8.3 Understanding Processing Time


**Metrics**:
- **Average**: Mean processing time per job
- **Min**: Fastest job processed
- **Max**: Slowest job processed
- **P50/P95/P99**: 50th, 95th, 99th percentile

| Avg Time (ms) | Status | Interpretation |
|---------------|--------|----------------|
| < 1000 | Excellent | Fast APIs, good configuration |
| 1000-2000 | Good | Normal operation |
| 2000-3000 | Acceptable | Consider optimization |
| 3000-5000 | Slow | Investigate bottlenecks |
| > 5000 | Very slow | Serious performance issue |

**Analyzing Distribution**:
```bash
# Get percentiles
grep '"processing_time_ms"' logs/async_pipeline.log | \
  jq '.processing_time_ms' | \
  sort -n | \
  awk '
    {
      values[NR] = $1
      sum += $1
    }
    END {
      print "Count:", NR
      print "Average:", sum/NR
      print "Min:", values[1]
      print "P50:", values[int(NR*0.5)]
      print "P95:", values[int(NR*0.95)]
      print "P99:", values[int(NR*0.99)]
      print "Max:", values[NR]
    }
  '
```

### 8.4 Understanding Queue Metrics

**Queue Size**: Number of jobs waiting in queue

| Queue Size | Status | Interpretation |
|------------|--------|----------------|
| 0-20% full | Healthy | Workers keeping up |
| 20-50% full | Normal | Good buffering |
| 50-80% full | Elevated | Monitor closely |
| 80-95% full | High | Backpressure active |
| 95-100% full | Critical | Producer blocked |

**Queue Health Check**:
```python
metrics = pipeline.get_metrics_snapshot()

queue_utilization = (metrics.current_queue_size / config.queue_size) * 100

if queue_utilization > 80:
    print("WARNING: Queue nearly full, workers may be bottleneck")
    print("Consider: Increasing worker count or reducing rate limits")
```

### 8.5 Understanding Retry Metrics

**Retry Rate** = (Retries / Total attempts) × 100

| Retry Rate | Status | Interpretation |
|------------|--------|----------------|
| 0-5% | Excellent | Stable APIs |
| 5-15% | Normal | Transient errors expected |
| 15-30% | Elevated | API instability |
| 30-50% | High | Serious API issues |
| > 50% | Critical | APIs failing |

**Retry Analysis**:
```bash
# Count retry attempts
grep '"event":"retry_attempt"' logs/async_pipeline.log | \
  jq '.attempt_count' | \
  sort | uniq -c

# Identify most retried operations
grep '"event":"retry_attempt"' logs/async_pipeline.log | \
  jq '.operation' | \
  sort | uniq -c | sort -rn
```

### 8.6 Dashboard Metrics

**Recommended Dashboard Panels**:

1. **Pipeline Overview**
   - Total jobs processed (counter)
   - Success rate (gauge, 0-100%)
   - Current throughput (gauge, jobs/sec)
   
2. **Performance**
   - Avg processing time (line chart, ms)
   - P95 processing time (line chart, ms)
   - Throughput over time (line chart, jobs/sec)
   
3. **Queue Health**
   - Queue size (gauge, 0-max)
   - Queue utilization (gauge, %)
   - Active workers (gauge, count)
   
4. **Error Tracking**
   - Error rate (gauge, %)
   - Retry rate (gauge, %)
   - Errors by type (pie chart)
   
5. **Resource Usage**
   - Memory usage (line chart, MB)
   - CPU usage (line chart, %)
   - Database connections (gauge, count)

---

## 9. Decision Trees

### 9.1 Troubleshooting Decision Tree

```
Pipeline Issue?
│
├─ Not Starting?
│  ├─ Import Errors? → Install dependencies
│  ├─ Config Invalid? → Validate configuration
│  └─ Database Error? → Check database connection
│
├─ Low Throughput?
│  ├─ Queue Full? → Increase workers
│  ├─ High API Latency? → Increase timeouts
│  ├─ Rate Limited? → Reduce rate limits
│  └─ Low Concurrency? → Increase max_concurrent_api_calls
│
├─ High Memory?
│  ├─ Queue Too Large? → Reduce queue_size
│  ├─ Too Many Workers? → Reduce worker_count
│  └─ Memory Leak? → Profile and fix code
│
├─ High Error Rate?
│  ├─ Timeout Errors? → Increase timeouts
│  ├─ 429 Errors? → Reduce rate limits
│  ├─ Database Errors? → Check DB health
│  └─ API Errors? → Check API status
│
└─ Workers Idle?
   ├─ Queue Empty? → Check producer
   ├─ Semaphore Full? → Increase max_concurrent_api_calls
   └─ Worker Crash? → Check error logs
```

### 9.2 Performance Tuning Decision Tree

```
Want to Improve Performance?
│
├─ Improve Throughput?
│  ├─ Step 1: Increase workers (5 → 8)
│  ├─ Step 2: Increase concurrency (3 → 5)
│  ├─ Step 3: Increase queue (100 → 200)
│  └─ Step 4: Optimize rate limits (if API allows)
│
├─ Reduce Memory?
│  ├─ Step 1: Reduce queue (100 → 50)
│  ├─ Step 2: Reduce workers (5 → 3)
│  └─ Step 3: Reduce chunk size (100 → 50)
│
└─ Improve Reliability?
   ├─ Step 1: Increase retries (3 → 5)
   ├─ Step 2: Increase timeouts
   └─ Step 3: Reduce rate limits (prevent 429s)
```

### 9.3 Scaling Decision Tree

```
Need to Scale?
│
├─ < 100 jobs?
│  └─ Config: 3 workers, queue=50
│
├─ 100-1000 jobs?
│  └─ Config: 5 workers, queue=100, API=3
│
├─ 1000-5000 jobs?
│  └─ Config: 8 workers, queue=200, API=5
│     + PostgreSQL recommended
│
└─ 5000+ jobs?
   └─ Config: 10-15 workers, queue=200, API=8
      + PostgreSQL required
      + Multiple instances (horizontal scaling)
      + Load balancer for API calls
```

### 9.4 Alert Response Decision Tree

```
Alert Received?
│
├─ Critical: Throughput < 1 jobs/sec
│  ├─ Check: Are workers running?
│  ├─ Check: Is queue blocked?
│  ├─ Check: Are APIs responding?
│  └─ Action: Restart pipeline if needed
│
├─ Warning: Success Rate < 85%
│  ├─ Check: What error types?
│  ├─ Timeout? → Increase timeouts
│  ├─ 429? → Reduce rate limits
│  └─ API down? → Wait and retry
│
├─ Warning: Memory > 3 GB
│  ├─ Check: Is memory growing?
│  ├─ Yes? → Memory leak, restart
│  └─ No? → Reduce queue/workers
│
└─ Critical: Database Errors
   ├─ Connection pool exhausted?
   ├─ Database locked?
   └─ Action: Check DB health, increase pool
```

---

## 10. Quick Reference

### 10.1 Common Commands

```bash
# Start pipeline
python -m src.cli process-async "query" --workers 5

# Check status
systemctl status job-pipeline

# View logs
tail -f logs/async_pipeline.log

# Monitor resources
top -p $(pgrep -f python.*async)

# Test configuration
python test_config.py

# Backup database
./backup_db.sh

# Restore database
./restore_db.sh backup_file.gz
```

### 10.2 Configuration Quick Reference

| Setting | Default | Range | Purpose |
|---------|---------|-------|---------|
| worker_count | 5 | 1-20 | Concurrent workers |
| queue_size | 100 | 10-500 | Buffer size |
| max_concurrent_api_calls | 3 | 1-20 | API concurrency |
| llm_rate_limit | 10 | 1-50 | LLM requests/sec |
| email_rate_limit | 2 | 1-10 | Email requests/sec |
| scraper_rate_limit | 30 | 10-100 | Scraper requests/sec |
| max_retries | 3 | 0-10 | Retry attempts |
| llm_timeout | 30 | 10-300 | LLM timeout (sec) |

### 10.3 Log Patterns Quick Reference

| Pattern | Command |
|---------|---------|
| Error count | `grep -c '"level":"error"' logs/async_pipeline.log` |
| Retry count | `grep -c '"event":"retry_attempt"' logs/async_pipeline.log` |
| Timeout errors | `grep '"error_type":"TimeoutError"' logs/async_pipeline.log` |
| Rate limit errors | `grep '429' logs/async_pipeline.log` |
| Average processing time | `grep '"processing_time_ms"' logs/async_pipeline.log \| jq '.processing_time_ms' \| awk '{sum+=$1; count++} END {print sum/count}'` |

### 10.4 Health Check Script

```python
#!/usr/bin/env python
"""Quick health check for async pipeline."""
import json
import sys
from pathlib import Path

def health_check():
    """Perform health check."""
    checks = {
        'logs_exist': Path('logs/async_pipeline.log').exists(),
        'db_exists': Path('job_automation.db').exists(),
        'config_valid': False,
    }
    
    # Check configuration
    try:
        from src.async_pipeline.config import ProcessorConfig
        config = ProcessorConfig()
        config.validate()
        checks['config_valid'] = True
    except Exception as e:
        print(f"Config error: {e}")
    
    # Check recent errors
    error_count = 0
    if checks['logs_exist']:
        with open('logs/async_pipeline.log') as f:
            for line in f.readlines()[-100:]:  # Last 100 lines
                try:
                    log = json.loads(line)
                    if log.get('level') == 'error':
                        error_count += 1
                except:
                    continue
    
    checks['recent_errors'] = error_count
    
    # Print results
    print("=== Pipeline Health Check ===")
    for check, status in checks.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {check}: {status}")
    
    # Overall status
    if all([checks['logs_exist'], checks['db_exists'], checks['config_valid']]):
        if error_count < 10:
            print("\n✓ System healthy")
            return 0
        else:
            print(f"\n⚠ System degraded ({error_count} recent errors)")
            return 1
    else:
        print("\n✗ System unhealthy")
        return 2

if __name__ == '__main__':
    sys.exit(health_check())
```

### 10.5 Emergency Procedures

#### Emergency Stop

```bash
# Graceful stop
systemctl stop job-pipeline

# Force stop (if graceful fails)
pkill -9 -f "python.*async_pipeline"

# Docker stop
docker stop job-pipeline
docker kill job-pipeline  # Force stop
```

#### Emergency Restart

```bash
# Quick restart
systemctl restart job-pipeline

# Full restart with cleanup
systemctl stop job-pipeline
# Wait for cleanup
sleep 5
# Clear any locks
rm -f /tmp/*.lock
# Restart
systemctl start job-pipeline
```

#### Emergency Rollback

```bash
# 1. Stop pipeline
systemctl stop job-pipeline

# 2. Restore database
./restore_db.sh /var/backups/job-pipeline/latest.bak.gz

# 3. Restore configuration
tar -xzf config_backup_latest.tar.gz

# 4. Restart
systemctl start job-pipeline

# 5. Verify
tail -f logs/async_pipeline.log
```

---

## 11. Contact and Escalation

### 11.1 Support Tiers

| Issue Severity | Response Time | Escalation Path |
|----------------|---------------|-----------------|
| Critical (pipeline down) | 15 minutes | On-call engineer → Team lead |
| High (degraded performance) | 1 hour | Email engineer → Team lead |
| Medium (errors increasing) | 4 hours | Ticket → Engineer |
| Low (questions) | 24 hours | Documentation → Ticket |

### 11.2 Useful Resources

- **Design Document**: `.kiro/specs/async-job-pipeline-refactor/design.md`
- **Requirements**: `.kiro/specs/async-job-pipeline-refactor/requirements.md`
- **Migration Guide**: `docs/async_pipeline_migration.md`
- **Quick Start**: `ASYNC_PIPELINE_QUICK_START.md`
- **Metrics Guide**: `src/async_pipeline/METRICS_GUIDE.md`
- **Logging Guide**: `src/async_pipeline/STRUCTURED_LOGGING_GUIDE.md`

---


## Appendix A: Metrics Collection Examples

### Example 1: Exporting Metrics to Prometheus

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Define metrics
jobs_processed = Counter('jobs_processed_total', 'Total jobs processed')
jobs_failed = Counter('jobs_failed_total', 'Total jobs failed')
processing_time = Histogram('job_processing_seconds', 'Job processing time')
queue_size = Gauge('queue_size', 'Current queue size')
active_workers = Gauge('active_workers', 'Number of active workers')

# Update metrics in callback
def metrics_callback(metrics):
    jobs_processed.inc()
    if metrics['status'] == 'failed':
        jobs_failed.inc()
    processing_time.observe(metrics['processing_time_ms'] / 1000)
    queue_size.set(metrics['queue_size'])
    active_workers.set(metrics['active_workers'])

# Start Prometheus server
start_http_server(8001)

# Use callback
pipeline.set_progress_callback(metrics_callback)
```

### Example 2: Sending Metrics to CloudWatch

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def send_to_cloudwatch(metrics):
    """Send metrics to AWS CloudWatch."""
    cloudwatch.put_metric_data(
        Namespace='JobPipeline',
        MetricData=[
            {
                'MetricName': 'Throughput',
                'Value': metrics['throughput'],
                'Unit': 'Count/Second',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'SuccessRate',
                'Value': metrics['success_rate'],
                'Unit': 'Percent',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'QueueSize',
                'Value': metrics['queue_size'],
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }
        ]
    )

pipeline.set_progress_callback(send_to_cloudwatch)
```

---

## Appendix B: Advanced Configuration Examples

### Example 1: Multi-Region Deployment

```python
# US East region configuration
us_east_config = ProcessorConfig(
    worker_count=10,
    queue_size=200,
    db_url="postgresql+asyncpg://user:pass@us-east-db.example.com/jobs",
    llm_rate_limit=20,
)

# EU West region configuration
eu_west_config = ProcessorConfig(
    worker_count=8,
    queue_size=150,
    db_url="postgresql+asyncpg://user:pass@eu-west-db.example.com/jobs",
    llm_rate_limit=15,
)
```

### Example 2: Environment-Specific Configuration

```python
import os

# Development
if os.getenv('ENV') == 'development':
    config = ProcessorConfig(
        worker_count=2,
        queue_size=20,
        log_level='DEBUG',
    )

# Staging
elif os.getenv('ENV') == 'staging':
    config = ProcessorConfig(
        worker_count=5,
        queue_size=100,
        log_level='INFO',
    )

# Production
else:
    config = ProcessorConfig(
        worker_count=10,
        queue_size=200,
        log_level='WARNING',
        db_url=os.getenv('DATABASE_URL'),
    )
```

---

## Appendix C: Monitoring Scripts

### System Health Monitor

```bash
#!/bin/bash
# monitor.sh - Continuous health monitoring

while true; do
    clear
    echo "=== Async Pipeline Monitor ==="
    echo "Time: $(date)"
    echo ""
    
    # Pipeline status
    echo "Pipeline Status:"
    systemctl status job-pipeline | grep Active
    echo ""
    
    # Resource usage
    echo "Resource Usage:"
    ps aux | grep python.*async | grep -v grep | \
        awk '{printf "  CPU: %s%%  Memory: %s%%  PID: %s\n", $3, $4, $2}'
    echo ""
    
    # Recent metrics
    echo "Recent Metrics (last 10 entries):"
    tail -10 logs/async_pipeline.log | \
        jq -r 'select(.throughput) | "  Throughput: \(.throughput) jobs/sec  Success: \(.success_rate)%"' | \
        tail -1
    echo ""
    
    # Recent errors
    echo "Recent Errors (last 5 minutes):"
    grep '"level":"error"' logs/async_pipeline.log | \
        tail -5 | \
        jq -r '"  [\(.timestamp)] \(.error_type): \(.error_message)"'
    echo ""
    
    # Wait 10 seconds
    sleep 10
done
```

### Automated Alert Script

```python
#!/usr/bin/env python
"""Automated alerting based on metrics."""
import json
import time
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

ALERT_EMAIL = "ops@example.com"
LOG_FILE = "logs/async_pipeline.log"

def check_alerts():
    """Check for alert conditions."""
    metrics = get_latest_metrics()
    alerts = []
    
    # Check throughput
    if metrics.get('throughput', 0) < 1.0:
        alerts.append({
            'severity': 'critical',
            'metric': 'throughput',
            'value': metrics['throughput'],
            'message': f"Throughput critically low: {metrics['throughput']:.2f} jobs/sec"
        })
    
    # Check success rate
    if metrics.get('success_rate', 100) < 75:
        alerts.append({
            'severity': 'critical',
            'metric': 'success_rate',
            'value': metrics['success_rate'],
            'message': f"Success rate critically low: {metrics['success_rate']:.1f}%"
        })
    
    # Check error rate
    recent_errors = count_recent_errors(minutes=5)
    if recent_errors > 20:
        alerts.append({
            'severity': 'warning',
            'metric': 'error_rate',
            'value': recent_errors,
            'message': f"High error rate: {recent_errors} errors in 5 minutes"
        })
    
    return alerts

def get_latest_metrics():
    """Get latest metrics from log file."""
    with open(LOG_FILE) as f:
        for line in reversed(list(f)):
            try:
                log = json.loads(line)
                if 'throughput' in log:
                    return log
            except:
                continue
    return {}

def count_recent_errors(minutes=5):
    """Count errors in recent time window."""
    import time
    cutoff = time.time() - (minutes * 60)
    count = 0
    
    with open(LOG_FILE) as f:
        for line in f:
            try:
                log = json.loads(line)
                if log.get('level') == 'error':
                    # Parse timestamp and check if recent
                    count += 1
            except:
                continue
    
    return count

def send_alert(alerts):
    """Send alert email."""
    if not alerts:
        return
    
    body = "Async Pipeline Alerts:\n\n"
    for alert in alerts:
        body += f"[{alert['severity'].upper()}] {alert['message']}\n"
    
    msg = MIMEText(body)
    msg['Subject'] = f"[{alerts[0]['severity'].upper()}] Pipeline Alert"
    msg['From'] = "pipeline@example.com"
    msg['To'] = ALERT_EMAIL
    
    # Send email (configure SMTP)
    # smtp = smtplib.SMTP('localhost')
    # smtp.send_message(msg)
    # smtp.quit()
    
    print(body)  # For testing

if __name__ == '__main__':
    while True:
        alerts = check_alerts()
        if alerts:
            send_alert(alerts)
        time.sleep(60)  # Check every minute
```

---

## Document Version

- **Version**: 1.0
- **Last Updated**: 2024-01-15
- **Author**: Operations Team
- **Status**: Production Ready

---

## Changelog

### Version 1.0 (2024-01-15)
- Initial release
- Comprehensive deployment procedures
- Monitoring and alerting guidelines
- Troubleshooting decision trees
- Performance tuning guide
- Backup and recovery procedures
- Maintenance schedules
- Metrics interpretation guide
- Quick reference sections

---

**End of Async Job Pipeline Operations Guide**
