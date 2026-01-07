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
