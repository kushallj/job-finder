#!/usr/bin/env python3
"""
Demonstration of environment-specific configuration profiles.

This script shows how to use configuration profiles for different environments
and how to override specific settings.

Requirements Coverage: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import only config module to avoid dependencies
from src.async_pipeline import config as config_module

ProcessorConfig = config_module.ProcessorConfig
get_current_profile = config_module.get_current_profile
PROFILE_DEFAULTS = config_module.PROFILE_DEFAULTS


def demo_basic_profiles():
    """Demonstrate loading each profile."""
    print("=" * 70)
    print("BASIC PROFILE LOADING")
    print("=" * 70)
    
    for profile in ["development", "staging", "production"]:
        print(f"\n{profile.upper()} Profile:")
        print("-" * 50)
        
        config = ProcessorConfig.from_profile(profile)
        
        print(f"  Workers: {config.worker_count}")
        print(f"  Queue Size: {config.queue_size}")
        print(f"  Max Retries: {config.max_retries}")
        print(f"  LLM Rate Limit: {config.llm_rate_limit} req/s")
        print(f"  Log Level: {config.log_level}")
        print(f"  Auto Send Emails: {config.auto_send_emails}")
        print(f"  DB Pool Size: {config.db_pool_size}")
        print(f"  Progress Bar: {config.enable_progress_bar}")


def demo_environment_variable():
    """Demonstrate profile selection via environment variable."""
    print("\n" + "=" * 70)
    print("ENVIRONMENT VARIABLE SELECTION")
    print("=" * 70)
    
    # Save original value
    original = os.environ.get("PIPELINE_PROFILE")
    
    try:
        # Set environment variable
        os.environ["PIPELINE_PROFILE"] = "production"
        
        # Get profile from environment
        profile = get_current_profile()
        print(f"\nPIPELINE_PROFILE={os.environ['PIPELINE_PROFILE']}")
        print(f"Detected profile: {profile}")
        
        # Load config using detected profile
        config = ProcessorConfig.from_profile(profile)
        print(f"Config loaded: {config.worker_count} workers, {config.log_level} logging")
        
    finally:
        # Restore original value
        if original is not None:
            os.environ["PIPELINE_PROFILE"] = original
        elif "PIPELINE_PROFILE" in os.environ:
            del os.environ["PIPELINE_PROFILE"]


def demo_profile_overrides():
    """Demonstrate overriding profile defaults."""
    print("\n" + "=" * 70)
    print("PROFILE OVERRIDES")
    print("=" * 70)
    
    print("\n1. Production profile with custom worker count:")
    config = ProcessorConfig.from_profile("production", worker_count=20)
    print(f"   Workers: {config.worker_count} (overridden)")
    print(f"   Log Level: {config.log_level} (from profile)")
    print(f"   Queue Size: {config.queue_size} (from profile)")
    
    print("\n2. Development profile with INFO logging:")
    config = ProcessorConfig.from_profile("development", log_level="INFO")
    print(f"   Workers: {config.worker_count} (from profile)")
    print(f"   Log Level: {config.log_level} (overridden)")
    print(f"   Auto Send: {config.auto_send_emails} (from profile)")
    
    print("\n3. Staging profile with multiple overrides:")
    config = ProcessorConfig.from_profile(
        "staging",
        worker_count=8,
        max_retries=5,
        log_level="DEBUG"
    )
    print(f"   Workers: {config.worker_count} (overridden)")
    print(f"   Max Retries: {config.max_retries} (overridden)")
    print(f"   Log Level: {config.log_level} (overridden)")
    print(f"   Queue Size: {config.queue_size} (from profile)")


def demo_profile_comparison():
    """Compare profiles side-by-side."""
    print("\n" + "=" * 70)
    print("PROFILE COMPARISON")
    print("=" * 70)
    
    dev = ProcessorConfig.from_profile("development")
    staging = ProcessorConfig.from_profile("staging")
    prod = ProcessorConfig.from_profile("production")
    
    print("\n{:<30} {:>12} {:>12} {:>12}".format(
        "Setting", "Development", "Staging", "Production"
    ))
    print("-" * 70)
    
    comparisons = [
        ("Workers", "worker_count"),
        ("Queue Size", "queue_size"),
        ("Max Retries", "max_retries"),
        ("LLM Rate Limit", "llm_rate_limit"),
        ("LLM Timeout (s)", "llm_timeout_seconds"),
        ("DB Pool Size", "db_pool_size"),
        ("Log Level", "log_level"),
        ("Progress Bar", "enable_progress_bar"),
        ("Auto Send Emails", "auto_send_emails"),
        ("Shutdown Timeout (s)", "shutdown_timeout_seconds"),
    ]
    
    for label, attr in comparisons:
        dev_val = getattr(dev, attr)
        staging_val = getattr(staging, attr)
        prod_val = getattr(prod, attr)
        
        print("{:<30} {:>12} {:>12} {:>12}".format(
            label, str(dev_val), str(staging_val), str(prod_val)
        ))


def demo_common_patterns():
    """Demonstrate common configuration patterns."""
    print("\n" + "=" * 70)
    print("COMMON PATTERNS")
    print("=" * 70)
    
    print("\n1. High-Throughput Batch Processing:")
    config = ProcessorConfig.from_profile(
        "production",
        worker_count=20,
        queue_size=200,
        max_concurrent_api_calls=30
    )
    print(f"   Workers: {config.worker_count}")
    print(f"   Queue: {config.queue_size}")
    print(f"   Concurrent API Calls: {config.max_concurrent_api_calls}")
    
    print("\n2. Rate-Limited Integration:")
    config = ProcessorConfig.from_profile(
        "production",
        worker_count=2,
        llm_rate_limit=2.0,
        max_concurrent_api_calls=3
    )
    print(f"   Workers: {config.worker_count}")
    print(f"   LLM Rate Limit: {config.llm_rate_limit} req/s")
    print(f"   Concurrent API Calls: {config.max_concurrent_api_calls}")
    
    print("\n3. Reliable Overnight Job:")
    config = ProcessorConfig.from_profile(
        "production",
        max_retries=10,
        log_level="INFO",
        shutdown_timeout_seconds=300.0
    )
    print(f"   Max Retries: {config.max_retries}")
    print(f"   Log Level: {config.log_level}")
    print(f"   Shutdown Timeout: {config.shutdown_timeout_seconds}s")
    
    print("\n4. Cost-Optimized Processing:")
    config = ProcessorConfig.from_profile(
        "production",
        worker_count=3,
        max_retries=2,
        min_match_score=70,
        llm_timeout_seconds=15.0
    )
    print(f"   Workers: {config.worker_count}")
    print(f"   Max Retries: {config.max_retries}")
    print(f"   Min Match Score: {config.min_match_score}")
    print(f"   LLM Timeout: {config.llm_timeout_seconds}s")


def demo_validation():
    """Demonstrate configuration validation."""
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)
    
    print("\n1. Valid configuration (production profile):")
    try:
        config = ProcessorConfig.from_profile("production")
        print(f"   ✅ Configuration valid")
        print(f"   Workers: {config.worker_count}, Log Level: {config.log_level}")
    except ValueError as e:
        print(f"   ❌ Validation failed: {e}")
    
    print("\n2. Invalid worker count (negative):")
    try:
        config = ProcessorConfig.from_profile("production", worker_count=-5)
        print(f"   ✅ Configuration valid")
    except ValueError as e:
        print(f"   ❌ Validation failed: {str(e)[:80]}...")
    
    print("\n3. Invalid queue size (too small):")
    try:
        config = ProcessorConfig.from_profile("production", queue_size=5)
        print(f"   ✅ Configuration valid")
    except ValueError as e:
        print(f"   ❌ Validation failed: {str(e)[:80]}...")
    
    print("\n4. Invalid profile name:")
    try:
        config = ProcessorConfig.from_profile("invalid_profile")  # type: ignore
        print(f"   ✅ Configuration valid")
    except ValueError as e:
        print(f"   ❌ Validation failed: {str(e)[:80]}...")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "CONFIGURATION PROFILES DEMONSTRATION" + " " * 17 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Run demos
    demo_basic_profiles()
    demo_environment_variable()
    demo_profile_overrides()
    demo_profile_comparison()
    demo_common_patterns()
    demo_validation()
    
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nFor more information, see:")
    print("  - docs/CONFIGURATION_PROFILES.md")
    print("  - docs/CONFIGURATION_GUIDE.md")
    print("  - src/async_pipeline/config.py")
    print()


if __name__ == "__main__":
    main()
