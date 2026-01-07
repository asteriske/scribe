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
