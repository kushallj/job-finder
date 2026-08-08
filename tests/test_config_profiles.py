"""
Unit tests for environment-specific configuration profiles.

Tests verify that:
1. All profiles are valid and can be loaded
2. Profile defaults match expected values for each environment
3. Profile selection via environment variable works
4. Override mechanism works correctly
5. Invalid profiles raise appropriate errors

Requirements Coverage: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import os
import pytest
from src.async_pipeline.config import (
    ProcessorConfig,
    PROFILE_DEFAULTS,
    get_current_profile,
    ProfileType
)


class TestProfileDefaults:
    """Test that profile defaults are correctly defined."""
    
    def test_all_profiles_exist(self):
        """Test that all expected profiles are defined."""
        expected_profiles = {"development", "staging", "production"}
        actual_profiles = set(PROFILE_DEFAULTS.keys())
        assert actual_profiles == expected_profiles, \
            f"Expected profiles {expected_profiles}, got {actual_profiles}"
    
    def test_development_profile_defaults(self):
        """Test development profile has expected values."""
        dev = PROFILE_DEFAULTS["development"]
        
        # Concurrency: Low for local debugging
        assert dev["worker_count"] == 2, "Development should have 2 workers"
        assert dev["max_concurrent_api_calls"] == 3
        assert dev["queue_size"] == 20
        assert dev["chunk_size"] == 50
        
        # Retry: Fewer retries for faster feedback
        assert dev["max_retries"] == 2
        assert dev["base_delay"] == 0.5
        assert dev["max_delay"] == 10.0
        
        # Rate limiting: Conservative
        assert dev["llm_rate_limit"] == 5.0
        assert dev["email_rate_limit"] == 0.5
        assert dev["scraper_rate_limit"] == 2.0
        
        # Timeouts: Shorter for debugging
        assert dev["llm_timeout_seconds"] == 20.0
        assert dev["email_timeout_seconds"] == 10.0
        assert dev["scraper_timeout_seconds"] == 15.0
        assert dev["db_timeout_seconds"] == 5.0
        
        # Database: Small pool
        assert dev["db_pool_size"] == 3
        assert dev["db_max_overflow"] == 5
        
        # Logging: Verbose
        assert dev["log_level"] == "DEBUG"
        assert dev["structured_logging"] is True
        
        # Progress: Always show
        assert dev["enable_progress_bar"] is True
        
        # Outreach: Disabled by default
        assert dev["auto_send_emails"] is False
        
        # Shutdown: Quick
        assert dev["shutdown_timeout_seconds"] == 30.0
    
    def test_staging_profile_defaults(self):
        """Test staging profile has expected values."""
        staging = PROFILE_DEFAULTS["staging"]
        
        # Concurrency: Moderate
        assert staging["worker_count"] == 5
        assert staging["max_concurrent_api_calls"] == 10
        assert staging["queue_size"] == 50
        
        # Retry: Standard
        assert staging["max_retries"] == 3
        assert staging["base_delay"] == 1.0
        assert staging["max_delay"] == 30.0
        
        # Rate limiting: Moderate
        assert staging["llm_rate_limit"] == 8.0
        assert staging["email_rate_limit"] == 1.0
        
        # Logging: Info level
        assert staging["log_level"] == "INFO"
        
        # Outreach: Enabled
        assert staging["auto_send_emails"] is True
        
        # Shutdown: Standard
        assert staging["shutdown_timeout_seconds"] == 60.0
    
    def test_production_profile_defaults(self):
        """Test production profile has expected values."""
        prod = PROFILE_DEFAULTS["production"]
        
        # Concurrency: High
        assert prod["worker_count"] == 10
        assert prod["max_concurrent_api_calls"] == 20
        assert prod["queue_size"] == 100
        
        # Retry: Aggressive
        assert prod["max_retries"] == 5
        assert prod["max_delay"] == 60.0
        
        # Rate limiting: Optimized
        assert prod["llm_rate_limit"] == 15.0
        assert prod["email_rate_limit"] == 2.0
        
        # Database: Large pool
        assert prod["db_pool_size"] == 20
        assert prod["db_max_overflow"] == 30
        
        # Logging: Minimal
        assert prod["log_level"] == "WARNING"
        
        # Progress: Disabled
        assert prod["enable_progress_bar"] is False
        
        # Shutdown: Extended
        assert prod["shutdown_timeout_seconds"] == 120.0


class TestProfileLoading:
    """Test loading configuration from profiles."""
    
    def test_load_development_profile(self):
        """Test loading development profile."""
        config = ProcessorConfig.from_profile("development")
        
        assert config.worker_count == 2
        assert config.log_level == "DEBUG"
        assert config.auto_send_emails is False
        
        # Validate config is valid
        config.validate()
    
    def test_load_staging_profile(self):
        """Test loading staging profile."""
        config = ProcessorConfig.from_profile("staging")
        
        assert config.worker_count == 5
        assert config.log_level == "INFO"
        assert config.auto_send_emails is True
        
        config.validate()
    
    def test_load_production_profile(self):
        """Test loading production profile."""
        config = ProcessorConfig.from_profile("production")
        
        assert config.worker_count == 10
        assert config.log_level == "WARNING"
        assert config.enable_progress_bar is False
        
        config.validate()
    
    def test_invalid_profile_raises_error(self):
        """Test that invalid profile name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ProcessorConfig.from_profile("invalid_profile")  # type: ignore
        
        assert "Invalid profile 'invalid_profile'" in str(exc_info.value)
        assert "development" in str(exc_info.value)
        assert "staging" in str(exc_info.value)
        assert "production" in str(exc_info.value)


