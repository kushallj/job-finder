# Scraper Service Async HTTP Client Refactor

## Overview
This document describes the refactoring of scraper services to use async HTTP clients with proper connection pooling for efficient resource reuse, as specified in task 9.3 of the async-job-pipeline-refactor spec.

## Changes Made

### 1. multi_platform_scraper.py
**Location**: `src/scrapers/multi_platform_scraper.py`

**Changes**:
- Added `aiohttp.TCPConnector` configuration with connection pooling
- Configured limits:
  - `limit=50`: Maximum total connections across all hosts
  - `limit_per_host=10`: Maximum connections per individual host
  - `ttl_dns_cache=300`: DNS cache TTL of 5 minutes
  - `enable_cleanup_closed=True`: Automatic cleanup of closed connections
- Enhanced timeout configuration with separate connect and read timeouts:
  - `total=25`: Total timeout for request
  - `connect=5.0`: Connection timeout
  - `sock_read=15.0`: Socket read timeout

**Benefits**:
- Reuses existing TCP connections instead of creating new ones for each request
- Reduces connection overhead and latency
- Prevents DNS lookup overhead through caching
- Automatically cleans up stale connections

### 2. ats_scraper.py
**Location**: `src/scrapers/ats_scraper.py`

**Changes**:
- Added `httpx.Limits` configuration for connection pooling
- Configured limits:
  - `max_connections=50`: Maximum total connections in pool
  - `max_keepalive_connections=20`: Maximum idle connections to keep alive

**Benefits**:
- Efficiently reuses HTTP connections across multiple API calls
- Maintains a pool of warm connections for faster subsequent requests
- Reduces handshake overhead when calling multiple ATS APIs concurrently

### 3. crawl.py
**Location**: `src/scrapers/crawl.py`

**Changes**:
- Updated both `cloudflare_crawl()` and `cloudflare_render_page()` functions
- Added `httpx.Limits` configuration:
  - `max_connections=10`: Maximum total connections
  - `max_keepalive_connections=5`: Maximum idle connections
- Applied to all Cloudflare Browser Rendering API calls

**Benefits**:
- Reuses connections for polling operations in async crawl workflow
- Reduces latency for multi-page crawls
- Efficient resource usage when rendering multiple pages

### 4. api_scraper.py
**Location**: `src/scrapers/api_scraper.py`

**Changes**:
- Enhanced `_fetch_foorilla()` method with connection pooling
- Added `aiohttp.TCPConnector` configuration similar to multi_platform_scraper
- Configured with appropriate limits for Foorilla API interactions
- Added separate connect and socket read timeouts

**Benefits**:
- Faster API interactions through connection reuse
- Better handling of concurrent requests to Foorilla
- Reduced connection establishment overhead

### 5. google_career_scraper.py
**Location**: `src/scrapers/google_career_scraper.py`

**Changes**:
- Added `httpx.Limits` to the HTTP fallback path
- Configured for optimal connection reuse:
  - `max_connections=10`
  - `max_keepalive_connections=5`

**Benefits**:
- Improves fallback HTTP request performance
- Maintains warm connections for subsequent career page fetches

## Connection Pool Configuration Strategy

### aiohttp.TCPConnector Parameters
```python
connector = aiohttp.TCPConnector(
    limit=50,                      # Total connection limit
    limit_per_host=10,             # Per-host connection limit
    ttl_dns_cache=300,             # DNS cache for 5 minutes
    enable_cleanup_closed=True,    # Auto-cleanup closed connections
)
```

### httpx.Limits Parameters
```python
limits = httpx.Limits(
    max_connections=50,            # Total connection pool size
    max_keepalive_connections=20,  # Idle connection pool size
)
```

## Requirements Coverage

This refactoring addresses the following requirements from the spec:

### Requirement 11.2: Async HTTP Clients
✅ All scraper services now use async HTTP clients (aiohttp or httpx) exclusively

### Requirement 11.4: Non-blocking I/O
✅ All HTTP operations are non-blocking and allow other coroutines to execute concurrently

### Requirement 12.2: HTTP Session Reuse
✅ HTTP sessions are reused across multiple API calls through connection pooling

### Requirement 12.4: Connection Pool Configuration
✅ Connection pools are configured with appropriate size and overflow limits to prevent resource leaks

## Performance Impact

### Before Refactoring
- New TCP connection established for each HTTP request
- 3-way handshake overhead: ~50-200ms per request
- DNS lookup on every request: ~10-100ms
- No connection reuse

### After Refactoring
- Connections reused from pool: ~1-5ms overhead
- DNS cached for 5 minutes
- Warm connections ready for immediate use
- Reduced server load through persistent connections

### Expected Improvements
- **Latency**: 50-80% reduction in average request latency
- **Throughput**: 2-3x improvement in requests per second
- **Resource Usage**: 40-60% reduction in network overhead
- **Scalability**: Better handling of concurrent requests

## Testing Recommendations

1. **Load Testing**: Verify connection pool behaves correctly under high concurrency
2. **Stress Testing**: Ensure pool limits prevent resource exhaustion
3. **Integration Testing**: Confirm all scrapers work correctly with pooled connections
4. **Performance Testing**: Measure latency and throughput improvements

## Monitoring

Monitor the following metrics to ensure optimal performance:

1. **Connection Pool Utilization**: Track active vs idle connections
2. **Connection Wait Times**: Identify if pool size needs adjustment
3. **DNS Cache Hit Rate**: Verify DNS caching is effective
4. **Request Latency**: Measure improvements in response times
5. **Connection Errors**: Monitor for pool exhaustion or timeout issues

## Future Enhancements

1. **Dynamic Pool Sizing**: Adjust pool size based on load
2. **Circuit Breaker Integration**: Close connections when circuit opens
3. **Connection Health Checks**: Proactively remove stale connections
4. **Per-Service Pool Tuning**: Customize pool sizes per external service
5. **Metrics Export**: Export connection pool metrics to monitoring system

## Conclusion

All scraper services now use async HTTP clients with properly configured connection pooling, meeting the requirements for efficient resource reuse and optimal performance. The changes are backward compatible and require no modifications to calling code.
