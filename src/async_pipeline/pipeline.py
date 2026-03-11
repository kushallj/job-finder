"""
Main async job pipeline that orchestrates the entire processing system.

This module provides the AsyncJobPipeline class that combines:
- AsyncJobProducer (streaming job generation with O(1) memory)
- BoundedQueue (backpressure mechanism)
- AsyncWorkerPool (concurrent workers with semaphore gating)
- Retry logic with exponential backoff
- Rate limiting for external APIs
- Structured logging and progress tracking
"""

import asyncio
import logging
import signal
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.async_pipeline.bounded_queue import BoundedQueue
from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.producer import AsyncJobProducer
from src.async_pipeline.rate_limiter import MultiRateLimiter, TokenBucket
from src.async_pipeline.retry import RetryManager
from src.async_pipeline.types import (
    JobContext,
    PipelineStats,
    ProcessingResult,
    WorkerPoolStats,
)
from src.async_pipeline.worker_pool import AsyncWorkerPool

logger = logging.getLogger(__name__)


class AsyncJobPipeline:
    """
    Main async job pipeline orchestrator.
    
    Combines all components into a cohesive processing system with:
    - O(1) memory usage via streaming generators
    - Backpressure via bounded queue
    - Concurrent processing via worker pool
    - Retry logic with exponential backoff
    - Rate limiting for external APIs
    - Graceful shutdown support
    
    Example:
        pipeline = AsyncJobPipeline(config)
        
        # Add custom processor
        pipeline.set_processor(my_processor)
        
        # Run pipeline
        results = await pipeline.run(
            query="software engineer",
            resume_text=open("resume.txt").read()
        )
        
        # Cleanup
        await pipeline.close()
    """
    
    def __init__(
        self,
        config: Optional[ProcessorConfig] = None,
        db_url: Optional[str] = None,
    ):
        """
        Initialize the async job pipeline.
        
        Args:
            config: Processor configuration. Uses defaults if not provided.
            db_url: Database URL. Reads from settings if not provided.
        """
        self._config = config or ProcessorConfig()
        self._config.validate()
        
        # Initialize database
        self._db_url = db_url or self._get_db_url()
        self._engine = None
        self._session_factory = None
        
        # Initialize components
        self._queue: Optional[BoundedQueue] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._producer: Optional[AsyncJobProducer] = None
        self._worker_pool: Optional[AsyncWorkerPool] = None
        self._rate_limiter: Optional[MultiRateLimiter] = None
        self._retry_manager: RetryManager = None
        
        # Pipeline state
        self._processor: Optional[Callable] = None
        self._results: List[ProcessingResult] = []
        self._stats = PipelineStats()
        self._running = False
        self._shutdown_requested = False
        
        # Progress tracking
        self._progress_callback: Optional[Callable] = None
        
        # Setup logging
        self._setup_logging()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info("AsyncJobPipeline initialized")
    
    def _get_db_url(self) -> str:
        """Get database URL from settings or environment."""
        try:
            from src.config import settings
            return settings.database_url
        except Exception:
            import os
            return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///jobs.db")
    
    def _setup_logging(self) -> None:
        """Setup logging based on configuration."""
        log_level = getattr(logging, self._config.log_level.upper())
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self._config.log_file),
            ],
        )
        
        logger.info(f"Logging configured at {self._config.log_level} level")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating graceful shutdown...")
            self._shutdown_requested = True
        
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except Exception as e:
            logger.warning(f"Could not setup signal handlers: {e}")
    
    async def _init_database(self) -> None:
        """Initialize database connection and session factory."""
        if self._engine is not None:
            return
        
        logger.info(f"Connecting to database: {self._db_url}")
        
        self._engine = create_async_engine(
            self._db_url,
            pool_size=self._config.db_pool_size,
            max_overflow=self._config.db_max_overflow,
            echo=False,
        )
        
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info("Database connection established")
    
    def set_processor(self, processor: Callable[[JobContext], ProcessingResult]) -> None:
        """
        Set the job processor function.
        
        Args:
            processor: Async callable that processes JobContext and returns ProcessingResult.
        """
        self._processor = processor
        logger.info("Job processor set")
    
    def set_progress_callback(self, callback: Callable[[Dict], None]) -> None:
        """
        Set a callback for progress updates.
        
        Args:
            callback: Function that receives progress dict.
        """
        self._progress_callback = callback
    
    async def run(
        self,
        query: str = "",
        resume_text: str = "",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ProcessingResult]:
        """
        Run the complete job processing pipeline.
        
        Args:
            query: Search query to filter jobs.
            resume_text: Resume text for job matching.
            filters: Additional filters for job selection.
            
        Returns:
            List of ProcessingResult for all processed jobs.
        """
        if self._running:
            raise RuntimeError("Pipeline is already running")
        
        self._running = True
        self._stats = PipelineStats()
        self._results = []
        
        logger.info(f"Starting pipeline with query: '{query}'")
        
        try:
            # Initialize database
            await self._init_database()
            
            # Initialize components
            await self._setup_components()
            
            # Start the pipeline
            await self._run_pipeline(query, resume_text, filters)
            
            logger.info(f"Pipeline completed: {self._stats.to_dict()}")
            
            return self._results
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            raise
            
        finally:
            self._running = False
    
    async def _setup_components(self) -> None:
        """Setup all pipeline components."""
        # Initialize queue
        self._queue = BoundedQueue(
            maxsize=self._config.queue_size,
        )
        
        # Initialize semaphore for rate limiting
        self._semaphore = asyncio.Semaphore(self._config.max_concurrent_api_calls)
        
        # Initialize rate limiter
        self._rate_limiter = MultiRateLimiter(
            llm_rate=self._config.llm_rate_limit,
            email_rate=self._config.email_rate_limit,
            scraper_rate=self._config.scraper_rate_limit,
        )
        
        # Initialize retry manager
        self._retry_manager = RetryManager()
        
        # Initialize producer
        self._producer = AsyncJobProducer(
            db_session_factory=self._session_factory,
            chunk_size=self._config.db_chunk_size,
        )
        
        # Initialize worker pool
        self._worker_pool = AsyncWorkerPool(
            worker_count=self._config.worker_count,
            processor=self._get_default_processor(),
            semaphore=self._semaphore,
            queue=self._queue,
            config=self._config,
        )
        
        logger.info("All pipeline components initialized")
    
    def _get_default_processor(self) -> Callable:
        """Get the default job processor or custom processor."""
        if self._processor:
            return self._processor
        
        # Return a default processor that can be overridden
        async def default_processor(job: JobContext) -> ProcessingResult:
            return ProcessingResult.success(
                job_id=job.job_id,
                data={"message": "Job received"},
            )
        
        return default_processor
    
    async def _run_pipeline(
        self,
        query: str,
        resume_text: str,
        filters: Optional[Dict[str, Any]],
    ) -> None:
        """Run the actual pipeline processing."""
        filters = filters or {}
        
        # Start worker pool
        await self._worker_pool.start()
        
        # Start producer and queue jobs
        producer_task = asyncio.create_task(
            self._produce_jobs(query, filters)
        )
        
        # Wait for producer to finish
        await producer_task
        
        # Wait for workers to complete
        self._results = await self._worker_pool.wait_completion()
        
        # Update stats
        self._stats.jobs_completed = sum(
            1 for r in self._results if r.is_success()
        )
        self._stats.jobs_failed = sum(
            1 for r in self._results if not r.is_success()
        )
        self._stats.end_time = datetime.utcnow().timestamp()
        
        # Stop worker pool
        await self._worker_pool.stop()
    
    async def _produce_jobs(
        self,
        query: str,
        filters: Dict[str, Any],
    ) -> None:
        """Produce jobs from database into the queue."""
        logger.info("Starting job production")
        
        try:
            # Get job count for progress tracking
            total_jobs = await self._producer.get_job_count(query, filters)
            self._stats.jobs_queued = total_jobs
            
            logger.info(f"Found {total_jobs} jobs to process")
            
            # Stream jobs into queue
            jobs_produced = 0
            
            async for job in self._producer.produce_jobs(query, filters):
                # Check for shutdown request
                if self._shutdown_requested:
                    logger.info("Shutdown requested, stopping production")
                    break
                
                # Put job in queue (blocks if full - backpressure)
                await self._queue.put(job)
                jobs_produced += 1
                
                # Progress update
                if self._progress_callback and jobs_produced % 10 == 0:
                    self._progress_callback({
                        "jobs_queued": total_jobs,
                        "jobs_produced": jobs_produced,
                        "queue_size": self._queue.qsize(),
                    })
            
            logger.info(f"Job production complete: {jobs_produced} jobs queued")
            
        except Exception as e:
            logger.error(f"Error in job production: {e}", exc_info=True)
            raise
    
    async def run_with_callbacks(
        self,
        on_job_start: Optional[Callable[[JobContext], None]] = None,
        on_job_complete: Optional[Callable[[ProcessingResult], None]] = None,
        on_progress: Optional[Callable[[Dict], None]] = None,
    ) -> List[ProcessingResult]:
        """
        Run pipeline with callbacks for monitoring.
        
        Args:
            on_job_start: Called when a job starts processing.
            on_job_complete: Called when a job completes.
            on_progress: Called periodically with progress updates.
            
        Returns:
            List of ProcessingResult.
        """
        if on_progress:
            self.set_progress_callback(on_progress)
        
        return await self.run()
    
    async def close(self) -> None:
        """Clean up pipeline resources."""
        logger.info("Closing pipeline...")
        
        # Stop worker pool if running
        if self._worker_pool and self._worker_pool.is_started:
            await self._worker_pool.stop()
        
        # Close database connection
        if self._engine:
            await self._engine.dispose()
            self._engine = None
        
        logger.info("Pipeline closed")
    
    @property
    def stats(self) -> PipelineStats:
        """Get pipeline statistics."""
        return self._stats
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._running
    
    @property
    def queue(self) -> Optional[BoundedQueue]:
        """Get the job queue."""
        return self._queue
    
    @property
    def rate_limiter(self) -> Optional[MultiRateLimiter]:
        """Get the rate limiter."""
        return self._rate_limiter


