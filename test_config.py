"""
Test configuration loader for async pipeline.
Validates all requirements from task 11.1.
"""

import os
import json
import tempfile
import pytest
from src.async_pipeline.config import ProcessorConfig, RetryConfig, RateLimitConfig


def test_processor_config_defaults():
    """Test that default configuration values are set correctly."""
    config = ProcessorConfig()
    
    # Concurrency settings
    assert config.worker_count == 5
    assert config.queue_size == 100
    assert config.max_concurrent_api_calls == 10
    assert config.chunk_size == 100
    
    # Retry configuration
    assert config.max_retries == 3
    assert config.base_delay == 1.0
    assert config.max_delay == 60.0
    assert config.exponential_base == 2.0
    
    # Rate limits
    assert config.llm_rate_limit == 10.0
    assert config.email_rate_limit == 1.0
    assert config.scraper_rate_limit == 5.0
    
    # Timeouts
    assert config.llm_timeout_seconds == 30.0
    assert config.email_timeout_seconds == 15.0
    assert config.scraper_timeout_seconds == 20.0
    assert config.db_timeout_seconds == 10.0


def test_processor_config_custom_values():
    """Test creating configuration with custom values."""
    config = ProcessorConfig(
        worker_count=10,
        queue_size=200,
        max_concurrent_api_calls=20,
        chunk_size=50,
        max_retries=5,
        base_delay=2.0,
        max_delay=120.0,
        exponential_base=3.0,
        llm_rate_limit=20.0,
        email_rate_limit=2.0,
        scraper_rate_limit=10.0,
        llm_timeout_seconds=60.0,
        email_timeout_seconds=30.0,
        scraper_timeout_seconds=40.0,
        db_timeout_seconds=20.0
    )
    
    assert config.worker_count == 10
    assert config.queue_size == 200
    assert config.max_concurrent_api_calls == 20
    assert config.chunk_size == 50
    assert config.max_retries == 5
    assert config.base_delay == 2.0
    assert config.max_delay == 120.0
    assert config.exponential_base == 3.0
    assert config.llm_rate_limit == 20.0
    assert config.email_rate_limit == 2.0
    assert config.scraper_rate_limit == 10.0
    assert config.llm_timeout_seconds == 60.0
    assert config.email_timeout_seconds == 30.0
    assert config.scraper_timeout_seconds == 40.0
    assert config.db_timeout_seconds == 20.0


def test_validation_worker_count():
    """Test validation: worker_count must be positive and within reasonable bounds (1-50)."""
    # Test zero value
    config = ProcessorConfig(worker_count=0)
    with pytest.raises(ValueError, match="worker_count must be positive"):
        config.validate()
    
    # Test negative value
    config = ProcessorConfig(worker_count=-1)
    with pytest.raises(ValueError, match="worker_count must be positive"):
        config.validate()
    
    # Test upper bound (Requirements 8.1, 26.1)
    config = ProcessorConfig(worker_count=51)
    with pytest.raises(ValueError, match="worker_count exceeds maximum allowed value of 50"):
        config.validate()
    
    config = ProcessorConfig(worker_count=100)
    with pytest.raises(ValueError, match="worker_count exceeds maximum allowed value of 50"):
        config.validate()
    
    # Test valid boundary values
    config = ProcessorConfig(worker_count=1)
    config.validate()  # Should not raise
    
    config = ProcessorConfig(worker_count=50)
    config.validate()  # Should not raise


def test_validation_queue_size():
    """Test validation: queue_size must be positive and sufficient (≥10)."""
    # Test zero value
    config = ProcessorConfig(queue_size=0)
    with pytest.raises(ValueError, match="queue_size must be positive"):
        config.validate()
    
    # Test negative value
    config = ProcessorConfig(queue_size=-1)
    with pytest.raises(ValueError, match="queue_size must be positive"):
        config.validate()
    
    # Test minimum bound (Requirements 8.2, 26.2)
    config = ProcessorConfig(queue_size=5)
    with pytest.raises(ValueError, match="queue_size is too small"):
        config.validate()
    
    config = ProcessorConfig(queue_size=9)
    with pytest.raises(ValueError, match="queue_size is too small"):
        config.validate()
    
    # Test valid boundary value
    config = ProcessorConfig(queue_size=10)
    config.validate()  # Should not raise
    
    config = ProcessorConfig(queue_size=100)
    config.validate()  # Should not raise


