# Configuration Guide

## Overview

The NEXUS async pipeline provides flexible configuration through environment-specific profiles, environment variables, and configuration files. This guide covers configuration best practices for different deployment scenarios.

## Quick Start

### Using Profiles (Recommended)

The simplest way to configure the pipeline is using environment profiles:

```python
from src.async_pipeline.config import ProcessorConfig

# Development (local debugging)
config = ProcessorConfig.from_profile("development")

# Staging (pre-production testing)
config = ProcessorConfig.from_profile("staging")

# Production (high performance)
config = ProcessorConfig.from_profile("production")
```

### Environment Variable Selection

Set the `PIPELINE_PROFILE` environment variable to automatically select a profile:

```bash
# In .env or shell
export PIPELINE_PROFILE=production

# In Python
from src.async_pipeline.config import ProcessorConfig, get_current_profile

profile = get_current_profile()  # Returns "production"
config = ProcessorConfig.from_profile(profile)
```

## Environment Profiles

### Development Profile

**Use Case:** Local development, debugging, testing new features

**Characteristics:**
- **Low concurrency:** 2 workers to avoid overwhelming local services
- **Verbose logging:** DEBUG level with detailed output
- **Short timeouts:** Fast feedback for debugging (20s LLM, 10s email)
- **Conservative rate limits:** 5 LLM calls/s, 0.5 emails/s
- **Disabled outreach:** `auto_send_emails=False` to prevent accidental sends
- **Small database pool:** 3 connections for local SQLite
- **Quick shutdown:** 30s timeout for fast iteration

**Typical Setup:**
```python
config = ProcessorConfig.from_profile("development")

# Override specific settings
config = ProcessorConfig.from_profile(
    "development",
    worker_count=1,           # Single worker for debugging
    log_level="DEBUG",        # Maximum verbosity
    enable_progress_bar=True  # Visual feedback
)
```

**Environment Variables:**
```bash
PIPELINE_PROFILE=development
PIPELINE_WORKER_COUNT=1
PIPELINE_LOG_LEVEL=DEBUG
PIPELINE_AUTO_SEND_EMAILS=false
```

### Staging Profile

**Use Case:** Pre-production testing, integration testing, QA validation

**Characteristics:**
- **Moderate concurrency:** 5 workers for realistic load testing
- **Standard logging:** INFO level with structured logs
- **Standard timeouts:** 25s LLM, 12s email
- **Moderate rate limits:** 8 LLM calls/s, 1 email/s
- **Enabled outreach:** With conservative delays (20s between emails)
- **Medium database pool:** 8 connections for staging database
- **Standard shutdown:** 60s timeout

**Typical Setup:**
```python
config = ProcessorConfig.from_profile("staging")

# Override for load testing
config = ProcessorConfig.from_profile(
    "staging",
    worker_count=8,           # Higher concurrency for load tests
    max_retries=5,            # More aggressive retry
    log_level="INFO"          # Standard logging
)
```

**Environment Variables:**
```bash
PIPELINE_PROFILE=staging
PIPELINE_WORKER_COUNT=5
PIPELINE_LOG_LEVEL=INFO
PIPELINE_AUTO_SEND_EMAILS=true
PIPELINE_EMAIL_DELAY_SECONDS=20.0
```

### Production Profile

**Use Case:** Production deployment, high-throughput processing

**Characteristics:**
- **High concurrency:** 10 workers for maximum throughput
- **Minimal logging:** WARNING level to reduce overhead
- **Longer timeouts:** 30s LLM, 15s email for reliability
- **Optimized rate limits:** 15 LLM calls/s, 2 emails/s
- **Fully enabled outreach:** With proper rate limiting (30s between emails)
- **Large database pool:** 20 connections + 30 overflow
- **Extended shutdown:** 120s timeout for in-flight jobs
- **No progress bar:** Disabled to reduce overhead
- **Higher quality threshold:** min_match_score=60

