"""
Unit tests for RateLimiter (TokenBucket) implementation.

Tests validate all requirements from Requirement 6:
- 6.1: Token bucket algorithm implementation
- 6.2: Token acquisition before API calls
- 6.3: Blocking when tokens insufficient
- 6.4: Token refill at configured rate
- 6.5: API call rate never exceeds limit in any sliding window

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
"""

import pytest
import asyncio
import time
from src.async_pipeline.rate_limiter import TokenBucket, MultiRateLimiter
from src.async_pipeline.types import RateLimiterStats


class TestTokenBucketBasics:
    """Test basic TokenBucket initialization and configuration."""
    
    def test_token_bucket_initialization(self):
        """Test creating a TokenBucket with default parameters."""
        limiter = TokenBucket(rate=10.0)
        
        assert limiter.rate == 10.0
        assert limiter.capacity == 10
        assert limiter.stats.tokens_consumed == 0
        assert limiter.stats.requests_blocked == 0
    
    def test_token_bucket_custom_capacity(self):
        """Test creating TokenBucket with custom capacity for burst handling."""
        limiter = TokenBucket(rate=10.0, capacity=20)
        
        assert limiter.rate == 10.0
        assert limiter.capacity == 20
    
    def test_token_bucket_validation_invalid_rate(self):
        """Test that invalid rate raises ValueError."""
        with pytest.raises(ValueError, match="rate must be positive"):
            TokenBucket(rate=0.0)
        
        with pytest.raises(ValueError, match="rate must be positive"):
            TokenBucket(rate=-1.0)
    
    def test_token_bucket_validation_invalid_capacity(self):
        """Test that invalid capacity raises ValueError."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            TokenBucket(rate=10.0, capacity=0)
        
        with pytest.raises(ValueError, match="capacity must be positive"):
            TokenBucket(rate=10.0, capacity=-1)
    
    def test_token_bucket_validation_invalid_time_period(self):
        """Test that invalid time_period raises ValueError."""
        with pytest.raises(ValueError, match="time_period must be positive"):
            TokenBucket(rate=10.0, time_period=0.0)


@pytest.mark.asyncio
class TestTokenAcquisition:
    """Test token acquisition behavior (Requirements 6.2, 6.3)."""
    
    async def test_acquire_single_token(self):
        """Test acquiring a single token when available."""
        limiter = TokenBucket(rate=10.0)
        
        result = await limiter.acquire(tokens=1)
        
        assert result is True
        assert limiter.stats.tokens_consumed == 1
        assert limiter.stats.requests_blocked == 0
    
    async def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens at once."""
        limiter = TokenBucket(rate=10.0, capacity=20)
        
        result = await limiter.acquire(tokens=5)
        
        assert result is True
        assert limiter.stats.tokens_consumed == 5
    
    async def test_acquire_blocks_when_insufficient_tokens(self):
        """Test that acquire blocks when insufficient tokens (Requirement 6.3)."""
        limiter = TokenBucket(rate=2.0, capacity=2)  # 2 tokens/sec
        
        # First acquire uses up all tokens
        await limiter.acquire(tokens=2)
        assert limiter.stats.tokens_consumed == 2
        
        # Second acquire should block until tokens refill
        start = time.monotonic()
        await limiter.acquire(tokens=1)
        elapsed = time.monotonic() - start
        
        # Should have waited ~0.5 seconds for 1 token at 2 tokens/sec
        assert elapsed >= 0.4  # Allow some tolerance
        assert limiter.stats.requests_blocked == 1
        assert limiter.stats.tokens_consumed == 3
    
    async def test_acquire_invalid_tokens(self):
        """Test that acquiring invalid token counts raises ValueError."""
        limiter = TokenBucket(rate=10.0)
        
        with pytest.raises(ValueError, match="tokens must be positive"):
            await limiter.acquire(tokens=0)
        
        with pytest.raises(ValueError, match="tokens must be positive"):
            await limiter.acquire(tokens=-1)
    
    async def test_acquire_exceeds_capacity(self):
        """Test that acquiring more than capacity raises ValueError."""
        limiter = TokenBucket(rate=10.0, capacity=5)
        
        with pytest.raises(ValueError, match="tokens .* cannot exceed capacity"):
            await limiter.acquire(tokens=10)
    
    async def test_acquire_with_timeout_success(self):
        """Test acquire with timeout that succeeds."""
        limiter = TokenBucket(rate=10.0)
        
        result = await limiter.acquire(tokens=1, timeout=1.0)
        
        assert result is True
    
    async def test_acquire_with_timeout_failure(self):
        """Test acquire with timeout that expires."""
        limiter = TokenBucket(rate=1.0, capacity=1)  # 1 token/sec
        
        # Use up the token
        await limiter.acquire(tokens=1)
        
        # Try to acquire with short timeout
        result = await limiter.acquire(tokens=1, timeout=0.1)
        
        assert result is False  # Timeout occurred


