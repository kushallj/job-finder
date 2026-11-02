# Async Pipeline Integration Plan

## Status: COMPLETED

## Progress:
- [x] main.py - Added async_pipeline imports
- [x] main.py - Added AsyncJobPipeline to AppState
- [x] main.py - Added initialization in lifespan
- [x] main.py - Added cleanup in shutdown
- [x] main.py - Added health check update
- [x] main.py - Added `/run-query-async` endpoint
- [x] comprehensive_job_search.py - Added async_pipeline imports
- [x] comprehensive_job_search.py - Added CLI argument parser
- [x] comprehensive_job_search.py - Add actual async pipeline processing logic

## Summary of Changes:

### main.py:
1. Added imports for `AsyncJobPipeline` and `ProcessorConfig` from `src.async_pipeline`
2. Added `async_pipeline` field to `AppState` dataclass
3 `. Added initialization ofAsyncJobPipeline` in the lifespan function
4. Added cleanup of `async_pipeline` in the shutdown section
5. Added `async_pipeline` to the health check endpoint
6. Added new endpoint `/run-query-async` that uses the high-performance async pipeline

### comprehensive_job_search.py:
1. Added imports for `AsyncJobPipeline` and `ProcessorConfig`
2. Added CLI argument `--async` / `-a` to enable async pipeline
3. Added conditional logic in Step 2 to use AsyncJobPipeline when `--async` flag is provided
4. Added full processor function that handles job processing with AI services

## Usage:

### API Endpoints:
- `/run-query` - Original endpoint using sequential processing
- `/run-query-async` - New endpoint using AsyncJobPipeline (high-performance)

### CLI:
- `python comprehensive_job_search.py` - Default sequential processing
- `python comprehensive_job_search.py --async-mode` - Using async_pipeline optimization
- `python comprehensive_job_search.py -a` - Short flag

## Information Gathered:

### Current Architecture:
1. **main.py** - FastAPI server with endpoints:
   - `/run-query` - Uses `JobProcessor.fetch_and_store_jobs()` + `JobProcessor.process_all_jobs()`
   - Uses `JobProcessor` from `src.job_processor`

2. **comprehensive_job_search.py** - CLI script:
   - Uses `JobProcessor` to fetch and process jobs
   - Uses `OutreachProcessor` for outreach campaigns

3. **async_pipeline** (existing but unused):
   - `AsyncJobPipeline` - Main orchestrator with O(1) memory
   - `AsyncWorkerPool` - Concurrent workers with semaphore gating
   - `BoundedQueue` - Backpressure mechanism
   - `MultiRateLimiter` - Rate limiting for external APIs
   - `RetryManager` - Retry logic with exponential backoff

### Key Observation:
The `JobProcessor` already has good concurrency (via `asyncio.Semaphore`), but lacks:
- O(1) memory via streaming generators
- Bounded queue with backpressure
- Structured pipeline stats
- Graceful shutdown with signal handlers
- Progress callbacks

## Plan:

### Phase 1: Add async_pipeline integration to main.py

1. **Add imports for async_pipeline components**
   - Import `AsyncJobPipeline`, `ProcessorConfig` from `src.async_pipeline`
   - Import existing components: `JobProcessor`, `OutreachProcessor`

2. **Create a new endpoint `/run-query-async`**
   - Uses the new `AsyncJobPipeline` for processing
   - Returns streaming progress updates
   - Keeps existing `/run-query` for backward compatibility

3. **Add AsyncJobPipeline to AppState**
   - Initialize in lifespan
   - Add to health check

### Phase 2: Add async_pipeline integration to comprehensive_job_search.py

1. **Add imports for async_pipeline**
2. **Add optional flag `--use-async-pipeline` or `-a`**
3. **When flag is set, use AsyncJobPipeline instead of JobProcessor**
4. **Maintain backward compatibility - default to existing behavior**

### Phase 3: Testing

1. Test existing `/run-query` endpoint still works
2. Test new `/run-query-async` endpoint
3. Test comprehensive_job_search.py with and without async flag

## Dependent Files to be Edited:

1. `main.py` - Add async_pipeline integration
2. `comprehensive_job_search.py` - Add async_pipeline CLI option

## Followup Steps:

After editing files:
1. Test the API endpoints
2. Run comprehensive_job_search.py to verify
3. Monitor logs for any issues

