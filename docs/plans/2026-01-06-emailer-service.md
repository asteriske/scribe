# Emailer Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a standalone email processing service that monitors an IMAP folder for transcription requests and emails results.

**Architecture:** Async Python service using aioimaplib/aiosmtplib for email, httpx for frontend API calls. Single process with semaphore-controlled concurrency. Polls IMAP folder, extracts URLs, submits to frontend API, emails results.

**Tech Stack:** Python 3.10+, aioimaplib, aiosmtplib, httpx, pydantic-settings, beautifulsoup4, pytest-asyncio

---

## Task 1: Project Scaffolding

**Files:**
- Create: `emailer/emailer/__init__.py`
- Create: `emailer/emailer/main.py`
- Create: `emailer/tests/__init__.py`
- Create: `emailer/requirements.txt`
- Create: `emailer/.env.example`
- Create: `emailer/.secrets.example`
- Create: `emailer/README.md`

**Step 1: Create directory structure**

```bash
mkdir -p emailer/emailer emailer/tests
```

**Step 2: Create `emailer/emailer/__init__.py`**

```python
"""Emailer service for Scribe transcription system."""

__version__ = "0.1.0"
```

**Step 3: Create `emailer/emailer/main.py` (stub)**

```python
"""Main entry point for the emailer service."""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    logger.info("Emailer service starting...")
    # TODO: Implement main loop
    logger.info("Emailer service stopped.")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Create `emailer/tests/__init__.py`**

```python
"""Tests for emailer service."""
```

**Step 5: Create `emailer/requirements.txt`**

```
aioimaplib>=1.0.0
aiosmtplib>=3.0.0
httpx>=0.26.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

**Step 6: Create `emailer/.env.example`**

```bash
# IMAP Settings
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USER=scribe@example.com
IMAP_USE_SSL=true

# SMTP Settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=scribe@example.com
SMTP_USE_TLS=true

# Folder Names
IMAP_FOLDER_INBOX=ToScribe
IMAP_FOLDER_DONE=ScribeDone
IMAP_FOLDER_ERROR=ScribeError

# Processing
POLL_INTERVAL_SECONDS=300
MAX_CONCURRENT_JOBS=3

# Destinations
RESULT_EMAIL_ADDRESS=results@example.com
FROM_EMAIL_ADDRESS=scribe@example.com

# Frontend Service
FRONTEND_URL=http://localhost:8000
```

**Step 7: Create `emailer/.secrets.example`**

```bash
# Email account passwords
# Copy this file to .secrets and fill in real values
# NEVER commit .secrets to version control

IMAP_PASSWORD=your_imap_password_here
SMTP_PASSWORD=your_smtp_password_here
```

**Step 8: Create `emailer/README.md`**

```markdown
# Emailer Service

Email-based job submission for Scribe transcription system.

## Overview

Monitors an IMAP folder for emails containing transcribable URLs, processes them through the frontend API, and sends results via email.

## Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   cp .secrets.example .secrets
   # Edit .env and .secrets with your settings
   ```

3. Create IMAP folders:
   - `ToScribe` - Inbox for transcription requests
   - `ScribeDone` - Completed requests
   - `ScribeError` - Failed requests

4. Run the service:
   ```bash
   python -m emailer.main
   ```

## Configuration

See `.env.example` for all configuration options.

Passwords are stored separately in `.secrets` (not committed to git).
```

**Step 9: Verify structure and commit**

```bash
ls -la emailer/
ls -la emailer/emailer/
ls -la emailer/tests/
git add emailer/
git commit -m "feat(emailer): scaffold project structure"
```

---

## Task 2: Configuration Module

**Files:**
- Create: `emailer/emailer/config.py`
- Create: `emailer/tests/test_config.py`

**Step 1: Write failing test for config loading**

Create `emailer/tests/test_config.py`:

```python
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
    assert settings.poll_interval_seconds == 300  # default
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
    assert settings.poll_interval_seconds == 300
    assert settings.max_concurrent_jobs == 3
```

**Step 2: Run test to verify it fails**

```bash
cd emailer && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt -q
PYTHONPATH=. pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'emailer.config'`

**Step 3: Write config implementation**

Create `emailer/emailer/config.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest tests/test_config.py -v
```

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/config.py emailer/tests/test_config.py
git commit -m "feat(emailer): add configuration module with validation"
```

---

## Task 3: URL Extractor

**Files:**
- Create: `emailer/emailer/url_extractor.py`
- Create: `emailer/tests/test_url_extractor.py`

**Step 1: Write failing tests for URL extraction**

Create `emailer/tests/test_url_extractor.py`:

