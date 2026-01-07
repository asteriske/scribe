"""Configuration settings for emailer service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Emailer service settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".secrets"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # IMAP Settings
    imap_host: str
    imap_port: int = 993
    imap_user: str
    imap_password: str
    imap_use_ssl: bool = True

    # SMTP Settings
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool = True

    # Folder Names
    imap_folder_inbox: str = "ToScribe"
    imap_folder_done: str = "ScribeDone"
    imap_folder_error: str = "ScribeError"

    # Processing
    poll_interval_seconds: int = 300
    max_concurrent_jobs: int = 3

    # Destinations
    result_email_address: str
    from_email_address: str

    # Frontend Service
    frontend_url: str = "http://localhost:8000"


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()
