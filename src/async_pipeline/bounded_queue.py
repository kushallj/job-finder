"""
Bounded queue with backpressure for the async job pipeline.

This module provides a thread-safe async queue that automatically
applies backpressure when the producer is faster than consumers.
"""

import asyncio
import logging
import time
from typing import Any, Optional

from src.async_pipeline.types import QueueStats

logger = logging.getLogger(__name__)


class BoundedQueue:
    """
    Async queue with configurable size that provides natural backpressure.
    
    The queue blocks producers when full, preventing unbounded memory growth.
    Supports the poison pill pattern for graceful worker shutdown.
    
    Example:
        queue = BoundedQueue(maxsize=100)
        
        # Producer
        await queue.put(job)  # Blocks if queue is full
        
        # Consumer
        job = await queue.get()  # Blocks if queue is empty
        
        # Poison pill for shutdown
        await queue.put_poison_pills(worker_count)
    """
    
    def __init__(
        self,
        maxsize: int = 100,
        stats: Optional[QueueStats] = None
    ):
        """
        Initialize the bounded queue.
        
        Args:
            maxsize: Maximum queue size. When 0, queue is unbounded (not recommended).
            stats: Optional QueueStats instance for tracking metrics.
        """
        if maxsize < 0:
            raise ValueError("maxsize must be non-negative")
        
        # Defer queue creation to avoid event loop binding issues
        # The queue will be created lazily in the correct event loop
        self._queue: Optional[asyncio.Queue[Optional[Any]]] = None
        self._maxsize = maxsize
        self._stats = stats or QueueStats()
        self._get_wait_times: list = []
        self._put_wait_times: list = []
        
        logger.debug(f"BoundedQueue initialized with maxsize={maxsize}")
    
    def _ensure_queue(self) -> None:
        """Ensure the queue is created in the current event loop."""
        if self._queue is None:
            try:
                # Get the current event loop
                loop = asyncio.get_running_loop()
                self._queue = asyncio.Queue(maxsize=self._maxsize)
                logger.debug(f"BoundedQueue created in event loop {id(loop)}")
            except RuntimeError:
                # No running loop, create queue anyway (will fail later if used incorrectly)
                self._queue = asyncio.Queue(maxsize=self._maxsize)
                logger.warning("BoundedQueue created outside of event loop")
    
    @property
    def maxsize(self) -> int:
        """Get the maximum queue size."""
        return self._maxsize
    
    @property
    def stats(self) -> QueueStats:
        """Get queue statistics."""
        return self._stats
    
    async def put(self, item: Any, timeout: Optional[float] = None) -> bool:
        """
        Put an item in the queue.
        
        Blocks if the queue is full (backpressure).
        
        Args:
            item: The item to enqueue. Use None for poison pills.
            timeout: Optional timeout in seconds. Raises asyncio.TimeoutError if exceeded.
            
        Returns:
            True if item was queued, False if timeout occurred.
            
        Raises:
            asyncio.TimeoutError: If timeout is exceeded.
        """
        self._ensure_queue()  # Ensure queue exists in current event loop
        start_time = time.perf_counter()
        
        try:
            if timeout:
                await asyncio.wait_for(self._queue.put(item), timeout=timeout)
            else:
                await self._queue.put(item)
            
            self._stats.items_put += 1
            
            wait_time = (time.perf_counter() - start_time) * 1000  # ms
            self._stats.total_wait_time_ms += wait_time
            
            # Check if we hit backpressure
            if self._queue.full():
                self._stats.backpressure_events += 1
                logger.debug(f"Queue is full, backpressure applied")
            
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Queue put timed out after {timeout}s")
            return False
    
    async def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Get an item from the queue.
        
        Blocks if the queue is empty.
        
        Args:
            timeout: Optional timeout in seconds. Raises asyncio.TimeoutError if exceeded.
            
        Returns:
            The queued item, or None if timeout occurred.
            
        Raises:
            asyncio.TimeoutError: If timeout is exceeded.
        """
        self._ensure_queue()  # Ensure queue exists in current event loop
        start_time = time.perf_counter()
        
        try:
            if timeout:
                item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                item = await self._queue.get()
            
            self._stats.items_get += 1
            
            wait_time = (time.perf_counter() - start_time) * 1000  # ms
            self._get_wait_times.append(wait_time)
            
            return item
            
        except asyncio.TimeoutError:
            logger.warning(f"Queue get timed out after {timeout}s")
            return None
    
    async def put_poison_pills(self, count: int) -> None:
        """
        Put poison pills to signal workers to stop.
        
        Args:
            count: Number of poison pills to put (typically equal to worker count).
        """
        self._ensure_queue()  # Ensure queue exists in current event loop
        logger.debug(f"Putting {count} poison pills in queue")
        
        for _ in range(count):
            await self._queue.put(None)
        
        logger.info(f"Added {count} poison pills to queue")
    
    def qsize(self) -> int:
        """
        Get the current queue size.
        
        Returns:
            Number of items currently in the queue.
        """
        self._ensure_queue()
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Note: This is approximate - the queue might become non-empty
        immediately after this check.
        
        Returns:
            True if the queue is empty.
        """
        self._ensure_queue()
        return self._queue.empty()
    
    def full(self) -> bool:
        """
        Check if the queue is full.
        
        Note: This is approximate - the queue might become non-full
        immediately after this check.
        
        Returns:
            True if the queue is full.
        """
        self._ensure_queue()
        return self._queue.full()
    
    def get_wait_time_stats(self) -> dict:
        """Get statistics about get() wait times."""
        if not self._get_wait_times:
            return {"count": 0, "avg_ms": 0, "max_ms": 0, "min_ms": 0}
        
        return {
            "count": len(self._get_wait_times),
            "avg_ms": sum(self._get_wait_times) / len(self._get_wait_times),
            "max_ms": max(self._get_wait_times),
            "min_ms": min(self._get_wait_times),
        }
    
    def reset_stats(self) -> None:
        """Reset queue statistics."""
        self._stats = QueueStats()
        self._get_wait_times = []
        self._put_wait_times = []


class AsyncJobQueue(BoundedQueue):
    """
    Type-specific bounded queue for JobContext objects.
    
    This is a type-annotated version of BoundedQueue specifically
    for job processing.
    """
    
    def __init__(self, maxsize: int = 100):
        super().__init__(maxsize=maxsize)
        logger.debug("AsyncJobQueue initialized")