@pytest.mark.asyncio
class TestTokenRefill:
    """Test token refill logic (Requirement 6.4)."""
    
    async def test_tokens_refill_at_configured_rate(self):
        """Test that tokens refill at the configured rate per second."""
        limiter = TokenBucket(rate=10.0, capacity=10)
        
        # Use 5 tokens
        await limiter.acquire(tokens=5)
        assert limiter.stats.tokens_consumed == 5
        
        # Wait 0.5 seconds, should refill 5 tokens (10 * 0.5)
        await asyncio.sleep(0.5)
        
        # Should be able to acquire 5 tokens without blocking
        start = time.monotonic()
        await limiter.acquire(tokens=5)
        elapsed = time.monotonic() - start
        
        assert elapsed < 0.1  # Should not have blocked
        assert limiter.stats.tokens_consumed == 10
    
    async def test_tokens_do_not_exceed_capacity(self):
        """Test that refilled tokens are capped at capacity."""
        limiter = TokenBucket(rate=10.0, capacity=5)
        
        # Wait 2 seconds - would refill 20 tokens, but capped at capacity
        await asyncio.sleep(2.0)
        
        # Should only be able to acquire capacity worth of tokens
        available = limiter.available_tokens()
        assert available <= 5
    
    async def test_refill_calculation_accuracy(self):
        """Test that refill calculation is accurate over time."""
        limiter = TokenBucket(rate=5.0, capacity=10)  # 5 tokens/sec
        
        # Use all tokens
        await limiter.acquire(tokens=10)
        
        # Wait exactly 1 second - should refill 5 tokens
        await asyncio.sleep(1.0)
        
        # Should be able to acquire 5 tokens without blocking
        result = await limiter.acquire(tokens=5)
        assert result is True
        
        # Trying to acquire more should block
        start = time.monotonic()
        await limiter.acquire(tokens=1)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.1  # Should have waited for refill


