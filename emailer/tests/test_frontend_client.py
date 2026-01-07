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
