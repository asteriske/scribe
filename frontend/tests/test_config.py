"""Test configuration loading."""
import os
from pathlib import Path
from frontend.core.config import Settings


def test_settings_defaults():
    """Test default settings values"""
    settings = Settings()
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.transcriber_url == "http://localhost:8001"
    assert settings.audio_cache_days == 7


def test_settings_from_env(monkeypatch):
    """Test settings load from environment"""
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("AUDIO_CACHE_DAYS", "14")
    settings = Settings()
    assert settings.port == 9000
    assert settings.audio_cache_days == 14