def test_validation_max_retries():
    """Test validation: max_retries must be non-negative."""
    config = ProcessorConfig(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries must be non-negative"):
        config.validate()
    
    # max_retries=0 should be valid
    config = ProcessorConfig(max_retries=0)
    config.validate()  # Should not raise


def test_validation_delays():
    """Test validation: delays must be positive."""
    config = ProcessorConfig(base_delay=0)
    with pytest.raises(ValueError, match="base_delay must be positive"):
        config.validate()
    
    config = ProcessorConfig(max_delay=0)
    with pytest.raises(ValueError, match="max_delay must be positive"):
        config.validate()


def test_validation_max_delay_vs_base_delay():
    """Test validation: max_delay must be >= base_delay."""
    config = ProcessorConfig(base_delay=10.0, max_delay=5.0)
    with pytest.raises(ValueError, match="max_delay.*must be >= base_delay"):
        config.validate()


def test_validation_exponential_base():
    """Test validation: exponential_base must be > 1.0."""
    config = ProcessorConfig(exponential_base=1.0)
    with pytest.raises(ValueError, match="exponential_base must be > 1.0"):
        config.validate()
    
    config = ProcessorConfig(exponential_base=0.5)
    with pytest.raises(ValueError, match="exponential_base must be > 1.0"):
        config.validate()


def test_validation_rate_limits():
    """Test validation: rate limits must be positive."""
    config = ProcessorConfig(llm_rate_limit=0)
    with pytest.raises(ValueError, match="llm_rate_limit must be positive"):
        config.validate()
    
    config = ProcessorConfig(email_rate_limit=-1)
    with pytest.raises(ValueError, match="email_rate_limit must be positive"):
        config.validate()
    
    config = ProcessorConfig(scraper_rate_limit=0)
    with pytest.raises(ValueError, match="scraper_rate_limit must be positive"):
        config.validate()


def test_validation_timeouts():
    """Test validation: timeouts must be positive."""
    config = ProcessorConfig(llm_timeout_seconds=0)
    with pytest.raises(ValueError, match="llm_timeout_seconds must be positive"):
        config.validate()
    
    config = ProcessorConfig(email_timeout_seconds=-1)
    with pytest.raises(ValueError, match="email_timeout_seconds must be positive"):
        config.validate()
    
    config = ProcessorConfig(scraper_timeout_seconds=0)
    with pytest.raises(ValueError, match="scraper_timeout_seconds must be positive"):
        config.validate()
    
    config = ProcessorConfig(db_timeout_seconds=0)
    with pytest.raises(ValueError, match="db_timeout_seconds must be positive"):
        config.validate()


def test_validation_log_level():
    """Test validation: log_level must be valid."""
    config = ProcessorConfig(log_level="INVALID")
    with pytest.raises(ValueError, match="log_level must be one of"):
        config.validate()
    
    # Valid log levels should pass
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        config = ProcessorConfig(log_level=level)
        config.validate()  # Should not raise


def test_validation_database_parameters():
    """Test validation: database parameters (pool_size, max_overflow) must be valid (Requirements 8.6, 8.7, 26.6)."""
    # Test db_pool_size validation
    config = ProcessorConfig(db_pool_size=0)
    with pytest.raises(ValueError, match="db_pool_size must be positive"):
        config.validate()
    
    config = ProcessorConfig(db_pool_size=-1)
    with pytest.raises(ValueError, match="db_pool_size must be positive"):
        config.validate()
    
    # Test db_max_overflow validation
    config = ProcessorConfig(db_max_overflow=-1)
    with pytest.raises(ValueError, match="db_max_overflow must be non-negative"):
        config.validate()
    
    # Test valid values
    config = ProcessorConfig(db_pool_size=10, db_max_overflow=20)
    config.validate()  # Should not raise
    
    config = ProcessorConfig(db_pool_size=1, db_max_overflow=0)
    config.validate()  # Should not raise


def test_validation_chunk_size():
    """Test validation: chunk_size must be positive (Requirements 8.6, 12.1)."""
    config = ProcessorConfig(chunk_size=0)
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        config.validate()
    
    config = ProcessorConfig(chunk_size=-1)
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        config.validate()
    
    # Valid value
    config = ProcessorConfig(chunk_size=100)
    config.validate()  # Should not raise


def test_validation_shutdown_timeout():
    """Test validation: shutdown_timeout_seconds must be positive."""
    config = ProcessorConfig(shutdown_timeout_seconds=0)
    with pytest.raises(ValueError, match="shutdown_timeout_seconds must be positive"):
        config.validate()
    
    config = ProcessorConfig(shutdown_timeout_seconds=-1)
    with pytest.raises(ValueError, match="shutdown_timeout_seconds must be positive"):
        config.validate()
    
    # Valid value
    config = ProcessorConfig(shutdown_timeout_seconds=60.0)
    config.validate()  # Should not raise


def test_valid_configuration():
    """Test that valid configuration passes validation."""
    config = ProcessorConfig()
    config.validate()  # Should not raise


def test_from_env():
    """Test loading configuration from environment variables."""
    # Set environment variables
    os.environ["PIPELINE_WORKER_COUNT"] = "10"
    os.environ["PIPELINE_QUEUE_SIZE"] = "200"
    os.environ["PIPELINE_MAX_RETRIES"] = "5"
    os.environ["PIPELINE_BASE_DELAY"] = "2.0"
    os.environ["PIPELINE_LLM_RATE_LIMIT"] = "20.0"
    os.environ["PIPELINE_LLM_TIMEOUT_SECONDS"] = "60.0"
    
    try:
        config = ProcessorConfig.from_env()
        
        assert config.worker_count == 10
        assert config.queue_size == 200
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.llm_rate_limit == 20.0
        assert config.llm_timeout_seconds == 60.0
    finally:
        # Clean up environment variables
        for key in list(os.environ.keys()):
            if key.startswith("PIPELINE_"):
                del os.environ[key]


def test_from_json():
    """Test loading configuration from JSON file."""
    config_data = {
        "worker_count": 10,
        "queue_size": 200,
        "max_concurrent_api_calls": 20,
        "chunk_size": 50,
        "max_retries": 5,
        "llm_rate_limit": 20.0,
        "llm_timeout_seconds": 60.0
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name
    
    try:
        config = ProcessorConfig.from_json(temp_path)
        
        assert config.worker_count == 10
        assert config.queue_size == 200
        assert config.max_concurrent_api_calls == 20
        assert config.chunk_size == 50
        assert config.max_retries == 5
        assert config.llm_rate_limit == 20.0
        assert config.llm_timeout_seconds == 60.0
    finally:
        os.unlink(temp_path)


def test_from_json_file_not_found():
    """Test that from_json raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        ProcessorConfig.from_json("/nonexistent/config.json")


def test_from_json_invalid_json():
    """Test that from_json raises ValueError for invalid JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json }")
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Invalid JSON"):
            ProcessorConfig.from_json(temp_path)
    finally:
        os.unlink(temp_path)


def test_from_dict():
    """Test creating configuration from dictionary."""
    config_dict = {
        "worker_count": 10,
        "queue_size": 200,
        "max_retries": 5
    }
    
    config = ProcessorConfig.from_dict(config_dict)
    
    assert config.worker_count == 10
    assert config.queue_size == 200
    assert config.max_retries == 5


def test_to_dict():
    """Test converting configuration to dictionary."""
    config = ProcessorConfig(
        worker_count=10,
        queue_size=200,
        max_retries=5
    )
    
    config_dict = config.to_dict()
    
    assert config_dict["worker_count"] == 10
    assert config_dict["queue_size"] == 200
    assert config_dict["max_retries"] == 5
    assert "llm_rate_limit" in config_dict
    assert "llm_timeout_seconds" in config_dict


def test_retry_config_validation():
    """Test RetryConfig validation."""
    # Valid config
    config = RetryConfig()
    config.validate()  # Should not raise
    
    # Invalid max_attempts
    config = RetryConfig(max_attempts=-1)
    with pytest.raises(ValueError, match="max_attempts must be non-negative"):
        config.validate()
    
    # Invalid base_delay
    config = RetryConfig(base_delay=0)
    with pytest.raises(ValueError, match="base_delay must be positive"):
        config.validate()
    
    # Invalid exponential_base
    config = RetryConfig(exponential_base=1.0)
    with pytest.raises(ValueError, match="exponential_base must be > 1.0"):
        config.validate()


def test_rate_limit_config_validation():
    """Test RateLimitConfig validation."""
    # Valid config
    config = RateLimitConfig(rate=10.0)
    config.validate()  # Should not raise
    
    # Invalid rate
    config = RateLimitConfig(rate=0)
    with pytest.raises(ValueError, match="rate must be positive"):
        config.validate()
    
    # Invalid capacity
    config = RateLimitConfig(rate=10.0, capacity=0)
    with pytest.raises(ValueError, match="capacity must be positive"):
        config.validate()
    
    # Invalid time_period
    config = RateLimitConfig(rate=10.0, time_period=0)
    with pytest.raises(ValueError, match="time_period must be positive"):
        config.validate()


def test_backward_compatibility_aliases():
    """Test backward compatibility property aliases for renamed fields."""
    config = ProcessorConfig(
        base_delay=2.0,
        max_delay=120.0,
        exponential_base=3.0,
        chunk_size=50
    )
    
    # Check that old property names still work
    assert config.retry_base_delay == 2.0
    assert config.retry_max_delay == 120.0
    assert config.retry_exponential_base == 3.0
    assert config.db_chunk_size == 50
    
    # Check that new names also work
    assert config.base_delay == 2.0
    assert config.max_delay == 120.0
    assert config.exponential_base == 3.0
    assert config.chunk_size == 50


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
