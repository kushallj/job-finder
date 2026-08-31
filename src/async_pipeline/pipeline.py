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
import logging.handlers
import signal
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.async_pipeline.bounded_queue import BoundedQueue
from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.metrics import MetricsCollector, MetricsSnapshot
from src.async_pipeline.producer import AsyncJobProducer
from src.async_pipeline.progress_tracker import ProgressTracker
from src.async_pipeline.rate_limiter import MultiRateLimiter, TokenBucket
from src.async_pipeline.retry import RetryManager
from src.async_pipeline.types import (
    JobContext,
    PipelineStats,
    ProcessingResult,
    WorkerPoolStats,
)
from src.async_pipeline import get_logger
from src.async_pipeline.worker_pool import AsyncWorkerPool

logger = get_logger(__name__)


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
        self._metrics_collector: Optional[MetricsCollector] = None
        
        # Pipeline state
        self._processor: Optional[Callable] = None
        self._results: List[ProcessingResult] = []
        self._stats = PipelineStats()
        self._running = False
        self._shutdown_requested = False
        
        # Progress tracking
        self._progress_callback: Optional[Callable] = None
        self._progress_tracker: Optional[ProgressTracker] = None
        self._enable_progress_display: bool = True
        
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
                logging.handlers.RotatingFileHandler(
                    self._config.log_file, maxBytes=5_000_000, backupCount=3
                ),
            ],
        )
        
        logger.info(f"Logging configured at {self._config.log_level} level")
    
    def _setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for graceful shutdown.
        
        Handles SIGTERM (kill) and SIGINT (Ctrl+C) by setting shutdown flag
        and initiating graceful shutdown of the pipeline.
        
        Requirements: 24.1, 24.2, 24.3, 24.4
        """
        def signal_handler(sig, frame):
            sig_name = "SIGTERM" if sig == signal.SIGTERM else "SIGINT" if sig == signal.SIGINT else f"signal-{sig}"
            logger.info(
                "shutdown_signal_received",
                signal=sig_name,
                message="Initiating graceful shutdown - will complete in-flight jobs",
            )
            self._shutdown_requested = True
            
            # If running in async context, trigger shutdown
            if self._running:
                logger.info(
                    "shutdown_in_progress",
                    message=f"Waiting up to {self._config.shutdown_timeout_seconds}s for in-flight jobs to complete",
                )
        
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            logger.debug("signal_handlers_registered", signals=["SIGTERM", "SIGINT"])
        except Exception as e:
            logger.warning(
                "signal_handler_setup_failed",
                error_type=type(e).__name__,
                error_message=str(e),
                message="Signal handlers could not be registered - graceful shutdown may not work",
            )
    
    async def _init_database(self) -> None:
        """Initialize database connection and session factory."""
        if self._engine is not None:
            return
        
        logger.info(f"Connecting to database: {self._db_url}")
        
        # SQLite doesn't support pool_size and max_overflow
        if "sqlite" in self._db_url.lower():
            self._engine = create_async_engine(
                self._db_url,
                echo=False,
            )
        else:
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
    
    def enable_progress_display(self, enable: bool = True) -> None:
        """
        Enable or disable rich progress display.
        
        Args:
            enable: True to enable progress display, False to disable.
        """
        self._enable_progress_display = enable
    
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
            # Initialize database if needed
            if not self._engine:
                await self._init_database()
            
            # Initialize components if needed
            if not self._queue:
                await self._setup_components()

            
            # Initialize progress tracker if enabled
            if self._enable_progress_display:
                # Get total job count for progress tracking
                total_jobs = await self._producer.get_job_count(query, filters or {})
                self._progress_tracker = ProgressTracker(
                    total_jobs=total_jobs,
                    worker_count=self._config.worker_count,
                    enable_logging=True,
                )
                self._progress_tracker.start()
            
            # Start the pipeline
            await self._run_pipeline(query, resume_text, filters)
            
            # Stop progress tracker
            if self._progress_tracker:
                self._progress_tracker.stop()
                self._progress_tracker = None
            
            logger.info(f"Pipeline completed: {self._stats.to_dict()}")
            
            return self._results
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            
            # Stop progress tracker on error
            if self._progress_tracker:
                self._progress_tracker.stop()
                self._progress_tracker = None
            
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
        
        # Initialize metrics collector
        self._metrics_collector = MetricsCollector(
            semaphore_total=self._config.max_concurrent_api_calls,
            workers_total=self._config.worker_count,
        )
        
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
        
        # Initialize worker pool with metrics collector
        self._worker_pool = AsyncWorkerPool(
            worker_count=self._config.worker_count,
            processor=self._get_default_processor(),
            semaphore=self._semaphore,
            queue=self._queue,
            config=self._config,
            metrics_collector=self._metrics_collector,
            on_job_complete=self._on_worker_job_complete,
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
    
    async def _on_worker_job_complete(self, result: ProcessingResult) -> None:
        """
        Callback invoked when a worker completes a job.
        
        Updates progress tracker and invokes user callback if set.
        
        Args:
            result: The processing result for the completed job.
        """
        # Update progress tracker
        if self._progress_tracker:
            await self._progress_tracker.update_job_completed(result)
            
            # Update queue size and active workers
            if self._queue:
                self._progress_tracker.update_queue_size(self._queue.qsize())
            
            if self._worker_pool:
                self._progress_tracker.update_active_workers(
                    self._worker_pool.get_active_workers()
                )
        
        # Invoke user callback if set
        if self._progress_callback:
            try:
                self._progress_callback({
                    "job_id": result.job_id,
                    "status": result.status.value,
                    "is_success": result.is_success(),
                    "processing_time_ms": result.processing_time_ms,
                    "worker_id": result.worker_id,
                })
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    async def _run_pipeline(
        self,
        query: str,
        resume_text: str,
        filters: Optional[Dict[str, Any]],
    ) -> None:
        """Run the actual pipeline processing."""
        filters = filters or {}
        
        # Start periodic metrics recording task
        metrics_task = None
        if self._metrics_collector:
            metrics_task = asyncio.create_task(
                self._periodic_metrics_recording()
            )
        
        try:
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
            
        finally:
            # Stop metrics recording
            if metrics_task:
                metrics_task.cancel()
                try:
                    await metrics_task
                except asyncio.CancelledError:
                    pass
    
    async def _periodic_metrics_recording(self) -> None:
        """
        Periodically record queue state and metrics.
        
        This runs as a background task during pipeline execution.
        """
        try:
            while True:
                await asyncio.sleep(1.0)  # Record every second
                
                if self._queue and self._worker_pool and self._metrics_collector:
                    # Record current queue state
                    queue_size = self._queue.qsize()
                    active_workers = self._worker_pool.get_active_workers()
                    
                    # Calculate available semaphore slots
                    # Note: asyncio.Semaphore doesn't expose available count directly
                    # We track it indirectly through the metrics collector
                    semaphore_available = (
                        self._config.max_concurrent_api_calls - active_workers
                    )
                    
                    self._metrics_collector.record_queue_state(
                        size=queue_size,
                        active_workers=active_workers,
                        semaphore_available=max(0, semaphore_available),
                    )
                    
        except asyncio.CancelledError:
            logger.debug("Metrics recording task cancelled")
            raise
    
    async def _produce_jobs(
        self,
        query: str,
        filters: Dict[str, Any],
    ) -> None:
        """
        Produce jobs from database into the queue.
        
        This method streams jobs from the database and adds them to the queue.
        It respects the shutdown flag and stops production gracefully when
        shutdown is requested.
        
        Requirements: 24.1 (stop accepting new jobs on shutdown)
        """
        logger.info("Starting job production")
        
        try:
            # Get job count for progress tracking
            total_jobs = await self._producer.get_job_count(query, filters)
            self._stats.jobs_queued = total_jobs
            
            logger.info(f"Found {total_jobs} jobs to process")
            
            # Stream jobs into queue
            jobs_produced = 0
            
            async for job in self._producer.produce_jobs(query, filters):
                # Check for shutdown request - stop accepting new jobs
                if self._shutdown_requested:
                    logger.info(
                        "job_production_stopped",
                        jobs_produced=jobs_produced,
                        jobs_remaining=total_jobs - jobs_produced,
                        message="Shutdown requested - stopped accepting new jobs",
                    )
                    break
                
                # Put job in queue (blocks if full - backpressure)
                await self._queue.put(job)
                jobs_produced += 1
                
                # Update progress tracker
                if self._progress_tracker:
                    self._progress_tracker.update_queue_size(self._queue.qsize())
                
                # Progress update callback
                if self._progress_callback and jobs_produced % 10 == 0:
                    self._progress_callback({
                        "jobs_queued": total_jobs,
                        "jobs_produced": jobs_produced,
                        "queue_size": self._queue.qsize(),
                    })
            
            if not self._shutdown_requested:
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
        """
        Clean up pipeline resources with graceful shutdown.
        
        This method implements the complete graceful shutdown procedure:
        1. Stop accepting new jobs
        2. Wait for in-flight jobs to complete (with timeout)
        3. Force terminate remaining jobs after timeout
        4. Clean up all resources (workers, database connections, file handles)
        
        Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 34.1
        """
        logger.info(
            "pipeline_shutdown_started",
            message="Closing pipeline with graceful shutdown",
        )
        
        shutdown_start_time = time.time()
        
        try:
            # Step 1: Stop accepting new jobs (already done via _shutdown_requested flag)
            logger.info(
                "shutdown_step_1",
                message="Stopped accepting new jobs",
            )
            
            # Step 2: Wait for in-flight jobs to complete with timeout
            if self._worker_pool and self._worker_pool.is_started:
                active_workers = self._worker_pool.get_active_workers()
                
                if active_workers > 0:
                    logger.info(
                        "shutdown_step_2",
                        active_workers=active_workers,
                        timeout_seconds=self._config.shutdown_timeout_seconds,
                        message=f"Waiting for {active_workers} in-flight jobs to complete",
                    )
                    
                    # Wait for workers with timeout
                    try:
                        await asyncio.wait_for(
                            self._wait_for_workers_graceful(),
                            timeout=self._config.shutdown_timeout_seconds,
                        )
                        
                        elapsed = time.time() - shutdown_start_time
                        logger.info(
                            "shutdown_step_2_complete",
                            elapsed_seconds=round(elapsed, 2),
                            message="All in-flight jobs completed successfully",
                        )
                        
                    except asyncio.TimeoutError:
                        # Step 3: Timeout exceeded, force terminate remaining jobs
                        remaining_workers = self._worker_pool.get_active_workers()
                        elapsed = time.time() - shutdown_start_time
                        
                        logger.warning(
                            "shutdown_timeout_exceeded",
                            remaining_workers=remaining_workers,
                            elapsed_seconds=round(elapsed, 2),
                            timeout_seconds=self._config.shutdown_timeout_seconds,
                            message=f"Shutdown timeout exceeded, forcefully terminating {remaining_workers} remaining jobs",
                        )
                        
                        # Force stop worker pool
                        await self._force_stop_workers()
                        
                        logger.info(
                            "shutdown_step_3_complete",
                            message="Forcefully terminated remaining jobs",
                        )
                else:
                    logger.info(
                        "shutdown_step_2_skipped",
                        message="No active workers, skipping wait",
                    )
                
                # Stop worker pool
                await self._worker_pool.stop()
            
            # Step 4: Clean up resources
            logger.info(
                "shutdown_step_4",
                message="Cleaning up resources",
            )
            
            # Close database connection
            if self._engine:
                logger.debug("shutdown_cleanup_database", message="Closing database connections")
                await self._engine.dispose()
                self._engine = None
                self._session_factory = None
            
            # Stop progress tracker
            if self._progress_tracker:
                logger.debug("shutdown_cleanup_progress", message="Stopping progress tracker")
                self._progress_tracker.stop()
                self._progress_tracker = None
            
            # Close logging handlers
            logger.debug("shutdown_cleanup_logging", message="Flushing log handlers")
            for handler in logging.getLogger().handlers:
                try:
                    handler.flush()
                except Exception as e:
                    logger.debug("log_handler_flush_error", error=str(e))
            
            total_elapsed = time.time() - shutdown_start_time
            logger.info(
                "pipeline_shutdown_complete",
                total_elapsed_seconds=round(total_elapsed, 2),
                message="Pipeline shutdown completed successfully",
            )
            
        except Exception as e:
            logger.error(
                "pipeline_shutdown_error",
                error_type=type(e).__name__,
                error_message=str(e),
                message="Error during pipeline shutdown",
                exc_info=True,
            )
            raise
    
    async def _wait_for_workers_graceful(self) -> None:
        """
        Wait for all workers to complete their current jobs gracefully.
        
        This method polls the worker pool until all active workers finish.
        Should be called with a timeout wrapper.
        """
        while True:
            active = self._worker_pool.get_active_workers()
            if active == 0:
                break
            
            # Check every 100ms
            await asyncio.sleep(0.1)
            
            # Log progress every 5 seconds
            if int(time.time()) % 5 == 0:
                logger.debug(
                    "shutdown_wait_progress",
                    active_workers=active,
                    message="Still waiting for in-flight jobs to complete",
                )
    
    async def _force_stop_workers(self) -> None:
        """
        Forcefully terminate all worker tasks.
        
        This method cancels all worker tasks immediately, which will
        interrupt any in-flight jobs.
        """
        if not self._worker_pool or not self._worker_pool._workers:
            return
        
        # Cancel all worker tasks
        for worker_task in self._worker_pool._workers:
            if not worker_task.done():
                worker_task.cancel()
        
        # Wait for cancellation to complete
        await asyncio.gather(*self._worker_pool._workers, return_exceptions=True)
        
        logger.info(
            "workers_force_stopped",
            worker_count=len(self._worker_pool._workers),
            message="All worker tasks forcefully cancelled",
        )
    
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
    
    @property
    def metrics_collector(self) -> Optional[MetricsCollector]:
        """Get the metrics collector."""
        return self._metrics_collector
    
    def get_metrics_snapshot(self) -> Optional[MetricsSnapshot]:
        """
        Get current metrics snapshot.
        
        Returns:
            MetricsSnapshot with all current metrics, or None if not initialized.
        """
        if self._metrics_collector:
            return self._metrics_collector.get_snapshot()
        return None
    
    def log_metrics_summary(self) -> None:
        """Log a summary of current metrics."""
        if self._metrics_collector:
            self._metrics_collector.log_summary()


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

