"""
Unit tests for BoundedQueue implementation.

Tests cover:
- Queue initialization with configurable maxsize
- Async put() method that blocks when full (backpressure)
- Async get() method that blocks when empty
- Poison pill pattern for graceful shutdown
- Queue statistics tracking
- Queue size constraints
"""

import pytest
import asyncio
from src.async_pipeline.bounded_queue import BoundedQueue, AsyncJobQueue
from src.async_pipeline.types import JobContext, QueueStats


class TestBoundedQueueInitialization:
    """Test BoundedQueue initialization and configuration."""
    
    def test_queue_initialization_with_maxsize(self):
        """Test that queue initializes with configurable maxsize."""
        queue = BoundedQueue(maxsize=50)
        
        assert queue.maxsize == 50
        assert queue.qsize() == 0
        assert queue.empty()
        assert not queue.full()
    
    def test_queue_initialization_default_maxsize(self):
        """Test that queue uses default maxsize of 100."""
        queue = BoundedQueue()
        
        assert queue.maxsize == 100
    
    def test_queue_initialization_with_stats(self):
        """Test that queue can be initialized with custom stats."""
        stats = QueueStats()
        queue = BoundedQueue(maxsize=50, stats=stats)
        
        assert queue.stats is stats
        assert queue.stats.items_put == 0
        assert queue.stats.items_get == 0
    
    def test_queue_initialization_negative_maxsize(self):
        """Test that negative maxsize raises ValueError."""
        with pytest.raises(ValueError, match="maxsize must be non-negative"):
            BoundedQueue(maxsize=-1)
    
    def test_queue_initialization_zero_maxsize(self):
        """Test that zero maxsize creates unbounded queue."""
        queue = BoundedQueue(maxsize=0)
        
        assert queue.maxsize == 0


class TestBoundedQueuePutMethod:
    """Test async put() method and backpressure behavior."""
    
    @pytest.mark.asyncio
    async def test_put_single_item(self):
        """Test putting a single item in the queue."""
        queue = BoundedQueue(maxsize=10)
        
        result = await queue.put("test_item")
        
        assert result is True
        assert queue.qsize() == 1
        assert queue.stats.items_put == 1
    
    @pytest.mark.asyncio
    async def test_put_multiple_items(self):
        """Test putting multiple items in the queue."""
        queue = BoundedQueue(maxsize=10)
        
        for i in range(5):
            await queue.put(f"item_{i}")
        
        assert queue.qsize() == 5
        assert queue.stats.items_put == 5
    
    @pytest.mark.asyncio
    async def test_put_blocks_when_full(self):
        """Test that put() blocks when queue reaches capacity (backpressure)."""
        queue = BoundedQueue(maxsize=2)
        
        # Fill the queue
        await queue.put("item_1")
        await queue.put("item_2")
        
        assert queue.full()
        
        # This should block, so we use a timeout
        put_task = asyncio.create_task(queue.put("item_3"))
        
        # Give it a moment to block
        await asyncio.sleep(0.1)
        
        # Task should not be done (still waiting)
        assert not put_task.done()
        
        # Consume one item to unblock
        await queue.get()
        
        # Now the put should complete
        await asyncio.wait_for(put_task, timeout=1.0)
        
        assert queue.qsize() == 2
    
    @pytest.mark.asyncio
    async def test_put_with_timeout(self):
        """Test put() with timeout when queue is full."""
        queue = BoundedQueue(maxsize=1)
        
        # Fill the queue
        await queue.put("item_1")
        
        # Try to put with timeout (should timeout)
        result = await queue.put("item_2", timeout=0.1)
        
        assert result is False  # Timeout occurred
        assert queue.qsize() == 1  # Queue unchanged
    
    @pytest.mark.asyncio
    async def test_put_tracks_backpressure_events(self):
        """Test that put() tracks backpressure events when queue is full."""
        queue = BoundedQueue(maxsize=2)
        
        # Fill the queue completely
        await queue.put("item_1")
        await queue.put("item_2")
        
        # Stats should show backpressure event
        assert queue.stats.backpressure_events > 0


class TestBoundedQueueGetMethod:
    """Test async get() method and blocking behavior."""
    
    @pytest.mark.asyncio
    async def test_get_single_item(self):
        """Test getting a single item from the queue."""
        queue = BoundedQueue(maxsize=10)
        
        await queue.put("test_item")
        item = await queue.get()
        
        assert item == "test_item"
        assert queue.qsize() == 0
        assert queue.stats.items_get == 1
    
    @pytest.mark.asyncio
    async def test_get_multiple_items_fifo(self):
        """Test that get() retrieves items in FIFO order."""
        queue = BoundedQueue(maxsize=10)
        
        # Put items
        for i in range(5):
            await queue.put(f"item_{i}")
        
        # Get items - should be in FIFO order
        items = []
        for _ in range(5):
            items.append(await queue.get())
        
        assert items == ["item_0", "item_1", "item_2", "item_3", "item_4"]
        assert queue.empty()
    
    @pytest.mark.asyncio
    async def test_get_blocks_when_empty(self):
        """Test that get() blocks when queue is empty."""
        queue = BoundedQueue(maxsize=10)
        
        # Try to get from empty queue
        get_task = asyncio.create_task(queue.get())
        
        # Give it a moment to block
        await asyncio.sleep(0.1)
        
        # Task should not be done (still waiting)
        assert not get_task.done()
        
        # Put an item to unblock
        await queue.put("test_item")
        
        # Now the get should complete
        item = await asyncio.wait_for(get_task, timeout=1.0)
        
        assert item == "test_item"
    
    @pytest.mark.asyncio
    async def test_get_with_timeout(self):
        """Test get() with timeout when queue is empty."""
        queue = BoundedQueue(maxsize=10)
        
        # Try to get with timeout (should timeout)
        item = await queue.get(timeout=0.1)
        
        assert item is None  # Timeout occurred
    
    @pytest.mark.asyncio
    async def test_get_tracks_wait_times(self):
        """Test that get() tracks wait time statistics."""
        queue = BoundedQueue(maxsize=10)
        
        await queue.put("item_1")
        await queue.get()
        
        wait_stats = queue.get_wait_time_stats()
        
        assert wait_stats["count"] == 1
        assert wait_stats["avg_ms"] >= 0
        assert wait_stats["max_ms"] >= 0
        assert wait_stats["min_ms"] >= 0


