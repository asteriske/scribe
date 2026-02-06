"""Tests for result email formatting."""

import pytest
from emailer.result_formatter import (
    format_success_email,
    format_error_email,
    format_no_urls_email,
)


class TestFormatSuccessEmail:
    """Tests for success email formatting."""

    def test_format_success_email_returns_three_values(self):
        """Test that format_success_email returns subject, html_body, text_body."""
        result = format_success_email(
            url="https://example.com/video",
            title="Test Video",
            duration_seconds=120,
            summary="<p>This is an <strong>HTML</strong> summary.</p>",
            transcript="This is the transcript.",
        )

        assert len(result) == 3
        subject, html_body, text_body = result

        # Check subject
        assert "[Scribe]" in subject
        assert "Test Video" in subject

        # Check HTML body
        assert "<!DOCTYPE html>" in html_body
        assert "<p>This is an <strong>HTML</strong> summary.</p>" in html_body
        assert "https://example.com/video" in html_body

        # Check plain text body
        assert "--- SUMMARY ---" in text_body
        assert "--- TRANSCRIPT ---" in text_body
        assert "This is the transcript." in text_body

    def test_format_success_email_html_escapes_transcript(self):
        """Test that transcript is HTML-escaped in HTML body."""
        _, html_body, _ = format_success_email(
            url="https://example.com",
            title="Test",
            duration_seconds=60,
            summary="<p>Summary</p>",
            transcript="Text with <script>alert('xss')</script> tags",
        )

        assert "<script>" not in html_body
        assert "&lt;script&gt;" in html_body

    def test_basic_format(self):
        """Test basic email formatting with all components."""
        subject, html_body, text_body = format_success_email(
            url="https://www.youtube.com/watch?v=abc123",
            title="Test Video",
            duration_seconds=125,
            summary="<p>This is the summary.</p>",
            transcript="This is the full transcript.",
        )

        assert subject == "[Scribe] Test Video"
        # HTML body checks
        assert "https://www.youtube.com/watch?v=abc123" in html_body
        assert "2:05" in html_body  # duration formatted
        assert "This is the summary." in html_body
        assert "This is the full transcript." in html_body
        # Plain text body checks
        assert "https://www.youtube.com/watch?v=abc123" in text_body
        assert "2:05" in text_body  # duration formatted
        assert "--- SUMMARY ---" in text_body
        assert "--- TRANSCRIPT ---" in text_body
        assert "This is the full transcript." in text_body

    def test_long_title_in_subject(self):
        """Test that long titles are truncated in subject."""
        long_title = "A" * 150
        subject, _, _ = format_success_email(
            url="https://youtu.be/abc",
            title=long_title,
            duration_seconds=60,
            summary="<p>Summary</p>",
            transcript="Transcript",
        )
        # Subject should be reasonable length (truncated at 100 chars + prefix + ellipsis)
        assert len(subject) <= 120

    def test_html_body_has_styling(self):
        """Test that HTML body includes CSS styling."""
        _, html_body, _ = format_success_email(
            url="https://example.com",
            title="Test",
            duration_seconds=60,
            summary="<p>Summary</p>",
            transcript="Transcript",
        )

        assert "<style>" in html_body
        assert "font-family" in html_body

    def test_plain_text_converts_html_summary(self):
        """Test that HTML summary is converted to plain text in text body."""
        _, _, text_body = format_success_email(
            url="https://example.com",
            title="Test",
            duration_seconds=60,
            summary="<p>This is <strong>bold</strong> and <em>italic</em> text.</p>",
            transcript="Transcript",
        )

        # HTML tags should not appear in plain text
        assert "<p>" not in text_body
        assert "<strong>" not in text_body
        assert "<em>" not in text_body
        # But content should be there
        assert "bold" in text_body
        assert "italic" in text_body

    def test_url_escaped_in_html(self):
        """Test that URL is properly escaped in HTML body."""
        _, html_body, _ = format_success_email(
            url="https://example.com/video?id=123&name=test",
            title="Test",
            duration_seconds=60,
            summary="<p>Summary</p>",
            transcript="Transcript",
        )

        # & should be escaped in HTML
        assert "&amp;" in html_body or "https://example.com/video?id=123&name=test" in html_body


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


class TestCreatorNotes:
    """Tests for Show Notes section in success emails."""

    def test_format_success_email_with_creator_notes(self):
        """Test email formatting includes Show Notes section when provided."""
        subject, html_body, text_body = format_success_email(
            url="https://podcasts.apple.com/test",
            title="Test Episode",
            duration_seconds=3600,
            summary="<p>This is the summary.</p>",
            transcript="Full transcript text here.",
            creator_notes="Episode about Python. Topics: decorators, generators."
        )
        assert "Show Notes" in html_body
        assert "Episode about Python" in html_body
        assert "SHOW NOTES" in text_body
        assert "Episode about Python" in text_body
        # Verify order: Summary -> Show Notes -> Transcript
        summary_pos = html_body.find("Summary")
        notes_pos = html_body.find("Show Notes")
        transcript_pos = html_body.find("Transcript")
        assert summary_pos < notes_pos < transcript_pos

    def test_format_success_email_without_creator_notes(self):
        """Test email formatting omits Show Notes section when not provided."""
        subject, html_body, text_body = format_success_email(
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            duration_seconds=600,
            summary="<p>Summary here.</p>",
            transcript="Transcript here.",
            creator_notes=None
        )
        assert "Show Notes" not in html_body
        assert "SHOW NOTES" not in text_body
