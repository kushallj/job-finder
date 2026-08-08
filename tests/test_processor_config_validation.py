"""
Tests for ProcessorConfig validation enhancements.

This module tests the enhanced validation logic for ProcessorConfig,
ensuring that all configuration parameters are properly validated with
descriptive error messages.

Requirements Coverage: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 26.1, 26.2, 26.3, 26.4, 26.5, 26.6, 12.1
"""

import pytest
from src.async_pipeline.config import ProcessorConfig


class TestWorkerCountValidation:
    """Test worker_count validation (Requirements 8.1, 26.1)."""
    
    def test_worker_count_positive(self):
        """worker_count must be positive."""
        config = ProcessorConfig(worker_count=5)
        config.validate()  # Should not raise
    
    def test_worker_count_zero_raises_error(self):
        """worker_count of 0 should raise ValueError."""
        config = ProcessorConfig(worker_count=0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "worker_count must be positive" in str(excinfo.value)
        assert "got 0" in str(excinfo.value)
        assert "Valid range: 1-50" in str(excinfo.value)
    
    def test_worker_count_negative_raises_error(self):
        """worker_count < 0 should raise ValueError."""
        config = ProcessorConfig(worker_count=-5)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "worker_count must be positive" in str(excinfo.value)
        assert "got -5" in str(excinfo.value)
    
    def test_worker_count_within_bounds(self):
        """worker_count within 1-50 should be valid."""
        for count in [1, 10, 25, 50]:
            config = ProcessorConfig(worker_count=count)
            config.validate()  # Should not raise
    
    def test_worker_count_exceeds_max_raises_error(self):
        """worker_count > 50 should raise ValueError."""
        config = ProcessorConfig(worker_count=51)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "exceeds maximum allowed value of 50" in str(excinfo.value)
        assert "got 51" in str(excinfo.value)
        assert "Too many workers can overwhelm" in str(excinfo.value)


class TestQueueSizeValidation:
    """Test queue_size validation (Requirements 8.2, 26.2)."""
    
    def test_queue_size_positive(self):
        """queue_size must be positive."""
        config = ProcessorConfig(queue_size=100)
        config.validate()  # Should not raise
    
    def test_queue_size_zero_raises_error(self):
        """queue_size of 0 should raise ValueError."""
        config = ProcessorConfig(queue_size=0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "queue_size must be positive" in str(excinfo.value)
        assert "got 0" in str(excinfo.value)
        assert "Minimum recommended: 10" in str(excinfo.value)
    
    def test_queue_size_negative_raises_error(self):
        """queue_size < 0 should raise ValueError."""
        config = ProcessorConfig(queue_size=-10)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "queue_size must be positive" in str(excinfo.value)
    
    def test_queue_size_below_minimum_raises_error(self):
        """queue_size < 10 should raise ValueError."""
        for size in [1, 5, 9]:
            config = ProcessorConfig(queue_size=size)
            with pytest.raises(ValueError) as excinfo:
                config.validate()
            assert "queue_size is too small" in str(excinfo.value)
            assert f"got {size}" in str(excinfo.value)
            assert "Minimum queue size is 10" in str(excinfo.value)
    
    def test_queue_size_at_minimum_valid(self):
        """queue_size = 10 should be valid."""
        config = ProcessorConfig(queue_size=10)
        config.validate()  # Should not raise
    
    def test_queue_size_above_minimum_valid(self):
        """queue_size > 10 should be valid."""
        for size in [10, 50, 100, 1000]:
            config = ProcessorConfig(queue_size=size)
            config.validate()  # Should not raise


class TestRateLimitValidation:
    """Test rate limit validation for all API types (Requirements 8.3, 26.3)."""
    
    def test_llm_rate_limit_positive(self):
        """llm_rate_limit must be positive."""
        config = ProcessorConfig(llm_rate_limit=10.0)
        config.validate()  # Should not raise
    
    def test_llm_rate_limit_zero_raises_error(self):
        """llm_rate_limit of 0 should raise ValueError."""
        config = ProcessorConfig(llm_rate_limit=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "llm_rate_limit must be positive" in str(excinfo.value)
        assert "got 0.0" in str(excinfo.value)
        assert "Prevents quota exhaustion" in str(excinfo.value)
    
    def test_llm_rate_limit_negative_raises_error(self):
        """llm_rate_limit < 0 should raise ValueError."""
        config = ProcessorConfig(llm_rate_limit=-5.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "llm_rate_limit must be positive" in str(excinfo.value)
    
    def test_email_rate_limit_positive(self):
        """email_rate_limit must be positive."""
        config = ProcessorConfig(email_rate_limit=1.0)
        config.validate()  # Should not raise
    
    def test_email_rate_limit_zero_raises_error(self):
        """email_rate_limit of 0 should raise ValueError."""
        config = ProcessorConfig(email_rate_limit=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "email_rate_limit must be positive" in str(excinfo.value)
        assert "Prevents spam detection" in str(excinfo.value)
    
    def test_scraper_rate_limit_positive(self):
        """scraper_rate_limit must be positive."""
        config = ProcessorConfig(scraper_rate_limit=5.0)
        config.validate()  # Should not raise
    
    def test_scraper_rate_limit_zero_raises_error(self):
        """scraper_rate_limit of 0 should raise ValueError."""
        config = ProcessorConfig(scraper_rate_limit=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "scraper_rate_limit must be positive" in str(excinfo.value)
        assert "Prevents IP blocking" in str(excinfo.value)


class TestTimeoutValidation:
    """Test timeout validation for all operation types (Requirements 8.5, 26.4)."""
    
    def test_llm_timeout_positive(self):
        """llm_timeout_seconds must be positive."""
        config = ProcessorConfig(llm_timeout_seconds=30.0)
        config.validate()  # Should not raise
    
    def test_llm_timeout_zero_raises_error(self):
        """llm_timeout_seconds of 0 should raise ValueError."""
        config = ProcessorConfig(llm_timeout_seconds=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "llm_timeout_seconds must be positive" in str(excinfo.value)
        assert "Typical LLM response time: 2-5 seconds" in str(excinfo.value)
    
    def test_email_timeout_positive(self):
        """email_timeout_seconds must be positive."""
        config = ProcessorConfig(email_timeout_seconds=15.0)
        config.validate()  # Should not raise
    
    def test_email_timeout_zero_raises_error(self):
        """email_timeout_seconds of 0 should raise ValueError."""
        config = ProcessorConfig(email_timeout_seconds=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "email_timeout_seconds must be positive" in str(excinfo.value)
        assert "Typical email send time: 1-3 seconds" in str(excinfo.value)
    
    def test_scraper_timeout_positive(self):
        """scraper_timeout_seconds must be positive."""
        config = ProcessorConfig(scraper_timeout_seconds=20.0)
        config.validate()  # Should not raise
    
    def test_scraper_timeout_zero_raises_error(self):
        """scraper_timeout_seconds of 0 should raise ValueError."""
        config = ProcessorConfig(scraper_timeout_seconds=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "scraper_timeout_seconds must be positive" in str(excinfo.value)
        assert "Typical page load time: 2-10 seconds" in str(excinfo.value)
    
    def test_db_timeout_positive(self):
        """db_timeout_seconds must be positive."""
        config = ProcessorConfig(db_timeout_seconds=10.0)
        config.validate()  # Should not raise
    
    def test_db_timeout_zero_raises_error(self):
        """db_timeout_seconds of 0 should raise ValueError."""
        config = ProcessorConfig(db_timeout_seconds=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "db_timeout_seconds must be positive" in str(excinfo.value)
        assert "Typical query time: <1 second" in str(excinfo.value)


class TestRetryParametersValidation:
    """Test retry parameter validation (Requirements 8.4, 26.5)."""
    
    def test_max_retries_non_negative(self):
        """max_retries must be non-negative."""
        for retries in [0, 1, 3, 10]:
            config = ProcessorConfig(max_retries=retries)
            config.validate()  # Should not raise
    
    def test_max_retries_negative_raises_error(self):
        """max_retries < 0 should raise ValueError."""
        config = ProcessorConfig(max_retries=-1)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "max_retries must be non-negative" in str(excinfo.value)
        assert "Set to 0 to disable retries" in str(excinfo.value)
    
    def test_base_delay_positive(self):
        """base_delay must be positive."""
        config = ProcessorConfig(base_delay=1.0)
        config.validate()  # Should not raise
    
    def test_base_delay_zero_raises_error(self):
        """base_delay of 0 should raise ValueError."""
        config = ProcessorConfig(base_delay=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "base_delay must be positive" in str(excinfo.value)
        assert "initial retry delay in seconds" in str(excinfo.value)
    
    def test_max_delay_positive(self):
        """max_delay must be positive."""
        config = ProcessorConfig(max_delay=60.0)
        config.validate()  # Should not raise
    
    def test_max_delay_zero_raises_error(self):
        """max_delay of 0 should raise ValueError."""
        config = ProcessorConfig(max_delay=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "max_delay must be positive" in str(excinfo.value)
        assert "caps the exponential backoff" in str(excinfo.value)
    
    def test_max_delay_less_than_base_delay_raises_error(self):
        """max_delay < base_delay should raise ValueError."""
        config = ProcessorConfig(base_delay=10.0, max_delay=5.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "max_delay (5.0s) must be >= base_delay (10.0s)" in str(excinfo.value)
        assert "cannot be less than initial delay" in str(excinfo.value)
    
    def test_max_delay_equal_to_base_delay_valid(self):
        """max_delay = base_delay should be valid (constant delay)."""
        config = ProcessorConfig(base_delay=5.0, max_delay=5.0)
        config.validate()  # Should not raise
    
    def test_exponential_base_greater_than_one(self):
        """exponential_base must be > 1.0."""
        for base in [1.1, 1.5, 2.0, 3.0]:
            config = ProcessorConfig(exponential_base=base)
            config.validate()  # Should not raise
    
    def test_exponential_base_one_raises_error(self):
        """exponential_base of 1.0 should raise ValueError."""
        config = ProcessorConfig(exponential_base=1.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "exponential_base must be > 1.0" in str(excinfo.value)
        assert "got 1.0" in str(excinfo.value)
        assert "Value of 1.0 would result in constant delays" in str(excinfo.value)
    
    def test_exponential_base_less_than_one_raises_error(self):
        """exponential_base < 1.0 should raise ValueError."""
        config = ProcessorConfig(exponential_base=0.5)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "exponential_base must be > 1.0" in str(excinfo.value)


class TestDatabaseParametersValidation:
    """Test database parameter validation (Requirements 8.6, 8.7, 26.6, 12.1)."""
    
    def test_chunk_size_positive(self):
        """chunk_size must be positive."""
        config = ProcessorConfig(chunk_size=100)
        config.validate()  # Should not raise
    
    def test_chunk_size_zero_raises_error(self):
        """chunk_size of 0 should raise ValueError."""
        config = ProcessorConfig(chunk_size=0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "chunk_size must be positive" in str(excinfo.value)
        assert "database streaming batch size" in str(excinfo.value)
        assert "Affects memory usage: O(chunk_size)" in str(excinfo.value)
    
    def test_db_pool_size_positive(self):
        """db_pool_size must be positive."""
        config = ProcessorConfig(db_pool_size=10)
        config.validate()  # Should not raise
    
    def test_db_pool_size_zero_raises_error(self):
        """db_pool_size of 0 should raise ValueError."""
        config = ProcessorConfig(db_pool_size=0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "db_pool_size must be positive" in str(excinfo.value)
        assert "concurrent database connections" in str(excinfo.value)
        assert "Should be >= worker_count" in str(excinfo.value)
    
    def test_db_max_overflow_non_negative(self):
        """db_max_overflow must be non-negative."""
        for overflow in [0, 5, 20]:
            config = ProcessorConfig(db_max_overflow=overflow)
            config.validate()  # Should not raise
    
    def test_db_max_overflow_negative_raises_error(self):
        """db_max_overflow < 0 should raise ValueError."""
        config = ProcessorConfig(db_max_overflow=-1)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        assert "db_max_overflow must be non-negative" in str(excinfo.value)
        assert "Total max connections = pool_size + max_overflow" in str(excinfo.value)


class TestValidConfigurationCombinations:
    """Test valid configuration combinations."""
    
    def test_default_configuration_valid(self):
        """Default ProcessorConfig should be valid."""
        config = ProcessorConfig()
        config.validate()  # Should not raise
    
    def test_minimal_configuration_valid(self):
        """Minimal valid configuration."""
        config = ProcessorConfig(
            worker_count=1,
            queue_size=10,
            chunk_size=1,
            max_retries=0,
            base_delay=0.1,
            max_delay=0.1,
            exponential_base=1.1,
            llm_rate_limit=0.1,
            email_rate_limit=0.1,
            scraper_rate_limit=0.1,
            llm_timeout_seconds=0.1,
            email_timeout_seconds=0.1,
            scraper_timeout_seconds=0.1,
            db_timeout_seconds=0.1,
            db_pool_size=1,
            db_max_overflow=0,
        )
        config.validate()  # Should not raise
    
    def test_maximum_configuration_valid(self):
        """Maximum valid configuration."""
        config = ProcessorConfig(
            worker_count=50,
            queue_size=1000,
            chunk_size=1000,
            max_retries=10,
            base_delay=1.0,
            max_delay=300.0,
            exponential_base=3.0,
            llm_rate_limit=100.0,
            email_rate_limit=50.0,
            scraper_rate_limit=100.0,
            llm_timeout_seconds=120.0,
            email_timeout_seconds=60.0,
            scraper_timeout_seconds=90.0,
            db_timeout_seconds=30.0,
            db_pool_size=50,
            db_max_overflow=100,
        )
        config.validate()  # Should not raise
    
    def test_production_like_configuration_valid(self):
        """Production-like configuration."""
        config = ProcessorConfig(
            worker_count=20,
            queue_size=200,
            chunk_size=100,
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=2.0,
            llm_rate_limit=15.0,
            email_rate_limit=2.0,
            scraper_rate_limit=10.0,
            llm_timeout_seconds=60.0,
            email_timeout_seconds=30.0,
            scraper_timeout_seconds=45.0,
            db_timeout_seconds=20.0,
            db_pool_size=25,
            db_max_overflow=50,
        )
        config.validate()  # Should not raise


class TestErrorMessageDescriptiveness:
    """Test that error messages are descriptive and helpful."""
    
    def test_worker_count_error_includes_context(self):
        """Worker count error should include helpful context."""
        config = ProcessorConfig(worker_count=100)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        error_msg = str(excinfo.value)
        # Check for descriptive elements
        assert "exceeds maximum" in error_msg
        assert "50" in error_msg
        assert "overwhelm" in error_msg
        assert "scaling horizontally" in error_msg
    
    def test_queue_size_error_includes_context(self):
        """Queue size error should include helpful context."""
        config = ProcessorConfig(queue_size=5)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        error_msg = str(excinfo.value)
        # Check for descriptive elements
        assert "too small" in error_msg
        assert "Minimum queue size is 10" in error_msg
        assert "backpressure" in error_msg
        assert "throughput" in error_msg
    
    def test_rate_limit_error_includes_purpose(self):
        """Rate limit error should explain the purpose."""
        config = ProcessorConfig(llm_rate_limit=-1.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        error_msg = str(excinfo.value)
        # Check that purpose is explained
        assert "quota" in error_msg or "throttling" in error_msg
    
    def test_timeout_error_includes_typical_values(self):
        """Timeout error should include typical values."""
        config = ProcessorConfig(llm_timeout_seconds=0.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        error_msg = str(excinfo.value)
        # Check for typical value guidance
        assert "Typical" in error_msg
        assert "seconds" in error_msg
    
    def test_retry_error_includes_explanation(self):
        """Retry parameter error should explain the parameter."""
        config = ProcessorConfig(exponential_base=1.0)
        with pytest.raises(ValueError) as excinfo:
            config.validate()
        error_msg = str(excinfo.value)
        # Check for explanation
        assert "exponential backoff" in error_msg
        assert "constant delays" in error_msg
        assert "Common values" in error_msg


class TestConfigurationBoundaryConditions:
    """Test boundary conditions for configuration values."""
    
    def test_worker_count_at_boundaries(self):
        """Test worker_count at boundary values."""
        # Lower boundary: 1 is valid
        config = ProcessorConfig(worker_count=1)
        config.validate()  # Should not raise
        
        # Upper boundary: 50 is valid
        config = ProcessorConfig(worker_count=50)
        config.validate()  # Should not raise
        
        # Just below lower: 0 is invalid
        config = ProcessorConfig(worker_count=0)
        with pytest.raises(ValueError):
            config.validate()
        
        # Just above upper: 51 is invalid
        config = ProcessorConfig(worker_count=51)
        with pytest.raises(ValueError):
            config.validate()
    
    def test_queue_size_at_boundaries(self):
        """Test queue_size at boundary values."""
        # At minimum: 10 is valid
        config = ProcessorConfig(queue_size=10)
        config.validate()  # Should not raise
        
        # Just below minimum: 9 is invalid
        config = ProcessorConfig(queue_size=9)
        with pytest.raises(ValueError):
            config.validate()
    
    def test_max_delay_equals_base_delay_valid(self):
        """Test max_delay = base_delay (constant backoff) is valid."""
        config = ProcessorConfig(base_delay=5.0, max_delay=5.0)
        config.validate()  # Should not raise
        
        # max_delay slightly less than base_delay is invalid
        config = ProcessorConfig(base_delay=5.0, max_delay=4.9)
        with pytest.raises(ValueError):
            config.validate()