@pytest.mark.asyncio
class TestRateLimitEnforcement:
    """Test that rate limit is enforced across sliding windows (Requirement 6.5)."""
    
    async def test_rate_never_exceeds_limit_burst(self):
        """Test that even with burst capacity, long-term rate is maintained."""
        limiter = TokenBucket(rate=5.0, capacity=10)  # 5/sec, burst of 10
        
        # First, use up the initial burst
        await limiter.acquire(tokens=10)
        
        # Now measure the sustained rate over 2 seconds
        start = time.monotonic()
        tokens_acquired = 0
        
        # Acquire 10 tokens - should take ~2 seconds at 5/sec
        for _ in range(10):
            await limiter.acquire(tokens=1)
            tokens_acquired += 1
        
        elapsed = time.monotonic() - start
        actual_rate = tokens_acquired / elapsed
        
        # Actual rate should not significantly exceed configured rate
        # Allow 10% margin for timing variance
        assert actual_rate <= 5.5, f"Rate {actual_rate} exceeds limit of 5.0"
        assert elapsed >= 1.8, "Should take at least 1.8 seconds for 10 tokens at 5/sec"
    
    async def test_rate_maintained_in_sliding_window(self):
        """Test rate limit is maintained in any sliding time window."""
        limiter = TokenBucket(rate=10.0, capacity=10)  # 10/sec
        
        # Use up initial burst
        await limiter.acquire(tokens=10)
        
        # Measure sustained rate over 2 seconds (after initial burst is gone)
        start = time.monotonic()
        count = 0
        
        while time.monotonic() - start < 2.0:
            await limiter.acquire(tokens=1)
            count += 1
        
        elapsed = time.monotonic() - start
        actual_rate = count / elapsed
        
        # Should be close to 10/sec (sustained rate, not burst)
        assert 9.0 <= actual_rate <= 11.0, f"Rate {actual_rate} outside expected range"
    
    async def test_concurrent_acquisitions_respect_limit(self):
        """Test that concurrent acquisitions from multiple tasks respect the limit."""
        limiter = TokenBucket(rate=5.0, capacity=5)
        
        async def acquire_task():
            await limiter.acquire(tokens=1)
            return time.monotonic()
        
        # Launch 10 concurrent tasks
        start = time.monotonic()
        results = await asyncio.gather(*[acquire_task() for _ in range(10)])
        elapsed = time.monotonic() - start
        
        # With 5 tokens/sec and 10 tokens needed, should take ~2 seconds
        # (initial burst of 5, then wait 1s for next 5)
        assert elapsed >= 1.0, "Concurrent tasks did not respect rate limit"
        assert limiter.stats.tokens_consumed == 10


class TestWaitTimeCalculation:
    """Test get_wait_time method."""
    
    def test_get_wait_time_tokens_available(self):
        """Test wait time is 0 when tokens are available."""
        limiter = TokenBucket(rate=10.0)
        
        wait_time = limiter.get_wait_time(tokens=5)
        
        assert wait_time == 0.0
    
    def test_get_wait_time_tokens_needed(self):
        """Test wait time calculation when tokens are needed."""
        limiter = TokenBucket(rate=10.0, capacity=10)
        
        # Use all tokens by setting internal state
        limiter._tokens = 0.0
        
        # Need 5 tokens at 10/sec = 0.5 seconds
        wait_time = limiter.get_wait_time(tokens=5)
        
        assert 0.45 <= wait_time <= 0.55  # Allow small variance


class TestRateLimiterStats:
    """Test rate limiter statistics tracking (Requirement 6.5)."""
    
    @pytest.mark.asyncio
    async def test_stats_tokens_consumed(self):
        """Test that tokens_consumed is tracked correctly."""
        limiter = TokenBucket(rate=10.0)
        
        await limiter.acquire(tokens=3)
        await limiter.acquire(tokens=2)
        
        assert limiter.stats.tokens_consumed == 5
        assert limiter.stats.tokens_acquired == 5  # Backwards compatibility
    
    @pytest.mark.asyncio
    async def test_stats_requests_blocked(self):
        """Test that requests_blocked is tracked correctly."""
        limiter = TokenBucket(rate=2.0, capacity=2)
        
        # Use all tokens
        await limiter.acquire(tokens=2)
        
        # This should block
        await limiter.acquire(tokens=1)
        
        assert limiter.stats.requests_blocked == 1
        assert limiter.stats.wait_events == 1  # Backwards compatibility
    
    @pytest.mark.asyncio
    async def test_stats_total_wait_time(self):
        """Test that total_wait_time_ms is tracked correctly."""
        limiter = TokenBucket(rate=2.0, capacity=2)
        
        # Use all tokens
        await limiter.acquire(tokens=2)
        
        # This should block and wait
        start = time.monotonic()
        await limiter.acquire(tokens=1)
        elapsed_ms = (time.monotonic() - start) * 1000
        
        assert limiter.stats.total_wait_time_ms > 0
        assert limiter.stats.total_wait_time_ms >= elapsed_ms * 0.9  # Allow 10% variance
    
    @pytest.mark.asyncio
    async def test_stats_average_wait_time(self):
        """Test average_wait_time_ms calculation."""
        limiter = TokenBucket(rate=2.0, capacity=2)
        
        # First blocking request
        await limiter.acquire(tokens=2)
        await limiter.acquire(tokens=1)
        
        # Second blocking request
        await limiter.acquire(tokens=1)
        
        assert limiter.stats.requests_blocked == 2
        avg_wait = limiter.stats.average_wait_time_ms
        assert avg_wait > 0
        assert avg_wait == limiter.stats.total_wait_time_ms / 2
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = RateLimiterStats(
            tokens_consumed=10,
            requests_blocked=2,
            total_wait_time_ms=500.0,
        )
        
        stats_dict = stats.to_dict()
        
        assert stats_dict["tokens_consumed"] == 10
        assert stats_dict["requests_blocked"] == 2
        assert stats_dict["total_wait_time_ms"] == 500.0
        assert "average_wait_time_ms" in stats_dict
        assert stats_dict["average_wait_time_ms"] == 250.0


