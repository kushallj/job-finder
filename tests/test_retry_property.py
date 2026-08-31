"""
Property-based tests for retry mechanism with exponential backoff.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.6**

This module uses hypothesis to generate test cases with various retry configurations
and validates the exponential backoff retry mechanism's correctness properties.
"""

import asyncio
import time
from unittest.mock import patch

import pytest
from hypothesis import given, strategies as st, assume, settings

from src.async_pipeline.retry import RetryManager
from src.async_pipeline.config import RetryConfig


# Strategy for generating valid retry configurations
@st.composite
def retry_config_strategy(draw):
    """Generate valid RetryConfig instances for property testing."""
    base_delay = draw(st.floats(min_value=0.1, max_value=10.0))
    max_delay = draw(st.floats(min_value=base_delay, max_value=120.0))
    
    return RetryConfig(
        max_attempts=draw(st.integers(min_value=1, max_value=10)),
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=draw(st.floats(min_value=1.1, max_value=5.0)),
        jitter=draw(st.booleans()),
    )


class TestExponentialBackoffRetryProperty:
    """
    Property-based tests for exponential backoff retry.
    
    **Property 7: Exponential Backoff Retry**
    **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.6**
    """
    
    @given(config=retry_config_strategy())
    @settings(max_examples=2)
    @pytest.mark.asyncio
    async def test_retry_delay_calculation_formula(self, config: RetryConfig):
        """
        Test retry delay calculation follows the formula: min(base × exponential^attempt, max).
        
        **Validates: Requirements 4.1, 4.3**
        
        Property: For any retry configuration with base_delay B, exponential_base E,
        and max_delay M, the delay for attempt A SHALL be min(B × E^(A-1), M).
        """
        # Create manager without jitter for deterministic testing
        config_no_jitter = RetryConfig(
            max_attempts=config.max_attempts,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            exponential_base=config.exponential_base,
            jitter=False,  # Disable jitter for predictable delays
        )
        manager = RetryManager(config_no_jitter)
        
        captured_delays = []
        
        async def always_failing_operation():
            raise ValueError("Test failure")
        
        # Mock asyncio.sleep to capture delays without actually sleeping
        async def mock_sleep(delay):
            captured_delays.append(delay)
            return None
        
        with patch('src.async_pipeline.retry.asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(ValueError):
                await manager.execute_with_retry(always_failing_operation)
        
        # Verify delays follow exponential backoff formula
        # Number of delays = max_attempts - 1 (no delay after last attempt)
        assert len(captured_delays) == config.max_attempts - 1
        
        for attempt_index, actual_delay in enumerate(captured_delays):
            # attempt_index is 0-based, but formula uses 1-based attempt number
            # First retry (attempt_index=0) uses attempt=1 in formula: B * E^(1-1) = B * E^0 = B
            expected_delay = min(
                config.base_delay * (config.exponential_base ** attempt_index),
                config.max_delay
            )
            
            # Allow small floating point tolerance
            assert abs(actual_delay - expected_delay) < 0.001, (
                f"Delay mismatch at attempt {attempt_index}: "
                f"expected {expected_delay}, got {actual_delay}"
            )
    
    @given(config=retry_config_strategy())
    @settings(max_examples=2)
    @pytest.mark.asyncio
    async def test_total_attempts_never_exceed_max(self, config: RetryConfig):
        """
        Test that total attempts never exceed max_attempts.
        
        **Validates: Requirements 4.2, 4.6**
        
        Property: For any retry configuration with max_attempts A, when all retries fail,
        the total number of operation invocations SHALL be exactly A, never exceeding it.
        """
        manager = RetryManager(config)
        
        call_count = 0
        
        async def counting_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        # Mock asyncio.sleep to avoid actual delays
        with patch('src.async_pipeline.retry.asyncio.sleep', return_value=None):
            with pytest.raises(ValueError):
                await manager.execute_with_retry(counting_operation)
        
        # Verify exactly max_attempts were made
        assert call_count == config.max_attempts, (
            f"Expected {config.max_attempts} attempts, got {call_count}"
        )
        
        # Also verify stats tracking
        assert manager.stats.total_attempts == config.max_attempts
    
    @given(
        config=retry_config_strategy(),
        success_attempt=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=2)
    @pytest.mark.asyncio
    async def test_retry_stops_on_success(self, config: RetryConfig, success_attempt: int):
        """
        Test that retries stop immediately upon success.
        
        **Validates: Requirements 4.1**
        
        Property: For any retry configuration, when an operation succeeds on attempt N
        (where N ≤ max_attempts), no further attempts SHALL be made.
        """
        # Only test cases where success_attempt is within max_attempts
        assume(success_attempt <= config.max_attempts)
        
        manager = RetryManager(config)
        
        call_count = 0
        
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < success_attempt:
                raise ValueError("Not yet")
            return "success"
        
        # Mock asyncio.sleep to avoid actual delays
        with patch('src.async_pipeline.retry.asyncio.sleep', return_value=None):
            result = await manager.execute_with_retry(flaky_operation)
        
        # Verify exactly success_attempt attempts were made, not more
        assert result == "success"
        assert call_count == success_attempt, (
            f"Expected {success_attempt} attempts, got {call_count}"
        )
        
        # Verify no more attempts than necessary
        assert call_count <= config.max_attempts
    
    @given(config=retry_config_strategy())
    @settings(max_examples=2)
    @pytest.mark.asyncio
    async def test_jitter_adds_randomness_to_delays(self, config: RetryConfig):
        """
        Test that jitter adds randomness to retry delays.
        
        **Validates: Requirements 4.4**
        
        Property: When jitter is enabled, the actual delay SHALL be greater than or equal
        to the base exponential delay and less than exponential delay + 1 second.
        When jitter is disabled, delays SHALL be deterministic.
        """
        # Test with jitter enabled
        config_with_jitter = RetryConfig(
            max_attempts=config.max_attempts,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            exponential_base=config.exponential_base,
            jitter=True,
        )
        manager_jitter = RetryManager(config_with_jitter)
        
        jitter_delays = []
        
        async def always_failing():
            raise ValueError("Test failure")
        
        async def mock_sleep_jitter(delay):
            jitter_delays.append(delay)
            return None
        
        with patch('src.async_pipeline.retry.asyncio.sleep', side_effect=mock_sleep_jitter):
            with pytest.raises(ValueError):
                await manager_jitter.execute_with_retry(always_failing)
        
        # Test with jitter disabled
        config_no_jitter = RetryConfig(
            max_attempts=config.max_attempts,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            exponential_base=config.exponential_base,
            jitter=False,
        )
        manager_no_jitter = RetryManager(config_no_jitter)
        
        no_jitter_delays = []
        
        async def mock_sleep_no_jitter(delay):
            no_jitter_delays.append(delay)
            return None
        
        with patch('src.async_pipeline.retry.asyncio.sleep', side_effect=mock_sleep_no_jitter):
            with pytest.raises(ValueError):
                await manager_no_jitter.execute_with_retry(always_failing)
        
        # Verify jitter adds randomness
        assert len(jitter_delays) == len(no_jitter_delays)
        
        for attempt_index in range(len(no_jitter_delays)):
            deterministic_delay = no_jitter_delays[attempt_index]
            jittered_delay = jitter_delays[attempt_index]
            
            # Jittered delay should be >= deterministic delay
            assert jittered_delay >= deterministic_delay, (
                f"Jittered delay {jittered_delay} is less than base {deterministic_delay}"
            )
            
            # Jittered delay should be < deterministic delay + 1.0 (max jitter)
            # Note: Due to capping at max_delay, this might not always hold
            # Only check if deterministic_delay < max_delay
            if deterministic_delay < config.max_delay:
                assert jittered_delay <= deterministic_delay + 1.0, (
                    f"Jittered delay {jittered_delay} exceeds base + 1.0: {deterministic_delay + 1.0}"
                )
    
    @given(config=retry_config_strategy())
    @settings(max_examples=2)
    @pytest.mark.asyncio
    async def test_max_delay_caps_exponential_growth(self, config: RetryConfig):
        """
        Test that max_delay caps exponential delay growth.
        
        **Validates: Requirements 4.3**
        
        Property: For any retry configuration with max_delay M, all retry delays
        SHALL be ≤ M, regardless of how large the exponential calculation grows.
        """
        # Force a scenario where exponential would exceed max_delay
        # Use a small max_delay and ensure multiple attempts
        config_with_cap = RetryConfig(
            max_attempts=max(5, config.max_attempts),  # At least 5 attempts
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            exponential_base=config.exponential_base,
            jitter=False,  # Disable jitter for clean testing
        )
        manager = RetryManager(config_with_cap)
        
        captured_delays = []
        
        async def always_failing():
            raise ValueError("Test failure")
        
        async def mock_sleep(delay):
            captured_delays.append(delay)
            return None
        
        with patch('src.async_pipeline.retry.asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(ValueError):
                await manager.execute_with_retry(always_failing)
        
        # Verify all delays are capped at max_delay
        for delay in captured_delays:
            assert delay <= config.max_delay, (
                f"Delay {delay} exceeds max_delay {config.max_delay}"
            )
    
    @given(config=retry_config_strategy())
    @settings(max_examples=2)
    @pytest.mark.asyncio
    async def test_failure_result_returned_when_exhausted(self, config: RetryConfig):
        """
        Test that failure result is returned when max attempts reached.
        
        **Validates: Requirements 4.6**
        
        Property: When maximum retry attempts is reached and actual retry attempts
        were made, RetryManager SHALL return a failure result (raise the exception).
        """
        manager = RetryManager(config)
        
        async def always_failing():
            raise RuntimeError("Persistent failure")
        
        # Mock asyncio.sleep to avoid delays
        with patch('src.async_pipeline.retry.asyncio.sleep', return_value=None):
            # Should raise the exception after max_attempts
            with pytest.raises(RuntimeError, match="Persistent failure"):
                await manager.execute_with_retry(always_failing)
        
        # Verify all attempts were exhausted
        assert manager.stats.total_attempts == config.max_attempts
        assert manager.stats.failed_retries == config.max_attempts
    
    @given(config=retry_config_strategy())
    @settings(max_examples=2)
    @pytest.mark.asyncio
    async def test_retry_statistics_tracking(self, config: RetryConfig):
        """
        Test that retry statistics are accurately tracked.
        
        **Validates: Requirements 4.1, 4.2**
        
        Property: RetryManager SHALL accurately track total_attempts, successful_retries,
        and failed_retries across all retry operations.
        """
        # Skip if max_attempts is 1 (no retries possible)
        assume(config.max_attempts >= 2)
        
        manager = RetryManager(config)
        
        # Reset stats to start clean
        manager.reset_stats()
        
        # Case 1: Operation that succeeds on first attempt
        async def immediate_success():
            return "success"
        
        with patch('src.async_pipeline.retry.asyncio.sleep', return_value=None):
            result = await manager.execute_with_retry(immediate_success)
        
        assert result == "success"
        assert manager.stats.total_attempts == 1
        assert manager.stats.successful_retries == 0  # No retry needed
        assert manager.stats.failed_retries == 0
        
        # Case 2: Operation that succeeds after retries
        manager.reset_stats()
        call_count = 0
        
        async def success_after_retries():
            nonlocal call_count
            call_count += 1
            if call_count < min(3, config.max_attempts):
                raise ValueError("Not yet")
            return "success"
        
        with patch('src.async_pipeline.retry.asyncio.sleep', return_value=None):
            result = await manager.execute_with_retry(success_after_retries)
        
        assert result == "success"
        assert manager.stats.total_attempts == min(3, config.max_attempts)
        assert manager.stats.successful_retries == 1
        assert manager.stats.failed_retries == min(3, config.max_attempts) - 1
    
    @given(
        base_delay=st.floats(min_value=0.1, max_value=5.0),
        max_delay=st.floats(min_value=0.1, max_value=5.0),
    )
    @settings(max_examples=2)
    @pytest.mark.asyncio
    async def test_constant_delay_when_max_equals_base(self, base_delay: float, max_delay: float):
        """
        Test constant delays when max_delay equals base_delay.
        
        **Validates: Requirements 4.3**
        
        Property: WHERE max_delay equals base_delay, THE delays SHALL remain
        constant from the first retry (no exponential growth).
        """
        # Ensure max_delay equals base_delay
        config = RetryConfig(
            max_attempts=4,
            base_delay=base_delay,
            max_delay=base_delay,  # Same as base_delay
            exponential_base=2.0,
            jitter=False,
        )
        manager = RetryManager(config)
        
        captured_delays = []
        
        async def always_failing():
            raise ValueError("Test failure")
        
        async def mock_sleep(delay):
            captured_delays.append(delay)
            return None
        
        with patch('src.async_pipeline.retry.asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(ValueError):
                await manager.execute_with_retry(always_failing)
        
        # All delays should be constant at base_delay
        for delay in captured_delays:
            assert abs(delay - base_delay) < 0.001, (
                f"Expected constant delay {base_delay}, got {delay}"
            )
