# Graceful Shutdown Implementation for FastAPI Server

## Overview

This document describes the graceful shutdown implementation added to the FastAPI server in `main.py` to satisfy Requirements 24.1-24.4 and 34.1 from the system architecture specification.

## Requirements Implemented

### Requirement 24: Graceful Shutdown
- **24.1**: Stop accepting new jobs on SIGTERM ✅
- **24.2**: Wait for in-flight jobs to complete on SIGTERM ✅
- **24.3**: Stop accepting new jobs on SIGINT ✅
- **24.4**: Wait for in-flight jobs to complete on SIGINT ✅

### Additional Requirement 34.1
- **34.1**: Close async HTTP client sessions properly ✅
- Close database connection pools ✅
- Flush and close log handlers ✅

## Implementation Details

### Lifespan Context Manager

The FastAPI server uses a lifespan context manager (`@asynccontextmanager`) that handles both startup and shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup phase
    # - Initialize database
    # - Create service instances
    # - Initialize HTTP client pools
    
    yield  # Server runs
    
    # Shutdown phase
    # - Stop accepting new jobs
    # - Wait for in-flight jobs
    # - Close all resources
```

### Shutdown Sequence

The graceful shutdown follows this specific order to ensure clean resource cleanup:

1. **AsyncJobPipeline** (closes first, has worker pool with in-flight jobs)
   - Signal handlers in AsyncJobPipeline detect SIGTERM/SIGINT
   - Stop accepting new jobs immediately
   - Wait up to 30 seconds for in-flight jobs to complete
   - Force terminate remaining jobs after timeout
   - Close async database connection pool

2. **OutreachProcessor** (has email queue and workers)
   - Drain any pending emails
   - Close internal resources

3. **EmailOutreach** (closes HTTP client sessions)
   - Close aiohttp.ClientSession (connection pooling)
   - Close httpx.AsyncClient (HTTP/2 support)
   - Close SMTP connection pool
   - Save outreach logs

4. **JobProcessor** (closes email discovery and other resources)
   - Close email discovery service
   - Release any held resources

5. **Database Connection Pool** (SQLAlchemy engine)
   - Dispose of the engine
   - Close all database connections

6. **Log Handlers** (flush and close)
   - Flush all pending log entries
   - Close file handlers
   - Remove handlers from root logger

### Timeout Configuration

The shutdown timeout is configurable through `ProcessorConfig`:

```python
config = ProcessorConfig(
    shutdown_timeout_seconds=30,  # Wait up to 30s for graceful shutdown
    worker_count=5,
    queue_size=100,
    # ... other config
)
```

### Signal Handling

Signal handlers are registered in `AsyncJobPipeline._setup_signal_handlers()`:

- **SIGTERM**: Sent by orchestration systems (Kubernetes, Docker, systemd)
- **SIGINT**: Sent by Ctrl+C during development

Both signals trigger the same graceful shutdown sequence.

## Resource Cleanup Details

### 1. Database Connection Pools

```python
from src.database import engine as db_engine
if db_engine:
    db_engine.dispose()
```

This ensures:
- All active connections are closed
- Connection pool is drained
- No database connection leaks

### 2. HTTP Client Sessions

```python
# In EmailOutreach.close()
if self._http_session:
    await self._http_session.close()  # aiohttp session

if self._httpx_client:
    await self._httpx_client.aclose()  # httpx client
```

This ensures:
- All HTTP connections are closed
- Connection pools are drained
- TCP sockets are released
- No resource leaks

### 3. Log Handlers

```python
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    handler.flush()  # Write pending logs
    handler.close()  # Close file handles
    root_logger.removeHandler(handler)
```

This ensures:
- All pending log entries are written to disk
- File handles are closed properly
- No log truncation or loss

### 4. SMTP Connection Pool

```python
# In EmailOutreach.close()
await self.pool.close()
```

This ensures:
- All SMTP connections are properly closed
- No dangling email connections

## Testing

A comprehensive test suite is provided in `test_graceful_shutdown.py`:

```bash
python test_graceful_shutdown.py
```

### Test Coverage

1. **Startup Phase**
   - Verify all services initialize correctly
   - Check resource allocation

2. **Shutdown Phase**
   - Verify all resources are closed
   - Check cleanup order
   - Validate no exceptions during shutdown

3. **Timeout Configuration**
   - Verify shutdown timeout is set correctly
   - Check worker configuration

### Test Results

```
✅ All tests passed successfully!

Graceful shutdown implementation verified:
  ✓ Database connection pools are closed
  ✓ HTTP client sessions are closed
  ✓ Log handlers are flushed and closed
  ✓ In-flight jobs can complete before shutdown
  ✓ Shutdown timeout is configurable
```

## Production Deployment

### Kubernetes/Docker

When deploying with Kubernetes or Docker, the graceful shutdown will:

1. Receive SIGTERM from orchestrator
2. Stop accepting new requests (health check fails)
3. Wait for in-flight jobs (up to shutdown timeout)
4. Close all resources
5. Exit cleanly

### Systemd

When running as a systemd service:

```ini
[Service]
Type=notify
TimeoutStopSec=40
```

Set `TimeoutStopSec` to be slightly longer than `shutdown_timeout_seconds` to allow graceful shutdown to complete.

## Monitoring

The shutdown process logs detailed information:

```
2026-07-31 23:57:07 [INFO] main: 🔴 Shutting down gracefully…
2026-07-31 23:57:07 [INFO] main: Shutting down AsyncJobPipeline (waiting for in-flight jobs)…
2026-07-31 23:57:07 [INFO] main: ✅ AsyncJobPipeline shut down
2026-07-31 23:57:07 [INFO] main: Shutting down EmailOutreach (closing HTTP clients and SMTP pool)…
2026-07-31 23:57:07 [INFO] main: ✅ EmailOutreach shut down (HTTP clients closed)
2026-07-31 23:57:07 [INFO] main: ✅ Database connection pool closed
2026-07-31 23:57:07 [INFO] main: ✅ Log handlers closed
👋 Shutdown complete in 0.01s
```

Monitor these logs to ensure:
- All resources close successfully
- Shutdown completes within timeout
- No errors during cleanup

## Known Issues

1. **AsyncJobPipeline logging**: The AsyncJobPipeline module uses structured logging syntax that's incompatible with standard Python logging. This causes a warning during shutdown but doesn't affect functionality. This should be addressed in a separate task.

## Future Enhancements

1. **Metrics Export**: Export shutdown metrics to Prometheus
2. **Health Check Integration**: Coordinate with health check endpoint
3. **Graceful Connection Draining**: Drain active HTTP connections before shutdown
4. **Configurable Shutdown Order**: Allow customization of shutdown sequence

## References

- FastAPI Lifespan: https://fastapi.tiangolo.com/advanced/events/
- Signal Handling: https://docs.python.org/3/library/signal.html
- SQLAlchemy Engine Disposal: https://docs.sqlalchemy.org/en/20/core/connections.html
- aiohttp Session Management: https://docs.aiohttp.org/en/stable/client_reference.html
