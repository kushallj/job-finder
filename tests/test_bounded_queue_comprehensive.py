"""
Comprehensive tests for BoundedQueue to achieve 100% coverage.
Tests all edge cases, error paths, and the new lazy initialization.
"""

import asyncio
import pytest
from src.async_pipeline.bounded_queue import BoundedQueue, AsyncJobQueue
from src.async_pipeline.types import QueueStats


class TestBoundedQueueLazyInit:
    """Test lazy queue initialization."""
    
    @pytest.mark.asyncio
    async def test_queue_created_lazily_on_first_put(self):
        """Queue should be created when first put() is called."""
        queue = BoundedQueue(maxsize=5)
        assert queue._queue is None  # Not created yet
        
        await queue.put("item1")
        assert queue._queue is not None  # Now created
        assert await queue.get() == "item1"
    
    @pytest.mark.asyncio
    async def test_queue_created_lazily_on_first_get(self):
        """Queue should be created when first get() is called."""
        queue = BoundedQueue(maxsize=5)
        assert queue._queue is None
        
        # Put an item to have something to get
        await queue.put("item")
        
        # Get should work
        item = await queue.get()
        assert item == "item"
        assert queue._queue is not None
    
    @pytest.mark.asyncio
    async def test_ensure_queue_called_multiple_times(self):
        """_ensure_queue should be idempotent."""
        queue = BoundedQueue(maxsize=5)
        
        # Call multiple times
        queue._ensure_queue()
        first_queue = queue._queue
        
        queue._ensure_queue()
        second_queue = queue._queue
        
        # Should be the same queue instance
        assert first_queue is second_queue
    
    @pytest.mark.asyncio
    async def test_qsize_with_lazy_init(self):
        """qsize() should trigger queue creation."""
        queue = BoundedQueue(maxsize=5)
        assert queue._queue is None
        
        size = queue.qsize()
        assert size == 0
        assert queue._queue is not None
    
    @pytest.mark.asyncio
    async def test_empty_with_lazy_init(self):
        """empty() should trigger queue creation."""
        queue = BoundedQueue(maxsize=5)
        assert queue._queue is None
        
        is_empty = queue.empty()
        assert is_empty is True
        assert queue._queue is not None
    
    @pytest.mark.asyncio
    async def test_full_with_lazy_init(self):
        """full() should trigger queue creation."""
        queue = BoundedQueue(maxsize=2)
        assert queue._queue is None
        
        is_full = queue.full()
        assert is_full is False
        assert queue._queue is not None


class TestBoundedQueueStats:
    """Test queue statistics tracking."""
    
    @pytest.mark.asyncio
    async def test_stats_items_put_count(self):
        """Stats should track number of items put."""
        queue = BoundedQueue(maxsize=10)
        
        await queue.put("item1")
        await queue.put("item2")
        await queue.put("item3")
        
        assert queue.stats.items_put == 3
    
    @pytest.mark.asyncio
    async def test_stats_items_get_count(self):
        """Stats should track number of items retrieved."""
        queue = BoundedQueue(maxsize=10)
        
        await queue.put("item1")
        await queue.put("item2")
        
        await queue.get()
        await queue.get()
        
        assert queue.stats.items_get == 2
    
    @pytest.mark.asyncio
    async def test_stats_backpressure_events(self):
        """Stats should track backpressure events."""
        queue = BoundedQueue(maxsize=2)
        
        # Fill the queue
        await queue.put("item1")
        await queue.put("item2")
        
        # This should trigger backpressure
        async def put_when_full():
            await queue.put("item3")
        
        # Start put and let it block briefly
        task = asyncio.create_task(put_when_full())
        await asyncio.sleep(0.1)
        
        # Consume an item to make space
        await queue.get()
        
        # Wait for put to complete
        await task
        
        # Should have recorded backpressure
        assert queue.stats.backpressure_events >= 1
    
    @pytest.mark.asyncio
    async def test_get_wait_time_stats(self):
        """Should track get wait times."""
        queue = BoundedQueue(maxsize=10)
        
        await queue.put("item1")
        await queue.get()
        
        stats = queue.get_wait_time_stats()
        assert stats["count"] == 1
        assert stats["avg_ms"] >= 0
        assert stats["max_ms"] >= 0
        assert stats["min_ms"] >= 0
    
    @pytest.mark.asyncio
    async def test_get_wait_time_stats_empty(self):
        """Stats should handle case when no gets have occurred."""
        queue = BoundedQueue(maxsize=10)
        
        stats = queue.get_wait_time_stats()
        assert stats["count"] == 0
        assert stats["avg_ms"] == 0
        assert stats["max_ms"] == 0
        assert stats["min_ms"] == 0
    
    @pytest.mark.asyncio
    async def test_reset_stats(self):
        """Should reset all statistics."""
        queue = BoundedQueue(maxsize=10)
        
        await queue.put("item1")
        await queue.get()
        
        assert queue.stats.items_put > 0
        assert queue.stats.items_get > 0
        
        queue.reset_stats()
        
        assert queue.stats.items_put == 0
        assert queue.stats.items_get == 0
    
    @pytest.mark.asyncio
    async def test_custom_stats_object(self):
        """Should accept custom QueueStats object."""
        custom_stats = QueueStats()
        custom_stats.items_put = 100
        
        queue = BoundedQueue(maxsize=10, stats=custom_stats)
        
        assert queue.stats.items_put == 100


