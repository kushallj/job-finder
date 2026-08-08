# Async Job Pipeline

High-performance async job processing system with O(1) memory usage, backpressure control, and automatic retry logic.

## Core Structure

### Data Models (`types.py`)

#### JobContext
Immutable (frozen) dataclass representing a job to be processed:
```python
@dataclass(frozen=True)
class JobContext:
    job_id: str
    title: str
    company: str
    description: str
    url: str
    source: str
    location: str = ""
    posted_date: Optional[datetime] = None
    salary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Key Features:**
- Frozen dataclass ensures thread-safety and prevents accidental mutations
- Validates required fields (job_id, title, company must be non-empty)
- Provides `to_dict()`, `from_dict()`, `to_json()`, `from_json()` methods

#### ProcessingResult
Dataclass capturing the result of job processing:
```python
@dataclass
class ProcessingResult:
    job_id: str
    status: JobStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    attempt_count: int = 1
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    worker_id: str = ""
```

**Key Features:**
- Factory methods: `ProcessingResult.success()` and `ProcessingResult.failure()`
- Validation: FAILED status requires error, COMPLETED status requires data
- Helper methods: `is_success()`, `is_retryable()`

#### JobStatus
Enum representing job processing states:
```python
class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
```

### Configuration (`config.py`)

#### ProcessorConfig
Main configuration dataclass with all tunable pipeline parameters:

**Concurrency Settings:**
- `worker_count`: Number of concurrent workers (default: 5)
- `max_concurrent_api_calls`: Max concurrent external API calls (default: 10)
- `queue_size`: Bounded queue size for backpressure (default: 100)

**Retry Settings:**
- `max_retries`: Maximum retry attempts (default: 3)
- `retry_base_delay`: Base delay for exponential backoff (default: 1.0s)
- `retry_max_delay`: Maximum delay between retries (default: 60.0s)
- `retry_exponential_base`: Exponential base for backoff (default: 2.0)
- `retry_jitter`: Add random jitter to delays (default: True)

**Rate Limiting (requests per second):**
- `llm_rate_limit`: Rate limit for LLM API calls (default: 10.0)
- `email_rate_limit`: Rate limit for email operations (default: 1.0)
- `scraper_rate_limit`: Rate limit for scraping (default: 5.0)

**Timeouts (seconds):**
- `llm_timeout`: Timeout for LLM calls (default: 30.0)
- `email_timeout`: Timeout for email operations (default: 15.0)
- `scraper_timeout`: Timeout for scraping (default: 20.0)
- `database_timeout`: Timeout for DB operations (default: 10.0)

**Database Settings:**
- `db_chunk_size`: Jobs per database query (default: 100)
- `db_pool_size`: Connection pool size (default: 10)
- `db_max_overflow`: Max overflow connections (default: 20)

**Usage:**
```python
# Use defaults
config = ProcessorConfig()

# Override specific values
config = ProcessorConfig(
    worker_count=10,
    queue_size=200,
    max_retries=5
)

# Load from environment variables
config = ProcessorConfig.from_env()

# Validate configuration
config.validate()
```

#### RetryConfig
Configuration for retry behavior:
```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_exceptions: tuple = (Exception,)
```

#### RateLimitConfig
Configuration for rate limiting:
```python
@dataclass
class RateLimitConfig:
    rate: float  # tokens per time_period
    capacity: int = 1
    time_period: float = 1.0
```

### Structured Logging (`__init__.py`)

#### configure_structured_logging()
Set up structured logging with JSON formatting or colored console output:

```python
from src.async_pipeline import configure_structured_logging, get_logger

# Configure for production (JSON format)
configure_structured_logging(
    log_level="INFO",
    json_format=True,
    include_timestamp=True
)

# Configure for development (colored console)
configure_structured_logging(
    log_level="DEBUG",
    json_format=False,
    include_timestamp=True
)

# Get a logger instance
logger = get_logger(__name__)

# Use structured logging with context
logger.info(
    "processing_job",
    job_id="job-123",
    worker_id="worker-1",
    attempt=1,
    processing_time_ms=1500.0
)
```

**Features:**
- Automatic context propagation (job_id, worker_id)
- JSON formatting for production monitoring
- Colored console output for development
- ISO timestamp formatting
- Exception stack traces

### Async Database (`config.py`)

#### create_async_db_engine()
Create async SQLAlchemy engine with connection pooling:

```python
from src.async_pipeline import create_async_db_engine, create_async_session_factory

# Create async engine
engine = create_async_db_engine(
    database_url="postgresql://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30.0,
    pool_pre_ping=True,
    echo=False
)

# Create async session factory
async_session = create_async_session_factory(engine)

# Use in async context
async with async_session() as session:
    result = await session.execute(select(Job))
    jobs = result.scalars().all()
```

**Supported Databases:**
- SQLite: `sqlite:///path/to/db` → automatically converts to `sqlite+aiosqlite:///`
- PostgreSQL: `postgresql://user:pass@host/db` → converts to `postgresql+asyncpg://`

**Connection Pooling:**
- `pool_size`: Number of persistent connections (default: 10)
- `max_overflow`: Additional connections when pool is full (default: 20)
- `pool_timeout`: Seconds to wait for connection (default: 30.0)
- `pool_pre_ping`: Test connections before use (prevents stale connections)

## Requirements Coverage

This implementation covers the following requirements:

### Requirement 1.1: Streaming Job Production
- **JobContext** (frozen dataclass) ensures immutable job data
- Prevents concurrent workers from causing race conditions

### Requirement 1.2: Bounded Queue with Backpressure
- **ProcessorConfig.queue_size** configures queue capacity
- Bounded queue blocks producer when full

### Requirement 17.1: Job Context Immutability
- **@dataclass(frozen=True)** on JobContext prevents mutations
- Thread-safe by design

### Requirement 17.2: Immutable Data Structures
- JobContext is frozen
- All data passed between workers is immutable

### Requirement 17.4: Shared State Avoidance
- No shared mutable state
- Each worker operates on immutable JobContext

### Requirement 12.1: Database Connection Pooling
- **create_async_db_engine()** with QueuePool
- Configurable pool_size and max_overflow

### Requirement 12.3: Connection Reuse
- Connection pool reuses connections across operations
- Automatic connection management

### Requirement 12.5: Connection Pool Timeouts
- **pool_timeout** prevents resource leaks
- Configurable per environment

### Requirement 19.4: Per-Task Database Sessions
- **create_async_session_factory()** for isolated sessions
- Each worker gets its own session context

## Testing

Run the test suite:
```bash
pytest tests/test_async_pipeline_core.py -v
```

Test coverage includes:
- JobContext immutability and validation
- ProcessingResult validation
- ProcessorConfig validation
- RetryConfig validation
- RateLimitConfig validation
- Structured logging setup
- Async database engine creation
- Session factory creation

## Next Steps

The following components build on this core structure:
1. **producer.py**: Streaming job producer with async generators
2. **bounded_queue.py**: Async queue with backpressure
3. **worker_pool.py**: Concurrent worker pool
4. **retry.py**: Exponential backoff retry logic
5. **rate_limiter.py**: Token bucket rate limiting
6. **pipeline.py**: Full pipeline orchestration
