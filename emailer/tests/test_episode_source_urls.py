"""Tests for episode source URL extraction."""
import pytest
from emailer.episode_source_urls import extract_episode_source_urls


class TestExtractEpisodeSourceUrls:
    """Tests for extracting Apple Podcasts and YouTube URLs only."""

    def test_apple_podcasts_url(self):
        text = "Check out https://podcasts.apple.com/us/podcast/ep123 today!"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == ["https://podcasts.apple.com/us/podcast/ep123"]

    def test_youtube_watch_url(self):
        text = "Watch https://youtube.com/watch?v=abc123"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == ["https://youtube.com/watch?v=abc123"]

    def test_youtube_short_url(self):
        text = "See https://youtu.be/abc123"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == ["https://youtu.be/abc123"]

    def test_youtube_live_url(self):
        text = "Live at https://youtube.com/live/abc123"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == ["https://youtube.com/live/abc123"]

    def test_ignores_direct_audio_urls(self):
        text = "Download https://example.com/episode.mp3"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == []

    def test_ignores_podcast_addict_urls(self):
        text = "Listen at https://podcastaddict.com/show/episode/12345"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == []

    def test_ignores_non_transcribable_urls(self):
        text = "Visit https://example.com and https://google.com"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == []

    def test_multiple_urls_returns_all(self):
        text = (
            "Apple: https://podcasts.apple.com/test "
            "YouTube: https://youtube.com/watch?v=abc"
        )
        urls = extract_episode_source_urls(text, is_html=False)
        assert len(urls) == 2

    def test_html_extracts_from_hrefs(self):
        html = '<a href="https://podcasts.apple.com/us/podcast/ep1">Listen</a>'
        urls = extract_episode_source_urls(html, is_html=True)
        assert urls == ["https://podcasts.apple.com/us/podcast/ep1"]

    def test_html_ignores_non_matching_hrefs(self):
        html = '<a href="https://example.com/page">Link</a>'
        urls = extract_episode_source_urls(html, is_html=True)
        assert urls == []

    def test_deduplicates_urls(self):
        text = (
            "https://podcasts.apple.com/test "
            "https://podcasts.apple.com/test"
        )
        urls = extract_episode_source_urls(text, is_html=False)
        assert len(urls) == 1

    def test_empty_input(self):
        assert extract_episode_source_urls("", is_html=False) == []
        assert extract_episode_source_urls("", is_html=True) == []