class TestBoundedQueuePoisonPills:
    """Test poison pill pattern for graceful shutdown."""
    
    @pytest.mark.asyncio
    async def test_put_poison_pills(self):
        """Test putting poison pills for worker shutdown."""
        queue = BoundedQueue(maxsize=10)
        worker_count = 3
        
        await queue.put_poison_pills(worker_count)
        
        assert queue.qsize() == worker_count
        
        # Verify all items are None (poison pills)
        for _ in range(worker_count):
            item = await queue.get()
            assert item is None
    
    @pytest.mark.asyncio
    async def test_workers_stop_on_poison_pill(self):
        """Test that workers can detect and stop on poison pills."""
        queue = BoundedQueue(maxsize=10)
        
        # Put some regular items and a poison pill
        await queue.put("item_1")
        await queue.put("item_2")
        await queue.put(None)  # Poison pill
        
        # Simulate worker behavior
        items = []
        while True:
            item = await queue.get()
            if item is None:  # Poison pill received
                break
            items.append(item)
        
        assert items == ["item_1", "item_2"]
        assert queue.empty()


class TestBoundedQueueStatistics:
    """Test queue statistics tracking."""
    
    @pytest.mark.asyncio
    async def test_queue_tracks_items_put(self):
        """Test that queue tracks total items put."""
        queue = BoundedQueue(maxsize=10)
        
        for i in range(5):
            await queue.put(f"item_{i}")
        
        assert queue.stats.items_put == 5
    
    @pytest.mark.asyncio
    async def test_queue_tracks_items_get(self):
        """Test that queue tracks total items retrieved."""
        queue = BoundedQueue(maxsize=10)
        
        for i in range(5):
            await queue.put(f"item_{i}")
        
        for _ in range(5):
            await queue.get()
        
        assert queue.stats.items_get == 5
    
    @pytest.mark.asyncio
    async def test_queue_tracks_wait_time(self):
        """Test that queue tracks total wait time."""
        queue = BoundedQueue(maxsize=10)
        
        await queue.put("item_1")
        await queue.get()
        
        assert queue.stats.total_wait_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_reset_stats(self):
        """Test that queue statistics can be reset."""
        queue = BoundedQueue(maxsize=10)
        
        # Generate some stats
        await queue.put("item_1")
        await queue.get()
        
        # Reset stats
        queue.reset_stats()
        
        assert queue.stats.items_put == 0
        assert queue.stats.items_get == 0
        assert queue.stats.total_wait_time_ms == 0.0
        assert queue.get_wait_time_stats()["count"] == 0


class TestBoundedQueueSizeConstraints:
    """Test that queue size never exceeds maxsize."""
    
    @pytest.mark.asyncio
    async def test_queue_size_never_exceeds_maxsize(self):
        """Test that queue size is always <= maxsize."""
        maxsize = 5
        queue = BoundedQueue(maxsize=maxsize)
        
        # Fill the queue
        for i in range(maxsize):
            await queue.put(f"item_{i}")
        
        assert queue.qsize() <= maxsize
        assert queue.full()
    
    @pytest.mark.asyncio
    async def test_concurrent_put_get_maintains_size_constraint(self):
        """Test that concurrent operations maintain size constraints."""
        maxsize = 10
        queue = BoundedQueue(maxsize=maxsize)
        
        async def producer():
            for i in range(20):
                await queue.put(f"item_{i}")
                await asyncio.sleep(0.01)
        
        async def consumer():
            for _ in range(20):
                await queue.get()
                await asyncio.sleep(0.02)
        
        # Run producer and consumer concurrently
        await asyncio.gather(
            producer(),
            consumer()
        )
        
        # Queue should be empty at the end
        assert queue.empty()
        assert queue.stats.items_put == 20
        assert queue.stats.items_get == 20
    
    @pytest.mark.asyncio
    async def test_qsize_accuracy(self):
        """Test that qsize() returns accurate count."""
        queue = BoundedQueue(maxsize=10)
        
        # Empty queue
        assert queue.qsize() == 0
        
        # Add items
        await queue.put("item_1")
        assert queue.qsize() == 1
        
        await queue.put("item_2")
        assert queue.qsize() == 2
        
        # Remove item
        await queue.get()
        assert queue.qsize() == 1


class TestAsyncJobQueue:
    """Test AsyncJobQueue (type-specific bounded queue)."""
    
    def test_async_job_queue_initialization(self):
        """Test that AsyncJobQueue initializes correctly."""
        queue = AsyncJobQueue(maxsize=50)
        
        assert queue.maxsize == 50
        assert queue.empty()
    
    @pytest.mark.asyncio
    async def test_async_job_queue_with_job_context(self):
        """Test AsyncJobQueue with JobContext objects."""
        queue = AsyncJobQueue(maxsize=10)
        
        job = JobContext(
            job_id="job-123",
            title="Software Engineer",
            company="Tech Corp",
            description="A" * 50,
            url="https://example.com/job",
            source="indeed",
        )
        
        await queue.put(job)
        retrieved_job = await queue.get()
        
        assert retrieved_job.job_id == "job-123"
        assert retrieved_job.title == "Software Engineer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
