"""Tests for IMAP client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from emailer.imap_client import ImapClient, EmailMessage


class TestEmailMessage:
    """Tests for EmailMessage dataclass."""

    def test_email_message_creation(self):
        msg = EmailMessage(
            uid="123",
            sender="test@example.com",
            subject="Test Subject",
            body_text="Plain text body",
            body_html="<p>HTML body</p>",
        )
        assert msg.uid == "123"
        assert msg.sender == "test@example.com"
        assert msg.subject == "Test Subject"


class TestImapClient:
    """Tests for ImapClient."""

    @pytest.mark.asyncio
    async def test_connect_creates_connection(self):
        """Test that connect establishes IMAP connection."""
        with patch("emailer.imap_client.IMAP4_SSL") as mock_imap:
            mock_instance = AsyncMock()
            mock_imap.return_value = mock_instance
            mock_instance.wait_hello_from_server = AsyncMock()
            mock_instance.login = AsyncMock(return_value=("OK", []))

            client = ImapClient(
                host="imap.test.com",
                port=993,
                user="test@test.com",
                password="testpass",
                use_ssl=True,
            )

            await client.connect()

            mock_imap.assert_called_once_with(host="imap.test.com", port=993)
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
        mock_client = AsyncMock()
        mock_client.logout = AsyncMock()
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
        client._client = AsyncMock()
        client._client.uid = AsyncMock(return_value=("OK", []))

        await client.mark_seen("123")

        client._client.uid.assert_called_with("STORE", "123", "+FLAGS", "\\Seen")

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
        client._client = AsyncMock()
        client._client.uid = AsyncMock(return_value=("OK", []))

        await client.move_to_folder("123", "ScribeDone")

        # Should copy then delete
        calls = client._client.uid.call_args_list
        assert any("COPY" in str(call) and "ScribeDone" in str(call) for call in calls)
        assert any("STORE" in str(call) and "\\Deleted" in str(call) for call in calls)
