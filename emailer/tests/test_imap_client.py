"""Tests for IMAP client."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from emailer.imap_client import ImapClient, EmailMessage


class TestEmailMessage:
    """Tests for EmailMessage dataclass."""

    def test_email_message_creation(self):
        msg = EmailMessage(
            msg_num="123",
            sender="test@example.com",
            subject="Test Subject",
            body_text="Plain text body",
            body_html="<p>HTML body</p>",
        )
        assert msg.msg_num == "123"
        assert msg.sender == "test@example.com"
        assert msg.subject == "Test Subject"


class TestImapClient:
    """Tests for ImapClient."""

    @pytest.mark.asyncio
    async def test_connect_creates_connection(self):
        """Test that connect establishes IMAP connection."""
        with patch("emailer.imap_client.imaplib") as mock_imaplib:
            mock_instance = MagicMock()
            mock_imaplib.IMAP4_SSL.return_value = mock_instance

            client = ImapClient(
                host="imap.test.com",
                port=993,
                user="test@test.com",
                password="testpass",
                use_ssl=True,
            )

            await client.connect()

            mock_imaplib.IMAP4_SSL.assert_called_once_with("imap.test.com", 993)
            mock_instance.login.assert_called_once_with("test@test.com", "testpass")

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self):
        """Test that disconnect closes IMAP connection."""
        client = ImapClient(
            host="imap.test.com",
            port=993,
            user="test@test.com",
            password="testpass",
            use_ssl=True,
        )
        mock_client = MagicMock()
        client._client = mock_client

        await client.disconnect()

        mock_client.logout.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_seen_sets_flag(self):
        """Test that mark_seen sets the Seen flag."""
        client = ImapClient(
            host="imap.test.com",
            port=993,
            user="test@test.com",
            password="testpass",
            use_ssl=True,
        )
        mock_client = MagicMock()
        client._client = mock_client

        await client.mark_seen("123")

        mock_client.store.assert_called_with("123", "+FLAGS", "\\Seen")

    @pytest.mark.asyncio
    async def test_move_to_folder(self):
        """Test that move_to_folder moves email to destination."""
        client = ImapClient(
            host="imap.test.com",
            port=993,
            user="test@test.com",
            password="testpass",
            use_ssl=True,
        )
        mock_client = MagicMock()
        mock_client.copy.return_value = ("OK", [])
        client._client = mock_client

        await client.move_to_folder("123", "ScribeDone")

        mock_client.copy.assert_called_with("123", "ScribeDone")
        mock_client.store.assert_called_with("123", "+FLAGS", "\\Deleted")
        mock_client.expunge.assert_called_once()
