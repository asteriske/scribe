"""Configuration management for transcriber service."""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 1
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Model Configuration
    whisper_model: Literal["tiny", "base", "small", "medium", "large-v3"] = "medium"
    model_dir: Path = Path.home() / ".cache" / "whisper"
    compute_type: Literal["float16", "float32"] = "float16"

    # Job Queue Configuration
    max_concurrent_jobs: int = 1
    queue_size: int = 10
    job_retention_hours: int = 1

    # Logging Configuration
    log_file: Path = Path("data/logs/transcriber.log")
    log_format: Literal["json", "text"] = "text"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
