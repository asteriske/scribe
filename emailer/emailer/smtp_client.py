"""SMTP client for sending emails."""

import logging
from email.message import EmailMessage

from aiosmtplib import SMTP

logger = logging.getLogger(__name__)


class SmtpClient:
    """Async SMTP client for sending emails."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_tls = use_tls

    async def send_email(
        self,
        from_addr: str,
        to_addr: str,
        subject: str,
        body: str,
    ) -> None:
        """
        Send an email.

        Args:
            from_addr: Sender email address
            to_addr: Recipient email address
            subject: Email subject
            body: Email body (plain text)
        """
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg.set_content(body)

        smtp = SMTP(hostname=self.host, port=self.port)

        try:
            await smtp.connect()

            if self.use_tls:
                await smtp.starttls()

            await smtp.login(self.user, self.password)
            await smtp.send_message(msg)

            logger.info(f"Sent email to {to_addr}: {subject}")

        finally:
            await smtp.quit()
