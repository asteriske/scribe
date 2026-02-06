"""Tests for the Apple Podcasts scraper."""
import pytest
from unittest.mock import patch, MagicMock

from frontend.services.apple_podcasts_scraper import ApplePodcastsScraper


class TestApplePodcastsScraper:
    """Tests for ApplePodcastsScraper."""

    def test_is_apple_podcasts_url_true(self):
        """Test detection of Apple Podcasts URLs."""
        scraper = ApplePodcastsScraper()
        assert scraper.is_apple_podcasts_url("https://podcasts.apple.com/us/podcast/test/id123?i=456")
        assert scraper.is_apple_podcasts_url("https://podcasts.apple.com/gb/podcast/test/id123")
        assert scraper.is_apple_podcasts_url("http://podcasts.apple.com/us/podcast/test/id123")

    def test_is_apple_podcasts_url_false(self):
        """Test rejection of non-Apple Podcasts URLs."""
        scraper = ApplePodcastsScraper()
        assert not scraper.is_apple_podcasts_url("https://youtube.com/watch?v=123")
        assert not scraper.is_apple_podcasts_url("https://spotify.com/episode/123")
        assert not scraper.is_apple_podcasts_url("https://example.com/audio.mp3")

    def test_extract_show_notes_success(self):
        """Test successful extraction of show notes."""
        html_content = """
        <html>
        <head>
            <meta name="description" content="Episode description here">
        </head>
        <body>
            <section class="product-hero-desc">
                <div>
                    <p>In this episode, we discuss Python programming.</p>
                </div>
            </section>
        </body>
        </html>
        """

        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            scraper = ApplePodcastsScraper()
            result = scraper.fetch_show_notes("https://podcasts.apple.com/us/podcast/test/id123")

            assert result is not None
            assert "Python programming" in result or "Episode description" in result

    def test_extract_show_notes_network_error_returns_none(self):
        """Test that network errors return None instead of raising."""
        import httpx

        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Connection failed")

            scraper = ApplePodcastsScraper()
            result = scraper.fetch_show_notes("https://podcasts.apple.com/us/podcast/test/id123")

            assert result is None

    def test_extract_show_notes_retries_on_transient_error(self):
        """Test that transient errors trigger retries."""
        import httpx

        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = "<html><body><p>Show notes</p></body></html>"
            mock_response.raise_for_status = MagicMock()

            # First two calls fail, third succeeds
            mock_client.return_value.__enter__.return_value.get.side_effect = [
                httpx.RequestError("Timeout"),
                httpx.RequestError("Timeout"),
                mock_response
            ]

            scraper = ApplePodcastsScraper(max_retries=3)
            result = scraper.fetch_show_notes("https://podcasts.apple.com/us/podcast/test/id123")

            # Should have tried 3 times
            assert mock_client.return_value.__enter__.return_value.get.call_count == 3

    def test_extract_show_notes_gives_up_after_max_retries(self):
        """Test that scraper gives up after max retries."""
        import httpx

        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Timeout")

            scraper = ApplePodcastsScraper(max_retries=3)
            result = scraper.fetch_show_notes("https://podcasts.apple.com/us/podcast/test/id123")

            assert result is None
            assert mock_client.return_value.__enter__.return_value.get.call_count == 3
