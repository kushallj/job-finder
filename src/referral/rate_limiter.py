from __future__ import annotations

import time
import threading
import inspect
from typing import Callable, Optional, Any

try:
    import redis
except Exception:
    redis = None


class InMemoryTokenBucket:
    """Thread-safe in-memory token bucket rate limiter with monotonic clock refills."""
    def __init__(self, rate: float = 1.0, capacity: float = 1.0):
        assert rate > 0 and capacity > 0
        self.rate = float(rate)
        self.capacity = float(capacity)
        self._state: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def _refill(self, key: str) -> None:
        tokens, last = self._state.get(key, (self.capacity, self._now()))
        now = self._now()
        if now <= last:
            self._state[key] = (tokens, last)
            return
        new_tokens = min(self.capacity, tokens + (now - last) * self.rate)
        self._state[key] = (new_tokens, now)

    def allow(self, key: str = "global", tokens: float = 1.0) -> bool:
        """Check and consume tokens. Returns True if allowed, False otherwise."""
        if tokens <= 0:
            return True
        with self._lock:
            self._refill(key)
            available, last = self._state.get(key, (self.capacity, self._now()))
            if available >= tokens:
                self._state[key] = (available - tokens, last)
                return True
            return False

    def acquire(self, key: str = "global", tokens: float = 1.0, block: bool = True, timeout: Optional[float] = None) -> bool:
        if self.allow(key, tokens):
            return True
        if not block:
            return False
        deadline = None if timeout is None else (time.monotonic() + timeout)
        while True:
            remaining = None if deadline is None else (deadline - time.monotonic())
            if remaining is not None and remaining <= 0:
                return False
            sleep_for = min(0.1, max(1.0 / (self.rate or 1.0) / 4.0, 0.01))
            time.sleep(sleep_for)
            if self.allow(key, tokens):
                return True

    async def acquire_async(self, key: str = "global", tokens: float = 1.0, block: bool = True, timeout: Optional[float] = None) -> bool:
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.acquire, key, tokens, block, timeout)

    def wrap(self, key_fn: Optional[Callable[..., str]] = None, tokens: float = 1.0, block: bool = False, timeout: Optional[float] = None):
        def decorator(fn: Callable):
            def wrapper(*args, **kwargs):
                key = key_fn(*args, **kwargs) if key_fn else "global"
                if not self.acquire(key, tokens=tokens, block=block, timeout=timeout):
                    raise RuntimeError(f"Rate limit exceeded for key={key}")
                return fn(*args, **kwargs)

            async def async_wrapper(*args, **kwargs):
                key = key_fn(*args, **kwargs) if key_fn else "global"
                ok = await self.acquire_async(key, tokens=tokens, block=block, timeout=timeout)
                if not ok:
                    raise RuntimeError(f"Rate limit exceeded for key={key}")
                return await fn(*args, **kwargs)

            if inspect.iscoroutinefunction(fn):
                return async_wrapper
            return wrapper

        return decorator


class RedisFixedWindowLimiter:
    """Fixed-window rate limiter utilizing Redis INCR and EXPIRE."""
    def __init__(self, redis_client, key_prefix: str = "referral_rl", max_calls: int = 10, window_seconds: int = 60):
        if redis is None:
            raise RuntimeError("redis package not available")
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.max_calls = int(max_calls)
        self.window_seconds = int(window_seconds)

    def _key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def allow(self, key: str = "global") -> bool:
        k = self._key(key)
        try:
            cur = self.redis.incr(k)
            if cur == 1:
                self.redis.expire(k, self.window_seconds)
            return cur <= self.max_calls
        except Exception:
            return False


default_rate_limiter = InMemoryTokenBucket(rate=2.0, capacity=5.0)
