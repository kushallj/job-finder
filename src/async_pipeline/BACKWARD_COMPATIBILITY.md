# Backward Compatibility & Migration Utilities

## Overview

This document describes the backward compatibility features and migration utilities provided for the async job pipeline refactor (Task 17.2).

## Quick Start

### Using Sync Wrapper (Recommended for Quick Migration)

```python
from src.async_pipeline import SyncJobPipelineWrapper, ProcessorConfig

# Create wrapper
config = ProcessorConfig(worker_count=5, queue_size=100)
wrapper = SyncJobPipelineWrapper(config=config)

# Run synchronously
results = wrapper.run_sync(
    query="python developer",
    resume_text=open("resume.txt").read()
)

# Cleanup
wrapper.close_sync()
```

### Using Compatibility Wrapper (Drop-in Replacement)

```python
from src.async_pipeline import JobProcessorCompatWrapper

# Drop-in replacement for old JobProcessor
processor = JobProcessorCompatWrapper()
await processor.run("software engineer", resume_text)
await processor.close()
```

## Features

### 1. Synchronous Wrapper (`SyncJobPipelineWrapper`)

Provides synchronous interface to the async pipeline:
- `run_sync()` - Run pipeline synchronously
- `close_sync()` - Close pipeline synchronously
- `set_processor()` - Set custom processor
- `get_stats()` - Get pipeline statistics
- `get_metrics_snapshot()` - Get detailed metrics

### 2. Compatibility Wrapper (`JobProcessorCompatWrapper`)

Mimics the old `JobProcessor` interface:
- `run()` - Async run method (old signature)
- `run_sync()` - Synchronous run method
- `close()` - Async close method
- `close_sync()` - Synchronous close method

### 3. Convenience Function (`run_pipeline_sync`)

One-liner for quick pipeline execution:

```python
from src.async_pipeline import run_pipeline_sync

results = run_pipeline_sync(
    query="python developer",
    processor=my_processor,
    resume_text=resume_text
)
```

## When to Use What

### Use `SyncJobPipelineWrapper` when:
- ✅ Migrating from synchronous code
- ✅ Need minimal code changes
- ✅ Want access to new pipeline features
- ✅ Working in synchronous contexts

### Use `JobProcessorCompatWrapper` when:
- ✅ Need zero-code-change migration
- ✅ Maintaining exact old interface
- ✅ Temporary compatibility during gradual migration
- ✅ Don't need new features immediately

### Use `run_pipeline_sync` when:
- ✅ Quick scripts or one-off tasks
- ✅ Don't need stateful pipeline
- ✅ Want simplest possible API
- ✅ Prototyping or testing

### Use `AsyncJobPipeline` directly when:
- ✅ Writing new async code
- ✅ Want best performance
- ✅ Need full control over pipeline
- ✅ Can leverage async/await throughout

## How It Works

### Sync Wrapper Implementation

The sync wrapper uses `asyncio.run()` to execute async operations:

```python
def run_sync(self, query: str, resume_text: str) -> List[ProcessingResult]:
    """Run pipeline synchronously using asyncio.run()."""
    pipeline = self._ensure_pipeline()
    return asyncio.run(pipeline.run(query, resume_text))
```

**Key Points:**
- Creates new event loop for each call
- Blocks until async operation completes
- Automatically handles cleanup
- Thread-safe (each call gets its own loop)

### Compatibility Wrapper Implementation

The compatibility wrapper translates old API to new:

```python
async def run(self, query: str, resume_text: str) -> Dict[str, Any]:
    """Run with old API signature, return old metrics format."""
    results = self._wrapper.run_sync(query, resume_text)
    stats = self._wrapper.get_stats()
    
    return {
        "jobs_processed": stats.get("jobs_completed", 0) + stats.get("jobs_failed", 0),
        "jobs_completed": stats.get("jobs_completed", 0),
        "jobs_failed": stats.get("jobs_failed", 0),
        "results": results,
    }
```

## Migration Paths

### Path 1: Minimal Changes (Sync Wrapper)

**Before:**
```python
from src.job_processor import JobProcessor
processor = JobProcessor()
await processor.run("software engineer", resume_text)
```

