from __future__ import annotations

import asyncio
import functools
import random
import time
import threading
from datetime import datetime, date
from typing import Dict, Any, Optional, Callable

DEFAULT_DAILY_LIMITS = {
    "follow": 20,
    "dm": 15,
    "like": 25,
    "reply": 10,
    "repost": 10,
}


class XRateLimiter:
    """
    Anti-ban rate limiter for X (Twitter) automated networking and engagement.
    Enforces per-minute token buckets, action pacing jitter, and daily rolling caps.
    """

    def __init__(self, rate_per_min: float = 12.0, burst: float = 3.0):
        self.rate = rate_per_min / 60.0  # tokens per second
        self.capacity = burst
        self.tokens = burst
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._daily_counts: Dict[str, Dict[str, int]] = {}  # "YYYY-MM-DD" -> {action: count}

    def _get_today_key(self) -> str:
        return date.today().isoformat()

    def check_daily_limit(self, action_type: str) -> bool:
        """Returns True if the action is within safe daily limits."""
        today = self._get_today_key()
        max_allowed = DEFAULT_DAILY_LIMITS.get(action_type, 20)
        with self._lock:
            day_stats = self._daily_counts.setdefault(today, {})
            current = day_stats.get(action_type, 0)
            return current < max_allowed

    def record_daily_action(self, action_type: str) -> int:
        """Increments the daily counter for a given action."""
        today = self._get_today_key()
        with self._lock:
            day_stats = self._daily_counts.setdefault(today, {})
            day_stats[action_type] = day_stats.get(action_type, 0) + 1
            return day_stats[action_type]

    def get_daily_usage(self) -> Dict[str, Any]:
        """Returns current daily usage vs limits."""
        today = self._get_today_key()
        with self._lock:
            day_stats = self._daily_counts.setdefault(today, {})
            usage = {}
            for act, limit in DEFAULT_DAILY_LIMITS.items():
                used = day_stats.get(act, 0)
                usage[act] = {
                    "used": used,
                    "limit": limit,
                    "remaining": max(0, limit - used),
                }
            return usage

    def allow(self, tokens: float = 1.0) -> bool:
        """Token bucket check."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def acquire(self, tokens: float = 1.0, max_wait: float = 10.0) -> None:
        """Synchronously waits until a token is available."""
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            if self.allow(tokens):
                # Add human jitter between 0.2s and 0.5s in local testing
                time.sleep(random.uniform(0.1, 0.3))
                return
            time.sleep(0.1)
        raise TimeoutError("X Rate limiter timeout exceeded")

    async def async_acquire(self, tokens: float = 1.0, max_wait: float = 10.0) -> None:
        """Asynchronously waits until a token is available."""
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            if self.allow(tokens):
                await asyncio.sleep(random.uniform(0.1, 0.3))
                return
            await asyncio.sleep(0.1)
        raise TimeoutError("X Rate limiter timeout exceeded")


default_x_limiter = XRateLimiter()
