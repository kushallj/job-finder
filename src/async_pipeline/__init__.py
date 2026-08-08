"""
Async Job Pipeline - High-performance async job processing system.

This package provides a complete async pipeline for processing jobs with:
- O(1) memory usage via streaming generators
- Backpressure via bounded queue
- Concurrent processing via worker pool
- Retry logic with exponential backoff
- Rate limiting for external APIs
- Graceful shutdown support

Example usage:
    from src.async_pipeline import AsyncJobPipeline, ProcessorConfig
    
    pipeline = AsyncJobPipeline(config)
    results = await pipeline.run(query="software engineer")
"""

import logging
import os
import sys
import uuid
from typing import Any, Dict, Optional

import structlog
from contextvars import ContextVar

# Context variable for correlation ID tracking across async tasks
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def configure_structured_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    include_timestamp: bool = True,
) -> None:
    """
    Configure structured logging using structlog.
    
    This sets up structured logging with JSON formatting for production
    or colored console output for development. All log entries include
    contextual information like job_id, worker_id, correlation_id, and processing metrics.
    
    Log Levels:
    - INFO: Job lifecycle events (started, completed)
    - WARNING: Retry events and recoverable errors
    - ERROR: Job failures and unrecoverable errors
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (True) or colored console (False)
        include_timestamp: Include timestamps in log entries
    
    Example:
        # For development (human-readable)
        configure_structured_logging(
            log_level="INFO",
            json_format=False,
            include_timestamp=True
        )
        
        # For production (JSON)
        configure_structured_logging(
            log_level="INFO",
            json_format=True,
            include_timestamp=True
        )
    """
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))
    
    # Add appropriate renderer based on format
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured structlog logger
    
    Example:
        logger = get_logger(__name__)
        logger.info("processing_job", job_id="123", worker_id="worker-1", correlation_id="abc-123")
    """
    return structlog.get_logger(name)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID for the current async context.
    
    This allows tracing a job through the entire pipeline by adding
    the same correlation_id to all log entries for that job.
    
    Args:
        correlation_id: Unique identifier for job tracing
    
    Example:
        set_correlation_id(f"job-{job_id}")
        # All subsequent log entries will include this correlation_id
    """
    correlation_id_var.set(correlation_id)
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def get_correlation_id() -> Optional[str]:
    """
    Get the correlation ID for the current async context.
    
    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_var.get()


def generate_correlation_id() -> str:
    """
    Generate a new unique correlation ID.
    
    Returns:
        UUID-based correlation ID string
    """
    return str(uuid.uuid4())


def clear_correlation_id() -> None:
    """
    Clear the correlation ID from the current async context.
    
    Useful for cleaning up context after job processing completes.
    """
    correlation_id_var.set(None)
    structlog.contextvars.clear_contextvars()


# Detect environment and configure logging accordingly
# Default to JSON in production, human-readable in development
is_production = os.environ.get("ENVIRONMENT", "development").lower() == "production"
log_level = os.environ.get("LOG_LEVEL", "INFO")

# Configure logging on module import with environment-appropriate defaults
configure_structured_logging(
    log_level=log_level,
    json_format=is_production,
    include_timestamp=True,
)

# Core types and models
from src.async_pipeline.types import (
    JobStatus,
    JobContext,
    ProcessingResult,
    QueueStats,
    WorkerPoolStats,
    RetryStats,
    RateLimiterStats,
    PipelineStats,
)

# Configuration
from src.async_pipeline.config import (
    ProcessorConfig,
    RetryConfig,
    RateLimitConfig,
    create_async_db_engine,
    create_async_session_factory,
)

# Core components
from src.async_pipeline.bounded_queue import (
    BoundedQueue,
    AsyncJobQueue,
)

from src.async_pipeline.retry import (
    RetryManager,
    get_retry_manager,
    retry_with_backoff,
    retry_on_api_error,
    retry_on_db_error,
)

from src.async_pipeline.rate_limiter import (
    TokenBucket,
    AdaptiveRateLimiter,
    MultiRateLimiter,
)

from src.async_pipeline.producer import (
    AsyncJobProducer,
    JobProducer,
)

from src.async_pipeline.worker_pool import (
    AsyncWorkerPool,
    WorkerPoolBuilder,
)

from src.async_pipeline.pipeline import (
    AsyncJobPipeline,
    AsyncJobPipelineBuilder,
    create_pipeline_and_run,
)

# Backward compatibility wrappers
from src.async_pipeline.sync_wrapper import (
    SyncJobPipelineWrapper,
    JobProcessorCompatWrapper,
    run_pipeline_sync,
)

# Package version
__version__ = "1.0.0"

# Public API
__all__ = [
    # Types
    "JobStatus",
    "JobContext",
    "ProcessingResult",
    "QueueStats",
    "WorkerPoolStats",
    "RetryStats",
    "RateLimiterStats",
    "PipelineStats",
    
    # Config
    "ProcessorConfig",
    "RetryConfig",
    "RateLimitConfig",
    "create_async_db_engine",
    "create_async_session_factory",
    
    # Components
    "BoundedQueue",
    "AsyncJobQueue",
    "RetryManager",
    "get_retry_manager",
    "retry_with_backoff",
    "retry_on_api_error",
    "retry_on_db_error",
    "TokenBucket",
    "AdaptiveRateLimiter",
    "MultiRateLimiter",
    "AsyncJobProducer",
    "JobProducer",
    "AsyncWorkerPool",
    "WorkerPoolBuilder",
    "AsyncJobPipeline",
    "AsyncJobPipelineBuilder",
    "create_pipeline_and_run",
    
    # Backward compatibility
    "SyncJobPipelineWrapper",
    "JobProcessorCompatWrapper",
    "run_pipeline_sync",
    
    # Logging
    "configure_structured_logging",
    "get_logger",
    "set_correlation_id",
    "get_correlation_id",
    "generate_correlation_id",
    "clear_correlation_id",
]