class TestProfileOverrides:
    """Test overriding profile defaults."""
    
    def test_override_single_value(self):
        """Test overriding a single configuration value."""
        config = ProcessorConfig.from_profile(
            "development",
            worker_count=10
        )
        
        # Overridden value
        assert config.worker_count == 10
        
        # Other values from profile
        assert config.log_level == "DEBUG"
        assert config.auto_send_emails is False
    
    def test_override_multiple_values(self):
        """Test overriding multiple configuration values."""
        config = ProcessorConfig.from_profile(
            "production",
            worker_count=20,
            log_level="INFO",
            enable_progress_bar=True
        )
        
        # Overridden values
        assert config.worker_count == 20
        assert config.log_level == "INFO"
        assert config.enable_progress_bar is True
        
        # Other values from profile
        assert config.max_retries == 5
        assert config.db_pool_size == 20
    
    def test_override_with_validation(self):
        """Test that overridden values are still validated."""
        with pytest.raises(ValueError) as exc_info:
            ProcessorConfig.from_profile(
                "production",
                worker_count=-5  # Invalid: negative
            )
        
        assert "worker_count must be positive" in str(exc_info.value)


class TestEnvironmentVariableSelection:
    """Test profile selection via environment variable."""
    
    def test_get_current_profile_default(self):
        """Test get_current_profile returns development by default."""
        # Save original values
        original_nexus = os.environ.get("NEXUS_ENV")
        original_pipeline = os.environ.get("PIPELINE_PROFILE")
        
        try:
            # Remove both environment variables
            if "NEXUS_ENV" in os.environ:
                del os.environ["NEXUS_ENV"]
            if "PIPELINE_PROFILE" in os.environ:
                del os.environ["PIPELINE_PROFILE"]
            
            profile = get_current_profile()
            assert profile == "development"
        finally:
            # Restore original values
            if original_nexus is not None:
                os.environ["NEXUS_ENV"] = original_nexus
            if original_pipeline is not None:
                os.environ["PIPELINE_PROFILE"] = original_pipeline
    
    def test_get_current_profile_from_nexus_env(self):
        """Test get_current_profile reads from NEXUS_ENV (primary)."""
        original_nexus = os.environ.get("NEXUS_ENV")
        original_pipeline = os.environ.get("PIPELINE_PROFILE")
        
        try:
            os.environ["NEXUS_ENV"] = "production"
            profile = get_current_profile()
            assert profile == "production"
            
            os.environ["NEXUS_ENV"] = "staging"
            profile = get_current_profile()
            assert profile == "staging"
        finally:
            if original_nexus is not None:
                os.environ["NEXUS_ENV"] = original_nexus
            elif "NEXUS_ENV" in os.environ:
                del os.environ["NEXUS_ENV"]
            if original_pipeline is not None:
                os.environ["PIPELINE_PROFILE"] = original_pipeline
            elif "PIPELINE_PROFILE" in os.environ:
                del os.environ["PIPELINE_PROFILE"]
    
    def test_get_current_profile_nexus_env_takes_precedence(self):
        """Test that NEXUS_ENV takes precedence over PIPELINE_PROFILE."""
        original_nexus = os.environ.get("NEXUS_ENV")
        original_pipeline = os.environ.get("PIPELINE_PROFILE")
        
        try:
            # Set both variables - NEXUS_ENV should win
            os.environ["NEXUS_ENV"] = "production"
            os.environ["PIPELINE_PROFILE"] = "staging"
            
            profile = get_current_profile()
            assert profile == "production", "NEXUS_ENV should take precedence over PIPELINE_PROFILE"
        finally:
            if original_nexus is not None:
                os.environ["NEXUS_ENV"] = original_nexus
            elif "NEXUS_ENV" in os.environ:
                del os.environ["NEXUS_ENV"]
            if original_pipeline is not None:
                os.environ["PIPELINE_PROFILE"] = original_pipeline
            elif "PIPELINE_PROFILE" in os.environ:
                del os.environ["PIPELINE_PROFILE"]
    
    def test_get_current_profile_backward_compatible_with_pipeline_profile(self):
        """Test backward compatibility with PIPELINE_PROFILE when NEXUS_ENV is not set."""
        original_nexus = os.environ.get("NEXUS_ENV")
        original_pipeline = os.environ.get("PIPELINE_PROFILE")
        
        try:
            # Remove NEXUS_ENV, set PIPELINE_PROFILE
            if "NEXUS_ENV" in os.environ:
                del os.environ["NEXUS_ENV"]
            os.environ["PIPELINE_PROFILE"] = "staging"
            
            profile = get_current_profile()
            assert profile == "staging", "Should fall back to PIPELINE_PROFILE when NEXUS_ENV not set"
        finally:
            if original_nexus is not None:
                os.environ["NEXUS_ENV"] = original_nexus
            elif "NEXUS_ENV" in os.environ:
                del os.environ["NEXUS_ENV"]
            if original_pipeline is not None:
                os.environ["PIPELINE_PROFILE"] = original_pipeline
            elif "PIPELINE_PROFILE" in os.environ:
                del os.environ["PIPELINE_PROFILE"]
    
    def test_get_current_profile_invalid_raises_error(self):
        """Test that invalid NEXUS_ENV raises ValueError."""
        original = os.environ.get("NEXUS_ENV")
        
        try:
            os.environ["NEXUS_ENV"] = "invalid"
            
            with pytest.raises(ValueError) as exc_info:
                get_current_profile()
            
            assert "Invalid NEXUS_ENV environment variable" in str(exc_info.value)
            assert "'invalid'" in str(exc_info.value)
        finally:
            if original is not None:
                os.environ["NEXUS_ENV"] = original
            elif "NEXUS_ENV" in os.environ:
                del os.environ["NEXUS_ENV"]
    
    def test_load_profile_from_environment(self):
        """Test loading profile using NEXUS_ENV environment variable."""
        original = os.environ.get("NEXUS_ENV")
        
        try:
            os.environ["NEXUS_ENV"] = "production"
            
            profile = get_current_profile()
            config = ProcessorConfig.from_profile(profile)
            
            assert config.worker_count == 10
            assert config.log_level == "WARNING"
        finally:
            if original is not None:
                os.environ["NEXUS_ENV"] = original
            elif "NEXUS_ENV" in os.environ:
                del os.environ["NEXUS_ENV"]