class TestAvailableTokens:
    """Test available_tokens method."""
    
    def test_available_tokens_full_capacity(self):
        """Test available tokens when at full capacity."""
        limiter = TokenBucket(rate=10.0, capacity=10)
        
        available = limiter.available_tokens()
        
        assert available == 10.0
    
    @pytest.mark.asyncio
    async def test_available_tokens_after_acquisition(self):
        """Test available tokens after acquiring some."""
        limiter = TokenBucket(rate=10.0, capacity=10)
        
        await limiter.acquire(tokens=3)
        available = limiter.available_tokens()
        
        assert 6.0 <= available <= 8.0  # Allow for slight refill during test


class TestTokenBucketReset:
    """Test token bucket reset functionality."""
    
    @pytest.mark.asyncio
    async def test_reset_refills_to_capacity(self):
        """Test that reset refills bucket to full capacity."""
        limiter = TokenBucket(rate=10.0, capacity=10)
        
        # Use some tokens
        await limiter.acquire(tokens=8)
        assert limiter.stats.tokens_consumed == 8
        
        # Reset
        limiter.reset()
        
        # Should be at full capacity
        available = limiter.available_tokens()
        assert available == 10.0


class TestMultiRateLimiter:
    """Test MultiRateLimiter for managing multiple services."""
    
    def test_multi_rate_limiter_initialization(self):
        """Test creating MultiRateLimiter with different rates per service."""
        limiter = MultiRateLimiter(
            llm_rate=10.0,
            email_rate=1.0,
            scraper_rate=5.0,
        )
        
        assert limiter.llm.rate == 10.0
        assert limiter.email.rate == 1.0
        assert limiter.scraper.rate == 5.0
    
    @pytest.mark.asyncio
    async def test_multi_rate_limiter_independent_limits(self):
        """Test that each service has independent rate limits."""
        limiter = MultiRateLimiter(
            llm_rate=10.0,
            email_rate=1.0,
            scraper_rate=5.0,
        )
        
        # Acquire from different services
        await limiter.acquire_llm(tokens=1)
        await limiter.acquire_email(tokens=1)
        await limiter.acquire_scraper(tokens=1)
        
        # Each should have consumed 1 token independently
        assert limiter.llm.stats.tokens_consumed == 1
        assert limiter.email.stats.tokens_consumed == 1
        assert limiter.scraper.stats.tokens_consumed == 1
    
    def test_multi_rate_limiter_get_stats(self):
        """Test getting stats from all rate limiters."""
        limiter = MultiRateLimiter()
        
        stats = limiter.get_stats()
        
        assert "llm" in stats
        assert "email" in stats
        assert "scraper" in stats
        assert isinstance(stats["llm"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
