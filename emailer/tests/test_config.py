"""Tests for configuration module."""

import os
import pytest


def test_config_loads_from_environment(monkeypatch):
    """Test that config loads all required settings from environment."""
    # Set required environment variables
    monkeypatch.setenv("IMAP_HOST", "imap.test.com")
    monkeypatch.setenv("IMAP_PORT", "993")
    monkeypatch.setenv("IMAP_USER", "test@test.com")
    monkeypatch.setenv("IMAP_PASSWORD", "testpass")
    monkeypatch.setenv("IMAP_USE_SSL", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "test@test.com")
    monkeypatch.setenv("SMTP_PASSWORD", "testpass")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("RESULT_EMAIL_ADDRESS", "results@test.com")
    monkeypatch.setenv("FROM_EMAIL_ADDRESS", "scribe@test.com")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:8000")

    from emailer.config import Settings
    settings = Settings()

    assert settings.imap_host == "imap.test.com"
    assert settings.imap_port == 993
    assert settings.smtp_host == "smtp.test.com"
    assert settings.poll_interval_seconds == 30  # default
    assert settings.max_concurrent_jobs == 3  # default


def test_config_validates_required_fields(monkeypatch):
    """Test that config raises error for missing required fields."""
    # Clear any existing env vars
    for key in ["IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)

    from pydantic import ValidationError
    from emailer.config import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_config_defaults(monkeypatch):
    """Test that config uses correct defaults."""
    # Set only required fields
    monkeypatch.setenv("IMAP_HOST", "imap.test.com")
    monkeypatch.setenv("IMAP_PORT", "993")
    monkeypatch.setenv("IMAP_USER", "test@test.com")
    monkeypatch.setenv("IMAP_PASSWORD", "testpass")
    monkeypatch.setenv("IMAP_USE_SSL", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "test@test.com")
    monkeypatch.setenv("SMTP_PASSWORD", "testpass")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("RESULT_EMAIL_ADDRESS", "results@test.com")
    monkeypatch.setenv("FROM_EMAIL_ADDRESS", "scribe@test.com")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:8000")

    from emailer.config import Settings
    settings = Settings()

    assert settings.imap_folder_inbox == "ToScribe"
    assert settings.imap_folder_done == "ScribeDone"
    assert settings.imap_folder_error == "ScribeError"
    assert settings.poll_interval_seconds == 30
    assert settings.max_concurrent_jobs == 3
    assert settings.default_tag == "email"


def test_default_tag_config(monkeypatch):
    """Test that default_tag can be configured."""
    monkeypatch.setenv("DEFAULT_TAG", "inbox")
    monkeypatch.setenv("IMAP_HOST", "imap.test.com")
    monkeypatch.setenv("IMAP_USER", "test")
    monkeypatch.setenv("IMAP_PASSWORD", "test")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_USER", "test")
    monkeypatch.setenv("SMTP_PASSWORD", "test")
    monkeypatch.setenv("RESULT_EMAIL_ADDRESS", "results@test.com")
    monkeypatch.setenv("FROM_EMAIL_ADDRESS", "scribe@test.com")

    from emailer.config import Settings
    settings = Settings()
    assert settings.default_tag == "inbox"