class TestBoundedQueueTimeouts:
    """Test timeout functionality."""
    
    @pytest.mark.asyncio
    async def test_put_with_timeout_success(self):
        """put() should succeed within timeout."""
        queue = BoundedQueue(maxsize=10)
        
        result = await queue.put("item", timeout=1.0)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_put_with_timeout_failure(self):
        """put() should return False on timeout."""
        queue = BoundedQueue(maxsize=1)
        
        # Fill the queue
        await queue.put("item1")
        
        # Try to put with short timeout (should fail)
        result = await queue.put("item2", timeout=0.1)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_with_timeout_success(self):
        """get() should succeed within timeout."""
        queue = BoundedQueue(maxsize=10)
        
        await queue.put("item")
        result = await queue.get(timeout=1.0)
        assert result == "item"
    
    @pytest.mark.asyncio
    async def test_get_with_timeout_failure(self):
        """get() should return None on timeout."""
        queue = BoundedQueue(maxsize=10)
        
        # Try to get from empty queue with short timeout
        result = await queue.get(timeout=0.1)
        assert result is None


class TestBoundedQueuePoisonPills:
    """Test poison pill functionality."""
    
    @pytest.mark.asyncio
    async def test_put_poison_pills_creates_queue(self):
        """put_poison_pills should create queue if not exists."""
        queue = BoundedQueue(maxsize=10)
        assert queue._queue is None
        
        await queue.put_poison_pills(3)
        assert queue._queue is not None
    
    @pytest.mark.asyncio
    async def test_put_poison_pills_correct_count(self):
        """Should put exactly the specified number of poison pills."""
        queue = BoundedQueue(maxsize=10)
        worker_count = 5
        
        await queue.put_poison_pills(worker_count)
        
        # Verify we can get exactly worker_count None values
        for _ in range(worker_count):
            item = await queue.get()
            assert item is None
        
        # Queue should be empty now
        assert queue.empty()
    
    @pytest.mark.asyncio
    async def test_poison_pills_with_regular_items(self):
        """Poison pills should work alongside regular items."""
        queue = BoundedQueue(maxsize=10)
        
        # Add some regular items
        await queue.put("item1")
        await queue.put("item2")
        
        # Add poison pills
        await queue.put_poison_pills(2)
        
        # Should get items in order
        assert await queue.get() == "item1"
        assert await queue.get() == "item2"
        assert await queue.get() is None
        assert await queue.get() is None


class TestBoundedQueueEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_negative_maxsize_raises_error(self):
        """Negative maxsize should raise ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            BoundedQueue(maxsize=-1)
    
    def test_zero_maxsize_creates_unbounded_queue(self):
        """Maxsize of 0 should create unbounded queue."""
        queue = BoundedQueue(maxsize=0)
        assert queue.maxsize == 0
    
    @pytest.mark.asyncio
    async def test_maxsize_property(self):
        """Should return correct maxsize."""
        queue = BoundedQueue(maxsize=42)
        assert queue.maxsize == 42
    
    @pytest.mark.asyncio
    async def test_stats_property(self):
        """Should return stats object."""
        queue = BoundedQueue(maxsize=10)
        assert isinstance(queue.stats, QueueStats)
    
    @pytest.mark.asyncio
    async def test_qsize_after_operations(self):
        """qsize should reflect actual queue size."""
        queue = BoundedQueue(maxsize=10)
        
        assert queue.qsize() == 0
        
        await queue.put("item1")
        assert queue.qsize() == 1
        
        await queue.put("item2")
        assert queue.qsize() == 2
        
        await queue.get()
        assert queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_empty_transitions(self):
        """empty() should correctly transition."""
        queue = BoundedQueue(maxsize=10)
        
        assert queue.empty() is True
        
        await queue.put("item")
        assert queue.empty() is False
        
        await queue.get()
        assert queue.empty() is True
    
    @pytest.mark.asyncio
    async def test_full_transitions(self):
        """full() should correctly transition."""
        queue = BoundedQueue(maxsize=2)
        
        assert queue.full() is False
        
        await queue.put("item1")
        assert queue.full() is False
        
        await queue.put("item2")
        assert queue.full() is True
        
        await queue.get()
        assert queue.full() is False


class TestAsyncJobQueue:
    """Test AsyncJobQueue type-specific queue."""
    
    @pytest.mark.asyncio
    async def test_async_job_queue_creation(self):
        """Should create AsyncJobQueue successfully."""
        queue = AsyncJobQueue(maxsize=100)
        assert isinstance(queue, BoundedQueue)
        assert queue.maxsize == 100
    
    @pytest.mark.asyncio
    async def test_async_job_queue_default_maxsize(self):
        """Should use default maxsize of 100."""
        queue = AsyncJobQueue()
        assert queue.maxsize == 100
    
    @pytest.mark.asyncio
    async def test_async_job_queue_operations(self):
        """Should support all queue operations."""
        queue = AsyncJobQueue(maxsize=10)
        
        # Mock job object
        job = {"job_id": "test-123", "title": "Test Job"}
        
        await queue.put(job)
        retrieved = await queue.get()
        
        assert retrieved == job


class TestBoundedQueueConcurrency:
    """Test concurrent access patterns."""
    
    @pytest.mark.asyncio
    async def test_concurrent_puts(self):
        """Should handle concurrent puts correctly."""
        queue = BoundedQueue(maxsize=100)
        
        async def put_items(start, count):
            for i in range(start, start + count):
                await queue.put(f"item-{i}")
        
        # Put items concurrently
        await asyncio.gather(
            put_items(0, 10),
            put_items(10, 10),
            put_items(20, 10),
        )
        
        assert queue.qsize() == 30
    
    @pytest.mark.asyncio
    async def test_concurrent_gets(self):
        """Should handle concurrent gets correctly."""
        queue = BoundedQueue(maxsize=100)
        
        # Fill queue
        for i in range(20):
            await queue.put(f"item-{i}")
        
        async def get_items(count):
            items = []
            for _ in range(count):
                item = await queue.get()
                items.append(item)
            return items
        
        # Get items concurrently
        results = await asyncio.gather(
            get_items(5),
            get_items(5),
            get_items(5),
        )
        
        # Should have retrieved 15 items total
        all_items = [item for sublist in results for item in sublist]
        assert len(all_items) == 15
        assert queue.qsize() == 5
    
    @pytest.mark.asyncio
    async def test_producer_consumer_pattern(self):
        """Should support classic producer-consumer pattern."""
        queue = BoundedQueue(maxsize=10)
        produced = []
        consumed = []
        
        async def producer(count):
            for i in range(count):
                item = f"item-{i}"
                produced.append(item)
                await queue.put(item)
                await asyncio.sleep(0.01)
        
        async def consumer(count):
            for _ in range(count):
                item = await queue.get()
                consumed.append(item)
                await asyncio.sleep(0.01)
        
        # Run producer and consumer concurrently
        await asyncio.gather(
            producer(10),
            consumer(10),
        )
        
        assert len(produced) == 10
        assert len(consumed) == 10
        assert set(produced) == set(consumed)
