"""Tests for src.config: the code's defaults, independent of the machine's .env.

These used to assert on the live `settings` singleton, so they passed or failed depending
on the developer's .env (Postgres DATABASE_URL, whether an Adzuna key was set). Each test
now builds Settings with no env file and a scrubbed environment.
"""

import pytest

from src.config import Settings, settings

SCRUB = ("DATABASE_URL", "REDIS_URL", "ENV", "EMAIL_PROVIDER", "ADZUNA_APP_ID", "ADZUNA_APP_KEY", "GEMINI_API_KEY")


@pytest.fixture
def defaults(monkeypatch) -> Settings:
    for key in SCRUB:
        monkeypatch.delenv(key, raising=False)
    return Settings(_env_file=None)


def test_singleton_exposes_core_fields():
    assert isinstance(settings, Settings)
    for name in ("adzuna_app_id", "adzuna_app_key", "database_url", "redis_url", "google_credentials_path", "gmail_address"):
        assert hasattr(settings, name)


def test_adzuna_keys_default_to_empty_strings(defaults):
    # Optional source: empty means "not configured" and the source stays off.
    assert defaults.adzuna_app_id == "" and defaults.adzuna_app_key == ""


def test_database_url_defaults_to_local_sqlite(defaults):
    assert defaults.database_url.lower().startswith("sqlite")


def test_redis_url_default(defaults):
    assert defaults.redis_url.startswith("redis://")


def test_email_provider_default_is_valid(defaults):
    assert defaults.email_provider in {"smtp", "sendgrid", "ses"}


def test_env_defaults_to_development(defaults):
    assert defaults.env == "development" and not defaults.is_production


def test_optional_keys_default_to_unset(defaults):
    assert defaults.gemini_api_key in (None, "")


def test_env_vars_override_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/x")
    monkeypatch.setenv("ENV", "staging")
    s = Settings(_env_file=None)
    assert s.database_url == "postgresql://u:p@db:5432/x" and s.env == "staging"