**Typical Setup:**
```python
config = ProcessorConfig.from_profile("production")

# Override for specific workload
config = ProcessorConfig.from_profile(
    "production",
    worker_count=20,          # Scale up for large batches
    max_retries=5,            # Aggressive retry for reliability
    log_level="WARNING"       # Minimal logging overhead
)
```

**Environment Variables:**
```bash
PIPELINE_PROFILE=production
PIPELINE_WORKER_COUNT=10
PIPELINE_LOG_LEVEL=WARNING
PIPELINE_ENABLE_PROGRESS_BAR=false
PIPELINE_MIN_MATCH_SCORE=60
```

## Configuration Methods

### 1. Profile-Based (Recommended)

**Pros:**
- Sensible defaults for each environment
- Easy to switch between environments
- Consistent configuration across team

**Usage:**
```python
from src.async_pipeline.config import ProcessorConfig

config = ProcessorConfig.from_profile("production")
```

### 2. Environment Variables

**Pros:**
- 12-factor app compliance
- Easy to configure in containerized environments
- No code changes required

**Usage:**
```bash
export PIPELINE_PROFILE=production
export PIPELINE_WORKER_COUNT=15
export PIPELINE_LOG_LEVEL=INFO
```

```python
from src.async_pipeline.config import ProcessorConfig, get_current_profile

profile = get_current_profile()
config = ProcessorConfig.from_profile(profile)
```

### 3. Configuration Files

**Pros:**
- Version controlled configuration
- Complex nested configuration
- Comments and documentation

**YAML Example:**
```yaml
# config/production.yaml
worker_count: 15
max_concurrent_api_calls: 20
queue_size: 200
max_retries: 5

# Rate limiting
llm_rate_limit: 15.0
email_rate_limit: 2.0
scraper_rate_limit: 8.0

# Timeouts
llm_timeout_seconds: 30.0
email_timeout_seconds: 15.0

# Database
db_pool_size: 20
db_max_overflow: 30

# Logging
log_level: WARNING
structured_logging: true
```

**Usage:**
```python
config = ProcessorConfig.from_yaml("config/production.yaml")
```

**JSON Example:**
```json
{
  "worker_count": 15,
  "max_concurrent_api_calls": 20,
  "queue_size": 200,
  "max_retries": 5,
  "llm_rate_limit": 15.0,
  "log_level": "WARNING"
}
```

**Usage:**
```python
config = ProcessorConfig.from_json("config/production.json")
```

### 4. Constructor Arguments

**Pros:**
- Maximum flexibility
- Programmatic configuration
- Override specific values

**Usage:**
```python
config = ProcessorConfig(
    worker_count=10,
    queue_size=100,
    max_retries=3,
    llm_rate_limit=10.0,
    log_level="INFO"
)
```

## Configuration Hierarchy

Configuration values are resolved in the following order (later values override earlier ones):

1. **Profile defaults** (from `PROFILE_DEFAULTS`)
2. **Environment variables** (via `from_env()`)
3. **Configuration file** (via `from_yaml()` or `from_json()`)
4. **Constructor arguments** (direct parameters)

**Example:**
```python
# Start with production profile
config = ProcessorConfig.from_profile(
    "production",
    worker_count=15,         # Override profile default (10)
    log_level="INFO"         # Override profile default (WARNING)
)

# Environment variable PIPELINE_WORKER_COUNT=20 would override this
# if using from_env() instead of from_profile()
```

## Best Practices

### 1. Use Profiles for Environment Separation

**DO:**
```python
# Development
config = ProcessorConfig.from_profile("development")

# Production
config = ProcessorConfig.from_profile("production")
```

**DON'T:**
```python
# Manually configure everything
config = ProcessorConfig(
    worker_count=2 if os.getenv("ENV") == "dev" else 10,
    log_level="DEBUG" if os.getenv("ENV") == "dev" else "WARNING",
    # ... many more conditionals
)
```

### 2. Override Selectively

**DO:**
```python
# Use profile defaults, override only what's needed
config = ProcessorConfig.from_profile(
    "production",
    worker_count=20  # Scale up for batch processing
)
```

