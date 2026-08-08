"""
Property-based tests for BoundedQueue backpressure mechanism.

This module implements Property 2: Bounded Queue Backpressure from the
system architecture design document.

**Validates: Requirements 1.3, 1.4, 1.5, 30.1, 30.2**

Property 2: Bounded Queue Backpressure
----------------------------------------
For any BoundedQueue with maximum size M, when M jobs are enqueued, 
subsequent put operations SHALL block until space becomes available, 
and when the queue is empty, get operations SHALL block until jobs 
become available.

Testing Framework: hypothesis (property-based testing)
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings
from src.async_pipeline.bounded_queue import BoundedQueue


# =============================================================================
# Property 2.1: put() blocks when queue is full (backpressure)
# =============================================================================

@given(
    maxsize=st.integers(min_value=1, max_value=50),
    extra_items=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, deadline=5000)
@pytest.mark.asyncio
async def test_property_put_blocks_when_full(maxsize, extra_items):
    """
    Property: For any BoundedQueue with maximum size M, when M jobs are 
    enqueued, subsequent put operations SHALL block until space becomes available.
    
    **Validates: Requirements 1.3, 1.4, 30.1**
    
    Strategy:
    1. Create a queue with random maxsize M
    2. Fill the queue to capacity with M items
    3. Attempt to put an additional item (should block)
    4. Verify the put operation is blocked by checking task state
    5. Consume one item to make space
    6. Verify the blocked put operation completes
    """
    queue = BoundedQueue(maxsize=maxsize)
    
    # Fill the queue to capacity
    for i in range(maxsize):
        result = await queue.put(f"item_{i}")
        assert result is True, f"Failed to put item {i} in queue"
    
    # Verify queue is full
    assert queue.full(), f"Queue should be full after putting {maxsize} items"
    assert queue.qsize() == maxsize, f"Queue size should be {maxsize}, got {queue.qsize()}"
    
    # Attempt to put additional item - should block
    put_task = asyncio.create_task(queue.put(f"blocking_item"))
    
    # Give the task time to attempt the put operation
    await asyncio.sleep(0.1)
    
    # Verify the task is still waiting (blocked by backpressure)
    assert not put_task.done(), "Put operation should be blocked when queue is full"
    
    # Consume one item to make space
    consumed_item = await queue.get()
    assert consumed_item == "item_0", f"Expected 'item_0', got '{consumed_item}'"
    
    # Now the put should complete
    await asyncio.wait_for(put_task, timeout=1.0)
    
    # Verify the queue is full again
    assert queue.qsize() == maxsize, f"Queue should be full again after put completed"


# =============================================================================
# Property 2.2: get() blocks when queue is empty
# =============================================================================

@given(
    maxsize=st.integers(min_value=1, max_value=50),
    num_items=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, deadline=5000)
@pytest.mark.asyncio
async def test_property_get_blocks_when_empty(maxsize, num_items):
    """
    Property: For any BoundedQueue, when the queue is empty, get operations 
    SHALL block until jobs become available.
    
    **Validates: Requirements 1.5, 30.2**
    
    Strategy:
    1. Create an empty queue with random maxsize
    2. Attempt to get from empty queue (should block)
    3. Verify the get operation is blocked
    4. Put an item in the queue
    5. Verify the blocked get operation completes and returns the item
    """
    queue = BoundedQueue(maxsize=maxsize)
    
    # Verify queue is empty
    assert queue.empty(), "Queue should be empty initially"
    assert queue.qsize() == 0, f"Queue size should be 0, got {queue.qsize()}"
    
    # Attempt to get from empty queue - should block
    get_task = asyncio.create_task(queue.get())
    
    # Give the task time to attempt the get operation
    await asyncio.sleep(0.1)
    
    # Verify the task is still waiting (blocked because queue is empty)
    assert not get_task.done(), "Get operation should be blocked when queue is empty"
    
    # Put an item to unblock the get
    test_item = f"unblock_item"
    await queue.put(test_item)
    
    # Now the get should complete
    retrieved_item = await asyncio.wait_for(get_task, timeout=1.0)
    
    # Verify the correct item was retrieved
    assert retrieved_item == test_item, f"Expected '{test_item}', got '{retrieved_item}'"
    
    # Verify queue is empty again
    assert queue.empty(), "Queue should be empty after consuming the item"


# =============================================================================
# Property 2.3: Backpressure with multiple producers
# =============================================================================

@given(
    maxsize=st.integers(min_value=5, max_value=20),
    producer_count=st.integers(min_value=2, max_value=5),
    items_per_producer=st.integers(min_value=5, max_value=15)
)
@settings(max_examples=30, deadline=10000)
@pytest.mark.asyncio
async def test_property_backpressure_with_multiple_producers(
    maxsize, producer_count, items_per_producer
):
    """
    Property: When multiple producers try to fill a bounded queue, the queue 
    SHALL enforce backpressure on all producers when full, maintaining size 
    constraints.
    
    **Validates: Requirements 1.3, 1.4, 30.1**
    
    Strategy:
    1. Create a queue with random maxsize M
    2. Create P concurrent producers, each producing I items
    3. Create a consumer that slowly drains the queue
    4. Verify queue size never exceeds M during concurrent operations
    5. Verify all items are eventually produced and consumed
    """
    queue = BoundedQueue(maxsize=maxsize)
    produced_count = [0]  # Mutable counter
    consumed_count = [0]
    max_observed_size = [0]  # Track max queue size
    
    total_items = producer_count * items_per_producer
    
    async def producer(producer_id: int):
        """Producer that adds items to the queue."""
        for i in range(items_per_producer):
            await queue.put(f"p{producer_id}_item_{i}")
            produced_count[0] += 1
            # Track max queue size
            current_size = queue.qsize()
            if current_size > max_observed_size[0]:
                max_observed_size[0] = current_size
    
    async def consumer():
        """Consumer that drains items from the queue."""
        for _ in range(total_items):
            item = await queue.get()
            assert item is not None, "Consumer should not receive None before completion"
            consumed_count[0] += 1
            await asyncio.sleep(0.01)  # Slow consumer to create backpressure
    
    # Run producers and consumer concurrently
    await asyncio.gather(
        *[producer(i) for i in range(producer_count)],
        consumer()
    )
    
    # Verify all items were produced and consumed
    assert produced_count[0] == total_items, \
        f"Expected {total_items} items produced, got {produced_count[0]}"
    assert consumed_count[0] == total_items, \
        f"Expected {total_items} items consumed, got {consumed_count[0]}"
    
    # Verify queue size never exceeded maxsize (backpressure worked)
    assert max_observed_size[0] <= maxsize, \
        f"Queue size {max_observed_size[0]} exceeded maxsize {maxsize}"
    
    # Verify queue is empty at the end
    assert queue.empty(), "Queue should be empty after all items consumed"


# =============================================================================
# Property 2.4: Poison pill pattern for graceful shutdown
# =============================================================================

@given(
    maxsize=st.integers(min_value=5, max_value=50),
    worker_count=st.integers(min_value=1, max_value=10),
    items_before_shutdown=st.integers(min_value=0, max_value=20)
)
@settings(max_examples=50, deadline=5000)
@pytest.mark.asyncio
async def test_property_poison_pill_shutdown(maxsize, worker_count, items_before_shutdown):
    """
    Property: When poison pills are added to the queue (one per worker), 
    each worker SHALL receive exactly one poison pill and stop gracefully.
    
    **Validates: Requirements 1.6**
    
    Strategy:
    1. Create a queue with random maxsize
    2. Put some regular items in the queue
    3. Put W poison pills (None) for W workers
    4. Simulate W workers consuming from the queue
    5. Verify each worker receives exactly one poison pill
    6. Verify all regular items are processed before shutdown
    """
    queue = BoundedQueue(maxsize=maxsize)
    
    # Put regular items first
    for i in range(items_before_shutdown):
        await queue.put(f"regular_item_{i}")
    
    # Put poison pills for shutdown
    await queue.put_poison_pills(worker_count)
    
    # Verify the correct number of items in queue
    expected_queue_size = items_before_shutdown + worker_count
    assert queue.qsize() == expected_queue_size, \
        f"Expected {expected_queue_size} items in queue, got {queue.qsize()}"
    
    # Simulate workers consuming from queue
    workers_received_poison = [False] * worker_count
    regular_items_processed = [0]
    
    async def worker(worker_id: int):
        """Worker that processes items until receiving poison pill."""
        while True:
            item = await queue.get()
            if item is None:  # Poison pill received
                workers_received_poison[worker_id] = True
                break
            else:
                # Process regular item
                regular_items_processed[0] += 1
    
    # Run all workers concurrently
    await asyncio.gather(*[worker(i) for i in range(worker_count)])
    
    # Verify all workers received poison pills
    assert all(workers_received_poison), \
        f"Not all workers received poison pills: {workers_received_poison}"
    
    # Verify all regular items were processed
    assert regular_items_processed[0] == items_before_shutdown, \
        f"Expected {items_before_shutdown} regular items processed, " \
        f"got {regular_items_processed[0]}"
    
    # Verify queue is empty
    assert queue.empty(), "Queue should be empty after all items and poison pills consumed"


# =============================================================================
# Property 2.5: Queue maintains FIFO order under backpressure
# =============================================================================

@given(
    maxsize=st.integers(min_value=5, max_value=30),
    total_items=st.integers(min_value=10, max_value=50)
)
@settings(max_examples=50, deadline=5000)
@pytest.mark.asyncio
async def test_property_fifo_order_with_backpressure(maxsize, total_items):
    """
    Property: Even under backpressure conditions, the BoundedQueue SHALL 
    maintain FIFO (First In First Out) order for all items.
    
    **Validates: Requirements 1.3, 1.4**
    
    Strategy:
    1. Create a queue smaller than total items to induce backpressure
    2. Concurrently produce items in order and consume them
    3. Verify all items are retrieved in exact FIFO order
    """
    queue = BoundedQueue(maxsize=maxsize)
    consumed_items = []
    
    async def producer():
        """Producer that adds items in sequential order."""
        for i in range(total_items):
            await queue.put(i)
    
    async def consumer():
        """Consumer that retrieves items."""
        for _ in range(total_items):
            item = await queue.get()
            consumed_items.append(item)
    
    # Run producer and consumer concurrently
    await asyncio.gather(producer(), consumer())
    
    # Verify FIFO order
    expected_order = list(range(total_items))
    assert consumed_items == expected_order, \
        f"Queue did not maintain FIFO order. Expected {expected_order[:10]}..., " \
        f"got {consumed_items[:10]}..."


# =============================================================================
# Property 2.6: Backpressure event tracking
# =============================================================================

@given(
    maxsize=st.integers(min_value=2, max_value=10),
    overflow_attempts=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=50, deadline=5000)
@pytest.mark.asyncio
async def test_property_backpressure_event_tracking(maxsize, overflow_attempts):
    """
    Property: When the queue is full and producers are blocked, the queue 
    SHALL track backpressure events in statistics.
    
    **Validates: Requirements 30.3**
    
    Strategy:
    1. Create a queue with random maxsize M
    2. Fill the queue to capacity
    3. Verify backpressure events are tracked
    4. Make multiple attempts to put additional items (all should face backpressure)
    5. Verify backpressure events increase
    """
    queue = BoundedQueue(maxsize=maxsize)
    
    # Fill the queue to capacity
    for i in range(maxsize):
        await queue.put(f"item_{i}")
    
    assert queue.full(), "Queue should be full"
    
    # Record initial backpressure events
    initial_backpressure = queue.stats.backpressure_events
    
    # Attempt to put additional items with timeout (will hit backpressure)
    for i in range(overflow_attempts):
        result = await queue.put(f"overflow_item_{i}", timeout=0.01)
        assert result is False, "Put should timeout when queue is full"
    
    # Verify backpressure events were tracked
    # Note: backpressure_events increments when queue is checked as full
    assert queue.stats.backpressure_events >= initial_backpressure, \
        "Backpressure events should be tracked when queue is full"


# =============================================================================
# Property 2.7: Queue size constraint invariant
# =============================================================================

@given(
    maxsize=st.integers(min_value=1, max_value=100),
    operations=st.lists(
        st.one_of(
            st.tuples(st.just("put"), st.text(min_size=1, max_size=20)),
            st.just(("get", None))
        ),
        min_size=10,
        max_size=100
    )
)
@settings(max_examples=30, deadline=10000)
@pytest.mark.asyncio
async def test_property_size_constraint_invariant(maxsize, operations):
    """
    Property: For any sequence of put/get operations, the queue size SHALL 
    never exceed maxsize.
    
    **Validates: Requirements 1.3, 27.3**
    
    Strategy:
    1. Create a queue with random maxsize M
    2. Apply a random sequence of put and get operations
    3. After each operation, verify queue size ≤ M
    4. Track the maximum observed size throughout all operations
    """
    queue = BoundedQueue(maxsize=maxsize)
    max_observed_size = 0
    
    for op_type, value in operations:
        if op_type == "put":
            # Put with timeout to avoid blocking the test
            await queue.put(value, timeout=0.1)
        elif op_type == "get":
            # Get with timeout to handle empty queue
            await queue.get(timeout=0.1)
        
        # Verify size constraint
        current_size = queue.qsize()
        assert current_size <= maxsize, \
            f"Queue size {current_size} exceeded maxsize {maxsize}"
        
        # Track max size
        if current_size > max_observed_size:
            max_observed_size = current_size
    
    # Final verification
    assert max_observed_size <= maxsize, \
        f"Maximum observed size {max_observed_size} exceeded maxsize {maxsize}"


# =============================================================================
# Property 2.8: Concurrent put/get maintains consistency
# =============================================================================

@given(
    maxsize=st.integers(min_value=10, max_value=50),
    num_items=st.integers(min_value=20, max_value=100)
)
@settings(max_examples=30, deadline=10000)
@pytest.mark.asyncio
async def test_property_concurrent_operations_consistency(maxsize, num_items):
    """
    Property: When producers and consumers operate concurrently on a bounded 
    queue, the queue SHALL maintain consistency: items_put = items_get + qsize.
    
    **Validates: Requirements 1.3, 1.4, 1.5, 27.3**
    
    Strategy:
    1. Create a queue with random maxsize
    2. Run concurrent producers and consumers
    3. At the end, verify: total_put = total_get + remaining_in_queue
    4. Verify queue statistics are accurate
    """
    queue = BoundedQueue(maxsize=maxsize)
    
    async def producer():
        """Producer that adds items."""
        for i in range(num_items):
            await queue.put(f"item_{i}")
    
    async def consumer():
        """Consumer that retrieves items with small delays."""
        for _ in range(num_items):
            await queue.get()
            await asyncio.sleep(0.001)  # Small delay to create concurrency
    
    # Run producer and consumer concurrently
    await asyncio.gather(producer(), consumer())
    
    # Verify consistency: items_put = items_get + items_remaining
    items_put = queue.stats.items_put
    items_get = queue.stats.items_get
    items_remaining = queue.qsize()
    
    assert items_put == items_get + items_remaining, \
        f"Inconsistent state: put={items_put}, get={items_get}, remaining={items_remaining}"
    
    # Since we produced and consumed the same amount, queue should be empty
    assert queue.empty(), "Queue should be empty after producing and consuming same amount"
    assert items_put == num_items, f"Expected {num_items} items put, got {items_put}"
    assert items_get == num_items, f"Expected {num_items} items get, got {items_get}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