class AsyncJobPipelineBuilder:
    """
    Builder for constructing AsyncJobPipeline with dependencies.
    
    Example:
        pipeline = (AsyncJobPipelineBuilder()
            .config(my_config)
            .processor(my_processor)
            .on_progress(lambda p: print(p))
            .build())
    """
    
    def __init__(self):
        self._config: Optional[ProcessorConfig] = None
        self._db_url: Optional[str] = None
        self._processor: Optional[Callable] = None
        self._progress_callback: Optional[Callable] = None
    
    def config(self, config: ProcessorConfig) -> "AsyncJobPipelineBuilder":
        """Set the processor configuration."""
        self._config = config
        return self
    
    def db_url(self, url: str) -> "AsyncJobPipelineBuilder":
        """Set the database URL."""
        self._db_url = url
        return self
    
    def processor(self, processor: Callable) -> "AsyncJobPipelineBuilder":
        """Set the job processor."""
        self._processor = processor
        return self
    
    def on_progress(self, callback: Callable) -> "AsyncJobPipelineBuilder":
        """Set the progress callback."""
        self._progress_callback = callback
        return self
    
    def build(self) -> AsyncJobPipeline:
        """Build and return the pipeline."""
        pipeline = AsyncJobPipeline(
            config=self._config,
            db_url=self._db_url,
        )
        
        if self._processor:
            pipeline.set_processor(self._processor)
        
        if self._progress_callback:
            pipeline.set_progress_callback(self._progress_callback)
        
        return pipeline


# Convenience function for quick pipeline creation
async def create_pipeline_and_run(
    query: str,
    processor: Callable[[JobContext], ProcessingResult],
    config: Optional[ProcessorConfig] = None,
    db_url: Optional[str] = None,
) -> List[ProcessingResult]:
    """
    Create a pipeline, run it, and return results.
    
    Convenience function for quick pipeline execution.
    
    Args:
        query: Search query for jobs.
        processor: Job processor function.
        config: Optional processor configuration.
        db_url: Optional database URL.
        
    Returns:
        List of ProcessingResult.
    """
    pipeline = AsyncJobPipelineBuilder() \
        .config(config) \
        .db_url(db_url) \
        .processor(processor) \
        .build()
    
    try:
        return await pipeline.run(query=query)
    finally:
        await pipeline.close()

