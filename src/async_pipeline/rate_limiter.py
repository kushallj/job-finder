"""
Rate limiter with token bucket algorithm for the async job pipeline.

This module provides rate limiting to prevent overwhelming external APIs
while allowing for bursty workloads.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from src.async_pipeline.types import RateLimiterStats

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token bucket rate limiter for async operations.
    
    Implements the token bucket algorithm to control the rate of operations.
    Supports burst capacity and automatic token refill.
    
    Example:
        # Limit to 10 requests per second
        rate_limiter = TokenBucket(rate=10.0)
        
        async def make_request():
            await rate_limiter.acquire()  # Blocks if rate limit reached
            await api.call()
    """
    
    def __init__(
        self,
        rate: float,
        capacity: Optional[int] = None,
        time_period: float = 1.0,
        stats: Optional[RateLimiterStats] = None,
    ):
        """
        Initialize the token bucket rate limiter.
        
        Args:
            rate: Number of tokens per time_period (e.g., 10.0 = 10 tokens per second).
            capacity: Maximum tokens in the bucket. Defaults to rate.
            time_period: Time period in seconds for token refill. Default 1.0.
            stats: Optional RateLimiterStats for tracking metrics.
        """
        if rate <= 0:
            raise ValueError("rate must be positive")
        if capacity is not None and capacity <= 0:
            raise ValueError("capacity must be positive")
        if time_period <= 0:
            raise ValueError("time_period must be positive")
        
        self._rate = rate
        self._capacity = capacity or int(rate)
        self._time_period = time_period
        self._tokens = float(self._capacity)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
        self._stats = stats or RateLimiterStats()
        
        logger.debug(
            f"TokenBucket initialized: rate={rate}, capacity={self._capacity}, "
            f"time_period={time_period}"
        )
    
    @property
    def rate(self) -> float:
        """Get the rate (tokens per time_period)."""
        return self._rate
    
    @property
    def capacity(self) -> int:
        """Get the bucket capacity."""
        return self._capacity
    
    @property
    def stats(self) -> RateLimiterStats:
        """Get rate limiter statistics."""
        return self._stats
    
    def _refill(self) -> None:
        """
        Refill tokens based on elapsed time. Must be called with lock held.
        
        This ensures the rate limit is maintained across any sliding time window
        by calculating tokens based on actual elapsed time since last update.
        The token bucket algorithm guarantees that the average rate over any
        time window cannot exceed the configured rate.
        """
        now = time.monotonic()
        elapsed = now - self._last_update
        
        # Calculate tokens to add based on elapsed time
        # This ensures rate is maintained in any sliding time window
        tokens_to_add = elapsed * (self._rate / self._time_period)
        
        # Update tokens, capping at capacity
        self._tokens = min(self._capacity, self._tokens + tokens_to_add)
        self._last_update = now
    
    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Blocks if insufficient tokens are available until they refill
        or timeout is reached. Ensures API call rate never exceeds 
        configured limit in any sliding time window.
        
        Args:
            tokens: Number of tokens to acquire. Default 1.
            timeout: Optional timeout in seconds. Raises asyncio.TimeoutError if exceeded.
            
        Returns:
            True if tokens were acquired, False if timeout occurred.
            
        Raises:
            asyncio.TimeoutError: If timeout is exceeded.
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        if tokens > self._capacity:
            raise ValueError(f"tokens ({tokens}) cannot exceed capacity ({self._capacity})")
        
        start_time = time.monotonic()
        had_to_wait = False
        
        async with self._lock:
            while True:
                self._refill()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    
                    # Track statistics
                    self._stats.tokens_consumed += tokens
                    self._stats.tokens_acquired += tokens  # Backwards compatibility
                    
                    wait_time = (time.monotonic() - start_time) * 1000  # ms
                    if had_to_wait:
                        self._stats.total_wait_time_ms += wait_time
                    
                    return True
                
                # Calculate wait time for tokens to refill
                tokens_needed = tokens - self._tokens
                wait_for_tokens = (tokens_needed / self._rate) * self._time_period
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= timeout:
                        logger.warning(f"Rate limiter acquire timed out after {timeout}s")
                        return False
                    wait_for_tokens = min(wait_for_tokens, timeout - elapsed)
                
                # Track that this request was blocked
                if not had_to_wait:
                    self._stats.requests_blocked += 1
                    self._stats.wait_events += 1  # Backwards compatibility
                    had_to_wait = True
                
                logger.debug(f"Rate limit reached, waiting {wait_for_tokens:.3f}s for tokens")
                
                # Release lock while waiting
                self._lock.release()
                try:
                    await asyncio.sleep(wait_for_tokens)
                finally:
                    await self._lock.acquire()
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Calculate the wait time for acquiring tokens.
        
        Args:
            tokens: Number of tokens to acquire.
            
        Returns:
            Estimated wait time in seconds, or 0 if tokens are available.
        """
        if tokens <= 0:
            return 0.0
        
        # Quick calculation without lock (may be slightly stale)
        now = time.monotonic()
        elapsed = now - self._last_update
        tokens_available = min(
            self._capacity,
            self._tokens + elapsed * (self._rate / self._time_period)
        )
        
        if tokens_available >= tokens:
            return 0.0
        
        tokens_needed = tokens - tokens_available
        return (tokens_needed / self._rate) * self._time_period
    
    def available_tokens(self) -> float:
        """
        Get the number of currently available tokens.
        
        Returns:
            Number of tokens available (may be slightly stale).
        """
        now = time.monotonic()
        elapsed = now - self._last_update
        return min(
            self._capacity,
            self._tokens + elapsed * (self._rate / self._time_period)
        )
    
    def reset(self) -> None:
        """Reset the bucket to full capacity."""
        self._tokens = float(self._capacity)
        self._last_update = time.monotonic()


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on API responses.
    
    Can dynamically decrease rate on 429 (Too Many Requests) errors
    and increase rate when successful.
    """
    
    def __init__(
        self,
        initial_rate: float,
        min_rate: float = 1.0,
        max_rate: float = 100.0,
        increase_factor: float = 1.1,
        decrease_factor: float = 0.5,
    ):
        """
        Initialize the adaptive rate limiter.
        
        Args:
            initial_rate: Initial rate in tokens per second.
            min_rate: Minimum allowed rate.
            max_rate: Maximum allowed rate.
            increase_factor: Factor to multiply rate on success.
            factor: Factor to multiply rate on rate limit error.
        """
        self._bucket = TokenBucket(rate=initial_rate)
        self._min_rate = min_rate
        self._max_rate = max_rate
        self._increase_factor = increase_factor
        self._decrease_factor = decrease_factor
        self._current_rate = initial_rate
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens with rate limiting."""
        return await self._bucket.acquire(tokens)
    
    def on_success(self) -> None:
        """Called on successful API call - increases rate."""
        new_rate = min(self._current_rate * self._increase_factor, self._max_rate)
        if new_rate != self._current_rate:
            self._current_rate = new_rate
            self._bucket = TokenBucket(rate=new_rate)
            logger.info(f"Rate limiter increased to {new_rate:.2f} req/s")
    
    def on_rate_limit_error(self) -> None:
        """Called on 429 error - decreases rate."""
        new_rate = max(self._current_rate * self._decrease_factor, self._min_rate)
        if new_rate != self._current_rate:
            self._current_rate = new_rate
            self._bucket = TokenBucket(rate=new_rate)
            logger.warning(f"Rate limiter decreased to {new_rate:.2f} req/s due to 429")


class MultiRateLimiter:
    """
    Manages multiple rate limiters for different services.
    
    Provides separate rate limiting for LLM, email, and scraping APIs.
    """
    
    def __init__(
        self,
        llm_rate: float = 10.0,
        email_rate: float = 1.0,
        scraper_rate: float = 5.0,
    ):
        """
        Initialize multi-rate limiter.
        
        Args:
            llm_rate: Rate for LLM API calls.
            email_rate: Rate for email API calls.
            scraper_rate: Rate for scraping operations.
        """
        self.llm = TokenBucket(rate=llm_rate)
        self.email = TokenBucket(rate=email_rate)
        self.scraper = TokenBucket(rate=scraper_rate)
        
        logger.info(
            f"MultiRateLimiter initialized: llm={llm_rate}, "
            f"email={email_rate}, scraper={scraper_rate}"
        )
    
    async def acquire_llm(self, tokens: int = 1) -> bool:
        """Acquire rate limit token for LLM API."""
        return await self.llm.acquire(tokens)
    
    async def acquire_email(self, tokens: int = 1) -> bool:
        """Acquire rate limit token for email API."""
        return await self.email.acquire(tokens)
    
    async def acquire_scraper(self, tokens: int = 1) -> bool:
        """Acquire rate limit token for scraper."""
        return await self.scraper.acquire(tokens)
    
    def get_stats(self) -> dict:
        """Get statistics for all rate limiters."""
        return {
            "llm": self.llm.stats.to_dict(),
            "email": self.email.stats.to_dict(),
            "scraper": self.scraper.stats.to_dict(),
        }

