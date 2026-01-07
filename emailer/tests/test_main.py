"""Tests for main service loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from emailer.main import EmailerService


class TestEmailerService:
    """Tests for EmailerService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.imap_host = "imap.test.com"
        settings.imap_port = 993
        settings.imap_user = "test@test.com"
        settings.imap_password = "testpass"
        settings.imap_use_ssl = True
        settings.smtp_host = "smtp.test.com"
        settings.smtp_port = 587
        settings.smtp_user = "test@test.com"
        settings.smtp_password = "testpass"
        settings.smtp_use_tls = True
        settings.imap_folder_inbox = "ToScribe"
        settings.imap_folder_done = "ScribeDone"
        settings.imap_folder_error = "ScribeError"
        settings.poll_interval_seconds = 300
        settings.max_concurrent_jobs = 3
        settings.result_email_address = "results@test.com"
        settings.from_email_address = "scribe@test.com"
        settings.frontend_url = "http://localhost:8000"
        return settings

    @pytest.mark.asyncio
    async def test_process_email_with_urls(self, mock_settings):
        """Test processing an email with transcribable URLs."""
        from emailer.imap_client import EmailMessage
        from emailer.job_processor import JobResult

        service = EmailerService(mock_settings)

        # Mock dependencies
        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.smtp.send_email = AsyncMock()
        service.processor = AsyncMock()
        service.processor.process_url = AsyncMock(
            return_value=JobResult(
                url="https://youtube.com/watch?v=abc123",
                success=True,
                title="Test Video",
                summary="Summary text",
                transcript="Transcript text",
                duration_seconds=120,
            )
        )

        email = EmailMessage(
            uid="123",
            sender="user@example.com",
            subject="Please transcribe",
            body_text="https://youtube.com/watch?v=abc123",
            body_html=None,
        )

        await service._process_email(email)

        # Should have processed the URL
        service.processor.process_url.assert_called_once_with(
            "https://youtube.com/watch?v=abc123"
        )

        # Should have sent success email
        service.smtp.send_email.assert_called()
        call_args = service.smtp.send_email.call_args
        assert call_args.kwargs["to_addr"] == "results@test.com"
        assert "[Scribe]" in call_args.kwargs["subject"]

        # Should have moved to done folder
        service.imap.move_to_folder.assert_called_with("123", "ScribeDone")

    @pytest.mark.asyncio
    async def test_process_email_no_urls(self, mock_settings):
        """Test processing an email with no transcribable URLs."""
        from emailer.imap_client import EmailMessage

        service = EmailerService(mock_settings)

        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.smtp.send_email = AsyncMock()

        email = EmailMessage(
            uid="123",
            sender="user@example.com",
            subject="Hello",
            body_text="No URLs here",
            body_html=None,
        )

        await service._process_email(email)

        # Should have sent error email to sender
        service.smtp.send_email.assert_called()
        call_args = service.smtp.send_email.call_args
        assert call_args.kwargs["to_addr"] == "user@example.com"
        assert "No transcribable URLs" in call_args.kwargs["subject"]

        # Should have moved to error folder
        service.imap.move_to_folder.assert_called_with("123", "ScribeError")

    @pytest.mark.asyncio
    async def test_process_email_partial_failure(self, mock_settings):
        """Test processing email where some URLs fail."""
        from emailer.imap_client import EmailMessage
        from emailer.job_processor import JobResult

        service = EmailerService(mock_settings)

        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.smtp.send_email = AsyncMock()
        service.processor = AsyncMock()

        # First URL succeeds, second fails
        service.processor.process_url = AsyncMock(
            side_effect=[
                JobResult(
                    url="https://youtube.com/watch?v=abc",
                    success=True,
                    title="Video 1",
                    summary="Summary 1",
                    transcript="Transcript 1",
                    duration_seconds=60,
                ),
                JobResult(
                    url="https://youtube.com/watch?v=def",
                    success=False,
                    error="Video not available",
                ),
            ]
        )

        email = EmailMessage(
            uid="123",
            sender="user@example.com",
            subject="Two videos",
            body_text="https://youtube.com/watch?v=abc https://youtube.com/watch?v=def",
            body_html=None,
        )

        await service._process_email(email)

        # Should have sent success email for first URL
        # Should have sent error email for second URL
        assert service.smtp.send_email.call_count == 2

        # Should have moved to done folder (partial success)
        service.imap.move_to_folder.assert_called_with("123", "ScribeDone")
