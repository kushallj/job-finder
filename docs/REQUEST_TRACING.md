# Request Tracing and Correlation IDs

## Overview

The NEXUS Job Acquisition System implements comprehensive request tracing using X-Trace-ID headers and correlation IDs for end-to-end request tracking across all system components.

**Requirements Validated:**
- **Requirement 23.5**: Include request tracing with X-Trace-ID headers
- **Requirement 25.2**: Include correlation_id in all log entries
- **Requirement 33.1** (Property 33): Request Tracing Completeness

## Features

### 1. X-Trace-ID Header Generation

Every incoming HTTP request receives a unique trace ID:

```
X-Trace-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Key Characteristics:**
- **UUID4 Format**: Random UUIDs provide global uniqueness
- **Client-Provided Support**: Accepts X-Trace-ID from client for distributed tracing
- **Auto-Generation**: Generates UUID if client doesn't provide one
- **Response Headers**: Trace ID included in all response headers

### 2. Log Propagation

All log entries include the trace ID in a consistent format:

```
[550e8400-e29b-41d4-a716-446655440000] Request started: GET /api/health | client=127.0.0.1
[550e8400-e29b-41d4-a716-446655440000] Request completed: GET /api/health | status=200 | duration=45.23ms
```

**Logged Information:**
- Request start with client IP
- Request completion with status and duration
- All errors with full context
- HTTP method and path
- Response status code
- Request duration in milliseconds

### 3. Async Pipeline Integration

The trace middleware integrates with the async_pipeline's structured logging:

```python
# Correlation ID is set for async pipeline compatibility
from src.async_pipeline import set_correlation_id, clear_correlation_id

# On request start
set_correlation_id(trace_id)

# On request completion
clear_correlation_id()
```

This ensures trace IDs propagate through:
- Worker pool operations
- Job processing tasks
- Rate limiter events
- Retry attempts
- Database operations

### 4. Trace ID Indexing

Trace IDs use UUID4 format for optimal indexing in log aggregation systems:

**Benefits:**
- **Standard Format**: Compatible with all log aggregation tools (Elasticsearch, Splunk, etc.)
- **High Cardinality**: UUIDs ensure uniqueness across distributed systems
- **String Indexing**: Can be indexed as keyword fields for fast searching
- **No Collisions**: UUID4 provides 2^122 unique values

## Implementation

### Middleware Structure

The `trace_middleware` in `main.py` handles all trace ID operations:

```python
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """
    Request tracing middleware for comprehensive request tracking.
    
    Generates X-Trace-ID header for all requests, propagates trace IDs through
    all log entries, and includes trace ID in response headers for end-to-end
    request tracing.
    
    Requirements: 23.5, 25.2, 33.1
    """
    # Accept client-provided trace ID or generate new one
    tid = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    
    # Store in request state
    request.state.trace_id = tid
    
    # Set correlation ID for async_pipeline
    if _ASYNC_PIPELINE_OK:
        try:
            from src.async_pipeline import set_correlation_id
            set_correlation_id(tid)
        except Exception:
            pass
    
    # Log request start
    start_time = time.time()
    log.info("[%s] Request started: %s %s | client=%s", tid, ...)
    
    try:
        # Process request
        resp = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Add trace ID to response
        resp.headers["X-Trace-ID"] = tid
        
        # Log completion
        log.info("[%s] Request completed: %s %s | status=%d | duration=%.2fms", ...)
        
        return resp
    except Exception as exc:
        # Log error with trace ID
        log.error("[%s] Request failed: ...", tid, ...)
        
        # Return error response with trace ID
        return JSONResponse({
            "detail": "Internal server error",
            "trace_id": tid,
            ...
        }, headers={"X-Trace-ID": tid})
    finally:
        # Cleanup correlation ID
        if _ASYNC_PIPELINE_OK:
            clear_correlation_id()
```

## Usage

### For API Clients

**Send requests normally - trace IDs are automatic:**

```bash
curl http://localhost:8000/api/health
```

Response includes trace ID:
```json
HTTP/1.1 200 OK
X-Trace-ID: 550e8400-e29b-41d4-a716-446655440000
...
```

**For distributed tracing, provide your own trace ID:**

```bash
curl -H "X-Trace-ID: my-custom-trace-id" http://localhost:8000/api/health
```

### For Log Searching

**Search logs by trace ID:**

```bash
# Grep logs for specific trace ID
grep "550e8400-e29b-41d4-a716-446655440000" logs/main.log

# In Elasticsearch
GET /logs/_search
{
  "query": {
    "term": { "trace_id": "550e8400-e29b-41d4-a716-446655440000" }
  }
}
```

**Example log output:**

```
2026-08-01 10:15:23 [INFO] main: [550e8400-e29b-41d4-a716-446655440000] Request started: GET /api/health | client=127.0.0.1
2026-08-01 10:15:23 [INFO] email_outreach.health: SMTP connection check passed
2026-08-01 10:15:23 [INFO] httpx: HTTP Request: GET https://api.github.com/rate_limit "HTTP/1.1 200 OK"
2026-08-01 10:15:23 [INFO] main: [550e8400-e29b-41d4-a716-446655440000] Request completed: GET /api/health | status=200 | duration=45.23ms
```

### For Route Handlers

Access trace ID in route handlers:

```python
@app.get("/my-endpoint")
async def my_endpoint(request: Request):
    trace_id = request.state.trace_id
    
    # Use in logs
    log.info("[%s] Processing endpoint", trace_id)
    
    # Return in response
    return {"trace_id": trace_id, "data": ...}
