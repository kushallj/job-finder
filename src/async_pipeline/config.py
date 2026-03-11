"""
Configuration for the async job pipeline.

This module provides the ProcessorConfig dataclass with all tunable
parameters for the pipeline, following the design specification.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessorConfig:
    """
    Configuration for the async job processor.
    
    All parameters have sensible defaults but can be overridden
    via constructor arguments or environment variables.
    """
    # Concurrency settings
    worker_count: int = 5
    """Number of concurrent workers processing jobs"""
    
    max_concurrent_api_calls: int = 10
    """Maximum number of concurrent external API calls"""
    
    queue_size: int = 100
    """Size of the bounded job queue (provides backpressure)"""
    
    # Retry settings
    max_retries: int = 3
    """Maximum number of retry attempts for failed operations"""
    
    retry_base_delay: float = 1.0
    """Base delay in seconds for exponential backoff"""
    
    retry_max_delay: float = 60.0
    """Maximum delay in seconds between retries"""
    
    retry_exponential_base: float = 2.0
    """Base for exponential backoff calculation"""
    
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
    llm_timeout: float = 30.0
    """Timeout for LLM API calls"""
    
    email_timeout: float = 15.0
    """Timeout for email API calls"""
    
    scraper_timeout: float = 20.0
    """Timeout for scraping operations"""
    
    database_timeout: float = 10.0
    """Timeout for database operations"""
    
    # Database settings
    db_chunk_size: int = 100
    """Number of jobs to fetch per database query"""
    
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
    
    # Outreach settings
    auto_send_emails: bool = True
    """Whether to automatically send outreach emails"""
    
    email_delay_seconds: float = 30.0
    """Delay between email sends for rate limiting"""
    
    def validate(self) -> None:
        """
        Validate configuration values.
        
        Raises:
            AssertionError: If any configuration value is invalid
        """
        assert self.worker_count > 0, "worker_count must be positive"
        assert self.max_concurrent_api_calls > 0, "max_concurrent_api_calls must be positive"
        assert self.queue_size > 0, "queue_size must be positive"
        assert self.max_retries >= 0, "max_retries must be non-negative"
        assert self.retry_base_delay > 0, "retry_base_delay must be positive"
        assert self.retry_max_delay >= self.retry_base_delay, "retry_max_delay must be >= retry_base_delay"
        assert self.retry_exponential_base > 1.0, "retry_exponential_base must be > 1.0"
        assert self.llm_rate_limit > 0, "llm_rate_limit must be positive"
        assert self.db_chunk_size > 0, "db_chunk_size must be positive"
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert self.log_level in valid_log_levels, f"log_level must be one of {valid_log_levels}"
    
    @classmethod
    def from_env(cls) -> "ProcessorConfig":
        """
        Create configuration from environment variables.
        
        Environment variables should be prefixed with PIPELINE_ and uppercase.
        Example: PIPELINE_WORKER_COUNT -> worker_count
        """
        import os
        
        def get_env_int(name: str, default: int) -> int:
            value = os.getenv(f"PIPELINE_{name}")
            return int(value) if value else default
        
        def get_env_float(name: str, default: float) -> float:
            value = os.getenv(f"PIPELINE_{name}")
            return float(value) if value else default
        
        def get_env_bool(name: str, default: bool) -> bool:
            value = os.getenv(f"PIPELINE_{name}")
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes")
        
        return cls(
            worker_count=get_env_int("WORKER_COUNT", cls.worker_count),
            max_concurrent_api_calls=get_env_int("MAX_CONCURRENT_API_CALLS", cls.max_concurrent_api_calls),
            queue_size=get_env_int("QUEUE_SIZE", cls.queue_size),
            max_retries=get_env_int("MAX_RETRIES", cls.max_retries),
            retry_base_delay=get_env_float("RETRY_BASE_DELAY", cls.retry_base_delay),
            retry_max_delay=get_env_float("RETRY_MAX_DELAY", cls.retry_max_delay),
            retry_exponential_base=get_env_float("RETRY_EXPONENTIAL_BASE", cls.retry_exponential_base),
            retry_jitter=get_env_bool("RETRY_JITTER", cls.retry_jitter),
            llm_rate_limit=get_env_float("LLM_RATE_LIMIT", cls.llm_rate_limit),
            email_rate_limit=get_env_float("EMAIL_RATE_LIMIT", cls.email_rate_limit),
            scraper_rate_limit=get_env_float("SCRAPER_RATE_LIMIT", cls.scraper_rate_limit),
            llm_timeout=get_env_float("LLM_TIMEOUT", cls.llm_timeout),
            email_timeout=get_env_float("EMAIL_TIMEOUT", cls.email_timeout),
            scraper_timeout=get_env_float("SCRAPER_TIMEOUT", cls.scraper_timeout),
            database_timeout=get_env_float("DATABASE_TIMEOUT", cls.database_timeout),
            db_chunk_size=get_env_int("DB_CHUNK_SIZE", cls.db_chunk_size),
            db_pool_size=get_env_int("DB_POOL_SIZE", cls.db_pool_size),
            db_max_overflow=get_env_int("DB_MAX_OVERFLOW", cls.db_max_overflow),
            structured_logging=get_env_bool("STRUCTURED_LOGGING", cls.structured_logging),
            enable_progress_bar=get_env_bool("ENABLE_PROGRESS_BAR", cls.enable_progress_bar),
            min_match_score=get_env_int("MIN_MATCH_SCORE", cls.min_match_score),
            max_contacts_per_job=get_env_int("MAX_CONTACTS_PER_JOB", cls.max_contacts_per_job),
            auto_send_emails=get_env_bool("AUTO_SEND_EMAILS", cls.auto_send_emails),
            email_delay_seconds=get_env_float("EMAIL_DELAY_SECONDS", cls.email_delay_seconds),
        )


@dataclass
class RetryConfig:
    """Configuration specifically for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_exceptions: tuple = (Exception,)
    
    def validate(self) -> None:
        """Validate retry configuration."""
        assert self.max_attempts >= 0, "max_attempts must be non-negative"
        assert self.base_delay > 0, "base_delay must be positive"
        assert self.max_delay >= self.base_delay, "max_delay must be >= base_delay"
        assert self.exponential_base > 1.0, "exponential_base must be > 1.0"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    rate: float  # tokens per time_period
    capacity: int = 1
    time_period: float = 1.0
    
    def validate(self) -> None:
        """Validate rate limit configuration."""
        assert self.rate > 0, "rate must be positive"
        assert self.capacity > 0, "capacity must be positive"
        assert self.time_period > 0, "time_period must be positive"

