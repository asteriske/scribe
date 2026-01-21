"""Format emails for transcription results and errors."""

import html
from datetime import datetime, timezone
from typing import Tuple

import html2text


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


def _html_to_plain_text(html_content: str) -> str:
    """Convert HTML to readable plain text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0  # Don't wrap lines
    return h.handle(html_content).strip()


def format_success_email(
    url: str,
    title: str,
    duration_seconds: int,
    summary: str,
    transcript: str,
) -> Tuple[str, str, str]:
    """
    Format a success email with summary and transcript.

    Args:
        url: Source URL
        title: Content title
        duration_seconds: Duration in seconds
        summary: Generated summary (HTML from LLM)
        transcript: Full transcript text

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    # Truncate title for subject if too long
    max_title_len = 100
    display_title = title[:max_title_len] + "..." if len(title) > max_title_len else title
    subject = f"[Scribe] {display_title}"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    duration = _format_duration(duration_seconds)

    # Escape transcript for HTML (prevent XSS)
    escaped_transcript = html.escape(transcript)
    # Convert newlines to <br> for HTML display
    html_transcript = escaped_transcript.replace("\n", "<br>\n")

    # HTML version
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .metadata {{ color: #666; font-size: 14px; border-bottom: 1px solid #eee; padding-bottom: 16px; margin-bottom: 24px; }}
        .metadata a {{ color: #0066cc; }}
        .section-title {{ font-size: 14px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin: 32px 0 16px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .transcript {{ font-size: 14px; color: #444; }}
    </style>
</head>
<body>
    <div class="metadata">
        <div><strong>Source:</strong> <a href="{html.escape(url)}">{html.escape(url)}</a></div>
        <div><strong>Duration:</strong> {duration}</div>
        <div><strong>Transcribed:</strong> {timestamp}</div>
    </div>

    <div class="section-title">Summary</div>
    {summary}

    <div class="section-title">Transcript</div>
    <div class="transcript">{html_transcript}</div>
</body>
</html>"""

    # Plain text version
    plain_summary = _html_to_plain_text(summary)

    text_body = f"""Source: {url}
Duration: {duration}
Transcribed: {timestamp}

--- SUMMARY ---

{plain_summary}

--- TRANSCRIPT ---

{transcript}
"""

    return subject, html_body, text_body


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
