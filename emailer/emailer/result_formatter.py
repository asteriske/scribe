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