```python
"""Tests for URL extraction from emails."""

import pytest
from emailer.url_extractor import extract_urls, is_transcribable_url


class TestIsTranscribableUrl:
    """Tests for URL validation."""

    def test_youtube_watch_url(self):
        assert is_transcribable_url("https://www.youtube.com/watch?v=abc123")

    def test_youtube_short_url(self):
        assert is_transcribable_url("https://youtu.be/abc123")

    def test_apple_podcasts_url(self):
        assert is_transcribable_url("https://podcasts.apple.com/us/podcast/episode/id123")

    def test_direct_mp3_url(self):
        assert is_transcribable_url("https://example.com/audio.mp3")

    def test_direct_m4a_url(self):
        assert is_transcribable_url("https://example.com/audio.m4a")

    def test_direct_wav_url(self):
        assert is_transcribable_url("https://example.com/audio.wav")

    def test_non_transcribable_url(self):
        assert not is_transcribable_url("https://google.com")

    def test_non_transcribable_image_url(self):
        assert not is_transcribable_url("https://example.com/image.jpg")


class TestExtractUrls:
    """Tests for URL extraction from email content."""

    def test_extract_single_youtube_url(self):
        body = "Please transcribe this: https://www.youtube.com/watch?v=abc123"
        urls = extract_urls(body)
        assert urls == ["https://www.youtube.com/watch?v=abc123"]

    def test_extract_multiple_urls(self):
        body = """
        Here are some videos:
        https://www.youtube.com/watch?v=abc123
        https://youtu.be/def456
        """
        urls = extract_urls(body)
        assert len(urls) == 2
        assert "https://www.youtube.com/watch?v=abc123" in urls
        assert "https://youtu.be/def456" in urls

    def test_extract_from_html(self):
        body = """
        <html>
        <body>
        <a href="https://www.youtube.com/watch?v=abc123">Watch this</a>
        </body>
        </html>
        """
        urls = extract_urls(body, is_html=True)
        assert urls == ["https://www.youtube.com/watch?v=abc123"]

    def test_deduplicate_urls(self):
        body = """
        https://www.youtube.com/watch?v=abc123
        Check out https://www.youtube.com/watch?v=abc123 again
        """
        urls = extract_urls(body)
        assert urls == ["https://www.youtube.com/watch?v=abc123"]

    def test_ignore_non_transcribable_urls(self):
        body = """
        Visit https://google.com for more info
        But transcribe https://www.youtube.com/watch?v=abc123
        """
        urls = extract_urls(body)
        assert urls == ["https://www.youtube.com/watch?v=abc123"]

    def test_empty_body_returns_empty_list(self):
        assert extract_urls("") == []

    def test_no_urls_returns_empty_list(self):
        body = "No URLs here, just text."
        assert extract_urls(body) == []
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. pytest tests/test_url_extractor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'emailer.url_extractor'`

**Step 3: Write URL extractor implementation**

Create `emailer/emailer/url_extractor.py`:

```python
"""Extract transcribable URLs from email content."""

import re
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Patterns for transcribable URLs
TRANSCRIBABLE_PATTERNS = [
    r"youtube\.com/watch",
    r"youtu\.be/",
    r"podcasts\.apple\.com/",
]

# File extensions for direct audio URLs
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac"}

# URL regex pattern
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\)\]]+",
    re.IGNORECASE
)


def is_transcribable_url(url: str) -> bool:
    """
    Check if a URL is transcribable.

    Args:
        url: URL to check

    Returns:
        True if the URL is a supported transcribable source
    """
    # Check known patterns
    for pattern in TRANSCRIBABLE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True

    # Check for direct audio file URLs
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    for ext in AUDIO_EXTENSIONS:
        if path_lower.endswith(ext):
            return True

    return False


def extract_urls(body: str, is_html: bool = False) -> List[str]:
    """
    Extract transcribable URLs from email body.

    Args:
        body: Email body content
        is_html: Whether the body is HTML content

    Returns:
        List of unique transcribable URLs found in the body
    """
    if not body:
        return []

    urls = set()

    if is_html:
        # Parse HTML and extract URLs from href attributes and text
        soup = BeautifulSoup(body, "html.parser")

        # Get URLs from anchor tags
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if is_transcribable_url(href):
                urls.add(href)

        # Also search text content for URLs
        text = soup.get_text()
        for match in URL_PATTERN.findall(text):
            # Clean trailing punctuation
            clean_url = match.rstrip(".,;:!?)")
            if is_transcribable_url(clean_url):
                urls.add(clean_url)
    else:
        # Plain text - use regex to find URLs
        for match in URL_PATTERN.findall(body):
            # Clean trailing punctuation
            clean_url = match.rstrip(".,;:!?)")
            if is_transcribable_url(clean_url):
                urls.add(clean_url)

    return list(urls)
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest tests/test_url_extractor.py -v
```

Expected: All 14 tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/url_extractor.py emailer/tests/test_url_extractor.py
git commit -m "feat(emailer): add URL extraction from email content"
```

---

## Task 4: Result Formatter

**Files:**
- Create: `emailer/emailer/result_formatter.py`
- Create: `emailer/tests/test_result_formatter.py`

**Step 1: Write failing tests for result formatting**

Create `emailer/tests/test_result_formatter.py`:

```python
"""Tests for result email formatting."""

import pytest
from emailer.result_formatter import (
    format_success_email,
    format_error_email,
    format_no_urls_email,
)


class TestFormatSuccessEmail:
    """Tests for success email formatting."""

    def test_basic_format(self):
        subject, body = format_success_email(
            url="https://www.youtube.com/watch?v=abc123",
            title="Test Video",
            duration_seconds=125,
            summary="This is the summary.",
            transcript="This is the full transcript.",
        )

        assert subject == "[Scribe] Test Video"
        assert "https://www.youtube.com/watch?v=abc123" in body
        assert "2:05" in body  # duration formatted
        assert "--- SUMMARY ---" in body
        assert "This is the summary." in body
        assert "--- TRANSCRIPT ---" in body
        assert "This is the full transcript." in body

    def test_long_title_in_subject(self):
        long_title = "A" * 100
        subject, _ = format_success_email(
            url="https://youtu.be/abc",
            title=long_title,
            duration_seconds=60,
            summary="Summary",
            transcript="Transcript",
        )
        # Subject should be reasonable length
        assert len(subject) <= 120


class TestFormatErrorEmail:
    """Tests for error email formatting."""

    def test_basic_format(self):
        subject, body = format_error_email(
            url="https://www.youtube.com/watch?v=abc123",
            error_message="Video not available",
        )

        assert subject == "[Scribe Error] Failed to process URL"
        assert "https://www.youtube.com/watch?v=abc123" in body
        assert "Video not available" in body


class TestFormatNoUrlsEmail:
    """Tests for no URLs found email formatting."""

    def test_basic_format(self):
        subject, body = format_no_urls_email()

        assert subject == "[Scribe Error] No transcribable URLs found"
        assert "did not contain any transcribable URLs" in body
        assert "YouTube" in body
        assert "Apple Podcasts" in body
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. pytest tests/test_result_formatter.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'emailer.result_formatter'`

**Step 3: Write result formatter implementation**

Create `emailer/emailer/result_formatter.py`:

```python
"""Format emails for transcription results and errors."""

