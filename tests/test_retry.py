"""
Tests for the retry module with exponential backoff.

Validates retry logic, exponential backoff calculation, jitter,
and structured logging for retry attempts.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.async_pipeline.retry import (
    RetryManager,
    retry_with_backoff,
    retry_on_api_error,
    retry_on_db_error,
    get_retry_manager,
)
from src.async_pipeline.config import RetryConfig
from src.async_pipeline.types import RetryStats


class TestRetryManager:
    """Test RetryManager with exponential backoff."""
    
    def test_retry_manager_initialization(self):
        """Test RetryManager initializes with correct config."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )
        
        manager = RetryManager(config)
        
        assert manager.config.max_attempts == 5
        assert manager.config.base_delay == 2.0
        assert manager.config.max_delay == 120.0
        assert manager.config.exponential_base == 3.0
        assert manager.config.jitter is False
        assert isinstance(manager.stats, RetryStats)
    
    def test_retry_manager_default_config(self):
        """Test RetryManager uses defaults when no config provided."""
        manager = RetryManager()
        
        assert manager.config.max_attempts == 3
        assert manager.config.base_delay == 1.0
        assert manager.config.max_delay == 60.0
        assert manager.config.exponential_base == 2.0
        assert manager.config.jitter is True
    
    def test_create_retry_decorator_with_defaults(self):
        """Test create_retry_decorator uses config defaults."""
        manager = RetryManager()
        decorator = manager.create_retry_decorator()
        
        assert decorator is not None
        assert callable(decorator)
    
    def test_create_retry_decorator_with_overrides(self):
        """Test create_retry_decorator accepts parameter overrides."""
        manager = RetryManager()
        decorator = manager.create_retry_decorator(
            max_attempts=5,
            base_delay=2.0,
            max_delay=100.0,
        )
        
        assert decorator is not None
        assert callable(decorator)
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self):
        """Test execute_with_retry succeeds on first attempt."""
        manager = RetryManager()
        
        async def successful_operation():
            return "success"
        
        result = await manager.execute_with_retry(successful_operation)
        
        assert result == "success"
        assert manager.stats.total_attempts == 1
        assert manager.stats.successful_retries == 0
        assert manager.stats.failed_retries == 0
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self):
        """Test execute_with_retry succeeds after retries."""
        manager = RetryManager()
        
        call_count = 0
        
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Simulated failure")
            return "success"
        
        result = await manager.execute_with_retry(flaky_operation)
        
        assert result == "success"
        assert call_count == 3
        assert manager.stats.total_attempts == 3
        assert manager.stats.successful_retries == 1
        assert manager.stats.failed_retries == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausted(self):
        """Test execute_with_retry raises exception when retries exhausted."""
        config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.05)
        manager = RetryManager(config)
        
        async def failing_operation():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError, match="Always fails"):
            await manager.execute_with_retry(failing_operation)
        
        assert manager.stats.total_attempts == 3
        assert manager.stats.successful_retries == 0
        assert manager.stats.failed_retries == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            max_attempts=4,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=False,
        )
        manager = RetryManager(config)
        
        call_count = 0
        delays = []
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test failure")
        
        # Patch asyncio.sleep to capture delays without recursion
        async def mock_sleep(delay):
            delays.append(delay)
            return None
        
        with patch('src.async_pipeline.retry.asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(ValueError):
                await manager.execute_with_retry(failing_operation)
        
        # Expected delays: 1.0 * (2^0) = 1.0, 1.0 * (2^1) = 2.0, 1.0 * (2^2) = 4.0
        assert len(delays) == 3  # 3 retries after initial attempt
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_capped_at_max_delay(self):
        """Test exponential backoff is capped at max_delay."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=10.0,
            max_delay=15.0,
            exponential_base=2.0,
            jitter=False,
        )
        manager = RetryManager(config)
        
        call_count = 0
        delays = []
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test failure")
        
        # Patch asyncio.sleep to capture delays without recursion
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            delays.append(delay)
            # Don't call sleep again to avoid recursion
            return None
        
        with patch('src.async_pipeline.retry.asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(ValueError):
                await manager.execute_with_retry(failing_operation)
        
        # All delays should be capped at max_delay=15.0
        for delay in delays:
            assert delay <= 15.0
    
    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delays."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
        )
        manager = RetryManager(config)
        
        call_count = 0
        delays = []
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test failure")
        
        # Patch asyncio.sleep to capture delays without recursion
        async def mock_sleep(delay):
            delays.append(delay)
            return None
        
        with patch('src.async_pipeline.retry.asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(ValueError):
                await manager.execute_with_retry(failing_operation)
        
        # With jitter, delays should be base + random(0, 1)
        # So delays should be > base_delay and within reasonable range
        assert len(delays) == 2
        # First retry: base_delay=1.0 + random(0,1) -> should be in [1.0, 2.0]
        assert 1.0 <= delays[0] <= 2.0
    
    @pytest.mark.asyncio
    async def test_structured_logging_on_retry(self, caplog):
        """Test structured logging includes error type, message, and attempt number."""
        config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.05)
        manager = RetryManager(config)
        
        async def failing_operation():
            raise ValueError("Custom error message")
        
        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError):
                await manager.execute_with_retry(failing_operation)
        
        # Check that warning logs contain structured information
        warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_logs) >= 2
        
        # Check first retry log
        first_log = warning_logs[0]
        assert first_log.error_type == "ValueError"
        assert first_log.error_message == "Custom error message"
        assert first_log.attempt_number == 1
        assert first_log.status == "retrying"
    
    def test_get_stats(self):
        """Test get_stats returns current statistics."""
        manager = RetryManager()
        stats = manager.get_stats()
        
        assert isinstance(stats, RetryStats)
        assert stats.total_attempts == 0
        assert stats.successful_retries == 0
        assert stats.failed_retries == 0
    
    def test_reset_stats(self):
        """Test reset_stats clears statistics."""
        manager = RetryManager()
        manager.stats.total_attempts = 10
        manager.stats.successful_retries = 5
        
        manager.reset_stats()
        
        assert manager.stats.total_attempts == 0
        assert manager.stats.successful_retries == 0
        assert manager.stats.failed_retries == 0


class TestRetryDecorators:
    """Test retry decorator functions."""
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_decorator(self):
        """Test retry_with_backoff decorator works correctly."""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, base_delay=0.01, max_delay=0.05)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = await flaky_function()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_on_api_error_aiohttp(self):
        """Test retry_on_api_error retries on aiohttp errors."""
        import aiohttp
        
        call_count = 0
        
        @retry_on_api_error(max_attempts=3, base_delay=0.01, max_delay=0.05)
        async def api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise aiohttp.ClientError("Connection error")
            return "success"
        
        result = await api_call()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_on_api_error_timeout(self):
        """Test retry_on_api_error retries on asyncio.TimeoutError."""
        call_count = 0
        
        @retry_on_api_error(max_attempts=3, base_delay=0.01, max_delay=0.05)
        async def api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Request timeout")
            return "success"
        
        result = await api_call()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_on_api_error_httpx(self):
        """Test retry_on_api_error retries on httpx.RequestError."""
        try:
            import httpx
            
            call_count = 0
            
            @retry_on_api_error(max_attempts=3, base_delay=0.01, max_delay=0.05)
            async def api_call():
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise httpx.RequestError("HTTP error")
                return "success"
            
            result = await api_call()
            
            assert result == "success"
            assert call_count == 2
        except ImportError:
            pytest.skip("httpx not installed")
    
    @pytest.mark.asyncio
    async def test_retry_on_db_error(self):
        """Test retry_on_db_error retries on database errors."""
        from sqlalchemy.exc import OperationalError
        
        call_count = 0
        
        @retry_on_db_error(max_attempts=3, base_delay=0.01, max_delay=0.05)
        async def db_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("DB connection lost", None, None)
            return "success"
        
        result = await db_operation()
        
        assert result == "success"
        assert call_count == 2


class TestGlobalRetryManager:
    """Test global retry manager singleton."""
    
    def test_get_retry_manager_singleton(self):
        """Test get_retry_manager returns singleton instance."""
        manager1 = get_retry_manager()
        manager2 = get_retry_manager()
        
        assert manager1 is manager2
    
    def test_get_retry_manager_with_config(self):
        """Test get_retry_manager accepts config on first call."""
        # Reset global state
        import src.async_pipeline.retry as retry_module
        retry_module._default_retry_manager = None
        
        config = RetryConfig(max_attempts=5)
        manager = get_retry_manager(config)
        
        assert manager.config.max_attempts == 5