class TestProfileCharacteristics:
    """Test that profiles have appropriate characteristics for their environment."""
    
    def test_development_is_conservative(self):
        """Test development profile is conservative (low throughput, high safety)."""
        config = ProcessorConfig.from_profile("development")
        
        # Low throughput
        assert config.worker_count <= 3
        assert config.queue_size <= 50
        
        # High safety
        assert config.log_level == "DEBUG"
        assert config.enable_progress_bar is True
        assert config.auto_send_emails is False
        
        # Fast feedback
        assert config.max_retries <= 2
        assert config.shutdown_timeout_seconds <= 30
    
    def test_staging_is_moderate(self):
        """Test staging profile is moderate (balanced throughput and safety)."""
        config = ProcessorConfig.from_profile("staging")
        
        # Moderate throughput
        assert 3 <= config.worker_count <= 8
        assert 30 <= config.queue_size <= 100
        
        # Standard safety
        assert config.log_level == "INFO"
        assert config.max_retries == 3
        
        # Realistic behavior
        assert config.auto_send_emails is True
    
    def test_production_is_optimized(self):
        """Test production profile is optimized (high throughput, reliability)."""
        config = ProcessorConfig.from_profile("production")
        
        # High throughput
        assert config.worker_count >= 10
        assert config.queue_size >= 100
        assert config.max_concurrent_api_calls >= 20
        
        # Reliability
        assert config.max_retries >= 5
        assert config.shutdown_timeout_seconds >= 120
        
        # Optimized settings
        assert config.log_level in ("WARNING", "ERROR")
        assert config.enable_progress_bar is False
        assert config.db_pool_size >= 20
    
    def test_profiles_are_progressively_more_aggressive(self):
        """Test that profiles scale from conservative to aggressive."""
        dev = ProcessorConfig.from_profile("development")
        staging = ProcessorConfig.from_profile("staging")
        prod = ProcessorConfig.from_profile("production")
        
        # Worker count increases
        assert dev.worker_count < staging.worker_count < prod.worker_count
        
        # Queue size increases
        assert dev.queue_size < staging.queue_size <= prod.queue_size
        
        # Retry attempts increase
        assert dev.max_retries <= staging.max_retries < prod.max_retries
        
        # Rate limits increase
        assert dev.llm_rate_limit < staging.llm_rate_limit < prod.llm_rate_limit
        
        # Database pool size increases
        assert dev.db_pool_size < staging.db_pool_size < prod.db_pool_size