**DON'T:**
```python
# Override everything unnecessarily
config = ProcessorConfig.from_profile(
    "production",
    worker_count=20,
    queue_size=100,      # Already the production default
    log_level="WARNING", # Already the production default
    # ...
)
```

### 3. Validate Configuration

Always call `.validate()` after creating configuration:

```python
config = ProcessorConfig.from_profile("production")
config.validate()  # Raises ValueError if invalid
```

Validation is automatic when using factory methods (`from_profile`, `from_env`, `from_yaml`, `from_json`).

### 4. Environment-Specific .env Files

Create separate `.env` files for each environment:

```bash
# .env.development
PIPELINE_PROFILE=development
PIPELINE_WORKER_COUNT=2
PIPELINE_LOG_LEVEL=DEBUG
PIPELINE_AUTO_SEND_EMAILS=false

# .env.staging
PIPELINE_PROFILE=staging
PIPELINE_WORKER_COUNT=5
PIPELINE_LOG_LEVEL=INFO

# .env.production
PIPELINE_PROFILE=production
PIPELINE_WORKER_COUNT=10
PIPELINE_LOG_LEVEL=WARNING
```

Load the appropriate file:
```bash
# Load development config
source .env.development

# Or use docker-compose
docker-compose --env-file .env.production up
```

### 5. Document Custom Configurations

When overriding defaults, document why:

```python
config = ProcessorConfig.from_profile(
    "production",
    worker_count=20,     # Increased for nightly batch processing
    max_retries=10,      # High retry for unreliable third-party API
    log_level="INFO"     # Verbose logging during migration period
)
```

## Tuning Guidelines

### Worker Count

**Formula:** `worker_count = min(CPU_cores, max_concurrent_api_calls, db_pool_size / 2)`

