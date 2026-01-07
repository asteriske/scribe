"""IMAP client for fetching and managing emails."""

import asyncio
import email
import imaplib
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from email.header import decode_header
from typing import List, Optional

logger = logging.getLogger(__name__)

# Thread pool for blocking IMAP operations
_executor = ThreadPoolExecutor(max_workers=2)


@dataclass
class EmailMessage:
    """Represents an email message."""

    msg_num: str
    sender: str
    subject: str
    body_text: Optional[str]
    body_html: Optional[str]


class ImapClient:
    """IMAP client using standard imaplib with async wrapper."""

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
        self._client: Optional[imaplib.IMAP4_SSL | imaplib.IMAP4] = None

    async def _run_sync(self, func, *args):
        """Run a blocking function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, func, *args)

    async def connect(self) -> None:
        """Establish connection to IMAP server."""
        def _connect():
            if self.use_ssl:
                client = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                client = imaplib.IMAP4(self.host, self.port)
            client.login(self.user, self.password)
            return client

        self._client = await self._run_sync(_connect)
        logger.info(f"Connected to IMAP server {self.host}")

    async def disconnect(self) -> None:
        """Close IMAP connection."""
        if self._client:
            try:
                await self._run_sync(self._client.logout)
            except Exception as e:
                logger.warning(f"Error during IMAP logout: {e}")
            self._client = None
            logger.info("Disconnected from IMAP server")

    async def select_folder(self, folder: str) -> None:
        """Select an IMAP folder."""
        status, _ = await self._run_sync(self._client.select, folder)
        if status != "OK":
            raise RuntimeError(f"Failed to select folder {folder}")

    async def fetch_unseen(self, folder: str) -> List[EmailMessage]:
        """Fetch unseen emails from a folder."""
        await self.select_folder(folder)

        # Search for unseen messages
        status, data = await self._run_sync(self._client.search, None, "UNSEEN")
        if status != "OK":
            raise RuntimeError(f"IMAP search failed")

        # Parse message numbers
        msg_nums = data[0].decode().split() if data[0] else []
        if not msg_nums:
            return []

        logger.info(f"Found {len(msg_nums)} unseen message(s)")

        # Fetch each message
        messages = []
        for msg_num in msg_nums:
            msg = await self._fetch_message(msg_num)
            if msg:
                messages.append(msg)

        return messages

    async def _fetch_message(self, msg_num: str) -> Optional[EmailMessage]:
        """Fetch a single message by sequence number."""
        # Use BODY[] instead of RFC822 for better compatibility (e.g., iCloud)
        status, data = await self._run_sync(
            self._client.fetch, msg_num, "(BODY[])"
        )

        if status != "OK" or not data or not data[0]:
            logger.warning(f"Failed to fetch message {msg_num}")
            return None

        # Parse email from response
        raw_email = None
        if isinstance(data[0], tuple) and len(data[0]) >= 2:
            raw_email = data[0][1]
        elif isinstance(data[0], bytes):
            raw_email = data[0]

        if not raw_email:
            logger.warning(f"No email data in response for {msg_num}")
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
            msg_num=msg_num,
            sender=sender,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    async def mark_seen(self, msg_num: str) -> None:
        """Mark a message as seen."""
        await self._run_sync(self._client.store, msg_num, "+FLAGS", "\\Seen")
        logger.debug(f"Marked message {msg_num} as seen")

    async def move_to_folder(self, msg_num: str, folder: str) -> None:
        """Move a message to another folder."""
        # Copy to destination
        status, _ = await self._run_sync(self._client.copy, msg_num, folder)
        if status != "OK":
            raise RuntimeError(f"Failed to copy message to {folder}")

        # Mark as deleted
        await self._run_sync(self._client.store, msg_num, "+FLAGS", "\\Deleted")

        # Expunge
        await self._run_sync(self._client.expunge)

        logger.debug(f"Moved message {msg_num} to {folder}")
