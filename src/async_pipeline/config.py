"""
Configuration for the async job pipeline.

This module provides the ProcessorConfig dataclass with all tunable
parameters for the pipeline, following the design specification.

Requirements Coverage: 15.1, 15.2, 15.3, 15.4, 15.5

Environment-Specific Profiles:
- development: Local development with verbose logging and reduced throughput
- staging: Pre-production testing with moderate throughput and full logging
- production: High-performance production with optimized settings

==============================================================================
CONFIGURATION BEST PRACTICES
==============================================================================

1. PROFILE SELECTION
   -----------------
   Use NEXUS_ENV environment variable to select the appropriate profile:
   
   # Development (default if not set)
   export NEXUS_ENV=development
   
   # Staging for pre-production testing
   export NEXUS_ENV=staging
   
   # Production for optimized performance
   export NEXUS_ENV=production

2. PROFILE CHARACTERISTICS
   -----------------------
   
   Development Profile (NEXUS_ENV=development):
   - Worker count: 2 (low for debugging)
   - Log level: DEBUG (verbose for troubleshooting)
   - Auto-send emails: DISABLED (safety first)
   - Timeouts: Shorter (faster feedback)
   - Retries: 2 attempts (quick failure detection)
   - Best for: Local development, debugging, testing new features
   
   Staging Profile (NEXUS_ENV=staging):
   - Worker count: 5 (moderate throughput)
   - Log level: INFO (balanced visibility)
   - Auto-send emails: ENABLED (test email delivery)
   - Timeouts: Standard (production-like)
   - Retries: 3 attempts (standard reliability)
   - Best for: Pre-production testing, integration testing, QA
   
   Production Profile (NEXUS_ENV=production):
   - Worker count: 10 (high throughput)
   - Log level: WARNING (reduce noise)
   - Auto-send emails: ENABLED (full operation)
   - Timeouts: Longer (reliability over speed)
   - Retries: 5 attempts (maximum reliability)
   - Best for: Production deployment, high-volume processing

3. CUSTOMIZING CONFIGURATIONS
   --------------------------
   Override profile defaults using keyword arguments:
   
   # Start with production but use fewer workers
   config = ProcessorConfig.from_profile("production", worker_count=5)
   
   # Start with staging but enable debug logging
   config = ProcessorConfig.from_profile("staging", log_level="DEBUG")
   
   # Use environment variables for individual overrides
   export PIPELINE_WORKER_COUNT=15
   config = ProcessorConfig.from_env()

4. PERFORMANCE TUNING
   ------------------
   
   Worker Count:
   - Start with 5 workers and increase based on throughput needs
   - Monitor CPU usage and API rate limits
   - Too many workers can overwhelm external APIs
   - Rule of thumb: workers <= (API rate limit * average processing time)
   
   Queue Size:
   - Should be 2-4x worker count for optimal throughput
   - Larger queues improve batching but increase memory
   - Minimum 10 to ensure adequate buffering
   
   Rate Limits:
   - Set based on external API quotas
   - LLM rate limit: Ollama (local) can handle higher rates than Gemini
   - Email rate limit: Keep low (1-2/s) to avoid spam detection
   - Scraper rate limit: Respect robots.txt and site policies

5. RELIABILITY SETTINGS
   --------------------
   
   Retry Configuration:
   - max_retries: Higher for production (5), lower for development (2)
   - base_delay: Start at 1.0s, increase for flaky APIs
   - max_delay: Cap at 60s to prevent indefinite waits
   - exponential_base: Use 2.0 for standard doubling backoff
   
   Timeout Configuration:
   - LLM timeout: 20-30s (LLM calls can be slow)
   - Email timeout: 10-15s (SMTP operations)
   - Scraper timeout: 15-20s (page loads)
   - DB timeout: 5-10s (local database)

6. DATABASE CONFIGURATION
   ----------------------
   - db_pool_size: Should be >= worker_count
   - db_max_overflow: Set to 2x pool_size for burst handling
   - chunk_size: 50-100 jobs per database query
   - Use SQLite for development, PostgreSQL for production

7. LOGGING CONFIGURATION
   ---------------------
   - Development: DEBUG level for all components
   - Staging: INFO level for visibility
   - Production: WARNING level to reduce noise
   - Always use structured_logging=True for log aggregation
   - Log files are rotated at 5MB with 5 backups

8. GRACEFUL SHUTDOWN
   -----------------
   - Development: 30s timeout (quick shutdown for iteration)
   - Staging: 60s timeout (standard)
   - Production: 120s timeout (wait for in-flight jobs)
   - Configure based on average job processing time

9. SECURITY CONSIDERATIONS
   ----------------------
   - Never commit .env files with credentials
   - Use secrets management for production (Vault, AWS Secrets Manager)
   - Disable auto_send_emails in development to prevent accidental sends
   - Use different database credentials per environment

10. MONITORING RECOMMENDATIONS
    -------------------------
    Key metrics to monitor per environment:
    
    Development:
    - Processing errors (should be immediately visible)
    - Queue backpressure events
    
    Staging:
    - End-to-end processing time
    - API error rates
    - Email delivery success rate
    
    Production:
    - Throughput (jobs/second)
    - P95/P99 latency
    - Worker utilization
    - Queue depth over time
    - API rate limit headroom
    - Error rate by type

==============================================================================
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
import os
import json

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool


# Type alias for environment profile names
ProfileType = Literal["development", "staging", "production"]


# Environment-specific configuration profiles
# Requirements Coverage: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
PROFILE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "development": {
        # Concurrency: Lower for local debugging
        "worker_count": 2,
        "max_concurrent_api_calls": 3,
        "queue_size": 20,
        "chunk_size": 50,
        
        # Retry: Fewer retries for faster failure feedback
        "max_retries": 2,
        "base_delay": 0.5,
        "max_delay": 10.0,
        "exponential_base": 2.0,
        "retry_jitter": True,
        
        # Rate limiting: Conservative to avoid overwhelming local services
        "llm_rate_limit": 5.0,
        "email_rate_limit": 0.5,
        "scraper_rate_limit": 2.0,
        
        # Timeouts: Shorter for faster debugging
        "llm_timeout_seconds": 20.0,
        "email_timeout_seconds": 10.0,
        "scraper_timeout_seconds": 15.0,
        "db_timeout_seconds": 5.0,
        
        # Database: Smaller pool for local SQLite
        "db_pool_size": 3,
        "db_max_overflow": 5,
        
        # Logging: Verbose for debugging
        "log_level": "DEBUG",
        "structured_logging": True,
        "log_file": "logs/processor_dev.log",
        
        # Progress: Always show progress bar
        "enable_progress_bar": True,
        "progress_update_interval": 0.5,
        
        # Job processing: Lower thresholds for testing
        "min_match_score": 40,
        "max_contacts_per_job": 2,
        
        # Outreach: Disabled by default in dev
        "auto_send_emails": False,
        "email_delay_seconds": 5.0,
        
        # Shutdown: Quick shutdown for development
        "shutdown_timeout_seconds": 30.0,
    },
    
    "staging": {
        # Concurrency: Moderate for pre-production testing
        "worker_count": 5,
        "max_concurrent_api_calls": 10,
        "queue_size": 50,
        "chunk_size": 75,
        
        # Retry: Standard retry settings
        "max_retries": 3,
        "base_delay": 1.0,
        "max_delay": 30.0,
        "exponential_base": 2.0,
        "retry_jitter": True,
        
        # Rate limiting: Moderate to match staging API quotas
        "llm_rate_limit": 8.0,
        "email_rate_limit": 1.0,
        "scraper_rate_limit": 4.0,
        
        # Timeouts: Standard timeouts
        "llm_timeout_seconds": 25.0,
        "email_timeout_seconds": 12.0,
        "scraper_timeout_seconds": 18.0,
        "db_timeout_seconds": 8.0,
        
        # Database: Moderate pool for staging database
        "db_pool_size": 8,
        "db_max_overflow": 15,
        
        # Logging: Info level with structured logs
        "log_level": "INFO",
        "structured_logging": True,
        "log_file": "logs/processor_staging.log",
        
        # Progress: Show progress bar
        "enable_progress_bar": True,
        "progress_update_interval": 1.0,
        
        # Job processing: Production-like thresholds
        "min_match_score": 50,
        "max_contacts_per_job": 3,
        
        # Outreach: Enabled but conservative
        "auto_send_emails": True,
        "email_delay_seconds": 20.0,
        
        # Shutdown: Standard graceful shutdown
        "shutdown_timeout_seconds": 60.0,
    },
    
    "production": {
        # Concurrency: High for maximum throughput
        "worker_count": 10,
        "max_concurrent_api_calls": 20,
        "queue_size": 100,
        "chunk_size": 100,
        
        # Retry: Aggressive retry for reliability
        "max_retries": 5,
        "base_delay": 1.0,
        "max_delay": 60.0,
        "exponential_base": 2.0,
        "retry_jitter": True,
        
        # Rate limiting: Optimized for production API quotas
        "llm_rate_limit": 15.0,
        "email_rate_limit": 2.0,
        "scraper_rate_limit": 8.0,
        
        # Timeouts: Longer for reliability
        "llm_timeout_seconds": 30.0,
        "email_timeout_seconds": 15.0,
        "scraper_timeout_seconds": 20.0,
        "db_timeout_seconds": 10.0,
        
        # Database: Large pool for concurrent access
        "db_pool_size": 20,
        "db_max_overflow": 30,
        
        # Logging: Warning level to reduce noise
        "log_level": "WARNING",
        "structured_logging": True,
        "log_file": "logs/processor_production.log",
        
        # Progress: Disabled for production (reduce overhead)
        "enable_progress_bar": False,
        "progress_update_interval": 2.0,
        
        # Job processing: High quality threshold
        "min_match_score": 60,
        "max_contacts_per_job": 5,
        
        # Outreach: Fully enabled with rate limiting
        "auto_send_emails": True,
        "email_delay_seconds": 30.0,
        
        # Shutdown: Longer timeout for in-flight jobs
        "shutdown_timeout_seconds": 120.0,
    },
}


def get_current_profile() -> ProfileType:
    """
    Get the current configuration profile from environment variable.
    
    Reads the NEXUS_ENV environment variable and returns the profile name.
    Defaults to "development" if not set.
    
    For backward compatibility, also checks PIPELINE_PROFILE if NEXUS_ENV is not set.
    
    Returns:
        Current profile name ("development", "staging", or "production")
    
    Raises:
        ValueError: If NEXUS_ENV contains an invalid profile name
    
    Example:
        # In shell:
        # export NEXUS_ENV=production
        
        # In Python:
        profile = get_current_profile()  # Returns "production"
        config = ProcessorConfig.from_profile(profile)
    """
    # Primary environment variable is NEXUS_ENV
    profile = os.getenv("NEXUS_ENV")
    
    # Backward compatibility: fall back to PIPELINE_PROFILE if NEXUS_ENV not set
    if profile is None:
        profile = os.getenv("PIPELINE_PROFILE", "development")
    
    if profile not in PROFILE_DEFAULTS:
        valid_profiles = ", ".join(PROFILE_DEFAULTS.keys())
        raise ValueError(
            f"Invalid NEXUS_ENV environment variable: '{profile}'. "
            f"Valid values are: {valid_profiles}"
        )
    
    return profile  # type: ignore


def create_async_db_engine(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: float = 30.0,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> AsyncEngine:
    """
    Create async SQLAlchemy engine with connection pooling.
    
    This function configures an async database engine optimized for
    concurrent access with proper connection pooling to prevent
    resource exhaustion.
    
    Args:
        database_url: Database connection string (should start with postgresql+asyncpg://, 
                     sqlite+aiosqlite://, etc.)
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum number of connections that can be created beyond pool_size
        pool_timeout: Timeout in seconds to wait for a connection from the pool
        pool_pre_ping: Test connections before using them
        echo: Log all SQL statements (useful for debugging)
    
    Returns:
        Configured AsyncEngine instance
    
    Example:
        engine = create_async_db_engine(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            pool_size=10,
            max_overflow=20
        )
        
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Job))
    
    Notes:
        - For SQLite, use sqlite+aiosqlite:///path/to/db
        - For PostgreSQL, use postgresql+asyncpg://user:pass@host/db
        - Pool size should be tuned based on worker count and database capacity
        - pool_pre_ping=True adds overhead but prevents "lost connection" errors
    """
    # Convert standard database URLs to async versions if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("sqlite:///") and "aiosqlite" not in database_url:
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    
    # Create engine with connection pooling
    engine = create_async_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_pre_ping=pool_pre_ping,
        echo=echo,
        future=True,
    )
    
    return engine


def create_async_session_factory(
    engine: AsyncEngine,
    expire_on_commit: bool = False,
) -> sessionmaker:
    """
    Create async session factory for database operations.
    
    Args:
        engine: AsyncEngine instance
        expire_on_commit: Whether to expire objects after commit
    
    Returns:
        Async session factory
    
    Example:
        engine = create_async_db_engine(database_url)
        async_session = create_async_session_factory(engine)
        
        async with async_session() as session:
            result = await session.execute(select(Job))
            jobs = result.scalars().all()
    """
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=expire_on_commit,
        autocommit=False,
        autoflush=False,
    )


@dataclass
class ProcessorConfig:
    """
    Configuration for the async job processor.
    
    All parameters have sensible defaults but can be overridden
    via constructor arguments, environment variables, or config files.
    
    Requirements Coverage: 15.1, 15.2, 15.3, 15.4, 15.5
    """
    # Concurrency settings
    worker_count: int = 5
    """Number of concurrent workers processing jobs"""
    
    max_concurrent_api_calls: int = 10
    """Maximum number of concurrent external API calls"""
    
    queue_size: int = 100
    """Size of the bounded job queue (provides backpressure)"""
    
    chunk_size: int = 100
    """Number of jobs to fetch per database query (streaming chunk size)"""
    
    # Retry settings
    max_retries: int = 3
    """Maximum number of retry attempts for failed operations"""
    
    base_delay: float = 1.0
    """Base delay in seconds for exponential backoff"""
    
    max_delay: float = 60.0
    """Maximum delay in seconds between retries"""
    
    exponential_base: float = 2.0
    """Base for exponential backoff calculation (must be > 1.0)"""
    
    retry_jitter: bool = True
    """Whether to add random jitter to retry delays"""
    
    # Rate limiting (requests per second)
    llm_rate_limit: float = 10.0
    """Rate limit for LLM API calls (requests per second)"""
    
    email_rate_limit: float = 1.0
    """Rate limit for email API calls (requests per second)"""
    
    scraper_rate_limit: float = 5.0
    """Rate limit for scraping operations (requests per second)"""
    
    # Timeouts (seconds)
    llm_timeout_seconds: float = 30.0
    """Timeout for LLM API calls in seconds"""
    
    email_timeout_seconds: float = 15.0
    """Timeout for email API calls in seconds"""
    
    scraper_timeout_seconds: float = 20.0
    """Timeout for scraping operations in seconds"""
    
    db_timeout_seconds: float = 10.0
    """Timeout for database operations in seconds"""
    
    # Database settings
    db_pool_size: int = 10
    """Database connection pool size"""
    
    db_max_overflow: int = 20
    """Maximum overflow connections in database pool"""
    
    # Logging settings
    log_level: str = "INFO"
    """Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
    
    structured_logging: bool = True
    """Whether to use structured logging"""
    
    log_file: str = "logs/processor.log"
    """Path to log file"""
    
    # Progress tracking
    enable_progress_bar: bool = True
    """Whether to show progress bar during processing"""
    
    progress_update_interval: float = 1.0
    """Interval in seconds between progress updates"""
    
    # Job processing settings
    min_match_score: int = 50
    """Minimum AI match score to send email"""
    
    max_contacts_per_job: int = 3
    """Maximum contacts to find per job"""
    
    # Resume settings
    resume_pdf_path: str = "data/resume.pdf"
    """Path to resume PDF file"""
    
    # Outreach settings
    auto_send_emails: bool = True
    """Whether to automatically send outreach emails"""
    
    email_delay_seconds: float = 30.0
    """Delay between email sends for rate limiting"""
    
    # Shutdown settings
    shutdown_timeout_seconds: float = 60.0
    """Timeout in seconds to wait for in-flight jobs during graceful shutdown"""

    
    def validate(self) -> None:
        """
        Validate configuration values.
        
        Raises:
            ValueError: If any configuration value is invalid with clear error message
        
        Requirements Coverage: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 26.1, 26.2, 26.3, 26.4, 26.5, 26.6, 12.1
        """
        # Validate worker_count: positive and within reasonable bounds (1-50) (Requirements 8.1, 26.1)
        if self.worker_count <= 0:
            raise ValueError(
                f"worker_count must be positive, got {self.worker_count}. "
                f"Worker count determines concurrent job processing capacity. "
                f"Valid range: 1-50 workers."
            )
        if self.worker_count > 50:
            raise ValueError(
                f"worker_count exceeds maximum allowed value of 50, got {self.worker_count}. "
                f"Too many workers can overwhelm external APIs and database connections. "
                f"Consider scaling horizontally instead of increasing worker count."
            )
        
        # Validate queue_size: positive and sufficient (≥10) (Requirements 8.2, 26.2)
        if self.queue_size <= 0:
            raise ValueError(
                f"queue_size must be positive, got {self.queue_size}. "
                f"Queue provides backpressure between producer and workers. "
                f"Minimum recommended: 10."
            )
        if self.queue_size < 10:
            raise ValueError(
                f"queue_size is too small, got {self.queue_size}. "
                f"Minimum queue size is 10 to ensure adequate buffering and backpressure. "
                f"Small queues can cause producer blocking and reduced throughput."
            )
        
        # Validate max_concurrent_api_calls: positive
        if self.max_concurrent_api_calls <= 0:
            raise ValueError(
                f"max_concurrent_api_calls must be positive, got {self.max_concurrent_api_calls}. "
                f"This limits concurrent external API calls via semaphore."
            )
        
        # Validate chunk_size: positive (Requirements 8.6, 12.1)
        if self.chunk_size <= 0:
            raise ValueError(
                f"chunk_size must be positive, got {self.chunk_size}. "
                f"Chunk size controls database streaming batch size. "
                f"Affects memory usage: O(chunk_size)."
            )
        
        # Validate retry parameters (Requirements 8.4, 26.5)
        if self.max_retries < 0:
            raise ValueError(
                f"max_retries must be non-negative, got {self.max_retries}. "
                f"Set to 0 to disable retries, or positive value for retry attempts."
            )
        
        if self.base_delay <= 0:
            raise ValueError(
                f"base_delay must be positive, got {self.base_delay}. "
                f"Base delay is the initial retry delay in seconds for exponential backoff."
            )
        
        if self.max_delay <= 0:
            raise ValueError(
                f"max_delay must be positive, got {self.max_delay}. "
                f"Max delay caps the exponential backoff retry delay in seconds."
            )
        
        if self.max_delay < self.base_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}s) must be >= base_delay ({self.base_delay}s). "
                f"Max delay caps exponential backoff and cannot be less than initial delay."
            )
        
        if self.exponential_base <= 1.0:
            raise ValueError(
                f"exponential_base must be > 1.0 for exponential backoff, got {self.exponential_base}. "
                f"Common values: 2.0 (double each retry) or 1.5 (moderate growth). "
                f"Value of 1.0 would result in constant delays."
            )
        
        # Validate rate_limits: positive for all API types (Requirements 8.3, 26.3)
        if self.llm_rate_limit <= 0:
            raise ValueError(
                f"llm_rate_limit must be positive, got {self.llm_rate_limit}. "
                f"Rate limit controls LLM API requests per second. "
                f"Prevents quota exhaustion and API throttling."
            )
        
        if self.email_rate_limit <= 0:
            raise ValueError(
                f"email_rate_limit must be positive, got {self.email_rate_limit}. "
                f"Rate limit controls email API requests per second. "
                f"Prevents spam detection and maintains sender reputation."
            )
        
        if self.scraper_rate_limit <= 0:
            raise ValueError(
                f"scraper_rate_limit must be positive, got {self.scraper_rate_limit}. "
                f"Rate limit controls web scraping requests per second. "
                f"Prevents IP blocking and respects robots.txt policies."
            )
        
        # Validate timeout values: positive for all operation types (Requirements 8.5, 26.4)
        if self.llm_timeout_seconds <= 0:
            raise ValueError(
                f"llm_timeout_seconds must be positive, got {self.llm_timeout_seconds}. "
                f"Timeout prevents indefinite blocking on LLM API calls. "
                f"Typical LLM response time: 2-5 seconds."
            )
        
        if self.email_timeout_seconds <= 0:
            raise ValueError(
                f"email_timeout_seconds must be positive, got {self.email_timeout_seconds}. "
                f"Timeout prevents indefinite blocking on email operations. "
                f"Typical email send time: 1-3 seconds."
            )
        
        if self.scraper_timeout_seconds <= 0:
            raise ValueError(
                f"scraper_timeout_seconds must be positive, got {self.scraper_timeout_seconds}. "
                f"Timeout prevents indefinite blocking on web scraping. "
                f"Typical page load time: 2-10 seconds."
            )
        
        if self.db_timeout_seconds <= 0:
            raise ValueError(
                f"db_timeout_seconds must be positive, got {self.db_timeout_seconds}. "
                f"Timeout prevents indefinite blocking on database operations. "
                f"Typical query time: <1 second."
            )
        
        # Validate database parameters (Requirements 8.6, 8.7, 26.6)
        if self.db_pool_size <= 0:
            raise ValueError(
                f"db_pool_size must be positive, got {self.db_pool_size}. "
                f"Pool size controls concurrent database connections. "
                f"Should be >= worker_count for optimal performance."
            )
        
        if self.db_max_overflow < 0:
            raise ValueError(
                f"db_max_overflow must be non-negative, got {self.db_max_overflow}. "
                f"Max overflow allows temporary connections beyond pool_size. "
                f"Total max connections = pool_size + max_overflow."
            )
        
        # Validate shutdown settings (Requirement 24.5)
        if self.shutdown_timeout_seconds <= 0:
            raise ValueError(
                f"shutdown_timeout_seconds must be positive, got {self.shutdown_timeout_seconds}. "
                f"Timeout for graceful shutdown waiting for in-flight jobs to complete."
            )
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(
                f"log_level must be one of {valid_log_levels}, got '{self.log_level}'. "
                f"Log level controls verbosity of structured logging output."
            )
    
    @classmethod
    def from_env(cls, prefix: str = "PIPELINE_") -> "ProcessorConfig":
        """
        Create configuration from environment variables.
        
        Environment variables should be prefixed (default: PIPELINE_) and uppercase.
        Example: PIPELINE_WORKER_COUNT -> worker_count
        
        Args:
            prefix: Environment variable prefix (default: "PIPELINE_")
        
        Returns:
            ProcessorConfig instance with values from environment
        
        Requirements Coverage: 15.5
        """
        def get_env_int(name: str, default: int) -> int:
            value = os.getenv(f"{prefix}{name}")
            return int(value) if value else default
        
        def get_env_float(name: str, default: float) -> float:
            value = os.getenv(f"{prefix}{name}")
            return float(value) if value else default
        
        def get_env_bool(name: str, default: bool) -> bool:
            value = os.getenv(f"{prefix}{name}")
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes")
        
        def get_env_str(name: str, default: str) -> str:
            return os.getenv(f"{prefix}{name}", default)
        
        return cls(
            worker_count=get_env_int("WORKER_COUNT", 5),
            max_concurrent_api_calls=get_env_int("MAX_CONCURRENT_API_CALLS", 10),
            queue_size=get_env_int("QUEUE_SIZE", 100),
            chunk_size=get_env_int("CHUNK_SIZE", 100),
            max_retries=get_env_int("MAX_RETRIES", 3),
            base_delay=get_env_float("BASE_DELAY", 1.0),
            max_delay=get_env_float("MAX_DELAY", 60.0),
            exponential_base=get_env_float("EXPONENTIAL_BASE", 2.0),
            retry_jitter=get_env_bool("RETRY_JITTER", True),
            llm_rate_limit=get_env_float("LLM_RATE_LIMIT", 10.0),
            email_rate_limit=get_env_float("EMAIL_RATE_LIMIT", 1.0),
            scraper_rate_limit=get_env_float("SCRAPER_RATE_LIMIT", 5.0),
            llm_timeout_seconds=get_env_float("LLM_TIMEOUT_SECONDS", 30.0),
            email_timeout_seconds=get_env_float("EMAIL_TIMEOUT_SECONDS", 15.0),
            scraper_timeout_seconds=get_env_float("SCRAPER_TIMEOUT_SECONDS", 20.0),
            db_timeout_seconds=get_env_float("DB_TIMEOUT_SECONDS", 10.0),
            db_pool_size=get_env_int("DB_POOL_SIZE", 10),
            db_max_overflow=get_env_int("DB_MAX_OVERFLOW", 20),
            log_level=get_env_str("LOG_LEVEL", "INFO"),
            structured_logging=get_env_bool("STRUCTURED_LOGGING", True),
            log_file=get_env_str("LOG_FILE", "logs/processor.log"),
            enable_progress_bar=get_env_bool("ENABLE_PROGRESS_BAR", True),
            progress_update_interval=get_env_float("PROGRESS_UPDATE_INTERVAL", 1.0),
            min_match_score=get_env_int("MIN_MATCH_SCORE", 50),
            max_contacts_per_job=get_env_int("MAX_CONTACTS_PER_JOB", 3),
            auto_send_emails=get_env_bool("AUTO_SEND_EMAILS", True),
            email_delay_seconds=get_env_float("EMAIL_DELAY_SECONDS", 30.0),
            shutdown_timeout_seconds=get_env_float("SHUTDOWN_TIMEOUT_SECONDS", 60.0),
        )
    
    @classmethod
    def from_profile(cls, profile: ProfileType = "development", **overrides: Any) -> "ProcessorConfig":
        """
        Create configuration from an environment-specific profile.
        
        Profiles provide sensible defaults for different deployment environments:
        - development: Local development with verbose logging, reduced throughput (2 workers)
        - staging: Pre-production testing with moderate throughput (5 workers)
        - production: High-performance production with optimized settings (10 workers)
        
        The profile can be selected via the NEXUS_ENV environment variable.
        Individual settings can be overridden via constructor arguments or environment variables.
        
        Args:
            profile: Environment profile name ("development", "staging", or "production")
            **overrides: Override specific configuration values
        
        Returns:
            ProcessorConfig instance with profile defaults and overrides applied
        
        Raises:
            ValueError: If profile name is invalid or configuration validation fails
        
        Requirements Coverage: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
        
        Examples:
            # Development profile with defaults
            config = ProcessorConfig.from_profile("development")
            
            # Production profile with custom worker count
            config = ProcessorConfig.from_profile("production", worker_count=20)
            
            # Profile from environment variable
            os.environ["NEXUS_ENV"] = "staging"
            config = ProcessorConfig.from_profile(get_current_profile())
        """
        if profile not in PROFILE_DEFAULTS:
            valid_profiles = ", ".join(PROFILE_DEFAULTS.keys())
            raise ValueError(
                f"Invalid profile '{profile}'. "
                f"Valid profiles are: {valid_profiles}. "
                f"Use PIPELINE_PROFILE environment variable or from_profile() method."
            )
        
        # Start with profile defaults
        config_dict = PROFILE_DEFAULTS[profile].copy()
        
        # Apply overrides from constructor arguments
        config_dict.update(overrides)
        
        # Create config instance
        config = cls(**config_dict)
        
        # Validate configuration
        config.validate()
        
        return config
    
    @classmethod
    def from_yaml(cls, filepath: str) -> "ProcessorConfig":
        """
        Load configuration from YAML file.
        
        Args:
            filepath: Path to YAML configuration file
        
        Returns:
            ProcessorConfig instance
        
        Raises:
            ImportError: If PyYAML is not installed
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid or contains invalid values
        
        Requirements Coverage: 15.5
        
        Example YAML:
            worker_count: 10
            max_concurrent_api_calls: 20
            queue_size: 200
            max_retries: 5
            llm_rate_limit: 15.0
        """
        if not YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is not installed. Install it with: pip install pyyaml"
            )
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                config_dict = yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"Invalid YAML in config file {filepath}: {e}")
        
        return cls(**config_dict)
    
    @classmethod
    def from_json(cls, filepath: str) -> "ProcessorConfig":
        """
        Load configuration from JSON file.
        
        Args:
            filepath: Path to JSON configuration file
        
        Returns:
            ProcessorConfig instance
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If JSON is invalid or contains invalid values
        
        Requirements Coverage: 15.5
        
        Example JSON:
            {
                "worker_count": 10,
                "max_concurrent_api_calls": 20,
                "queue_size": 200,
                "max_retries": 5,
                "llm_rate_limit": 15.0
            }
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                config_dict = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file {filepath}: {e}")
        
        return cls(**config_dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "ProcessorConfig":
        """
        Create configuration from dictionary.
        
        Args:
            config_dict: Dictionary with configuration values
        
        Returns:
            ProcessorConfig instance
        
        Raises:
            ValueError: If dictionary contains invalid values
        """
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "worker_count": self.worker_count,
            "max_concurrent_api_calls": self.max_concurrent_api_calls,
            "queue_size": self.queue_size,
            "chunk_size": self.chunk_size,
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "exponential_base": self.exponential_base,
            "retry_jitter": self.retry_jitter,
            "llm_rate_limit": self.llm_rate_limit,
            "email_rate_limit": self.email_rate_limit,
            "scraper_rate_limit": self.scraper_rate_limit,
            "llm_timeout_seconds": self.llm_timeout_seconds,
            "email_timeout_seconds": self.email_timeout_seconds,
            "scraper_timeout_seconds": self.scraper_timeout_seconds,
            "db_timeout_seconds": self.db_timeout_seconds,
            "db_pool_size": self.db_pool_size,
            "db_max_overflow": self.db_max_overflow,
            "log_level": self.log_level,
            "structured_logging": self.structured_logging,
            "log_file": self.log_file,
            "enable_progress_bar": self.enable_progress_bar,
            "progress_update_interval": self.progress_update_interval,
            "min_match_score": self.min_match_score,
            "max_contacts_per_job": self.max_contacts_per_job,
            "auto_send_emails": self.auto_send_emails,
            "email_delay_seconds": self.email_delay_seconds,
            "shutdown_timeout_seconds": self.shutdown_timeout_seconds,
        }
    
    # Backward compatibility aliases for existing code
    @property
    def retry_base_delay(self) -> float:
        """Backward compatibility alias for base_delay."""
        return self.base_delay
    
    @property
    def retry_max_delay(self) -> float:
        """Backward compatibility alias for max_delay."""
        return self.max_delay
    
    @property
    def retry_exponential_base(self) -> float:
        """Backward compatibility alias for exponential_base."""
        return self.exponential_base
    
    @property
    def db_chunk_size(self) -> int:
        """Backward compatibility alias for chunk_size."""
        return self.chunk_size


@dataclass
class RetryConfig:
    """
    Configuration specifically for retry behavior.
    
    Requirements Coverage: 15.2
    """
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_exceptions: tuple = (Exception,)
    
    def validate(self) -> None:
        """
        Validate retry configuration.
        
        Raises:
            ValueError: If any configuration value is invalid
        """
        if self.max_attempts < 0:
            raise ValueError(f"max_attempts must be non-negative, got {self.max_attempts}")
        
        if self.base_delay <= 0:
            raise ValueError(f"base_delay must be positive, got {self.base_delay}")
        
        if self.max_delay <= 0:
            raise ValueError(f"max_delay must be positive, got {self.max_delay}")
        
        if self.max_delay < self.base_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}) must be >= base_delay ({self.base_delay})"
            )
        
        if self.exponential_base <= 1.0:
            raise ValueError(f"exponential_base must be > 1.0, got {self.exponential_base}")


@dataclass
class RateLimitConfig:
    """
    Configuration for rate limiting.
    
    Requirements Coverage: 15.3
    """
    rate: float  # tokens per time_period
    capacity: int = 1
    time_period: float = 1.0
    
    def validate(self) -> None:
        """
        Validate rate limit configuration.
        
        Raises:
            ValueError: If any configuration value is invalid
        """
        if self.rate <= 0:
            raise ValueError(f"rate must be positive, got {self.rate}")
        
        if self.capacity <= 0:
            raise ValueError(f"capacity must be positive, got {self.capacity}")
        
        if self.time_period <= 0:
            raise ValueError(f"time_period must be positive, got {self.time_period}")