**Guidelines:**
- **Development:** 1-2 workers for debugging
- **Staging:** 3-5 workers for realistic testing
- **Production:** 5-20 workers depending on:
  - API rate limits (don't exceed external quotas)
  - Database capacity (ensure pool_size ≥ worker_count)
  - CPU cores (workers are I/O bound, can exceed core count)

**Example:**
```python
# 4 CPU cores, 100 LLM API calls/min quota, 20 DB connections
worker_count = min(4, 100/60/2, 20/2) = min(4, 0.83, 10) = 0.83
# Round up to 1-2 workers to stay within LLM quota
```

### Queue Size

**Formula:** `queue_size = worker_count × 10` (buffer 10 jobs per worker)

**Guidelines:**
- Larger queue = more memory, better throughput
- Smaller queue = less memory, more backpressure
- Minimum: 10 (ensures buffering)
- Typical: 50-200

### Rate Limits

**LLM Rate Limit:**
- Check provider quota (e.g., OpenAI: 3,500 requests/min = 58 req/s)
- Set limit below quota to avoid throttling: `llm_rate_limit = quota * 0.8`
- Development: 5-10 req/s
- Production: 10-20 req/s

**Email Rate Limit:**
- Gmail SMTP: 500 emails/day = ~0.006 emails/s
- Set conservative limit: 0.5-2 req/s
- Add delays between sends for better reputation

**Scraper Rate Limit:**
- Respect robots.txt and API terms
- Typical: 2-10 req/s
- Use exponential backoff on rate limit errors

### Timeouts

**Guidelines:**
- LLM: 20-30s (typical response: 2-5s)
- Email: 10-15s (typical send: 1-3s)
- Scraper: 15-20s (typical page load: 2-10s)
- Database: 5-10s (typical query: <1s)

**Set timeouts 3-5x expected latency for safety margin**

### Retry Parameters

**Conservative (Development):**
```python
max_retries=2
base_delay=0.5
max_delay=10.0
```

**Standard (Staging):**
```python
max_retries=3
base_delay=1.0
max_delay=30.0
```

**Aggressive (Production):**
```python
max_retries=5
base_delay=1.0
max_delay=60.0
```

**Retry Delay Formula:**
```
delay = min(base_delay × (exponential_base ^ attempt), max_delay) + jitter
```

### Database Pool

**Formula:** `pool_size ≥ worker_count + 5` (headroom for admin operations)

**Guidelines:**
- SQLite: 3-10 connections (limited concurrency)
- PostgreSQL: 10-50 connections (based on max_connections)
- Set `max_overflow = pool_size × 1.5` for burst capacity

## Monitoring Configuration

### Key Metrics to Track

1. **Worker utilization:** Should be 70-90% (not idle, not overloaded)
2. **Queue depth:** Should fluctuate 0-queue_size (backpressure working)
3. **Rate limiter waits:** Should be minimal (<10% of time)
4. **Retry rate:** Should be <5% of requests
5. **Timeout rate:** Should be <1% of requests

### Logging Levels

- **DEBUG:** Development only (very verbose)
- **INFO:** Staging and troubleshooting (structured logs)
- **WARNING:** Production default (errors and warnings only)
- **ERROR:** Production minimal (errors only)
- **CRITICAL:** Production minimal (critical failures only)

## Troubleshooting

### Issue: Low Throughput

**Symptoms:** Jobs/second below expected

**Check:**
1. Worker utilization (should be 70-90%)
2. Queue depth (should be near capacity)
3. Rate limiter waits (minimize API blocking)
4. Retry rate (reduce transient failures)

**Fixes:**
- Increase `worker_count` (if utilization is high)
- Increase `queue_size` (if queue is always full)
- Increase rate limits (if waits are frequent)
- Optimize retry settings (reduce unnecessary retries)

### Issue: High Memory Usage

**Symptoms:** Memory growing unbounded

**Check:**
1. Queue size (bounded?)
2. Chunk size (streaming working?)
3. Result accumulation (discarding results?)

**Fixes:**
- Reduce `queue_size` (limit buffering)
- Reduce `chunk_size` (smaller batches)
- Ensure results are not accumulated in memory

### Issue: Frequent Timeouts

**Symptoms:** Many jobs failing with timeout errors

**Check:**
1. Timeout settings (too short?)
2. External API latency (provider issues?)
3. Network latency (connectivity problems?)

**Fixes:**
- Increase timeout values (allow more time)
- Check API provider status
- Investigate network latency

### Issue: Rate Limit Errors

**Symptoms:** 429 errors from external APIs

**Check:**
1. Rate limit settings (too high?)
2. Burst behavior (many simultaneous requests?)
3. Provider quota (exceeded limits?)

**Fixes:**
- Reduce rate limits (respect quotas)
- Add delays between requests
- Upgrade API plan if needed

## Example Configurations

### High-Throughput Batch Processing

```python
config = ProcessorConfig.from_profile(
    "production",
    worker_count=20,
    queue_size=200,
    max_concurrent_api_calls=30,
    llm_rate_limit=20.0,
    log_level="WARNING",
    enable_progress_bar=False
)
```

### Reliable Overnight Job

```python
config = ProcessorConfig.from_profile(
    "production",
    worker_count=5,
    max_retries=10,
    retry_exponential_base=1.5,  # Slower backoff
    log_level="INFO",            # Log everything for morning review
    shutdown_timeout_seconds=300.0  # Wait 5 minutes for completion
)
```

### Rate-Limited API Integration

```python
config = ProcessorConfig.from_profile(
    "production",
    worker_count=2,              # Low concurrency
    llm_rate_limit=2.0,          # Strict rate limit
    email_rate_limit=0.5,
    max_concurrent_api_calls=3,
    log_level="INFO"
)
```

### Cost-Optimized Processing

```python
config = ProcessorConfig.from_profile(
    "production",
    worker_count=3,              # Minimal workers
    max_retries=2,               # Fewer retries (less API cost)
    llm_timeout_seconds=15.0,    # Fail fast
    min_match_score=70,          # Higher quality threshold
    log_level="WARNING"
)
```

## References

- [Async Pipeline Architecture](../ASYNC_PIPELINE_QUICK_START.md)
- [Requirements Document](.kiro/specs/system-architecture/requirements.md)
- [Design Document](.kiro/specs/system-architecture/design.md)
- [12-Factor App Configuration](https://12factor.net/config)
