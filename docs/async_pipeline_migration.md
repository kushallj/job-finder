# Async Pipeline Migration Guide

This guide helps you migrate from the synchronous `JobProcessor` to the new high-performance async pipeline.

## Table of Contents

- [Overview](#overview)
- [What Changed](#what-changed)
- [Migration Paths](#migration-paths)
  - [Path 1: Using Sync Wrapper (Easiest)](#path-1-using-sync-wrapper-easiest)
  - [Path 2: Full Async Migration (Recommended)](#path-2-full-async-migration-recommended)
  - [Path 3: Compatibility Wrapper](#path-3-compatibility-wrapper)
- [Configuration Differences](#configuration-differences)
- [API Differences](#api-differences)
- [Code Examples](#code-examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

The new async pipeline provides:

- **3.3+ jobs/second throughput** (vs ~0.5 jobs/second in old system)
- **O(1) memory usage** through streaming (no memory growth with job count)
- **Natural backpressure** via bounded queues
- **Automatic retry** with exponential backoff
- **Rate limiting** for external APIs
- **Structured logging** and progress tracking
- **Graceful shutdown** support

## What Changed

### Architecture Changes

| Component | Old System | New System |
|-----------|-----------|-----------|
| Processing Model | Sequential | Concurrent (async workers) |
| Memory Usage | O(total_jobs) | O(queue_size + worker_count) |
| Job Loading | Load all at once | Stream in chunks |
| Concurrency Control | Threading/asyncio mix | Pure asyncio with semaphores |
| Rate Limiting | Manual delays | Token bucket algorithm |
| Retry Logic | Manual per-operation | Automatic with exponential backoff |
| Backpressure | None | Bounded queue |

### Key Technical Changes

1. **Database Sessions**: Old system used shared sessions; new system uses per-task async sessions
2. **HTTP Clients**: Old system mixed sync/async; new system is fully async (aiohttp/httpx)
3. **Configuration**: Centralized in `ProcessorConfig` dataclass
4. **Metrics**: Structured metrics collection with `MetricsCollector`
5. **Progress Tracking**: Rich terminal UI with real-time updates

---

## Migration Paths

### Path 1: Using Sync Wrapper (Easiest)

**Best for**: Quick migration with minimal code changes.

**Before (Old Code)**:
```python
from src.job_processor import JobProcessor

processor = JobProcessor()
results = await processor.run(
    query="software engineer",
    resume_text=open("resume.txt").read()
)
await processor.close()
```

**After (Using Sync Wrapper)**:
```python
from src.async_pipeline.sync_wrapper import SyncJobPipelineWrapper
from src.async_pipeline.config import ProcessorConfig

config = ProcessorConfig(
    worker_count=5,
    queue_size=100,
    max_concurrent_api_calls=3,
)

wrapper = SyncJobPipelineWrapper(config=config)
results = wrapper.run_sync(
    query="software engineer",
    resume_text=open("resume.txt").read()
)
wrapper.close_sync()
```

**Advantages**:
- Minimal code changes
- Works in synchronous contexts
- Drop-in replacement for old code

**Disadvantages**:
- Doesn't leverage full async benefits
- Cannot be used in async contexts efficiently

---

### Path 2: Full Async Migration (Recommended)

**Best for**: New code or when refactoring existing async code.

**Before (Old Code)**:
```python
from src.job_processor import JobProcessor

processor = JobProcessor()
metrics = await processor.run(
    query="python developer",
    resume_text=resume_text
)
```

**After (Full Async)**:
```python
from src.async_pipeline import AsyncJobPipeline, ProcessorConfig
from src.async_pipeline.processor import AsyncJobProcessor

# Configuration
config = ProcessorConfig(
    worker_count=5,
    queue_size=100,
    max_concurrent_api_calls=3,
    llm_rate_limit=10,      # requests per second
    email_rate_limit=2,
    scraper_rate_limit=30,
)

# Create pipeline
pipeline = AsyncJobPipeline(config=config)

# Optional: Set custom processor
processor = AsyncJobProcessor(config=config)
pipeline.set_processor(processor.process_job)

# Run pipeline
results = await pipeline.run(
    query="python developer",
    resume_text=resume_text
)

# Cleanup
await pipeline.close()
```

**Advantages**:
- Full async benefits
- Better performance
- Native async/await code

**Disadvantages**:
- Requires async context
- More code changes

---

### Path 3: Compatibility Wrapper

**Best for**: Legacy code that expects the exact old interface.

**Before (Old Code)**:
```python
from src.job_processor import JobProcessor

processor = JobProcessor()
await processor.run("software engineer", resume_text)
await processor.close()
```

**After (Compatibility Wrapper)**:
```python
from src.async_pipeline.sync_wrapper import JobProcessorCompatWrapper

processor = JobProcessorCompatWrapper()
await processor.run("software engineer", resume_text)
await processor.close()
```

**Advantages**:
- Near-zero code changes
- Maintains old interface

**Disadvantages**:
- Limited access to new features
- Abstraction overhead

---

## Configuration Differences

### Old Configuration (settings.py)

```python
# settings.py
job_concurrency = 5
min_score = 50
email_delay_seconds = 30.0
max_contacts = 3
db_chunk_size = 100
max_retries = 3
retry_base_delay = 1.0
auto_send_emails = True
```

### New Configuration (ProcessorConfig)

```python
from src.async_pipeline.config import ProcessorConfig

config = ProcessorConfig(
    # Worker configuration
    worker_count=5,                    # number of concurrent workers
    queue_size=100,                    # bounded queue size
    max_concurrent_api_calls=3,        # concurrent external API calls
    
    # Database configuration
    db_chunk_size=100,                 # jobs per database fetch
    db_pool_size=5,                    # database connection pool
    db_max_overflow=10,                # max overflow connections
    
    # Rate limiting (requests per second)
    llm_rate_limit=10,                 # LLM API calls/sec
    email_rate_limit=2,                # Email API calls/sec
    scraper_rate_limit=30,             # Scraper API calls/sec
    
    # Retry configuration
    max_retries=3,                     # max retry attempts
    retry_base_delay=1.0,              # base delay in seconds
    retry_max_delay=60.0,              # max delay in seconds
    retry_exponential_base=2.0,        # exponential backoff base
    
    # Timeout configuration (seconds)
    llm_timeout=30,                    # LLM API timeout
    email_timeout=10,                  # Email API timeout
    scraper_timeout=30,                # Scraper timeout
    db_timeout=5,                      # Database query timeout
    
    # Logging configuration
    log_level="INFO",                  # log level
    log_file="logs/async_pipeline.log", # log file path
)
```

### Loading from Environment

```python
import os
from src.async_pipeline.config import ProcessorConfig

config = ProcessorConfig(
    worker_count=int(os.getenv("WORKER_COUNT", "5")),
    queue_size=int(os.getenv("QUEUE_SIZE", "100")),
    max_concurrent_api_calls=int(os.getenv("MAX_CONCURRENT_API", "3")),
    llm_rate_limit=float(os.getenv("LLM_RATE_LIMIT", "10")),
    email_rate_limit=float(os.getenv("EMAIL_RATE_LIMIT", "2")),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
)
```

---

## API Differences

### Method Signatures

#### Old JobProcessor

```python
class JobProcessor:
    async def run(
        self, 
        query: str = "software engineer", 
        resume_text: str = ""
    ) -> RunMetrics
    
    async def fetch_and_store_jobs(self, query: str) -> int
    
    async def process_all_jobs(
        self, 
        resume_text: str, 
        min_score: Optional[int] = None
    ) -> None
    
    async def close(self) -> None
```

#### New AsyncJobPipeline

```python
class AsyncJobPipeline:
    async def run(
        self,
        query: str = "",
        resume_text: str = "",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ProcessingResult]
    
    def set_processor(
        self, 
        processor: Callable[[JobContext], ProcessingResult]
    ) -> None
    
    def set_progress_callback(
        self, 
        callback: Callable[[Dict], None]
    ) -> None
    
    async def close(self) -> None
    
    def get_metrics_snapshot(self) -> Optional[MetricsSnapshot]
```

### Return Types

#### Old System

```python
@dataclass
class RunMetrics:
    jobs_fetched: int = 0
    jobs_stored: int = 0
    jobs_processed: int = 0
    jobs_skipped: int = 0
    jobs_failed: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
```

#### New System

```python
@dataclass
class ProcessingResult:
    job_id: str
    status: JobStatus
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    error_type: Optional[str]
    attempt_count: int
    processing_time_ms: float
    timestamp: datetime
    worker_id: str
```

---

## Code Examples

### Example 1: Basic Pipeline Execution

**Old Code**:
```python
from src.job_processor import JobProcessor

async def process_jobs():
    processor = JobProcessor()
    try:
        metrics = await processor.run(
            query="python developer",
            resume_text=open("resume.txt").read()
        )
        print(f"Processed {metrics.jobs_processed} jobs")
        print(f"Sent {metrics.emails_sent} emails")
    finally:
        await processor.close()

asyncio.run(process_jobs())
```

**New Code**:
```python
from src.async_pipeline import AsyncJobPipeline, ProcessorConfig

async def process_jobs():
    config = ProcessorConfig(worker_count=5, queue_size=100)
    pipeline = AsyncJobPipeline(config=config)
    
    try:
        results = await pipeline.run(
            query="python developer",
            resume_text=open("resume.txt").read()
        )
        
        # Analyze results
        completed = sum(1 for r in results if r.is_success())
        failed = sum(1 for r in results if not r.is_success())
        
        print(f"Completed: {completed}, Failed: {failed}")
        
        # Get detailed metrics
        metrics = pipeline.get_metrics_snapshot()
        if metrics:
            print(f"Throughput: {metrics.throughput:.2f} jobs/sec")
            print(f"Avg processing time: {metrics.avg_processing_time_ms:.1f}ms")
        
    finally:
        await pipeline.close()

asyncio.run(process_jobs())
```

### Example 2: Custom Processor

**Old Code**:
```python
from src.job_processor import JobProcessor

class CustomJobProcessor(JobProcessor):
    async def _process_job(self, job_data, resume_text, min_score):
        # Custom processing logic
        pass

processor = CustomJobProcessor()
await processor.run("software engineer", resume_text)
```

**New Code**:
```python
from src.async_pipeline import AsyncJobPipeline, ProcessorConfig
from src.async_pipeline.types import JobContext, ProcessingResult

async def custom_processor(job: JobContext) -> ProcessingResult:
    """Custom job processing logic."""
    try:
        # Your custom logic here
        result_data = {
            "title": job.title,
            "company": job.company,
            "processed": True,
        }
        
        return ProcessingResult.success(
            job_id=job.job_id,
            data=result_data,
        )
    except Exception as e:
        return ProcessingResult.failure(
            job_id=job.job_id,
            error=str(e),
        )

# Use custom processor
config = ProcessorConfig(worker_count=5)
pipeline = AsyncJobPipeline(config=config)
pipeline.set_processor(custom_processor)

results = await pipeline.run(query="software engineer")
await pipeline.close()
```

### Example 3: Progress Tracking

**Old Code**:
```python
# No built-in progress tracking
processor = JobProcessor()
await processor.run("python developer", resume_text)
```

**New Code**:
```python
from src.async_pipeline import AsyncJobPipeline, ProcessorConfig

def on_progress(progress: Dict):
    """Progress callback."""
    print(f"Job {progress['job_id']}: {progress['status']}")
    print(f"Processing time: {progress['processing_time_ms']:.1f}ms")

config = ProcessorConfig(worker_count=5)
pipeline = AsyncJobPipeline(config=config)
pipeline.set_progress_callback(on_progress)

# Enable rich terminal progress display
pipeline.enable_progress_display(True)

results = await pipeline.run(query="python developer")
await pipeline.close()
```

### Example 4: Error Handling

**Old Code**:
```python
try:
    processor = JobProcessor()
    await processor.run("software engineer", resume_text)
except Exception as e:
    print(f"Error: {e}")
finally:
    await processor.close()
```

**New Code**:
```python
from src.async_pipeline import AsyncJobPipeline

pipeline = AsyncJobPipeline()

try:
    results = await pipeline.run(query="software engineer")
    
    # Check for failures
    failures = [r for r in results if not r.is_success()]
    if failures:
        print(f"Failed jobs: {len(failures)}")
        for failure in failures:
            print(f"  Job {failure.job_id}: {failure.error}")
    
except Exception as e:
    print(f"Pipeline error: {e}")
    
finally:
    await pipeline.close()
```

### Example 5: Configuration from File

**New Code Only**:
```python
import json
from src.async_pipeline import AsyncJobPipeline
from src.async_pipeline.config import ProcessorConfig

# Load config from JSON
with open("pipeline_config.json") as f:
    config_dict = json.load(f)

config = ProcessorConfig(**config_dict)
pipeline = AsyncJobPipeline(config=config)

results = await pipeline.run(query="python developer")
await pipeline.close()
```

**Example pipeline_config.json**:
```json
{
  "worker_count": 5,
  "queue_size": 100,
  "max_concurrent_api_calls": 3,
  "llm_rate_limit": 10,
  "email_rate_limit": 2,
  "scraper_rate_limit": 30,
  "max_retries": 3,
  "retry_base_delay": 1.0,
  "retry_max_delay": 60.0,
  "log_level": "INFO"
}
```

---

## Troubleshooting

### Issue: "RuntimeError: Event loop is closed"

**Cause**: Calling `asyncio.run()` multiple times or mixing sync/async contexts.

**Solution**: Use the sync wrapper for synchronous contexts:
```python
from src.async_pipeline.sync_wrapper import SyncJobPipelineWrapper

wrapper = SyncJobPipelineWrapper()
results = wrapper.run_sync(query="python developer")
wrapper.close_sync()
```

### Issue: "RuntimeError: Pipeline is already running"

**Cause**: Attempting to run the same pipeline instance concurrently.

**Solution**: Create separate pipeline instances or await previous run:
```python
# Option 1: Await previous run
results1 = await pipeline.run(query="python developer")
results2 = await pipeline.run(query="java developer")

# Option 2: Create separate instances
pipeline1 = AsyncJobPipeline()
pipeline2 = AsyncJobPipeline()

results1, results2 = await asyncio.gather(
    pipeline1.run(query="python developer"),
    pipeline2.run(query="java developer"),
)
```

### Issue: Database connection errors

**Cause**: Database URL not configured or incorrect format.

**Solution**: Ensure correct database URL:
```python
# For SQLite (async)
db_url = "sqlite+aiosqlite:///jobs.db"

# For PostgreSQL (async)
db_url = "postgresql+asyncpg://user:pass@localhost/jobs"

pipeline = AsyncJobPipeline(db_url=db_url)
```

### Issue: "No jobs processed"

**Cause**: Jobs may already have been processed or query returns no results.

**Solution**: Check database and query:
```python
from src.async_pipeline.producer import AsyncJobProducer

# Check job count
producer = AsyncJobProducer(session_factory)
count = await producer.get_job_count(query="python developer")
print(f"Found {count} jobs to process")
```

### Issue: High memory usage

**Cause**: Queue size or worker count too high.

**Solution**: Reduce queue size and worker count:
```python
config = ProcessorConfig(
    worker_count=3,      # Reduce from 5
    queue_size=50,       # Reduce from 100
)
```

### Issue: Rate limiting errors from external APIs

**Cause**: Rate limits set too high for API quotas.

**Solution**: Lower rate limits:
```python
config = ProcessorConfig(
    llm_rate_limit=5,      # Reduce from 10
    email_rate_limit=1,    # Reduce from 2
)
```

### Issue: Jobs timing out

**Cause**: Timeout values too low for slow operations.

**Solution**: Increase timeout values:
```python
config = ProcessorConfig(
    llm_timeout=60,        # Increase from 30
    scraper_timeout=60,    # Increase from 30
)
```

---

## Performance Tuning

### Optimizing Throughput

1. **Increase Worker Count**: More workers = more concurrency
   ```python
   config = ProcessorConfig(worker_count=10)  # Default: 5
   ```

2. **Increase Concurrent API Calls**: Allow more parallel external calls
   ```python
   config = ProcessorConfig(max_concurrent_api_calls=5)  # Default: 3
   ```

3. **Optimize Queue Size**: Larger queue = more buffering
   ```python
   config = ProcessorConfig(queue_size=200)  # Default: 100
   ```

### Optimizing Memory

1. **Reduce Queue Size**: Less memory for buffering
   ```python
   config = ProcessorConfig(queue_size=50)  # Default: 100
   ```

2. **Reduce Chunk Size**: Smaller database fetches
   ```python
   config = ProcessorConfig(db_chunk_size=50)  # Default: 100
   ```

### Optimizing for Slow APIs

1. **Increase Timeouts**: Avoid premature failures
   ```python
   config = ProcessorConfig(
       llm_timeout=90,
       scraper_timeout=90,
   )
   ```

2. **Increase Retry Attempts**: More chances to succeed
   ```python
   config = ProcessorConfig(max_retries=5)  # Default: 3
   ```

---

## Best Practices

1. **Always close the pipeline**: Use try/finally or async context managers
2. **Configure rate limits conservatively**: Start low and increase if needed
3. **Monitor metrics**: Use `get_metrics_snapshot()` to track performance
4. **Use structured logging**: Set appropriate log levels for debugging
5. **Handle failures gracefully**: Check `ProcessingResult.is_success()`
6. **Tune for your environment**: Test different configurations
7. **Use progress callbacks**: Monitor long-running pipelines
8. **Validate configuration**: Call `config.validate()` before use

---

## Additional Resources

- [Design Document](../.kiro/specs/async-job-pipeline-refactor/design.md)
- [Requirements Document](../.kiro/specs/async-job-pipeline-refactor/requirements.md)
- [Configuration Guide](../src/async_pipeline/CONFIG_IMPLEMENTATION_SUMMARY.md)
- [Metrics Guide](../src/async_pipeline/METRICS_GUIDE.md)
- [Structured Logging Guide](../src/async_pipeline/STRUCTURED_LOGGING_GUIDE.md)

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the design and requirements documents
3. Check logs at `logs/async_pipeline.log`
4. Review metrics with `pipeline.get_metrics_snapshot()`
