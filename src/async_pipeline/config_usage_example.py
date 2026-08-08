"""
Example usage of ProcessorConfig for async pipeline.

This demonstrates the three ways to load configuration:
1. From environment variables
2. From JSON file
3. From code (direct instantiation)

Requirements Coverage: 15.1, 15.2, 15.3, 15.4, 15.5
"""

import os
from config import ProcessorConfig


def example_from_defaults():
    """Example 1: Use default configuration values."""
    print("=== Example 1: Default Configuration ===")
    config = ProcessorConfig()
    config.validate()
    
    print(f"Worker count: {config.worker_count}")
    print(f"Queue size: {config.queue_size}")
    print(f"Max concurrent API calls: {config.max_concurrent_api_calls}")
    print(f"Chunk size: {config.chunk_size}")
    print(f"Max retries: {config.max_retries}")
    print(f"LLM rate limit: {config.llm_rate_limit} req/sec")
    print(f"LLM timeout: {config.llm_timeout_seconds} seconds")
    print()


def example_from_code():
    """Example 2: Create configuration with custom values in code."""
    print("=== Example 2: Custom Configuration from Code ===")
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
        db_timeout_seconds=20.0,
        log_level="DEBUG"
    )
    config.validate()
    
    print(f"Worker count: {config.worker_count}")
    print(f"Queue size: {config.queue_size}")
    print(f"Max retries: {config.max_retries}")
    print(f"Exponential base: {config.exponential_base}")
    print(f"Log level: {config.log_level}")
    print()


def example_from_env():
    """Example 3: Load configuration from environment variables."""
    print("=== Example 3: Configuration from Environment Variables ===")
    
    # Set environment variables
    os.environ["PIPELINE_WORKER_COUNT"] = "15"
    os.environ["PIPELINE_QUEUE_SIZE"] = "300"
    os.environ["PIPELINE_MAX_RETRIES"] = "7"
    os.environ["PIPELINE_LLM_RATE_LIMIT"] = "25.0"
    os.environ["PIPELINE_LOG_LEVEL"] = "WARNING"
    
    config = ProcessorConfig.from_env()
    config.validate()
    
    print(f"Worker count: {config.worker_count}")
    print(f"Queue size: {config.queue_size}")
    print(f"Max retries: {config.max_retries}")
    print(f"LLM rate limit: {config.llm_rate_limit} req/sec")
    print(f"Log level: {config.log_level}")
    print()
    
    # Clean up
    for key in list(os.environ.keys()):
        if key.startswith("PIPELINE_"):
            del os.environ[key]


def example_from_json():
    """Example 4: Load configuration from JSON file."""
    print("=== Example 4: Configuration from JSON File ===")
    
    try:
        config = ProcessorConfig.from_json("example_config.json")
        config.validate()
        
        print(f"Worker count: {config.worker_count}")
        print(f"Queue size: {config.queue_size}")
        print(f"Max concurrent API calls: {config.max_concurrent_api_calls}")
        print(f"Chunk size: {config.chunk_size}")
        print(f"Max retries: {config.max_retries}")
        print(f"Base delay: {config.base_delay} seconds")
        print(f"Max delay: {config.max_delay} seconds")
        print(f"Exponential base: {config.exponential_base}")
        print(f"LLM rate limit: {config.llm_rate_limit} req/sec")
        print(f"LLM timeout: {config.llm_timeout_seconds} seconds")
        print()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure example_config.json exists in src/async_pipeline/")
        print()


def example_to_dict():
    """Example 5: Convert configuration to dictionary."""
    print("=== Example 5: Convert to Dictionary ===")
    config = ProcessorConfig(worker_count=10, max_retries=5)
    config_dict = config.to_dict()
    
    print("Configuration as dictionary:")
    for key, value in list(config_dict.items())[:10]:  # Show first 10 items
        print(f"  {key}: {value}")
    print(f"  ... ({len(config_dict)} total fields)")
    print()


def example_validation_errors():
    """Example 6: Demonstrate validation errors with clear messages."""
    print("=== Example 6: Validation Error Examples ===")
    
    # Invalid worker_count
    try:
        config = ProcessorConfig(worker_count=0)
        config.validate()
    except ValueError as e:
        print(f"✗ Invalid worker_count: {e}")
    
    # Invalid exponential_base
    try:
        config = ProcessorConfig(exponential_base=1.0)
        config.validate()
    except ValueError as e:
        print(f"✗ Invalid exponential_base: {e}")
    
    # Invalid max_delay vs base_delay
    try:
        config = ProcessorConfig(base_delay=10.0, max_delay=5.0)
        config.validate()
    except ValueError as e:
        print(f"✗ Invalid delay configuration: {e}")
    
    # Invalid rate limit
    try:
        config = ProcessorConfig(llm_rate_limit=-1)
        config.validate()
    except ValueError as e:
        print(f"✗ Invalid rate limit: {e}")
    
    # Invalid timeout
    try:
        config = ProcessorConfig(llm_timeout_seconds=0)
        config.validate()
    except ValueError as e:
        print(f"✗ Invalid timeout: {e}")
    
    print()


if __name__ == "__main__":
    # Run all examples
    example_from_defaults()
    example_from_code()
    example_from_env()
    example_from_json()
    example_to_dict()
    example_validation_errors()
    
    print("=== All Examples Complete ===")
    print("Configuration can be loaded from:")
    print("  1. Default values (built-in)")
    print("  2. Code (direct instantiation)")
    print("  3. Environment variables (PIPELINE_* prefix)")
    print("  4. JSON file (ProcessorConfig.from_json)")
    print("  5. YAML file (ProcessorConfig.from_yaml, requires PyYAML)")
    print("\nAll configurations are validated with clear error messages.")