class TestProfileValidation:
    """Test that all profiles pass validation."""
    
    def test_development_profile_validates(self):
        """Test development profile passes validation."""
        config = ProcessorConfig.from_profile("development")
        config.validate()  # Should not raise
    
    def test_staging_profile_validates(self):
        """Test staging profile passes validation."""
        config = ProcessorConfig.from_profile("staging")
        config.validate()  # Should not raise
    
    def test_production_profile_validates(self):
        """Test production profile passes validation."""
        config = ProcessorConfig.from_profile("production")
        config.validate()  # Should not raise
    
    def test_all_profile_values_are_positive(self):
        """Test that all numeric values in profiles are positive where required."""
        for profile_name, profile_dict in PROFILE_DEFAULTS.items():
            # These values must be positive
            positive_fields = [
                "worker_count", "max_concurrent_api_calls", "queue_size",
                "chunk_size", "base_delay", "max_delay", "exponential_base",
                "llm_rate_limit", "email_rate_limit", "scraper_rate_limit",
                "llm_timeout_seconds", "email_timeout_seconds",
                "scraper_timeout_seconds", "db_timeout_seconds",
                "db_pool_size", "shutdown_timeout_seconds"
            ]
            
            for field in positive_fields:
                value = profile_dict.get(field)
                assert value is not None, f"{profile_name}.{field} is missing"
                assert value > 0, f"{profile_name}.{field}={value} must be positive"
    
    def test_all_profile_max_delay_gte_base_delay(self):
        """Test that max_delay >= base_delay in all profiles."""
        for profile_name, profile_dict in PROFILE_DEFAULTS.items():
            max_delay = profile_dict["max_delay"]
            base_delay = profile_dict["base_delay"]
            assert max_delay >= base_delay, \
                f"{profile_name}: max_delay ({max_delay}) < base_delay ({base_delay})"


class TestProfileDocumentation:
    """Test that profiles are properly documented."""
    
    def test_all_profiles_have_required_fields(self):
        """Test that all profiles define all required configuration fields."""
        required_fields = {
            "worker_count", "max_concurrent_api_calls", "queue_size", "chunk_size",
            "max_retries", "base_delay", "max_delay", "exponential_base", "retry_jitter",
            "llm_rate_limit", "email_rate_limit", "scraper_rate_limit",
            "llm_timeout_seconds", "email_timeout_seconds", "scraper_timeout_seconds", "db_timeout_seconds",
            "db_pool_size", "db_max_overflow",
            "log_level", "structured_logging", "log_file",
            "enable_progress_bar", "progress_update_interval",
            "min_match_score", "max_contacts_per_job",
            "auto_send_emails", "email_delay_seconds",
            "shutdown_timeout_seconds"
        }
        
        for profile_name, profile_dict in PROFILE_DEFAULTS.items():
            actual_fields = set(profile_dict.keys())
            missing_fields = required_fields - actual_fields
            
            assert not missing_fields, \
                f"{profile_name} is missing fields: {missing_fields}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
