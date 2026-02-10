"""Tests for episode source email processing."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from emailer.episode_source_processor import EpisodeSourceProcessor
from emailer.imap_client import EmailMessage
from emailer.job_processor import JobResult


class TestEpisodeSourceProcessor:
    """Tests for EpisodeSourceProcessor."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        frontend = AsyncMock()
        p = EpisodeSourceProcessor(frontend_client=frontend)
        return p

    @pytest.mark.asyncio
    async def test_process_email_with_apple_podcasts_url(self, processor):
        """Test processing email containing Apple Podcasts URL."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_123")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed",
                title="Test Podcast",
                duration_seconds=1200,
                source_context="Show notes here",
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="Transcript text")
        processor.frontend.generate_summary = AsyncMock(return_value="Summary text")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_abc")

        email = EmailMessage(
            msg_num="1",
            sender="newsletter@example.com",
            subject="New Episode: Testing 101",
            body_text="Check out our latest episode https://podcasts.apple.com/us/podcast/ep1?i=1000123456 about testing",
            body_html=None,
        )

        result = await processor.process_email(email)

        assert result.success
        assert result.url == "https://podcasts.apple.com/us/podcast/ep1?i=1000123456"
        assert result.title == "Test Podcast"
        processor.frontend.submit_url.assert_called_once_with(
            "https://podcasts.apple.com/us/podcast/ep1?i=1000123456", tag="digest"
        )
        processor.frontend.create_episode_source.assert_called_once()
        call_kwargs = processor.frontend.create_episode_source.call_args.kwargs
        assert call_kwargs["transcription_id"] == "trans_123"
        assert "Check out our latest episode" in call_kwargs["source_text"]
        assert call_kwargs["matched_url"] == "https://podcasts.apple.com/us/podcast/ep1?i=1000123456"
        assert call_kwargs["email_subject"] == "New Episode: Testing 101"
        assert call_kwargs["email_from"] == "newsletter@example.com"

    @pytest.mark.asyncio
    async def test_process_email_with_youtube_url(self, processor):
        """Test processing email containing YouTube URL."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_456")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed",
                title="YouTube Video",
                duration_seconds=600,
                source_context=None,
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="Transcript")
        processor.frontend.generate_summary = AsyncMock(return_value="Summary")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_def")

        email = EmailMessage(
            msg_num="2",
            sender="user@example.com",
            subject="Check this video",
            body_text="Watch https://youtube.com/watch?v=abc123",
            body_html=None,
        )

        result = await processor.process_email(email)

        assert result.success
        assert result.url == "https://youtube.com/watch?v=abc123"

    @pytest.mark.asyncio
    async def test_process_email_no_matching_urls(self, processor):
        """Test processing email with no Apple Podcasts or YouTube URLs."""
        email = EmailMessage(
            msg_num="3",
            sender="user@example.com",
            subject="Random email",
            body_text="Visit https://example.com for more info",
            body_html=None,
        )

        result = await processor.process_email(email)

        assert not result.success
        assert "No Apple Podcasts or YouTube URL" in result.error

    @pytest.mark.asyncio
    async def test_process_email_uses_first_url(self, processor):
        """Test that only the first matching URL is processed."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_789")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed",
                title="First",
                duration_seconds=300,
                source_context=None,
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="Transcript")
        processor.frontend.generate_summary = AsyncMock(return_value="Summary")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_ghi")

        email = EmailMessage(
            msg_num="4",
            sender="user@example.com",
            subject="Two episodes",
            body_text=(
                "First: https://podcasts.apple.com/us/podcast/ep1?i=1000111111 "
                "Second: https://podcasts.apple.com/us/podcast/ep2?i=1000222222"
            ),
            body_html=None,
        )

        result = await processor.process_email(email)

        assert result.success
        # Should have submitted only once (first URL)
        processor.frontend.submit_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_email_prefers_html_for_urls(self, processor):
        """Test that HTML body is searched for URLs when present."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_html")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed", title="HTML", duration_seconds=100, source_context=None,
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="T")
        processor.frontend.generate_summary = AsyncMock(return_value="S")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_html")

        email = EmailMessage(
            msg_num="5",
            sender="user@example.com",
            subject="HTML email",
            body_text=None,
            body_html='<a href="https://podcasts.apple.com/us/podcast/html-ep?i=1000333333">Listen</a>',
        )

        result = await processor.process_email(email)

        assert result.success
        assert result.url == "https://podcasts.apple.com/us/podcast/html-ep?i=1000333333"

    @pytest.mark.asyncio
    async def test_process_email_converts_html_to_plain_text(self, processor):
        """Test that HTML body is converted to plain text for source_text."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_conv")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed", title="Conv", duration_seconds=100, source_context=None,
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="T")
        processor.frontend.generate_summary = AsyncMock(return_value="S")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_conv")

        email = EmailMessage(
            msg_num="6",
            sender="user@example.com",
            subject="HTML only",
            body_text=None,
            body_html='<p>Great episode about <b>testing</b>.</p><a href="https://podcasts.apple.com/us/podcast/conv?i=1000444444">Listen</a>',
        )

        result = await processor.process_email(email)

        assert result.success
        call_kwargs = processor.frontend.create_episode_source.call_args.kwargs
        # Should contain plain text, not HTML tags
        assert "<p>" not in call_kwargs["source_text"]
        assert "testing" in call_kwargs["source_text"]

    @pytest.mark.asyncio
    async def test_process_email_transcription_failure(self, processor):
        """Test handling when transcription fails."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_fail")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="failed",
                error="Audio download failed",
            )
        )

        email = EmailMessage(
            msg_num="7",
            sender="user@example.com",
            subject="Will fail",
            body_text="https://podcasts.apple.com/us/podcast/fail?i=1000555555",
            body_html=None,
        )

        result = await processor.process_email(email)

        assert not result.success
        assert "Audio download failed" in result.error
        # Should not create episode source on failure
        processor.frontend.create_episode_source.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_next_url_on_failure(self, processor):
        """Test that if first URL fails, the next URL is tried."""
        # First call fails, second succeeds
        processor.frontend.submit_url = AsyncMock(
            side_effect=["trans_fail", "trans_ok"]
        )
        processor.frontend.wait_for_completion = AsyncMock(
            side_effect=[
                MagicMock(status="failed", error="Download failed"),
                MagicMock(
                    status="completed",
                    title="Second URL",
                    duration_seconds=600,
                    source_context=None,
                ),
            ]
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="Transcript")
        processor.frontend.generate_summary = AsyncMock(return_value="Summary")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_fb")

        email = EmailMessage(
            msg_num="8",
            sender="user@example.com",
            subject="Two URLs",
            body_text=(
                "First: https://youtu.be/fail123 "
                "Second: https://youtube.com/watch?v=ok456"
            ),
            body_html=None,
        )

        result = await processor.process_email(email)

        assert result.success
        # The successful URL should be whichever one completed
        assert result.title == "Second URL"
        assert processor.frontend.submit_url.call_count == 2
