"""Configuration management for transcriber service."""

import os
from pathlib import Path
from typing import Literal, Optional

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

    # Hallucination Mitigation
    condition_on_previous_text: bool = False
    compression_ratio_threshold: float = 2.4
    no_speech_threshold: float = 0.6
    logprob_threshold: float = -1.0
    temperature: str = "0.0,0.2,0.4,0.6,0.8,1.0"
    hallucination_silence_threshold: Optional[float] = 2.0
    initial_prompt: Optional[str] = None

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
