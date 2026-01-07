"""IMAP client for fetching and managing emails."""

import email
import logging
from dataclasses import dataclass
from email.header import decode_header
from typing import List, Optional

from aioimaplib import IMAP4_SSL, IMAP4

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Represents an email message."""

    uid: str
    sender: str
    subject: str
    body_text: Optional[str]
    body_html: Optional[str]


class ImapClient:
    """Async IMAP client for email operations."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        use_ssl: bool = True,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self._client: Optional[IMAP4_SSL | IMAP4] = None

    async def connect(self) -> None:
        """Establish connection to IMAP server."""
        if self.use_ssl:
            self._client = IMAP4_SSL(host=self.host, port=self.port)
        else:
            self._client = IMAP4(host=self.host, port=self.port)

        await self._client.wait_hello_from_server()
        response = await self._client.login(self.user, self.password)

        if response[0] != "OK":
            raise ConnectionError(f"IMAP login failed: {response}")

        logger.info(f"Connected to IMAP server {self.host}")

    async def disconnect(self) -> None:
        """Close IMAP connection."""
        if self._client:
            try:
                await self._client.logout()
            except Exception as e:
                logger.warning(f"Error during IMAP logout: {e}")
            self._client = None
            logger.info("Disconnected from IMAP server")

    async def select_folder(self, folder: str) -> int:
        """
        Select an IMAP folder.

        Args:
            folder: Folder name to select

        Returns:
            Number of messages in folder
        """
        response = await self._client.select(folder)
        if response[0] != "OK":
            raise RuntimeError(f"Failed to select folder {folder}: {response}")
        # Parse message count from response
        return int(response[1][0].decode() if response[1] else 0)

    async def fetch_unseen(self, folder: str) -> List[EmailMessage]:
        """
        Fetch unseen emails from a folder.

        Args:
            folder: Folder to fetch from

        Returns:
            List of EmailMessage objects
        """
        await self.select_folder(folder)

        # Search for unseen messages
        response = await self._client.uid("SEARCH", "UNSEEN")
        if response[0] != "OK":
            raise RuntimeError(f"IMAP search failed: {response}")

        # Parse UIDs from response
        uid_data = response[1][0].decode() if response[1] and response[1][0] else ""
        uids = uid_data.split() if uid_data else []

        if not uids:
            return []

        messages = []
        for uid in uids:
            msg = await self._fetch_message(uid)
            if msg:
                messages.append(msg)

        return messages

    async def _fetch_message(self, uid: str) -> Optional[EmailMessage]:
        """Fetch a single message by UID."""
        response = await self._client.uid("FETCH", uid, "(RFC822)")
        if response[0] != "OK" or not response[1]:
            logger.warning(f"Failed to fetch message {uid}")
            return None

        # Parse the email
        raw_email = None
        for item in response[1]:
            if isinstance(item, tuple) and len(item) >= 2:
                raw_email = item[1]
                break

        if not raw_email:
            return None

        msg = email.message_from_bytes(raw_email)

        # Decode sender
        sender = msg.get("From", "")

        # Decode subject
        subject = ""
        raw_subject = msg.get("Subject", "")
        if raw_subject:
            decoded_parts = decode_header(raw_subject)
            subject = "".join(
                part.decode(charset or "utf-8") if isinstance(part, bytes) else part
                for part, charset in decoded_parts
            )

        # Extract body
        body_text = None
        body_html = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and body_text is None:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="replace")
                elif content_type == "text/html" and body_html is None:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode("utf-8", errors="replace")
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                decoded = payload.decode("utf-8", errors="replace")
                if content_type == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded

        return EmailMessage(
            uid=uid,
            sender=sender,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    async def mark_seen(self, uid: str) -> None:
        """Mark a message as seen."""
        await self._client.uid("STORE", uid, "+FLAGS", "\\Seen")
        logger.debug(f"Marked message {uid} as seen")

    async def move_to_folder(self, uid: str, folder: str) -> None:
        """
        Move a message to another folder.

        Args:
            uid: Message UID
            folder: Destination folder name
        """
        # Copy to destination folder
        response = await self._client.uid("COPY", uid, folder)
        if response[0] != "OK":
            raise RuntimeError(f"Failed to copy message to {folder}: {response}")

        # Mark original as deleted
        await self._client.uid("STORE", uid, "+FLAGS", "\\Deleted")

        # Expunge deleted messages
        await self._client.expunge()

        logger.debug(f"Moved message {uid} to {folder}")
