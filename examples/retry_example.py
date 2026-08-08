"""
Example demonstrating RetryManager usage with exponential backoff.

This script shows how to use the RetryManager to handle retries
for API calls with exponential backoff, jitter, and structured logging.
"""

import asyncio
import logging
from typing import Dict, Any

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.async_pipeline.retry import (
    RetryManager,
    retry_with_backoff,
    retry_on_api_error,
)
from src.async_pipeline.config import RetryConfig


async def example_1_basic_retry():
    """Example 1: Basic retry with RetryManager."""
    print("\n=== Example 1: Basic Retry ===")
    
    # Create retry manager with custom config
    config = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True,
    )
    manager = RetryManager(config)
    
    # Simulated flaky operation
    call_count = 0
    
    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        print(f"  Attempt {call_count}...")
        
        if call_count < 3:
            raise ValueError("Simulated temporary failure")
        
        return {"status": "success", "data": "Operation completed"}
    
    # Execute with retry
    try:
        result = await manager.execute_with_retry(flaky_operation)
        print(f"  ✓ Success: {result}")
        print(f"  Stats: {manager.stats.to_dict()}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")


async def example_2_decorator():
    """Example 2: Using retry decorator."""
    print("\n=== Example 2: Retry Decorator ===")
    
    call_count = 0
    
    @retry_with_backoff(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=True,
    )
    async def api_call(endpoint: str) -> Dict[str, Any]:
        nonlocal call_count
        call_count += 1
        print(f"  Calling {endpoint} (attempt {call_count})...")
        
        if call_count < 2:
            raise ConnectionError("Network error")
        
        return {"endpoint": endpoint, "status": 200, "data": "Success"}
    
    try:
        result = await api_call("/api/jobs")
        print(f"  ✓ Result: {result}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")


async def example_3_api_error_handling():
    """Example 3: API-specific error handling with retry."""
    print("\n=== Example 3: API Error Handling ===")
    
    import aiohttp
    
    call_count = 0
    
    @retry_on_api_error(max_attempts=3, base_delay=0.5, max_delay=5.0)
    async def call_external_api() -> Dict[str, Any]:
        nonlocal call_count
        call_count += 1
        print(f"  API call attempt {call_count}...")
        
        if call_count == 1:
            raise aiohttp.ClientError("Connection timeout")
        elif call_count == 2:
            raise asyncio.TimeoutError("Request timeout")
        
        return {"status": "ok", "message": "API call successful"}
    
    try:
        result = await call_external_api()
        print(f"  ✓ Result: {result}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")


async def example_4_exponential_backoff():
    """Example 4: Demonstrating exponential backoff calculation."""
    print("\n=== Example 4: Exponential Backoff ===")
    print("  Formula: delay = base_delay × (exponential_base ^ attempt)")
    print("  Config: base_delay=1.0, exponential_base=2.0, max_delay=60.0")
    
    config = RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=False,  # Disable jitter for predictable delays
    )
    manager = RetryManager(config)
    
    delays = []
    
    async def always_fails():
        raise ValueError("Test failure")
    
    # Capture delays by patching sleep
    original_sleep = asyncio.sleep
    
    async def capture_sleep(delay):
        delays.append(delay)
        # Don't actually sleep for the demo
    
    asyncio.sleep = capture_sleep
    
    try:
        await manager.execute_with_retry(always_fails)
    except ValueError:
        pass
    
    # Restore original sleep
    asyncio.sleep = original_sleep
    
    print("\n  Calculated delays:")
    for i, delay in enumerate(delays, 1):
        print(f"    Retry {i}: {delay:.2f} seconds (2^{i-1} = {2**(i-1)})")


async def example_5_jitter():
    """Example 5: Demonstrating jitter to prevent thundering herd."""
    print("\n=== Example 5: Jitter (Prevents Thundering Herd) ===")
    print("  Jitter adds random 0-1 second to each delay")
    print("  This prevents multiple clients from retrying simultaneously")
    
    config = RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True,
    )
    manager = RetryManager(config)
    
    delays = []
    
    async def always_fails():
        raise ValueError("Test failure")
    
    # Capture delays
    original_sleep = asyncio.sleep
    
    async def capture_sleep(delay):
        delays.append(delay)
    
    asyncio.sleep = capture_sleep
    
    try:
        await manager.execute_with_retry(always_fails)
    except ValueError:
        pass
    
    asyncio.sleep = original_sleep
    
    print("\n  Delays with jitter:")
    for i, delay in enumerate(delays, 1):
        base = 2.0 * (2.0 ** (i - 1))
        jitter = delay - base
        print(f"    Retry {i}: {delay:.2f}s (base: {base:.2f}s + jitter: {jitter:.2f}s)")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("RetryManager Examples - Exponential Backoff with Jitter")
    print("=" * 60)
    
    await example_1_basic_retry()
    await example_2_decorator()
    await example_3_api_error_handling()
    await example_4_exponential_backoff()
    await example_5_jitter()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
