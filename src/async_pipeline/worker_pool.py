"""
Async worker pool for the job pipeline.

This module manages concurrent workers that process jobs from a bounded queue,
with semaphore-based rate limiting and graceful shutdown support.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, List, Optional

from src.async_pipeline.bounded_queue import BoundedQueue
from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.types import (
    JobContext,
    ProcessingResult,
    WorkerPoolStats,
)

logger = logging.getLogger(__name__)


class AsyncWorkerPool:
    """
    Manages N concurrent workers that drain a job queue.
    
    Each worker is semaphore-gated for rate control and implements
    the poison pill pattern for graceful shutdown.
    
    Example:
        pool = AsyncWorkerPool(
            worker_count=5,
            processor=process_job,
            semaphore=asyncio.Semaphore(10),
            queue=job_queue,
        )
        
        await pool.start()
        results = await pool.wait_completion()
        await pool.stop()
    """
    
    def __init__(
        self,
        worker_count: int,
        processor: Callable[[JobContext], ProcessingResult],
        semaphore: asyncio.Semaphore,
        queue: BoundedQueue,
        config: Optional[ProcessorConfig] = None,
    ):
        """
        Initialize the worker pool.
        
        Args:
            worker_count: Number of concurrent workers.
            processor: Async callable that processes JobContext and returns ProcessingResult.
            semaphore: Concurrency limiter for external API calls.
            queue: Bounded queue for job distribution.
            config: Optional processor configuration.
        """
        if worker_count <= 0:
            raise ValueError("worker_count must be positive")
        
        self._worker_count = worker_count
        self._processor = processor
        self._semaphore = semaphore
        self._queue = queue
        self._config = config or ProcessorConfig()
        
        self._workers: List[asyncio.Task] = []
        self._results: List[ProcessingResult] = []
        self._results_lock = asyncio.Lock()
        self._active_workers = 0
        self._active_lock = asyncio.Lock()
        
        self._stats = WorkerPoolStats(workers_total=worker_count)
        self._shutdown_event = asyncio.Event()
        self._started = False
        
        logger.debug(
            f"AsyncWorkerPool initialized with {worker_count} workers"
        )
    
    @property
    def worker_count(self) -> int:
        """Get the number of workers."""
        return self._worker_count
    
    @property
    def stats(self) -> WorkerPoolStats:
        """Get worker pool statistics."""
        return self._stats
    
    @property
    def is_started(self) -> bool:
        """Check if the pool has started."""
        return self._started
    
    async def start(self) -> None:
        """
        Start all workers.
        
        Creates worker tasks that will run until shutdown.
        """
        if self._started:
            logger.warning("Worker pool already started")
            return
        
        logger.info(f"Starting {self._worker_count} workers...")
        
        for i in range(self._worker_count):
            worker_id = f"worker-{i}"
            task = asyncio.create_task(self._worker_loop(worker_id))
            self._workers.append(task)
        
        self._started = True
        logger.info(f"All {self._worker_count} workers started")
    
    async def stop(self) -> None:
        """
        Stop all workers gracefully.
        
        Sends poison pills to workers and waits for them to finish.
        """
        if not self._started:
            logger.warning("Worker pool not started")
            return
        
        logger.info("Stopping worker pool...")
        
        # Send poison pills to all workers
        await self._queue.put_poison_pills(self._worker_count)
        
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers = []
        self._started = False
        
        logger.info("Worker pool stopped")
    
    async def wait_completion(self) -> List[ProcessingResult]:
        """
        Wait for all jobs to be processed.
        
        Returns:
            List of ProcessingResult for all processed jobs.
        """
        # Wait for queue to be empty and all workers to finish
        while not self._queue.empty() or self._active_workers > 0:
            await asyncio.sleep(0.1)
        
        # Get results
        async with self._results_lock:
            return self._results.copy()
    
    async def _worker_loop(self, worker_id: str) -> None:
        """
        Main worker loop that processes jobs from the queue.
        
        Args:
            worker_id: Unique identifier for this worker.
        """
        logger.debug(f"{worker_id} started")
        
        while True:
            try:
                # Get job from queue (blocks if empty)
                job = await self._queue.get()
                
                # Check for poison pill
                if job is None:
                    logger.debug(f"{worker_id} received poison pill, shutting down")
                    break
                
                # Track active workers
                async with self._active_lock:
                    self._active_workers += 1
                    self._stats.workers_active = self._active_workers
                
                try:
                    # Process job with semaphore
                    await self._semaphore.acquire()
                    try:
                        result = await self._process_job_with_metrics(job, worker_id)
                        
                        # Store result
                        async with self._results_lock:
                            self._results.append(result)
                        
                    finally:
                        # Always release semaphore
                        self._semaphore.release()
                        
                finally:
                    # Decrement active workers
                    async with self._active_lock:
                        self._active_workers -= 1
                        self._stats.workers_active = self._active_workers
                
            except asyncio.CancelledError:
                logger.info(f"{worker_id} cancelled")
                break
            except Exception as exc:
                logger.error(f"{worker_id} error: {exc}", exc_info=True)
                # Continue processing other jobs
        
        logger.debug(f"{worker_id} stopped")
    
    async def _process_job_with_metrics(
        self,
        job: JobContext,
        worker_id: str,
    ) -> ProcessingResult:
        """
        Process a job with retry logic and metrics tracking.
        
        Args:
            job: Job to process.
            worker_id: ID of the worker processing this job.
            
        Returns:
            ProcessingResult with status and data.
        """
        start_time = time.perf_counter()
        attempt_count = 1
        
        while True:
            try:
                # Process the job
                result = await self._processor(job)
                
                # Add worker info and timing
                result.worker_id = worker_id
                result.processing_time_ms = (time.perf_counter() - start_time) * 1000
                
                # Update stats
                if result.is_success():
                    self._stats.jobs_processed += 1
                    logger.debug(
                        f"{worker_id} completed job {job.job_id} in "
                        f"{result.processing_time_ms:.2f}ms"
                    )
                else:
                    self._stats.jobs_failed += 1
                    logger.warning(
                        f"{worker_id} failed job {job.job_id}: {result.error}"
                    )
                
                self._stats.total_processing_time_ms += result.processing_time_ms
                
                return result
                
            except Exception as exc:
                # Check if we should retry
                if attempt_count < self._config.max_retries:
                    attempt_count += 1
                    self._stats.jobs_retried += 1
                    
                    # Calculate backoff delay
                    delay = min(
                        self._config.retry_base_delay * (
                            self._config.retry_exponential_base ** (attempt_count - 1)
                        ),
                        self._config.retry_max_delay,
                    )
                    
                    logger.warning(
                        f"{worker_id} retrying job {job.job_id} "
                        f"(attempt {attempt_count}/{self._config.max_retries}) "
                        f"after {delay:.2f}s: {exc}"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted
                    self._stats.jobs_failed += 1
                    
                    logger.error(
                        f"{worker_id} failed job {job.job_id} after "
                        f"{attempt_count} attempts: {exc}"
                    )
                    
                    return ProcessingResult.failure(
                        job_id=job.job_id,
                        error=str(exc),
                        error_type=type(exc).__name__,
                        attempt_count=attempt_count,
                        worker_id=worker_id,
                    )
    
    def get_active_workers(self) -> int:
        """Get the number of currently active workers."""
        return self._active_workers
    
    def get_results(self) -> List[ProcessingResult]:
        """Get all processing results."""
        return self._results.copy()
    
    def reset_stats(self) -> None:
        """Reset worker pool statistics."""
        self._stats = WorkerPoolStats(workers_total=self._worker_count)
        self._results = []


class WorkerPoolBuilder:
    """
    Builder pattern for constructing WorkerPool with dependencies.
    
    Example:
        pool = (WorkerPoolBuilder()
            .worker_count(5)
            .semaphore_limit(10)
            .queue_size(100)
            .processor(my_processor)
            .build())
    """
    
    def __init__(self):
        self._worker_count: int = 5
        self._semaphore_limit: int = 10
        self._queue_size: int = 100
        self._processor: Optional[Callable] = None
        self._config: Optional[ProcessorConfig] = None
    
    def worker_count(self, count: int) -> "WorkerPoolBuilder":
        """Set the number of workers."""
        self._worker_count = count
        return self
    
    def semaphore_limit(self, limit: int) -> "WorkerPoolBuilder":
        """Set the semaphore limit."""
        self._semaphore_limit = limit
        return self
    
    def queue_size(self, size: int) -> "WorkerPoolBuilder":
        """Set the queue size."""
        self._queue_size = size
        return self
    
    def processor(self, processor: Callable) -> "WorkerPoolBuilder":
        """Set the job processor function."""
        self._processor = processor
        return self
    
    def config(self, config: ProcessorConfig) -> "WorkerPoolBuilder":
        """Set the processor configuration."""
        self._config = config
        return self
    
    def build(self) -> AsyncWorkerPool:
        """Build and return the worker pool."""
        if self._processor is None:
            raise ValueError("processor is required")
        
        queue = BoundedQueue(maxsize=self._queue_size)
        semaphore = asyncio.Semaphore(self._semaphore_limit)
        config = self._config or ProcessorConfig()
        
        return AsyncWorkerPool(
            worker_count=self._worker_count,
            processor=self._processor,
            semaphore=semaphore,
            queue=queue,
            config=config,
        )

