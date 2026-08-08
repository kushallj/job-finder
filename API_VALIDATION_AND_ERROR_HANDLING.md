# API Request Validation and Error Handling Implementation

This document details the comprehensive request validation and error handling system implemented for the FastAPI REST API.

**Requirements Addressed:**
- **23.2**: Validate request parameters with comprehensive error responses and proper HTTP status codes
- **23.3**: Return processing statistics in response
- **23.4**: Implement request timeout handling

## Implementation Summary

### 1. Pydantic Request Models (`src/api_models.py`)

Comprehensive Pydantic models for all API endpoints with field validation:

#### Request Models

| Model | Purpose | Key Validations |
|-------|---------|-----------------|
| `QueryRequest` | Job search and processing | - Query: non-empty, max 500 chars<br>- min_score: 0-100<br>- timeout_seconds: 10-3600 |
| `ContactSearchRequest` | Contact discovery | - company_name: non-empty, max 200 chars<br>- limit: 1-50<br>- SMTP verify toggle |
| `OutreachRequest` | Send outreach emails | - job_id: positive integer<br>- contact_email: RFC 5321 format, normalized<br>- contact_name: non-empty |
| `FollowUpRequest` | Send follow-up emails | - outreach_id: positive integer<br>- follow_up_number: 1-3 |
| `CrawlRequest` | Cloudflare crawling | - URL: HTTPS only, max 2048 chars<br>- limit: 1-500 pages<br>- depth: 1-5 levels |

#### Response Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `QueryResponse` | Pipeline execution results | - Statistics (jobs_fetched, jobs_processed, etc.)<br>- Trace ID for debugging<br>- Resume used<br>- Timestamp |
| `AsyncPipelineResponse` | Async pipeline results | - PipelineStatistics with throughput<br>- Success/failure counts<br>- Processing time |
| `ContactSearchResponse` | Contact discovery results | - Contacts found/saved counts<br>- List of ContactData<br>- Timestamp |
| `OutreachResponse` | Outreach send status | - Email sent status<br>- Outreach record ID<br>- Trace ID |
| `FollowUpResponse` | Follow-up send status | - Follow-up number<br>- Email sent status<br>- Trace ID |
| `JobsResponse` | Jobs list with pagination | - List of JobData<br>- PaginationData<br>- Timestamp |
| `ContactsResponse` | Contacts list with pagination | - List of ContactData<br>- PaginationData<br>- Timestamp |

#### Statistics Models

**PipelineStatistics** (Requirement 23.3 - Return processing statistics):
```python
- jobs_fetched: int              # Jobs retrieved from source
- jobs_processed: int            # Jobs sent through pipeline
- jobs_completed: int            # Successfully processed jobs
- jobs_failed: int               # Failed jobs
- processing_time_seconds: float # Total processing time
- throughput_jobs_per_second: float  # Jobs per second
- success_rate: float (property) # Auto-calculated percentage
```

#### Error Response Models

| Model | Purpose | HTTP Status |
|-------|---------|-------------|
| `ErrorResponse` | Standard error format | Varies (400, 422, 500, etc.) |
| `TimeoutErrorResponse` | Request timeouts | 504 Gateway Timeout |
| `RateLimitErrorResponse` | Rate limit exceeded | 429 Too Many Requests |

### 2. Comprehensive Error Handlers (`src/api_error_handlers.py`)

Custom exception classes and handlers for proper HTTP error responses:

#### Custom Exceptions

| Exception | Status Code | Use Case |
|-----------|-------------|----------|
| `APIError` | 500 | Base exception for all API errors |
| `ValidationError` | 422 | Request validation failures |
| `ResourceNotFoundError` | 404 | Database record not found |
| `ServiceUnavailableError` | 503 | Service initialization failed |
| `TimeoutError` | 504 | Request/operation timeout |
| `RateLimitError` | 429 | Rate limit exceeded |
| `DatabaseError` | 500 | Database operation failures |
| `ExternalAPIError` | 502 | External API call failures |

#### Exception Handlers

All handlers registered automatically via `register_error_handlers(app)`:

1. **api_error_handler**: Catches custom APIError exceptions
2. **validation_error_handler**: Catches Pydantic RequestValidationError
3. **pydantic_validation_error_handler**: Catches Pydantic ValidationError
4. **asyncio_timeout_error_handler**: Catches asyncio.TimeoutError
5. **generic_exception_handler**: Catch-all for unhandled exceptions

#### Error Response Format

All error responses follow this structure:
```json
{
  "status": "error",
  "error": "ValidationError",
  "message": "Request validation failed. Please check the request parameters.",
  "details": [
    {
      "field": "min_score",
      "message": "Value must be between 0 and 100",
      "type": "value_error"
    }
  ],
  "trace_id": "a4f8-123",
  "timestamp": "2024-03-03T10:15:23.123456"
}
```

### 3. Updated API Endpoints

All endpoints updated with:
- Response model type hints
- Request validation with comprehensive error handling
- Timeout protection using `asyncio.wait_for()`
- Proper exception raising with custom exceptions
- Trace ID propagation for debugging

#### Updated Endpoints

