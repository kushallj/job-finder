# Configuration Profiles - Quick Reference

## Overview

NEXUS async pipeline provides three environment-specific configuration profiles: **development**, **staging**, and **production**. Each profile has sensible defaults optimized for its deployment environment.

## Quick Start

### Select a Profile

```python
from src.async_pipeline.config import ProcessorConfig

# Development (local debugging, verbose logging)
config = ProcessorConfig.from_profile("development")

# Staging (pre-production testing)
config = ProcessorConfig.from_profile("staging")

# Production (high performance)
config = ProcessorConfig.from_profile("production")
```

### Use Environment Variable

```bash
# Set profile in .env or shell
export PIPELINE_PROFILE=production
```

```python
from src.async_pipeline.config import ProcessorConfig, get_current_profile

# Automatically use profile from environment
profile = get_current_profile()  # Returns "production"
config = ProcessorConfig.from_profile(profile)
```

### Override Specific Settings

```python
# Start with production defaults, customize worker count
config = ProcessorConfig.from_profile(
    "production",
    worker_count=20,
    log_level="INFO"
)
```

## Profile Comparison

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| **Concurrency** |
| `worker_count` | 2 | 5 | 10 |
| `max_concurrent_api_calls` | 3 | 10 | 20 |
| `queue_size` | 20 | 50 | 100 |
| `chunk_size` | 50 | 75 | 100 |
| **Retry** |
| `max_retries` | 2 | 3 | 5 |
| `base_delay` | 0.5s | 1.0s | 1.0s |
| `max_delay` | 10s | 30s | 60s |
| **Rate Limiting** |
| `llm_rate_limit` (req/s) | 5.0 | 8.0 | 15.0 |
| `email_rate_limit` (req/s) | 0.5 | 1.0 | 2.0 |
| `scraper_rate_limit` (req/s) | 2.0 | 4.0 | 8.0 |
| **Timeouts** |
| `llm_timeout_seconds` | 20 | 25 | 30 |
| `email_timeout_seconds` | 10 | 12 | 15 |
| `scraper_timeout_seconds` | 15 | 18 | 20 |
| `db_timeout_seconds` | 5 | 8 | 10 |
| **Database** |
| `db_pool_size` | 3 | 8 | 20 |
| `db_max_overflow` | 5 | 15 | 30 |
| **Logging** |
| `log_level` | DEBUG | INFO | WARNING |
| `log_file` | `processor_dev.log` | `processor_staging.log` | `processor_production.log` |
| **Progress** |
| `enable_progress_bar` | ✅ True | ✅ True | ❌ False |
| `progress_update_interval` | 0.5s | 1.0s | 2.0s |
| **Job Processing** |
| `min_match_score` | 40 | 50 | 60 |
| `max_contacts_per_job` | 2 | 3 | 5 |
| **Outreach** |
| `auto_send_emails` | ❌ False | ✅ True | ✅ True |
| `email_delay_seconds` | 5.0 | 20.0 | 30.0 |
| **Shutdown** |
| `shutdown_timeout_seconds` | 30 | 60 | 120 |

## Profile Characteristics

### Development Profile

**Purpose:** Local development, debugging, feature testing

**Key Features:**
- ✅ **Low throughput** (2 workers) - won't overwhelm local services
- ✅ **Verbose logging** (DEBUG level) - detailed diagnostics
- ✅ **Fast feedback** (2 retries, 10s max delay) - quick iteration
- ✅ **Safe defaults** (auto_send_emails=False) - no accidental sends
- ✅ **Visual progress** - always show progress bar

**When to Use:**
- Writing new features
- Debugging issues
- Running unit tests
- Local prototyping

**Example:**
```python
config = ProcessorConfig.from_profile("development")
# Results: 2 workers, DEBUG logs, no emails sent
```

### Staging Profile

**Purpose:** Pre-production testing, integration validation, QA

**Key Features:**
- ⚖️ **Moderate throughput** (5 workers) - realistic load
- ⚖️ **Standard logging** (INFO level) - important events
- ⚖️ **Standard retry** (3 attempts) - production-like behavior
- ✅ **Outreach enabled** - test full workflow
- ⚖️ **Conservative delays** (20s between emails) - safe testing

**When to Use:**
- Integration testing
- QA validation
- Load testing
- Pre-deployment verification

**Example:**
```python
config = ProcessorConfig.from_profile("staging")
# Results: 5 workers, INFO logs, emails sent with delays
```

### Production Profile

**Purpose:** Production deployment, high-throughput processing

**Key Features:**
- 🚀 **High throughput** (10 workers) - maximum performance
- 🔇 **Minimal logging** (WARNING level) - reduce overhead
- 🔄 **Aggressive retry** (5 attempts, 60s max) - reliability
- 📊 **Large DB pool** (20 connections) - concurrent access
- ⏱️ **Extended shutdown** (120s timeout) - protect in-flight jobs
- 📊 **High quality** (min_match_score=60) - better results
- 🚫 **No progress bar** - reduce overhead

