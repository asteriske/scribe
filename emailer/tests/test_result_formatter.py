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