| Endpoint | Request Model | Response Model | Timeout |
|----------|---------------|----------------|---------|
| `POST /run-query` | `QueryRequest` | `QueryResponse` | Configurable (default 300s) |
| `POST /run-query-async` | `QueryRequest` | `AsyncPipelineResponse` | Configurable (default 300s) |
| `POST /api/contacts/search` | `ContactSearchRequest` | `ContactSearchResponse` | 120s |
| `POST /api/outreach/send` | `OutreachRequest` | `OutreachResponse` | 30s |
| `POST /api/outreach/followup` | `FollowUpRequest` | `FollowUpResponse` | 30s |
| `GET /api/jobs` | Query params | `JobsResponse` | None |
| `GET /api/contacts` | Query params | `ContactsResponse` | None |

### 4. Request Timeout Handling (Requirement 23.4)

All async operations now have timeout protection:

```python
# Example: Pipeline execution with timeout
results = await asyncio.wait_for(
    state.async_pipeline.run(
        query=request.query,
        resume_text=resume_text,
        filters={"min_score": request.min_score},
    ),
    timeout=request.timeout_seconds or 300,  # Configurable timeout
)
```

Timeouts trigger `APITimeoutError` which returns:
```json
{
  "status": "error",
  "error": "TimeoutError",
  "message": "Operation 'job processing pipeline' timed out after 300 seconds",
  "timeout_seconds": 300,
  "trace_id": "abc-123",
  "timestamp": "2024-03-03T10:15:23.123456"
}
```

## Validation Examples

### 1. Query Validation

**Valid:**
```python
QueryRequest(
    query="python developer",
    min_score=70,
    location="Remote"
)
```

**Invalid - Empty Query:**
```python
QueryRequest(query="")  # ValidationError: Query cannot be empty
```

**Invalid - Score Out of Range:**
```python
QueryRequest(query="test", min_score=150)  # ValidationError: Value must be 0-100
```

### 2. Email Validation

**Valid:**
```python
OutreachRequest(
    job_id=123,
    contact_email="hiring@company.com",  # Normalized to lowercase
    contact_name="Jane Smith"
)
```

**Invalid - Bad Email Format:**
```python
OutreachRequest(
    job_id=123,
    contact_email="not-an-email",  # ValidationError: Invalid email format
    contact_name="Jane"
)
```

### 3. URL Validation

**Valid:**
```python
CrawlRequest(url="https://stripe.com/jobs")  # HTTPS required
```

**Invalid - HTTP URL:**
```python
CrawlRequest(url="http://stripe.com/jobs")  # ValidationError: URL must start with https://
```

## Testing

Comprehensive test suite in `tests/test_api_validation.py`:

- **27 test cases** covering:
  - Valid request creation
  - Field validation (empty strings, ranges, formats)
  - Default values
  - Email normalization
  - Success rate calculation
  - Error response structure

**Test Results:**
```
tests/test_api_validation.py ............................ [100%]
27 passed in 0.14s
```

## HTTP Status Codes

| Status Code | Description | Use Cases |
|-------------|-------------|-----------|
| 200 OK | Success | Successful GET requests |
| 404 Not Found | Resource not found | Job, Contact, or OutreachRecord not found |
| 422 Unprocessable Entity | Validation error | Invalid request parameters |
| 429 Too Many Requests | Rate limit exceeded | API rate limiting |
| 500 Internal Server Error | Server error | Unexpected exceptions, database errors |
| 502 Bad Gateway | External API error | External service failures |
| 503 Service Unavailable | Service not available | Service not initialized |
| 504 Gateway Timeout | Request timeout | Operation exceeded timeout threshold |

## Benefits

### 1. Type Safety
- Pydantic models ensure type correctness at runtime
- FastAPI generates OpenAPI schema automatically
- IDE autocomplete for request/response fields

### 2. Clear Error Messages
- Detailed validation errors with field paths
- Human-readable error messages
- Trace IDs for debugging

### 3. Consistent API
- All endpoints follow same error response format
- Predictable validation behavior
- Standard HTTP status codes

### 4. Developer Experience
- Auto-generated API documentation at `/docs`
- Request examples in models
- Comprehensive test coverage

### 5. Security
- Input sanitization through validation
- Email normalization prevents case sensitivity issues
- URL protocol enforcement (HTTPS only)
- Request size limits (max length validations)

### 6. Observability
- Trace IDs in all responses for request correlation
- Structured error logging
- Timeout tracking

## Migration Notes

### Breaking Changes
None - all endpoints maintain backward compatibility while adding:
- Response model type hints
- Better error messages
- Timeout protection

### Removed Code
- Duplicate outreach endpoints (consolidated to single implementation)
- Old request model definitions (moved to `src/api_models.py`)
- Basic `HTTPException` usage (replaced with custom exceptions)

## Future Enhancements

Potential improvements for future iterations:

1. **Rate Limiting Middleware**: Global rate limiting per IP/API key
2. **Request Validation Logging**: Log all validation failures for analytics
3. **Custom Validators**: Domain-specific validation (e.g., check if job exists before outreach)
4. **Response Compression**: Compress large responses (jobs list, contacts list)
5. **API Versioning**: Version endpoints for future breaking changes
6. **Webhook Validation**: Validate webhook signatures for external integrations
7. **Field-Level Permissions**: Role-based field access control
8. **Request Caching**: Cache identical requests to reduce load

## Related Files

- `src/api_models.py` - Pydantic request/response models
- `src/api_error_handlers.py` - Custom exceptions and error handlers
- `main.py` - Updated FastAPI application with validation
- `tests/test_api_validation.py` - Validation test suite
- `.kiro/specs/system-architecture/requirements.md` - Original requirements
- `.kiro/specs/system-architecture/design.md` - System architecture design
