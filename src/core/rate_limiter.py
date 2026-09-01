"""
Core Utility: TokenBucketRateLimiter
Provides O(1) rate limiting per target domain / host with thread safety.
"""
import asyncio
import time
from typing import Dict


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter ensuring external API calls adhere to concurrency caps.

    Time Complexity:
        acquire(): O(1)
    Space Complexity:
        O(H) where H is the number of distinct hostnames tracked.
    """

    def __init__(self, rate: float = 5.0, capacity: float = 10.0):
        self.rate = rate
        self.capacity = capacity
        self._tokens: Dict[str, float] = {}
        self._last_updated: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str = "default") -> None:
        """
        Wait until a token is available for the given key.

        Time Complexity: O(1) average time.
        """
        async with self._lock:
            now = time.monotonic()
            last = self._last_updated.get(key, now)
            elapsed = max(0.0, now - last)
            self._last_updated[key] = now

            tokens = self._tokens.get(key, self.capacity)
            tokens = min(self.capacity, tokens + elapsed * self.rate)

            if tokens < 1.0:
                sleep_time = (1.0 - tokens) / self.rate
                await asyncio.sleep(sleep_time)
                tokens = 0.0
            else:
                tokens -= 1.0

            self._tokens[key] = tokens