from datetime import datetime, timezone
from typing import Tuple


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}:{secs:02d}"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{mins:02d}:{secs:02d}"


def format_success_email(
    url: str,
    title: str,
    duration_seconds: int,
    summary: str,
    transcript: str,
) -> Tuple[str, str]:
    """
    Format a success email with summary and transcript.

    Args:
        url: Source URL
        title: Content title
        duration_seconds: Duration in seconds
        summary: Generated summary text
        transcript: Full transcript text

    Returns:
        Tuple of (subject, body)
    """
    # Truncate title for subject if too long
    max_title_len = 100
    display_title = title[:max_title_len] + "..." if len(title) > max_title_len else title
    subject = f"[Scribe] {display_title}"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    duration = _format_duration(duration_seconds)

    body = f"""Source: {url}
Duration: {duration}
Transcribed: {timestamp}

--- SUMMARY ---

{summary}

--- TRANSCRIPT ---

{transcript}
"""

    return subject, body


def format_error_email(
    url: str,
    error_message: str,
) -> Tuple[str, str]:
    """
    Format an error notification email.

    Args:
        url: URL that failed
        error_message: Error description

    Returns:
        Tuple of (subject, body)
    """
    subject = "[Scribe Error] Failed to process URL"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""The following URL could not be transcribed:

{url}

Error: {error_message}

---
Original request received: {timestamp}
"""

    return subject, body


def format_no_urls_email() -> Tuple[str, str]:
    """
    Format an email for when no transcribable URLs were found.

    Returns:
        Tuple of (subject, body)
    """
    subject = "[Scribe Error] No transcribable URLs found"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""Your email did not contain any transcribable URLs.

Supported sources:
- YouTube (youtube.com, youtu.be)
- Apple Podcasts (podcasts.apple.com)
- Direct audio URLs (.mp3, .m4a, .wav)

---
Original request received: {timestamp}
"""

    return subject, body
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest tests/test_result_formatter.py -v
```

Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/result_formatter.py emailer/tests/test_result_formatter.py
git commit -m "feat(emailer): add result email formatting"
```

---

## Task 5: IMAP Client

**Files:**
- Create: `emailer/emailer/imap_client.py`
- Create: `emailer/tests/test_imap_client.py`

**Step 1: Write failing tests for IMAP client**

Create `emailer/tests/test_imap_client.py`:

```python
"""Tests for IMAP client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from emailer.imap_client import ImapClient, EmailMessage


class TestEmailMessage:
    """Tests for EmailMessage dataclass."""

    def test_email_message_creation(self):
        msg = EmailMessage(
            uid="123",
            sender="test@example.com",
            subject="Test Subject",
            body_text="Plain text body",
            body_html="<p>HTML body</p>",
        )
        assert msg.uid == "123"
        assert msg.sender == "test@example.com"
        assert msg.subject == "Test Subject"


class TestImapClient:
    """Tests for ImapClient."""

    @pytest.mark.asyncio
    async def test_connect_creates_connection(self):
        """Test that connect establishes IMAP connection."""
        with patch("emailer.imap_client.IMAP4_SSL") as mock_imap:
            mock_instance = AsyncMock()
            mock_imap.return_value = mock_instance
            mock_instance.wait_hello_from_server = AsyncMock()
            mock_instance.login = AsyncMock(return_value=("OK", []))

            client = ImapClient(
                host="imap.test.com",
                port=993,
                user="test@test.com",
                password="testpass",
                use_ssl=True,
            )

            await client.connect()

            mock_imap.assert_called_once_with(host="imap.test.com", port=993)
            mock_instance.login.assert_called_once_with("test@test.com", "testpass")

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self):
        """Test that disconnect closes IMAP connection."""
        client = ImapClient(
            host="imap.test.com",
            port=993,
            user="test@test.com",
            password="testpass",
            use_ssl=True,
        )
        client._client = AsyncMock()
        client._client.logout = AsyncMock()

        await client.disconnect()

        client._client.logout.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_seen_sets_flag(self):
        """Test that mark_seen sets the Seen flag."""
        client = ImapClient(
            host="imap.test.com",
            port=993,
            user="test@test.com",
            password="testpass",
            use_ssl=True,
        )
        client._client = AsyncMock()
        client._client.uid = AsyncMock(return_value=("OK", []))

        await client.mark_seen("123")

        client._client.uid.assert_called_with("STORE", "123", "+FLAGS", "\\Seen")

    @pytest.mark.asyncio
    async def test_move_to_folder(self):
        """Test that move_to_folder moves email to destination."""
        client = ImapClient(
            host="imap.test.com",
            port=993,
            user="test@test.com",
            password="testpass",
            use_ssl=True,
        )
        client._client = AsyncMock()
        client._client.uid = AsyncMock(return_value=("OK", []))

        await client.move_to_folder("123", "ScribeDone")

        # Should copy then delete
        calls = client._client.uid.call_args_list
        assert any("COPY" in str(call) and "ScribeDone" in str(call) for call in calls)
        assert any("STORE" in str(call) and "\\Deleted" in str(call) for call in calls)
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. pytest tests/test_imap_client.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'emailer.imap_client'`

**Step 3: Write IMAP client implementation**

Create `emailer/emailer/imap_client.py`:

```python
"""IMAP client for fetching and managing emails."""

import email
import logging
from dataclasses import dataclass
from email.header import decode_header
from typing import List, Optional

from aioimaplib import IMAP4_SSL, IMAP4

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Represents an email message."""

    uid: str
    sender: str
    subject: str
    body_text: Optional[str]
    body_html: Optional[str]


class ImapClient:
    """Async IMAP client for email operations."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        use_ssl: bool = True,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self._client: Optional[IMAP4_SSL | IMAP4] = None

    async def connect(self) -> None:
        """Establish connection to IMAP server."""
        if self.use_ssl:
            self._client = IMAP4_SSL(host=self.host, port=self.port)
        else:
            self._client = IMAP4(host=self.host, port=self.port)

        await self._client.wait_hello_from_server()
        response = await self._client.login(self.user, self.password)

        if response[0] != "OK":
            raise ConnectionError(f"IMAP login failed: {response}")

        logger.info(f"Connected to IMAP server {self.host}")

    async def disconnect(self) -> None:
        """Close IMAP connection."""
        if self._client:
            try:
                await self._client.logout()
            except Exception as e:
                logger.warning(f"Error during IMAP logout: {e}")
            self._client = None
            logger.info("Disconnected from IMAP server")

    async def select_folder(self, folder: str) -> int:
        """
        Select an IMAP folder.

        Args:
            folder: Folder name to select

        Returns:
            Number of messages in folder
        """
        response = await self._client.select(folder)
        if response[0] != "OK":
            raise RuntimeError(f"Failed to select folder {folder}: {response}")
        # Parse message count from response
        return int(response[1][0].decode() if response[1] else 0)

    async def fetch_unseen(self, folder: str) -> List[EmailMessage]:
        """
        Fetch unseen emails from a folder.

        Args:
            folder: Folder to fetch from

        Returns:
            List of EmailMessage objects
        """
        await self.select_folder(folder)

        # Search for unseen messages
        response = await self._client.uid("SEARCH", "UNSEEN")
        if response[0] != "OK":
            raise RuntimeError(f"IMAP search failed: {response}")

        # Parse UIDs from response
        uid_data = response[1][0].decode() if response[1] and response[1][0] else ""
        uids = uid_data.split() if uid_data else []

        if not uids:
            return []

        messages = []
        for uid in uids:
            msg = await self._fetch_message(uid)
            if msg:
                messages.append(msg)

        return messages

    async def _fetch_message(self, uid: str) -> Optional[EmailMessage]:
        """Fetch a single message by UID."""
        response = await self._client.uid("FETCH", uid, "(RFC822)")
        if response[0] != "OK" or not response[1]:
            logger.warning(f"Failed to fetch message {uid}")
            return None

        # Parse the email
        raw_email = None
        for item in response[1]:
            if isinstance(item, tuple) and len(item) >= 2:
                raw_email = item[1]
                break

        if not raw_email:
            return None

        msg = email.message_from_bytes(raw_email)

        # Decode sender
        sender = msg.get("From", "")

        # Decode subject
        subject = ""
        raw_subject = msg.get("Subject", "")
        if raw_subject:
            decoded_parts = decode_header(raw_subject)
            subject = "".join(
                part.decode(charset or "utf-8") if isinstance(part, bytes) else part
                for part, charset in decoded_parts
            )

        # Extract body
        body_text = None
        body_html = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and body_text is None:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="replace")
                elif content_type == "text/html" and body_html is None:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode("utf-8", errors="replace")
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                decoded = payload.decode("utf-8", errors="replace")
                if content_type == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded

        return EmailMessage(
            uid=uid,
            sender=sender,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    async def mark_seen(self, uid: str) -> None:
        """Mark a message as seen."""
        await self._client.uid("STORE", uid, "+FLAGS", "\\Seen")
        logger.debug(f"Marked message {uid} as seen")

    async def move_to_folder(self, uid: str, folder: str) -> None:
        """
        Move a message to another folder.

        Args:
            uid: Message UID
            folder: Destination folder name
        """
        # Copy to destination folder
        response = await self._client.uid("COPY", uid, folder)
        if response[0] != "OK":
            raise RuntimeError(f"Failed to copy message to {folder}: {response}")

        # Mark original as deleted
        await self._client.uid("STORE", uid, "+FLAGS", "\\Deleted")

        # Expunge deleted messages
        await self._client.expunge()

        logger.debug(f"Moved message {uid} to {folder}")
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest tests/test_imap_client.py -v
```

Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/imap_client.py emailer/tests/test_imap_client.py
git commit -m "feat(emailer): add IMAP client for email operations"
```

---

## Task 6: SMTP Client

**Files:**
- Create: `emailer/emailer/smtp_client.py`
- Create: `emailer/tests/test_smtp_client.py`

**Step 1: Write failing tests for SMTP client**

Create `emailer/tests/test_smtp_client.py`:

```python
"""Tests for SMTP client."""

import pytest
from unittest.mock import AsyncMock, patch
from emailer.smtp_client import SmtpClient


