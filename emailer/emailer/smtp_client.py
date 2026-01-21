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
        html_body: str | None = None,
    ) -> None:
        """
        Send an email.

        Args:
            from_addr: Sender email address
            to_addr: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            html_body: Optional HTML body (creates multipart email)
        """
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr

        # Set plain text as base content
        msg.set_content(body)

        # Add HTML alternative if provided
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        # Port 587 uses STARTTLS (start_tls=True), port 465 uses implicit TLS (use_tls=True)
        use_implicit_tls = self.port == 465
        smtp = SMTP(
            hostname=self.host,
            port=self.port,
            use_tls=use_implicit_tls,
            start_tls=self.use_tls and not use_implicit_tls,
        )

        try:
            logger.debug(f"Connecting to SMTP server {self.host}:{self.port}")
            await smtp.connect()
            logger.debug("SMTP connected, logging in...")
            await smtp.login(self.user, self.password)
            await smtp.send_message(msg)

            logger.info(f"Sent email to {to_addr}: {subject}")

        finally:
            await smtp.quit()
