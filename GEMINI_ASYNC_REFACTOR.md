# Gemini Service Async HTTP Refactor

## Summary

Refactored `src/ai/gemini_service.py` from using blocking SDK calls with thread executor to true async HTTP calls using `aiohttp`. This change eliminates blocking I/O and enables efficient concurrent processing in the async job pipeline.

## Changes Made

### 1. Replaced Blocking SDK with Async HTTP

**Before:**
```python
# Blocking SDK call wrapped in thread executor
loop = asyncio.get_event_loop()
return await loop.run_in_executor(None, _blocking_call)
```

**After:**
```python
# True async HTTP call with aiohttp
async with session.post(url, json=payload, params=params) as response:
    data = await response.json()
    return data
```

### 2. Added Connection Pooling

Implemented shared `ClientSession` with configurable connection pooling:

```python
def __init__(
    self,
    max_connections: int = 100,
    max_connections_per_host: int = 10,
    connection_timeout: float = 30.0,
    request_timeout: float = 60.0,
):
    connector = aiohttp.TCPConnector(
        limit=max_connections,
        limit_per_host=max_connections_per_host,
        ttl_dns_cache=300,
        enable_cleanup_closed=True,
    )
    self._session = aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
    )
```

### 3. Added Proper Session Cleanup

Implemented async context manager for automatic cleanup:

```python
async with GeminiService() as ai:
    skills = await ai.extract_skills(description)
    # Session automatically closed on exit
```

Or manual initialization:

```python
ai = GeminiService()
await ai.initialize()
# ... use ai ...
await ai.close()
```

### 4. Maintained Backward Compatibility

Auto-initialization on first use for existing code:

```python
ai = GeminiService()  # No await needed
skills = await ai.extract_skills(description)  # Auto-initializes
```

## Requirements Coverage

This refactor satisfies the following requirements from the async-job-pipeline-refactor spec:

- **11.1**: Uses async HTTP client (aiohttp) for all External_API calls ✓
- **11.2**: Uses async operations (no blocking I/O) ✓
- **11.4**: Allows other coroutines to execute concurrently ✓
- **12.2**: Reuses HTTP sessions across multiple API calls ✓
- **12.4**: Properly closes HTTP sessions on shutdown ✓

## API Changes

### Public Interface (Unchanged)

All public methods maintain the same signature:

```python
await ai.extract_skills(description) → List[str]
await ai.match_resume_to_job(resume, skills) → Dict
await ai.rewrite_resume(resume, description) → str
await ai.generate_cover_letter(resume, desc, company) → str
```

### New Configuration Options

```python
GeminiService(
    max_connections=100,           # Total connection pool size
    max_connections_per_host=10,   # Max connections per host
    connection_timeout=30.0,       # Connection timeout (seconds)
    request_timeout=60.0,          # Total request timeout (seconds)
)
```

## Benefits

1. **No Thread Executor Overhead**: Direct async I/O instead of blocking calls in thread pool
2. **Connection Reuse**: HTTP connections are pooled and reused across requests
3. **Configurable Rate Limiting**: Connection-per-host limits prevent overwhelming API
4. **Proper Resource Cleanup**: Async context manager ensures sessions are closed
5. **Better Concurrency**: True async allows event loop to handle other work during I/O
6. **Memory Efficient**: Single shared session instead of per-request connections

## Testing

All functionality verified with unit tests (`test_gemini_refactor.py`):

- ✓ Initialization and configuration
- ✓ Async context manager
- ✓ HTTP request structure
- ✓ Auto-initialization (backward compatibility)
- ✓ Connection pool configuration
- ✓ Error handling

## Migration Notes

### For New Code (Recommended)

```python
async with GeminiService() as ai:
    skills = await ai.extract_skills(description)
```

### For Existing Code

No changes required - auto-initialization ensures backward compatibility:

```python
ai = GeminiService()  # Works as before
skills = await ai.extract_skills(description)
```

### For Long-Running Services

Initialize once and reuse:

```python
# At startup
ai = GeminiService()
await ai.initialize()

# During runtime
skills = await ai.extract_skills(description)

# At shutdown
await ai.close()
```

## Performance Impact

- **Before**: Each API call blocked a thread executor worker
- **After**: All API calls are truly concurrent, limited only by connection pool
- **Expected Improvement**: Better throughput in high-concurrency scenarios

## Dependencies

- `aiohttp==3.9.1` (already in requirements.txt)
- Removed dependency on `google-genai` SDK (was causing blocking I/O)

## Files Modified

- `src/ai/gemini_service.py` - Complete refactor to async HTTP
- `test_gemini_refactor.py` - New unit tests
- `test_async_gemini.py` - Integration test (requires API key)

## Next Steps

This refactor enables:
- Integration with async job queue workers
- Concurrent processing of multiple jobs
- Efficient use of semaphores for rate limiting
- Better resource utilization in high-throughput scenarios