class TestSmtpClient:
    """Tests for SmtpClient."""

    @pytest.mark.asyncio
    async def test_send_email_calls_smtp(self):
        """Test that send_email sends via SMTP."""
        with patch("emailer.smtp_client.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value = mock_instance
            mock_instance.connect = AsyncMock()
            mock_instance.starttls = AsyncMock()
            mock_instance.login = AsyncMock()
            mock_instance.send_message = AsyncMock()
            mock_instance.quit = AsyncMock()

            client = SmtpClient(
                host="smtp.test.com",
                port=587,
                user="test@test.com",
                password="testpass",
                use_tls=True,
            )

            await client.send_email(
                from_addr="from@test.com",
                to_addr="to@test.com",
                subject="Test Subject",
                body="Test Body",
            )

            mock_instance.send_message.assert_called_once()
            call_args = mock_instance.send_message.call_args
            msg = call_args[0][0]
            assert msg["Subject"] == "Test Subject"
            assert msg["From"] == "from@test.com"
            assert msg["To"] == "to@test.com"

    @pytest.mark.asyncio
    async def test_send_email_without_tls(self):
        """Test sending without TLS."""
        with patch("emailer.smtp_client.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value = mock_instance
            mock_instance.connect = AsyncMock()
            mock_instance.login = AsyncMock()
            mock_instance.send_message = AsyncMock()
            mock_instance.quit = AsyncMock()

            client = SmtpClient(
                host="smtp.test.com",
                port=25,
                user="test@test.com",
                password="testpass",
                use_tls=False,
            )

            await client.send_email(
                from_addr="from@test.com",
                to_addr="to@test.com",
                subject="Test",
                body="Body",
            )

            mock_instance.starttls.assert_not_called()
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. pytest tests/test_smtp_client.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'emailer.smtp_client'`

**Step 3: Write SMTP client implementation**

Create `emailer/emailer/smtp_client.py`:

```python
"""SMTP client for sending emails."""

import logging
from email.message import EmailMessage

from aiosmtplib import SMTP

logger = logging.getLogger(__name__)


class SmtpClient:
    """Async SMTP client for sending emails."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_tls = use_tls

    async def send_email(
        self,
        from_addr: str,
        to_addr: str,
        subject: str,
        body: str,
    ) -> None:
        """
        Send an email.

        Args:
            from_addr: Sender email address
            to_addr: Recipient email address
            subject: Email subject
            body: Email body (plain text)
        """
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg.set_content(body)

        smtp = SMTP(hostname=self.host, port=self.port)

        try:
            await smtp.connect()

            if self.use_tls:
                await smtp.starttls()

            await smtp.login(self.user, self.password)
            await smtp.send_message(msg)

            logger.info(f"Sent email to {to_addr}: {subject}")

        finally:
            await smtp.quit()
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest tests/test_smtp_client.py -v
```

Expected: All 2 tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/smtp_client.py emailer/tests/test_smtp_client.py
git commit -m "feat(emailer): add SMTP client for sending emails"
```

---

## Task 7: Frontend API Client

**Files:**
- Create: `emailer/emailer/frontend_client.py`
- Create: `emailer/tests/test_frontend_client.py`

**Step 1: Write failing tests for frontend client**

Create `emailer/tests/test_frontend_client.py`:

```python
"""Tests for frontend API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from emailer.frontend_client import FrontendClient, TranscriptionResult


class TestFrontendClient:
    """Tests for FrontendClient."""

    @pytest.mark.asyncio
    async def test_submit_url_returns_transcription_id(self):
        """Test that submit_url returns the transcription ID."""
        with patch("emailer.frontend_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post = AsyncMock(
                return_value=MagicMock(
                    status_code=202,
                    json=lambda: {"id": "youtube_abc123", "status": "pending"},
                )
            )

            client = FrontendClient(base_url="http://localhost:8000")
            result = await client.submit_url("https://youtube.com/watch?v=abc123")

            assert result == "youtube_abc123"

    @pytest.mark.asyncio
    async def test_submit_url_raises_on_error(self):
        """Test that submit_url raises on API error."""
        with patch("emailer.frontend_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post = AsyncMock(
                return_value=MagicMock(
                    status_code=400,
                    json=lambda: {"detail": "Invalid URL"},
                    raise_for_status=MagicMock(
                        side_effect=httpx.HTTPStatusError(
                            "Bad Request",
                            request=MagicMock(),
                            response=MagicMock(status_code=400),
                        )
                    ),
                )
            )

            client = FrontendClient(base_url="http://localhost:8000")
            with pytest.raises(httpx.HTTPStatusError):
                await client.submit_url("invalid-url")

    @pytest.mark.asyncio
    async def test_get_transcription_returns_result(self):
        """Test that get_transcription returns TranscriptionResult."""
        with patch("emailer.frontend_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: {
                        "id": "youtube_abc123",
                        "status": "completed",
                        "source": {"title": "Test Video"},
                        "transcription": {
                            "full_text": "Hello world",
                            "duration": 120,
                        },
                    },
                )
            )

            client = FrontendClient(base_url="http://localhost:8000")
            result = await client.get_transcription("youtube_abc123")

            assert result.transcription_id == "youtube_abc123"
            assert result.status == "completed"
            assert result.title == "Test Video"
            assert result.full_text == "Hello world"
            assert result.duration_seconds == 120

    @pytest.mark.asyncio
    async def test_generate_summary_returns_text(self):
        """Test that generate_summary returns summary text."""
        with patch("emailer.frontend_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            # First call creates summary
            mock_instance.post = AsyncMock(
                return_value=MagicMock(
                    status_code=201,
                    json=lambda: {
                        "id": "sum_123",
                        "summary_text": "This is a summary.",
                    },
                )
            )

            client = FrontendClient(base_url="http://localhost:8000")
            result = await client.generate_summary("youtube_abc123")

            assert result == "This is a summary."
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. pytest tests/test_frontend_client.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'emailer.frontend_client'`

**Step 3: Write frontend client implementation**

Create `emailer/emailer/frontend_client.py`:

```python
"""Client for frontend API communication."""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result from a transcription job."""

    transcription_id: str
    status: str
    title: Optional[str] = None
    full_text: Optional[str] = None
    duration_seconds: Optional[int] = None
    error: Optional[str] = None


class FrontendClient:
    """Client for communicating with the frontend API."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def submit_url(self, url: str) -> str:
        """
        Submit a URL for transcription.

        Args:
            url: URL to transcribe

        Returns:
            Transcription ID

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/transcribe",
                json={"url": url},
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Submitted URL for transcription: {url} -> {data['id']}")
            return data["id"]

    async def get_transcription(self, transcription_id: str) -> TranscriptionResult:
        """
        Get transcription status and result.

        Args:
            transcription_id: ID of the transcription

        Returns:
            TranscriptionResult with current status and data
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/api/transcriptions/{transcription_id}"
            )
            response.raise_for_status()
            data = response.json()

            result = TranscriptionResult(
                transcription_id=data["id"],
                status=data["status"],
            )

            # Extract source info if available
            if "source" in data:
                result.title = data["source"].get("title")

            # Extract transcription data if completed
            if "transcription" in data and data["transcription"]:
                result.full_text = data["transcription"].get("full_text")
                duration = data["transcription"].get("duration")
                if duration:
                    result.duration_seconds = int(duration)

            # Extract error if failed
            if data["status"] == "failed":
                result.error = data.get("error", "Unknown error")

            return result

    async def generate_summary(self, transcription_id: str) -> str:
        """
        Generate a summary for a transcription.

        Args:
            transcription_id: ID of the transcription

        Returns:
            Summary text

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for LLM
            response = await client.post(
                f"{self.base_url}/api/summaries",
                json={"transcription_id": transcription_id},
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Generated summary for {transcription_id}")
            return data["summary_text"]

    async def wait_for_completion(
        self,
        transcription_id: str,
        poll_interval: float = 5.0,
        max_wait: float = 3600.0,
    ) -> TranscriptionResult:
        """
        Wait for a transcription to complete.

        Args:
            transcription_id: ID of the transcription
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            Final TranscriptionResult

        Raises:
            TimeoutError: If max_wait exceeded
        """
        import asyncio

        elapsed = 0.0
        while elapsed < max_wait:
            result = await self.get_transcription(transcription_id)

            if result.status in ("completed", "failed"):
                return result

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"Transcription {transcription_id} did not complete within {max_wait}s"
        )
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest tests/test_frontend_client.py -v
```

Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/frontend_client.py emailer/tests/test_frontend_client.py
git commit -m "feat(emailer): add frontend API client"
```

---

## Task 8: Job Processor

**Files:**
- Create: `emailer/emailer/job_processor.py`
- Create: `emailer/tests/test_job_processor.py`

**Step 1: Write failing tests for job processor**

Create `emailer/tests/test_job_processor.py`:

```python
"""Tests for job processor."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from emailer.job_processor import JobProcessor, JobResult
from emailer.frontend_client import TranscriptionResult