**When to Use:**
- Production deployment
- Nightly batch processing
- High-volume job processing
- Production workflows

**Example:**
```python
config = ProcessorConfig.from_profile("production")
# Results: 10 workers, WARNING logs, high throughput
```

## Common Patterns

### Pattern 1: Environment-Based Selection

```python
import os
from src.async_pipeline.config import ProcessorConfig, get_current_profile

# Automatically select based on PIPELINE_PROFILE env var
profile = get_current_profile()  # development, staging, or production
config = ProcessorConfig.from_profile(profile)
```

### Pattern 2: Override for Specific Workload

```python
# High-throughput batch processing
config = ProcessorConfig.from_profile(
    "production",
    worker_count=20,          # Double workers
    queue_size=200,           # Larger queue
    max_concurrent_api_calls=30
)
```

### Pattern 3: Rate-Limited Integration

```python
# Strict rate limits for third-party API
config = ProcessorConfig.from_profile(
    "production",
    worker_count=2,           # Low concurrency
    llm_rate_limit=2.0,       # Strict limit
    max_concurrent_api_calls=3
)
```

### Pattern 4: Reliable Overnight Job

```python
# Maximize reliability, not speed
config = ProcessorConfig.from_profile(
    "production",
    max_retries=10,           # Aggressive retry
    log_level="INFO",         # Detailed logs for morning review
    shutdown_timeout_seconds=300.0  # 5 min wait
)
```

### Pattern 5: Cost-Optimized Processing

```python
# Minimize API costs
config = ProcessorConfig.from_profile(
    "production",
    worker_count=3,           # Fewer workers
    max_retries=2,            # Fewer retries = less API cost
    min_match_score=70,       # Higher quality threshold
    llm_timeout_seconds=15.0  # Fail fast
)
```

## Environment Variable Mapping

All configuration values can be overridden via environment variables with the `PIPELINE_` prefix:

```bash
# Profile selection
export PIPELINE_PROFILE=production

# Concurrency
export PIPELINE_WORKER_COUNT=15
export PIPELINE_QUEUE_SIZE=200

# Rate limits
export PIPELINE_LLM_RATE_LIMIT=20.0
export PIPELINE_EMAIL_RATE_LIMIT=2.5

# Timeouts
export PIPELINE_LLM_TIMEOUT_SECONDS=35.0

# Logging
export PIPELINE_LOG_LEVEL=INFO
export PIPELINE_ENABLE_PROGRESS_BAR=false

# Database
export PIPELINE_DB_POOL_SIZE=25
export PIPELINE_DB_MAX_OVERFLOW=35
```

## Validation

All profiles are automatically validated when loaded:

```python
config = ProcessorConfig.from_profile("production")
# Validation happens automatically - no need to call validate()

# Override with invalid value
try:
    config = ProcessorConfig.from_profile("production", worker_count=-5)
except ValueError as e:
    print(f"Invalid config: {e}")
    # Output: worker_count must be positive, got -5. Worker count determines...
```

## Migration from Manual Configuration

**Before (manual configuration):**
```python
config = ProcessorConfig(
    worker_count=10,
    queue_size=100,
    max_retries=5,
    llm_rate_limit=15.0,
    # ... 20+ more parameters
)
```

**After (profile-based):**
```python
# All defaults from production profile
config = ProcessorConfig.from_profile("production")

# Or override specific values
config = ProcessorConfig.from_profile("production", worker_count=15)
```

## Troubleshooting

### Issue: Wrong Profile Loaded

**Symptom:** Pipeline behaves unexpectedly (too slow, too verbose, etc.)

**Check:**
```python
from src.async_pipeline.config import get_current_profile
print(f"Current profile: {get_current_profile()}")
```

**Fix:**
```bash
export PIPELINE_PROFILE=production  # Set correct profile
```

### Issue: Profile Not Found

**Symptom:** `ValueError: Invalid profile 'prod'`

**Fix:** Use exact profile names: `"development"`, `"staging"`, `"production"`

```python
# Wrong
config = ProcessorConfig.from_profile("prod")  # ❌

# Correct
config = ProcessorConfig.from_profile("production")  # ✅
```

### Issue: Validation Error After Override

**Symptom:** `ValueError: worker_count must be positive`

**Fix:** Ensure overridden values are valid:

```python
# Wrong
config = ProcessorConfig.from_profile("production", worker_count=-5)  # ❌

# Correct
config = ProcessorConfig.from_profile("production", worker_count=15)  # ✅
```

## See Also

- [Complete Configuration Guide](CONFIGURATION_GUIDE.md) - Detailed tuning and best practices
- [Async Pipeline Quick Start](../ASYNC_PIPELINE_QUICK_START.md) - Pipeline architecture
- [Requirements Document](../.kiro/specs/system-architecture/requirements.md) - Requirement 8.1-8.6
- [Design Document](../.kiro/specs/system-architecture/design.md) - Architecture details
