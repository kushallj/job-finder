"""Tests for src.config module."""
import pytest
from src.config import Settings, settings


class TestSettingsLoadsFromEnv:
    """Verify settings object exists and loads values from .env."""

    def test_settings_loads_from_env(self):
        """Settings singleton should exist and be a Settings instance."""
        assert settings is not None
        assert isinstance(settings, Settings)
        # Should have loaded required fields (they'd fail validation otherwise)
        assert hasattr(settings, "adzuna_app_id")
        assert hasattr(settings, "adzuna_app_key")
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "google_credentials_path")
        assert hasattr(settings, "gmail_address")


class TestSettingsHasAdzunaKeys:
    """Verify Adzuna API keys are present and non-empty."""

    def test_settings_has_adzuna_keys(self):
        """settings.adzuna_app_id should be a non-empty string."""
        assert settings.adzuna_app_id is not None
        assert isinstance(settings.adzuna_app_id, str)
        assert len(settings.adzuna_app_id) > 0


class TestSettingsDatabaseUrl:
    """Verify database_url contains 'sqlite'."""

    def test_settings_database_url(self):
        """settings.database_url should contain 'sqlite'."""
        assert settings.database_url is not None
        assert "sqlite" in settings.database_url.lower()


class TestSettingsRedisUrl:
    """Verify redis_url starts with 'redis://'."""

    def test_settings_redis_url(self):
        """settings.redis_url should start with 'redis://'."""
        assert settings.redis_url is not None
        assert settings.redis_url.startswith("redis://")


class TestSettingsEmailProviderDefault:
    """Verify email_provider default is 'smtp' or matches .env value."""

    def test_settings_email_provider_default(self):
        """email_provider should be 'smtp' (default) or a valid provider string."""
        assert settings.email_provider is not None
        assert isinstance(settings.email_provider, str)
        # Default is 'smtp'; if overridden via .env it should still be a valid provider
        valid_providers = {"smtp", "sendgrid", "ses"}
        assert settings.email_provider in valid_providers


class TestSettingsEnvDevelopment:
    """Verify settings.env is 'development'."""

    def test_settings_env_development(self):
        """settings.env should be 'development'."""
        assert settings.env == "development"


class TestSettingsOptionalFields:
    """Verify optional fields can be None."""

    def test_settings_optional_fields(self):
        """gemini_api_key can be None (it's Optional[str])."""
        # This just verifies the field exists and accepts None as a valid value
        # If it's set via .env, it will be a string; if not, it will be None
        assert hasattr(settings, "gemini_api_key")
        if settings.gemini_api_key is not None:
            assert isinstance(settings.gemini_api_key, str)
        # The field type allows None — that's what we're testing
        fresh = Settings.model_fields["gemini_api_key"]
        assert fresh.default is None


class TestSettingsOllamaModel:
    """Verify ollama_model is a string."""

    def test_settings_ollama_model(self):
        """settings.ollama_model should be a non-empty string."""
        assert settings.ollama_model is not None
        assert isinstance(settings.ollama_model, str)
        assert len(settings.ollama_model) > 0