class TestJobProcessor:
    """Tests for JobProcessor."""

    @pytest.mark.asyncio
    async def test_process_url_success(self):
        """Test successful URL processing."""
        mock_frontend = AsyncMock()
        mock_frontend.submit_url = AsyncMock(return_value="youtube_abc123")
        mock_frontend.wait_for_completion = AsyncMock(
            return_value=TranscriptionResult(
                transcription_id="youtube_abc123",
                status="completed",
                title="Test Video",
                full_text="Hello world",
                duration_seconds=120,
            )
        )
        mock_frontend.generate_summary = AsyncMock(return_value="This is a summary.")

        processor = JobProcessor(frontend_client=mock_frontend)
        result = await processor.process_url("https://youtube.com/watch?v=abc123")

        assert result.success is True
        assert result.url == "https://youtube.com/watch?v=abc123"
        assert result.title == "Test Video"
        assert result.summary == "This is a summary."
        assert result.transcript == "Hello world"

    @pytest.mark.asyncio
    async def test_process_url_transcription_failed(self):
        """Test handling of transcription failure."""
        mock_frontend = AsyncMock()
        mock_frontend.submit_url = AsyncMock(return_value="youtube_abc123")
        mock_frontend.wait_for_completion = AsyncMock(
            return_value=TranscriptionResult(
                transcription_id="youtube_abc123",
                status="failed",
                error="Video not available",
            )
        )

        processor = JobProcessor(frontend_client=mock_frontend)
        result = await processor.process_url("https://youtube.com/watch?v=abc123")

        assert result.success is False
        assert result.error == "Video not available"

    @pytest.mark.asyncio
    async def test_process_url_submit_error(self):
        """Test handling of submission error."""
        import httpx

        mock_frontend = AsyncMock()
        mock_frontend.submit_url = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Bad Request",
                request=MagicMock(),
                response=MagicMock(status_code=400, text="Invalid URL"),
            )
        )

        processor = JobProcessor(frontend_client=mock_frontend)
        result = await processor.process_url("invalid-url")

        assert result.success is False
        assert "Invalid URL" in result.error or "Bad Request" in result.error
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. pytest tests/test_job_processor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'emailer.job_processor'`

**Step 3: Write job processor implementation**

Create `emailer/emailer/job_processor.py`:

```python
"""Process transcription jobs from URLs."""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from emailer.frontend_client import FrontendClient

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    """Result of processing a URL."""

    url: str
    success: bool
    title: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    duration_seconds: Optional[int] = None
    error: Optional[str] = None


