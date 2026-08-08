# NEXUS Configuration Best Practices

This guide covers configuration best practices for the NEXUS async job pipeline across different deployment environments.

## Environment Profiles

NEXUS supports three environment-specific profiles, selected via the `NEXUS_ENV` environment variable:

```bash
# Development (default if not set)
export NEXUS_ENV=development

# Staging for pre-production testing
export NEXUS_ENV=staging

# Production for optimized performance
export NEXUS_ENV=production
```

### Profile Comparison

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| Worker Count | 2 | 5 | 10 |
| Queue Size | 20 | 50 | 100 |
| Max Retries | 2 | 3 | 5 |
| Log Level | DEBUG | INFO | WARNING |
| Auto-Send Emails | ❌ | ✅ | ✅ |
| Progress Bar | ✅ | ✅ | ❌ |
| LLM Rate Limit | 5/s | 8/s | 15/s |
| Email Rate Limit | 0.5/s | 1/s | 2/s |
| Shutdown Timeout | 30s | 60s | 120s |

---

## 1. Selecting the Right Profile

### Development Profile

Best for: Local development, debugging, testing new features

```bash
export NEXUS_ENV=development
python main.py
```

Characteristics:
- **Low throughput** (2 workers) - easier to debug
- **Verbose logging** (DEBUG level) - see everything
- **Emails disabled** - prevent accidental sends
- **Shorter timeouts** - faster feedback loops
- **Quick shutdown** (30s) - fast iteration

### Staging Profile

Best for: Pre-production testing, integration testing, QA environments

```bash
export NEXUS_ENV=staging
python main.py
```

Characteristics:
- **Moderate throughput** (5 workers) - production-like
- **Info logging** - balanced visibility
- **Emails enabled** - test delivery
- **Standard timeouts** - production-like behavior
- **Standard shutdown** (60s)

### Production Profile

Best for: Production deployment, high-volume processing

```bash
export NEXUS_ENV=production
python main.py
```

Characteristics:
- **High throughput** (10 workers) - maximum performance
- **Minimal logging** (WARNING) - reduce noise
- **Emails enabled** - full operation
- **Aggressive retries** (5 attempts) - maximum reliability
- **Extended shutdown** (120s) - wait for in-flight jobs

---

## 2. Customizing Configurations

### Override Profile Defaults

```python
from src.async_pipeline.config import ProcessorConfig, get_current_profile

# Start with production but use fewer workers
config = ProcessorConfig.from_profile("production", worker_count=5)

# Start with staging but enable debug logging
config = ProcessorConfig.from_profile("staging", log_level="DEBUG")

# Load from environment with overrides
profile = get_current_profile()  # Reads NEXUS_ENV
config = ProcessorConfig.from_profile(profile, max_retries=10)
```

### Environment Variable Overrides

Individual settings can be overridden via environment variables:

```bash
# Override worker count regardless of profile
export PIPELINE_WORKER_COUNT=15

# Override rate limit
export PIPELINE_LLM_RATE_LIMIT=20.0

# Then load config
python -c "from src.async_pipeline.config import ProcessorConfig; print(ProcessorConfig.from_env().worker_count)"
```

### Configuration Files

For complex configurations, use YAML or JSON files:

```yaml
# config/production.yaml
worker_count: 15
max_concurrent_api_calls: 25
queue_size: 150
max_retries: 5
llm_rate_limit: 20.0
log_level: WARNING
```

```python
config = ProcessorConfig.from_yaml("config/production.yaml")
```

---

## 3. Performance Tuning

### Worker Count

**Rule of thumb**: `workers <= (API rate limit × average processing time)`

```python
# Example: LLM rate limit = 10/s, average LLM call = 3s
# Maximum useful workers ≈ 10 × 3 = 30
# Start lower and increase based on monitoring

config = ProcessorConfig.from_profile("production", worker_count=10)
```

**Guidelines**:
- Start with 5 workers and monitor
- Increase if workers are idle
- Decrease if hitting API rate limits
- Maximum 50 workers (diminishing returns beyond)

### Queue Size

**Rule of thumb**: `queue_size = 2-4 × worker_count`

```python
# For 10 workers, use 20-40 queue size
config = ProcessorConfig.from_profile("production", 
    worker_count=10,
    queue_size=30
)
```

**Guidelines**:
- Minimum 10 for adequate buffering
- Larger queues improve batching efficiency
- Very large queues increase memory usage

### Rate Limits

Configure based on external API quotas:

```python
config = ProcessorConfig.from_profile("production",
    llm_rate_limit=10.0,      # Ollama can handle more; Gemini has quotas
    email_rate_limit=1.0,      # Keep low to avoid spam detection
    scraper_rate_limit=5.0     # Respect site rate limits
)
```

---

## 4. Reliability Settings

### Retry Configuration

```python
config = ProcessorConfig.from_profile("production",
    max_retries=5,          # Number of retry attempts
    base_delay=1.0,         # Initial delay (seconds)
    max_delay=60.0,         # Maximum delay cap
    exponential_base=2.0,   # Backoff multiplier
    retry_jitter=True       # Add randomization
)
```

**Retry delay formula**: `delay = min(base_delay × exponential_base^attempt, max_delay)`

