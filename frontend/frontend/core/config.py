"""Configuration management for frontend service."""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Service Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Transcriber Service
    transcriber_url: str = "http://localhost:8001"
    transcriber_timeout: int = 300  # 5 minutes

    # Storage Configuration
    data_dir: Path = Path("data")
    transcriptions_dir: Path = Path("data/transcriptions")
    audio_cache_dir: Path = Path("data/cache/audio")
    database_url: str = "sqlite:///data/scribe.db"

    # Audio Cache
    audio_cache_days: int = 7

    # Download Configuration
    max_audio_size_mb: int = 500
    download_timeout: int = 600  # 10 minutes

    # WebSocket Configuration
    ws_heartbeat_interval: int = 30

    # Logging Configuration
    log_file: Path = Path("data/logs/frontend.log")
    log_format: Literal["json", "text"] = "text"


# Global settings instance
settings = Settings()
