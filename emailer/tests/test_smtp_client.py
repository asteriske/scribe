"""Tests for SMTP client."""

import pytest
from unittest.mock import AsyncMock, patch
from emailer.smtp_client import SmtpClient


class TestSmtpClient:
    """Tests for SmtpClient."""

    @pytest.mark.asyncio
    async def test_send_email_calls_smtp(self):
        """Test that send_email sends via SMTP."""
        with patch("emailer.smtp_client.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value = mock_instance
            mock_instance.connect = AsyncMock()
            mock_instance.starttls = AsyncMock()
            mock_instance.login = AsyncMock()
            mock_instance.send_message = AsyncMock()
            mock_instance.quit = AsyncMock()

            client = SmtpClient(
                host="smtp.test.com",
                port=587,
                user="test@test.com",
                password="testpass",
                use_tls=True,
            )

            await client.send_email(
                from_addr="from@test.com",
                to_addr="to@test.com",
                subject="Test Subject",
                body="Test Body",
            )

            mock_instance.send_message.assert_called_once()
            call_args = mock_instance.send_message.call_args
            msg = call_args[0][0]
            assert msg["Subject"] == "Test Subject"
            assert msg["From"] == "from@test.com"
            assert msg["To"] == "to@test.com"

    @pytest.mark.asyncio
    async def test_send_email_without_tls(self):
        """Test sending without TLS."""
        with patch("emailer.smtp_client.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value = mock_instance
            mock_instance.connect = AsyncMock()
            mock_instance.login = AsyncMock()
            mock_instance.send_message = AsyncMock()
            mock_instance.quit = AsyncMock()

            client = SmtpClient(
                host="smtp.test.com",
                port=25,
                user="test@test.com",
                password="testpass",
                use_tls=False,
            )

            await client.send_email(
                from_addr="from@test.com",
                to_addr="to@test.com",
                subject="Test",
                body="Body",
            )

            mock_instance.starttls.assert_not_called()