**After:**
```python
from src.async_pipeline import SyncJobPipelineWrapper
wrapper = SyncJobPipelineWrapper()
wrapper.run_sync("software engineer", resume_text)
```

**Changes:** Import + method call

### Path 2: Zero Changes (Compat Wrapper)

**Before:**
```python
from src.job_processor import JobProcessor
processor = JobProcessor()
await processor.run("software engineer", resume_text)
```

**After:**
```python
from src.async_pipeline import JobProcessorCompatWrapper
processor = JobProcessorCompatWrapper()
await processor.run("software engineer", resume_text)
```

**Changes:** Import only

### Path 3: Full Migration (Async Pipeline)

**Before:**
```python
from src.job_processor import JobProcessor
processor = JobProcessor()
await processor.run("software engineer", resume_text)
```

**After:**
```python
from src.async_pipeline import AsyncJobPipeline, ProcessorConfig
config = ProcessorConfig(worker_count=5)
pipeline = AsyncJobPipeline(config=config)
results = await pipeline.run(query="software engineer", resume_text=resume_text)
```

**Changes:** Full API migration, best performance

## Configuration Migration

### Old Configuration

```python
# settings.py
job_concurrency = 5
min_score = 50
email_delay_seconds = 30.0
```

### New Configuration

```python
from src.async_pipeline import ProcessorConfig

config = ProcessorConfig(
    worker_count=5,
    queue_size=100,
    max_concurrent_api_calls=3,
    llm_rate_limit=10,
    email_rate_limit=2,
)
```

## Testing

Unit tests are available in `tests/async_pipeline/test_sync_wrapper.py`:

```bash
pytest tests/async_pipeline/test_sync_wrapper.py -v
```

**Test Coverage:**
- ✅ Wrapper initialization
- ✅ Processor setting
- ✅ Pipeline execution
- ✅ Cleanup and resource management
- ✅ Error handling
- ✅ Metrics and stats
- ✅ Integration scenarios

## Performance Considerations

### Sync Wrapper Performance

- **Overhead:** ~1-2ms per `asyncio.run()` call
- **Memory:** Same as async pipeline (O(1))
- **Throughput:** Similar to async (slight overhead from event loop creation)

### Recommended Usage

1. **Development/Testing:** Use sync wrapper for simplicity
2. **Production:** Migrate to full async for best performance
3. **Scripts:** Use `run_pipeline_sync()` convenience function
4. **Legacy Systems:** Use compat wrapper temporarily

## Common Issues

### Issue: "RuntimeError: Event loop is closed"

**Solution:** Don't mix `asyncio.run()` with existing event loops:

```python
# BAD: Don't do this
async def main():
    wrapper = SyncJobPipelineWrapper()
    wrapper.run_sync(query)  # Creates nested event loop!

# GOOD: Use async pipeline directly
async def main():
    pipeline = AsyncJobPipeline()
    await pipeline.run(query)
```

### Issue: Performance degradation

**Solution:** Migrate to full async pipeline:

```python
# Sync wrapper (good for migration, not optimal performance)
wrapper = SyncJobPipelineWrapper()
results = wrapper.run_sync(query)

# Full async (best performance)
pipeline = AsyncJobPipeline()
results = await pipeline.run(query)
```

## Documentation

- **Full Migration Guide:** [`docs/async_pipeline_migration.md`](../../docs/async_pipeline_migration.md)
- **Design Document:** [`.kiro/specs/async-job-pipeline-refactor/design.md`](../../.kiro/specs/async-job-pipeline-refactor/design.md)
- **Configuration Guide:** [`CONFIG_IMPLEMENTATION_SUMMARY.md`](CONFIG_IMPLEMENTATION_SUMMARY.md)

## Support

For questions or issues:
1. Check migration guide: `docs/async_pipeline_migration.md`
2. Review examples in this document
3. Check test file: `tests/async_pipeline/test_sync_wrapper.py`
4. Review logs: `logs/async_pipeline.log`

## Summary

The backward compatibility layer provides three levels of migration support:

1. **Level 1 (Easiest):** Sync wrapper with minimal changes
2. **Level 2 (Zero-change):** Compatibility wrapper for drop-in replacement
3. **Level 3 (Best):** Full async migration for maximum performance

Choose the level that best fits your migration timeline and performance requirements.
