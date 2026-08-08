"""
Retry logic with exponential backoff for the async job pipeline.

This module provides retry functionality using the tenacity library,
with configurable policies and statistics tracking.

Supports retryable exceptions:
- aiohttp.ClientError: HTTP client errors from aiohttp
- asyncio.TimeoutError: Async operation timeouts
- httpx.RequestError: HTTP errors from httpx library
"""

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, Union

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

from src.async_pipeline.config import RetryConfig
from src.async_pipeline.types import RetryStats

logger = logging.getLogger(__name__)


class RetryManager:
    """
    Centralized retry logic with exponential backoff and jitter.
    
    Provides reusable retry decorators and statistics tracking.
    
    Example:
        retry_manager = RetryManager(config=RetryConfig(max_attempts=3))
        
        @retry_manager.create_retry_decorator()
        async def call_api():
            await api.request()
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize the retry manager.
        
        Args:
            config: Retry configuration. Uses defaults if not provided.
        """
        self.config = config or RetryConfig()
        self.stats = RetryStats()
        self._log = logging.getLogger(f"{__name__}.RetryManager")
    
    def create_retry_decorator(
        self,
        max_attempts: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        exponential_base: Optional[float] = None,
        jitter: Optional[bool] = None,
        retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ) -> Callable:
        """
        Create a tenacity retry decorator with the specified policy.
        
        Args:
            max_attempts: Maximum number of retry attempts.
            base_delay: Base delay in seconds for exponential backoff.
            max_delay: Maximum delay in seconds between retries.
            exponential_base: Base for exponential backoff calculation.
            jitter: Whether to add random jitter to delays.
            retry_exceptions: Tuple of exception types to retry on.
            
        Returns:
            Configured retry decorator.
        """
        # Use instance config as defaults
        max_attempts = max_attempts or self.config.max_attempts
        base_delay = base_delay or self.config.base_delay
        max_delay = max_delay or self.config.max_delay
        exponential_base = exponential_base or self.config.exponential_base
        jitter = jitter if jitter is not None else self.config.jitter
        retry_exceptions = retry_exceptions or self.config.retry_exceptions
        
        # Build wait strategy
        wait_strategy = wait_exponential(
            multiplier=base_delay,
            max=max_delay,
            exp_base=exponential_base,
        )
        
        # Add jitter if enabled
        if jitter:
            wait_strategy = wait_strategy + wait_random(0, 1)
        
        # Create the decorator
        decorator = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_strategy,
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        
        return decorator
    
    async def execute_with_retry(
        self,
        operation: Callable,
        *args,
        max_attempts: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """
        Execute an async operation with retry logic.
        
        Args:
            operation: Async callable to execute.
            *args: Positional arguments for the operation.
            max_attempts: Override for max retry attempts.
            **kwargs: Keyword arguments for the operation.
            
        Returns:
            Result of the operation if successful.
            
        Raises:
            RetryError: If all retry attempts are exhausted.
        """
        max_attempts = max_attempts or self.config.max_attempts
        last_exception = None
        
        for attempt in range(1, max_attempts + 1):
            self.stats.total_attempts += 1
            
            try:
                result = await operation(*args, **kwargs)
                
                if attempt > 1:
                    self.stats.successful_retries += 1
                    logger.info(
                        f"Operation succeeded on attempt {attempt}/{max_attempts}",
                        extra={
                            "attempt_number": attempt,
                            "max_attempts": max_attempts,
                            "status": "success_after_retry"
                        }
                    )
                
                return result
                
            except Exception as exc:
                last_exception = exc
                self.stats.failed_retries += 1
                
                # Extract error type and message for structured logging
                error_type = type(exc).__name__
                error_message = str(exc)
                
                if attempt < max_attempts:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.config.base_delay * (self.config.exponential_base ** (attempt - 1)),
                        self.config.max_delay
                    )
                    
                    # Add jitter if configured
                    if self.config.jitter:
                        delay += random.uniform(0, 1)
                    
                    self.stats.total_delay_seconds += delay
                    
                    # Structured logging with error details
                    logger.warning(
                        f"Operation failed on attempt {attempt}/{max_attempts}",
                        extra={
                            "error_type": error_type,
                            "error_message": error_message,
                            "attempt_number": attempt,
                            "max_attempts": max_attempts,
                            "retry_delay_seconds": round(delay, 2),
                            "status": "retrying"
                        }
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted - final failure
                    logger.error(
                        f"Operation failed after {max_attempts} attempts",
                        extra={
                            "error_type": error_type,
                            "error_message": error_message,
                            "attempt_number": attempt,
                            "max_attempts": max_attempts,
                            "status": "failed"
                        }
                    )
        
        # All retries exhausted
        raise last_exception
    
    def get_stats(self) -> RetryStats:
        """Get retry statistics."""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset retry statistics."""
        self.stats = RetryStats()


# Global retry manager instance for convenience
_default_retry_manager: Optional[RetryManager] = None


def get_retry_manager(config: Optional[RetryConfig] = None) -> RetryManager:
    """
    Get or create the global retry manager instance.
    
    Args:
        config: Optional retry configuration.
        
    Returns:
        The global RetryManager instance.
    """
    global _default_retry_manager
    
    if _default_retry_manager is None:
        _default_retry_manager = RetryManager(config)
    
    return _default_retry_manager


# Convenience decorator factory
def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator factory for adding retry logic to async functions.
    
    This is a convenient way to add retry logic without creating
    a RetryManager instance.
    
    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        async def call_api():
            await api.request()
    
    Args:
        max_attempts: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        exponential_base: Base for exponential backoff.
        jitter: Whether to add random jitter.
        retry_exceptions: Exception types to retry on.
        
    Returns:
        Configured retry decorator.
    """
    # Build wait strategy
    wait_strategy = wait_exponential(
        multiplier=base_delay,
        max=max_delay,
        exp_base=exponential_base,
    )
    
    if jitter:
        wait_strategy = wait_strategy + wait_random(0, 1)
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(retry_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# HTTP-specific retry decorator for common API errors
def retry_on_api_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> Callable:
    """
    Retry decorator specifically for API calls.
    
    Retries on common HTTP errors and timeouts from aiohttp, httpx, and asyncio.
    
    Retryable exceptions:
    - aiohttp.ClientError: HTTP client errors from aiohttp
    - asyncio.TimeoutError: Async operation timeouts
    - httpx.RequestError: HTTP errors from httpx library
    
    Example:
        @retry_on_api_error()
        async def call_llm_api(text):
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"text": text}) as resp:
                    return await resp.json()
    
    Args:
        max_attempts: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        
    Returns:
        Configured retry decorator.
    """
    import aiohttp
    
    # Build exception tuple - include httpx if available
    retry_exceptions = [
        aiohttp.ClientError,
        aiohttp.ClientResponseError,
        asyncio.TimeoutError,
        TimeoutError,
    ]
    
    try:
        import httpx
        retry_exceptions.append(httpx.RequestError)
    except ImportError:
        logger.debug("httpx not available, skipping httpx.RequestError in retry policy")
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_delay, max=max_delay),
        retry=retry_if_exception_type(tuple(retry_exceptions)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# Database-specific retry decorator
def retry_on_db_error(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
) -> Callable:
    """
    Retry decorator specifically for database operations.
    
    Retries on common database errors like connection issues.
    
    Example:
        @retry_on_db_error()
        async def store_result(job_id, data):
            await db.execute(...)
    
    Args:
        max_attempts: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        
    Returns:
        Configured retry decorator.
    """
    from sqlalchemy.exc import (
        SQLAlchemyError,
        OperationalError,
        InterfaceError,
    )
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_delay, max=max_delay),
        retry=retry_if_exception_type((
            SQLAlchemyError,
            OperationalError,
            InterfaceError,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