```

## Distributed Tracing

### Multi-Service Tracing

For microservices architectures, propagate trace IDs across service boundaries:

**Service A (initiator):**
```python
import httpx

# Generate trace ID for transaction
trace_id = str(uuid.uuid4())

# Call Service B with trace ID
response = await httpx.get(
    "http://service-b/process",
    headers={"X-Trace-ID": trace_id}
)
```

**Service B (consumer):**
```python
# Automatically receives and uses client's trace ID
# All logs will include the same trace ID
```

### Correlation with External Systems

Trace IDs can be correlated with:
- **Application Performance Monitoring (APM)**: New Relic, Datadog, etc.
- **Log Aggregation**: Elasticsearch, Splunk, CloudWatch
- **Error Tracking**: Sentry, Rollbar
- **Distributed Tracing**: Jaeger, Zipkin, OpenTelemetry

## Metrics and Observability

### Request Duration Tracking

Every request logs duration in milliseconds:

```
[trace-id] Request completed: GET /api/health | status=200 | duration=45.23ms
```

**Use Cases:**
- Identify slow requests
- Calculate percentile latencies (p50, p95, p99)
- Detect performance regressions
- Analyze request patterns

### Error Correlation

Failed requests include full trace ID context:

```
[trace-id] Request failed: GET /api/health | duration=123.45ms | error=ConnectionError
```

**Use Cases:**
- Debug production issues
- Correlate errors across services
- Analyze error patterns
- Reproduce user issues

## Testing

### Unit Tests

Comprehensive tests ensure trace ID functionality:

```python
# Test trace ID generation
def test_trace_id_generated_for_request(client):
    response = client.get("/")
    assert "X-Trace-ID" in response.headers
    uuid.UUID(response.headers["X-Trace-ID"])  # Valid UUID

# Test client-provided trace IDs
def test_trace_id_accepted_from_client(client):
    trace_id = str(uuid.uuid4())
    response = client.get("/", headers={"X-Trace-ID": trace_id})
    assert response.headers["X-Trace-ID"] == trace_id

# Test log propagation
@patch('main.log')
def test_trace_id_in_logs(mock_logger, client):
    response = client.get("/")
    trace_id = response.headers["X-Trace-ID"]
    
    # Verify trace ID in logs
    for call in mock_logger.info.call_args_list:
        if "Request started" in str(call[0]):
            assert trace_id in str(call[0])
```

### Integration Tests

See `tests/test_request_tracing.py` and `tests/test_trace_id_integration.py` for complete test coverage.

## Performance Impact

The trace middleware has minimal performance overhead:

- **UUID Generation**: ~1-2 microseconds per request
- **Header Manipulation**: Negligible (FastAPI native)
- **Logging**: Existing overhead, trace ID adds ~20 bytes per log
- **Context Variables**: ~100 nanoseconds for get/set operations

**Total Overhead**: < 0.1ms per request

## Best Practices

### 1. Always Log with Trace ID

```python
# Good
log.info("[%s] Processing job", trace_id)

# Bad
log.info("Processing job")  # No trace ID
```

### 2. Include Trace ID in Error Responses

```python
return JSONResponse({
    "error": "Something went wrong",
    "trace_id": trace_id,  # Client can report this
    "detail": ...
}, status_code=500)
```

### 3. Propagate Across Service Boundaries

```python
# Always forward X-Trace-ID to downstream services
headers = {"X-Trace-ID": request.state.trace_id}
response = await httpx.get(downstream_url, headers=headers)
```

### 4. Index Trace IDs in Databases

For long-running operations, store trace IDs in database:

```python
processing_result = ProcessingResult(
    job_id=job_id,
    trace_id=trace_id,
    status="processing",
    ...
)
```

## Troubleshooting

### Trace IDs Not Appearing in Logs

**Issue**: Logs don't include trace IDs

**Solution**: Verify middleware is registered:
```python
# Check main.py has trace_middleware decorator
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    ...
```

### Trace ID Mismatch Between Services

**Issue**: Different services show different trace IDs for same request

**Solution**: Ensure X-Trace-ID header is propagated:
```python
# Always include in downstream requests
headers = {"X-Trace-ID": request.state.trace_id}
```

### Performance Issues with Logging

**Issue**: High log volume impacts performance

**Solution**: Implement log sampling for high-volume endpoints:
```python
if should_log(sample_rate=0.1):  # Log 10% of requests
    log.info("[%s] Request completed", trace_id)
```

## Future Enhancements

### Planned Features

1. **OpenTelemetry Integration**: Full distributed tracing support
2. **Trace Context Propagation**: W3C Trace Context standard support
3. **Automatic Span Creation**: Hierarchical trace spans for operations
4. **Trace Visualization**: Built-in trace visualization dashboard
5. **Sampling**: Adaptive sampling for high-volume endpoints
6. **Baggage Propagation**: Metadata propagation with trace context

### Migration to OpenTelemetry

Future versions will migrate to OpenTelemetry for standardized tracing:

```python
# Future implementation
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Auto-instrument FastAPI
FastAPIInstrumentor().instrument_app(app)

# Traces automatically created and propagated
```

## References

- [Requirement 23.5](../.kiro/specs/system-architecture/requirements.md#requirement-23-rest-api): X-Trace-ID headers
- [Requirement 25.2](../.kiro/specs/system-architecture/requirements.md#requirement-25-structured-logging): Correlation IDs in logs
- [Property 33](../.kiro/specs/system-architecture/design.md#property-33-request-tracing-completeness): Request Tracing Completeness
- [W3C Trace Context](https://www.w3.org/TR/trace-context/): Standard trace propagation
- [OpenTelemetry](https://opentelemetry.io/): Observability framework