class JobProcessor:
    """Process transcription jobs."""

    def __init__(self, frontend_client: FrontendClient):
        self.frontend = frontend_client

    async def process_url(self, url: str) -> JobResult:
        """
        Process a single URL through transcription and summarization.

        Args:
            url: URL to process

        Returns:
            JobResult with success status and data or error
        """
        try:
            # Submit for transcription
            logger.info(f"Submitting URL: {url}")
            transcription_id = await self.frontend.submit_url(url)

            # Wait for completion
            logger.info(f"Waiting for transcription: {transcription_id}")
            result = await self.frontend.wait_for_completion(transcription_id)

            if result.status == "failed":
                return JobResult(
                    url=url,
                    success=False,
                    error=result.error or "Transcription failed",
                )

            # Generate summary
            logger.info(f"Generating summary for: {transcription_id}")
            summary = await self.frontend.generate_summary(transcription_id)

            return JobResult(
                url=url,
                success=True,
                title=result.title,
                summary=summary,
                transcript=result.full_text,
                duration_seconds=result.duration_seconds,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_msg = e.response.text or error_msg
            except Exception:
                pass
            logger.error(f"HTTP error processing {url}: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)

        except TimeoutError as e:
            logger.error(f"Timeout processing {url}: {e}")
            return JobResult(url=url, success=False, error=str(e))

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return JobResult(url=url, success=False, error=str(e))
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest tests/test_job_processor.py -v
```

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/job_processor.py emailer/tests/test_job_processor.py
git commit -m "feat(emailer): add job processor for URL handling"
```

---

## Task 9: Main Service Loop

**Files:**
- Modify: `emailer/emailer/main.py`
- Create: `emailer/tests/test_main.py`

**Step 1: Write failing tests for main service**

Create `emailer/tests/test_main.py`:

```python
"""Tests for main service loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from emailer.main import EmailerService


class TestEmailerService:
    """Tests for EmailerService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.imap_host = "imap.test.com"
        settings.imap_port = 993
        settings.imap_user = "test@test.com"
        settings.imap_password = "testpass"
        settings.imap_use_ssl = True
        settings.smtp_host = "smtp.test.com"
        settings.smtp_port = 587
        settings.smtp_user = "test@test.com"
        settings.smtp_password = "testpass"
        settings.smtp_use_tls = True
        settings.imap_folder_inbox = "ToScribe"
        settings.imap_folder_done = "ScribeDone"
        settings.imap_folder_error = "ScribeError"
        settings.poll_interval_seconds = 300
        settings.max_concurrent_jobs = 3
        settings.result_email_address = "results@test.com"
        settings.from_email_address = "scribe@test.com"
        settings.frontend_url = "http://localhost:8000"
        return settings

    @pytest.mark.asyncio
    async def test_process_email_with_urls(self, mock_settings):
        """Test processing an email with transcribable URLs."""
        from emailer.imap_client import EmailMessage
        from emailer.job_processor import JobResult

        service = EmailerService(mock_settings)

        # Mock dependencies
        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.smtp.send_email = AsyncMock()
        service.processor = AsyncMock()
        service.processor.process_url = AsyncMock(
            return_value=JobResult(
                url="https://youtube.com/watch?v=abc123",
                success=True,
                title="Test Video",
                summary="Summary text",
                transcript="Transcript text",
                duration_seconds=120,
            )
        )

        email = EmailMessage(
            uid="123",
            sender="user@example.com",
            subject="Please transcribe",
            body_text="https://youtube.com/watch?v=abc123",
            body_html=None,
        )

        await service._process_email(email)

        # Should have processed the URL
        service.processor.process_url.assert_called_once_with(
            "https://youtube.com/watch?v=abc123"
        )

        # Should have sent success email
        service.smtp.send_email.assert_called()
        call_args = service.smtp.send_email.call_args
        assert call_args.kwargs["to_addr"] == "results@test.com"
        assert "[Scribe]" in call_args.kwargs["subject"]

        # Should have moved to done folder
        service.imap.move_to_folder.assert_called_with("123", "ScribeDone")

    @pytest.mark.asyncio
    async def test_process_email_no_urls(self, mock_settings):
        """Test processing an email with no transcribable URLs."""
        from emailer.imap_client import EmailMessage

        service = EmailerService(mock_settings)

        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.smtp.send_email = AsyncMock()

        email = EmailMessage(
            uid="123",
            sender="user@example.com",
            subject="Hello",
            body_text="No URLs here",
            body_html=None,
        )

        await service._process_email(email)

        # Should have sent error email to sender
        service.smtp.send_email.assert_called()
        call_args = service.smtp.send_email.call_args
        assert call_args.kwargs["to_addr"] == "user@example.com"
        assert "No transcribable URLs" in call_args.kwargs["subject"]

        # Should have moved to error folder
        service.imap.move_to_folder.assert_called_with("123", "ScribeError")

    @pytest.mark.asyncio
    async def test_process_email_partial_failure(self, mock_settings):
        """Test processing email where some URLs fail."""
        from emailer.imap_client import EmailMessage
        from emailer.job_processor import JobResult

        service = EmailerService(mock_settings)

        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.smtp.send_email = AsyncMock()
        service.processor = AsyncMock()

        # First URL succeeds, second fails
        service.processor.process_url = AsyncMock(
            side_effect=[
                JobResult(
                    url="https://youtube.com/watch?v=abc",
                    success=True,
                    title="Video 1",
                    summary="Summary 1",
                    transcript="Transcript 1",
                    duration_seconds=60,
                ),
                JobResult(
                    url="https://youtube.com/watch?v=def",
                    success=False,
                    error="Video not available",
                ),
            ]
        )

        email = EmailMessage(
            uid="123",
            sender="user@example.com",
            subject="Two videos",
            body_text="https://youtube.com/watch?v=abc https://youtube.com/watch?v=def",
            body_html=None,
        )

        await service._process_email(email)

        # Should have sent success email for first URL
        # Should have sent error email for second URL
        assert service.smtp.send_email.call_count == 2

        # Should have moved to done folder (partial success)
        service.imap.move_to_folder.assert_called_with("123", "ScribeDone")
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. pytest tests/test_main.py -v
```

Expected: FAIL with `ImportError: cannot import name 'EmailerService'`

**Step 3: Update main.py with full implementation**

Replace `emailer/emailer/main.py`:

```python
"""Main entry point for the emailer service."""

import asyncio
import logging
import signal
from typing import Optional

from emailer.config import Settings, get_settings
from emailer.frontend_client import FrontendClient
from emailer.imap_client import ImapClient, EmailMessage
from emailer.job_processor import JobProcessor, JobResult
from emailer.result_formatter import (
    format_success_email,
    format_error_email,
    format_no_urls_email,
)
from emailer.smtp_client import SmtpClient
from emailer.url_extractor import extract_urls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EmailerService:
    """Main emailer service."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.running = False
        self.semaphore: Optional[asyncio.Semaphore] = None

        # Initialize clients
        self.imap = ImapClient(
            host=settings.imap_host,
            port=settings.imap_port,
            user=settings.imap_user,
            password=settings.imap_password,
            use_ssl=settings.imap_use_ssl,
        )

        self.smtp = SmtpClient(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
        )

        frontend = FrontendClient(base_url=settings.frontend_url)
        self.processor = JobProcessor(frontend_client=frontend)

    async def start(self) -> None:
        """Start the emailer service."""
        logger.info("Emailer service starting...")

        self.running = True
        self.semaphore = asyncio.Semaphore(self.settings.max_concurrent_jobs)

        # Connect to IMAP
        await self.imap.connect()

        logger.info(
            f"Monitoring folder: {self.settings.imap_folder_inbox} "
            f"(poll interval: {self.settings.poll_interval_seconds}s)"
        )

        try:
            while self.running:
                await self._poll_and_process()
                await asyncio.sleep(self.settings.poll_interval_seconds)
        finally:
            await self.imap.disconnect()
            logger.info("Emailer service stopped.")

    async def stop(self) -> None:
        """Stop the emailer service."""
        logger.info("Stopping emailer service...")
        self.running = False

    async def _poll_and_process(self) -> None:
        """Poll for new emails and process them."""
        try:
            emails = await self.imap.fetch_unseen(self.settings.imap_folder_inbox)

            if emails:
                logger.info(f"Found {len(emails)} new email(s)")

            tasks = []
            for email in emails:
                # Mark as seen immediately
                await self.imap.mark_seen(email.uid)
                # Process concurrently with semaphore
                task = asyncio.create_task(self._process_email_with_semaphore(email))
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error during poll: {e}")

    async def _process_email_with_semaphore(self, email: EmailMessage) -> None:
        """Process email with concurrency limit."""
        async with self.semaphore:
            await self._process_email(email)

    async def _process_email(self, email: EmailMessage) -> None:
        """Process a single email."""
        logger.info(f"Processing email {email.uid} from {email.sender}")

        # Extract URLs from both text and HTML
        urls = []
        if email.body_text:
            urls.extend(extract_urls(email.body_text, is_html=False))
        if email.body_html:
            urls.extend(extract_urls(email.body_html, is_html=True))

        # Deduplicate
        urls = list(dict.fromkeys(urls))

        if not urls:
            # No transcribable URLs found
            await self._handle_no_urls(email)
            return

        # Process each URL
        results = []
        for url in urls:
            result = await self.processor.process_url(url)
            results.append(result)
            await self._send_result_email(email, result)

        # Determine final folder
        any_success = any(r.success for r in results)
        if any_success:
            await self.imap.move_to_folder(email.uid, self.settings.imap_folder_done)
        else:
            await self.imap.move_to_folder(email.uid, self.settings.imap_folder_error)

    async def _handle_no_urls(self, email: EmailMessage) -> None:
        """Handle email with no transcribable URLs."""
        subject, body = format_no_urls_email()

        await self.smtp.send_email(
            from_addr=self.settings.from_email_address,
            to_addr=email.sender,
            subject=subject,
            body=body,
        )

        await self.imap.move_to_folder(email.uid, self.settings.imap_folder_error)
        logger.info(f"No URLs in email {email.uid}, notified sender")

    async def _send_result_email(self, email: EmailMessage, result: JobResult) -> None:
        """Send result or error email based on job result."""
        if result.success:
            subject, body = format_success_email(
                url=result.url,
                title=result.title or "Untitled",
                duration_seconds=result.duration_seconds or 0,
                summary=result.summary or "",
                transcript=result.transcript or "",
            )
            to_addr = self.settings.result_email_address
        else:
            subject, body = format_error_email(
                url=result.url,
                error_message=result.error or "Unknown error",
            )
            to_addr = email.sender

        await self.smtp.send_email(
            from_addr=self.settings.from_email_address,
            to_addr=to_addr,
            subject=subject,
            body=body,
        )


async def main() -> None:
    """Main entry point."""
    settings = get_settings()
    service = EmailerService(settings)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        asyncio.create_task(service.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. pytest tests/test_main.py -v
```

Expected: All 3 tests PASS

**Step 5: Run all tests**

```bash
PYTHONPATH=. pytest tests/ -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add emailer/emailer/main.py emailer/tests/test_main.py
git commit -m "feat(emailer): implement main service loop with email processing"
```

---

## Task 10: Final Integration & Documentation

**Files:**
- Modify: `emailer/README.md` (update with final details)
- Modify: `README.md` (add emailer to project documentation)

**Step 1: Update emailer README**

Update `emailer/README.md` with complete documentation including all configuration options and troubleshooting.

**Step 2: Update main project README**

Add emailer service to the main `README.md` architecture section.

**Step 3: Run full test suite**

```bash
cd /Users/patrick/git/scribe/.worktrees/emailer-feature
source frontend/venv/bin/activate && PYTHONPATH=frontend pytest frontend/tests -q
cd emailer && source venv/bin/activate && PYTHONPATH=. pytest tests -v
```

Expected: All tests PASS

**Step 4: Final commit**

```bash
git add .
git commit -m "docs(emailer): complete documentation and integration"
```

---

## Summary

This plan creates the emailer service in 10 tasks:

1. **Scaffolding** - Project structure and dependencies
2. **Config** - Environment-based configuration with validation
3. **URL Extractor** - Parse emails for transcribable URLs
4. **Result Formatter** - Format success/error emails
5. **IMAP Client** - Fetch and manage emails
6. **SMTP Client** - Send result emails
7. **Frontend Client** - Communicate with transcription API
8. **Job Processor** - Orchestrate transcription workflow
9. **Main Service** - Polling loop with concurrency control
10. **Integration** - Final testing and documentation

Each task follows TDD: write failing test → implement → verify → commit.
