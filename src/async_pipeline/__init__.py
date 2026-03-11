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
]