| Attempt | Delay (base=1, exp=2, max=60) |
|---------|-------------------------------|
| 1 | 1s |
| 2 | 2s |
| 3 | 4s |
| 4 | 8s |
| 5 | 16s |

### Timeout Configuration

```python
config = ProcessorConfig.from_profile("production",
    llm_timeout_seconds=30.0,     # LLM calls can be slow
    email_timeout_seconds=15.0,   # SMTP operations
    scraper_timeout_seconds=20.0, # Page loads
    db_timeout_seconds=10.0       # Database queries
)
```

**Guidelines**:
- LLM timeout: 20-30s (model loading can be slow)
- Email timeout: 10-15s (SMTP is usually fast)
- Scraper timeout: 15-20s (depends on target sites)
- DB timeout: 5-10s (should be fast for local DB)

---

## 5. Database Configuration

### Connection Pool

```python
config = ProcessorConfig.from_profile("production",
    db_pool_size=20,        # Base pool size
    db_max_overflow=30      # Extra connections for bursts
)
```

**Guidelines**:
- `db_pool_size >= worker_count`
- `db_max_overflow = 1.5-2 × db_pool_size`
- Total max connections = pool_size + max_overflow

### Chunk Size

```python
config = ProcessorConfig.from_profile("production",
    chunk_size=100  # Jobs per database query
)
```

**Memory usage**: O(chunk_size), not O(total_jobs)

---

## 6. Logging Configuration

### Log Levels by Environment

| Environment | Log Level | Use Case |
|-------------|-----------|----------|
| Development | DEBUG | See all details |
| Staging | INFO | Balanced visibility |
| Production | WARNING | Reduce noise |

### Structured Logging

Always use structured logging for log aggregation:

```python
config = ProcessorConfig.from_profile("production",
    structured_logging=True,
    log_file="logs/processor.log"
)
```

Log files are automatically rotated at 5MB with 5 backups.

---

## 7. Graceful Shutdown

Configure shutdown timeout based on job processing time:

```python
# If average job takes 5s, and you want to wait for 20 in-flight jobs:
# timeout = 5s × 20 = 100s

config = ProcessorConfig.from_profile("production",
    shutdown_timeout_seconds=120.0
)
```

**Signal handling**:
- SIGTERM: Graceful shutdown (stop accepting, wait for in-flight)
- SIGINT: Same as SIGTERM
- After timeout: Force termination

---

## 8. Security Considerations

### Environment-Specific Credentials

```bash
# .env.development
DATABASE_URL=sqlite:///dev_job_automation.db
OLLAMA_HOST=http://localhost:11434

# .env.production (use secrets manager)
DATABASE_URL=postgresql://user:${DB_PASSWORD}@prod-db:5432/nexus
```

### Email Safety

```python
# Development: ALWAYS disable auto-send
config = ProcessorConfig.from_profile("development",
    auto_send_emails=False  # Default in development
)

# Production: Enable with rate limits
config = ProcessorConfig.from_profile("production",
    auto_send_emails=True,
    email_delay_seconds=30.0  # Rate limit
)
```

---

## 9. Monitoring Recommendations

### Key Metrics by Environment

**Development**:
- Processing errors (immediate visibility)
- Queue backpressure events

**Staging**:
- End-to-end processing time
- API error rates
- Email delivery success rate

**Production**:
- Throughput (jobs/second)
- P95/P99 latency
- Worker utilization
- Queue depth over time
- API rate limit headroom
- Error rate by type

### Example Monitoring Setup

```python
from src.async_pipeline import AsyncJobPipeline, ProcessorConfig

config = ProcessorConfig.from_profile("production")
pipeline = AsyncJobPipeline(config=config)

# After processing
stats = pipeline.stats
print(f"Throughput: {stats.throughput_jobs_per_second:.2f} jobs/s")
print(f"P95 Latency: {stats.latency_p95_ms:.0f}ms")
print(f"Success Rate: {stats.success_rate * 100:.1f}%")
```

---

## 10. Troubleshooting

### Common Issues

**Low Throughput**:
1. Check worker count (increase if workers are idle)
2. Check rate limits (increase if not hitting API quotas)
3. Check database performance (optimize queries)

**High Memory Usage**:
1. Reduce queue_size
2. Reduce chunk_size
3. Check for memory leaks in custom processors

**Frequent Timeouts**:
1. Increase timeout values
2. Check external service health
3. Consider adding more retries

**Backpressure Events**:
1. Increase queue_size
2. Increase worker_count
3. Check for slow downstream services

---

## Quick Reference

### Minimum Configuration

```python
# Use defaults from profile
config = ProcessorConfig.from_profile(get_current_profile())
```

### Development Configuration

```python
config = ProcessorConfig.from_profile("development")
# worker_count=2, log_level=DEBUG, auto_send_emails=False
```

### Production Configuration

```python
config = ProcessorConfig.from_profile("production",
    worker_count=15,          # Adjust based on load
    max_retries=5,            # High reliability
    shutdown_timeout_seconds=180.0  # Wait for in-flight jobs
)
```

### Configuration Validation

```python
config = ProcessorConfig.from_profile("production", worker_count=-1)
# Raises: ValueError: worker_count must be positive, got -1
```

All configurations are automatically validated on creation.
