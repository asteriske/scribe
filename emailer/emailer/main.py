"""Main entry point for the emailer service."""

import asyncio
import logging
import signal
from typing import Optional

from emailer.config import Settings, get_settings
from emailer.frontend_client import FrontendClient
from emailer.imap_client import ImapClient, EmailMessage
from emailer.job_processor import JobProcessor, JobResult
from emailer.result_formatter import (
    format_success_email,
    format_error_email,
    format_no_urls_email,
)
from emailer.smtp_client import SmtpClient
from emailer.url_extractor import extract_urls
from emailer.tag_resolver import resolve_tag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EmailerService:
    """Main emailer service."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._shutdown_event: Optional[asyncio.Event] = None
        self.semaphore: Optional[asyncio.Semaphore] = None

        # Initialize clients
        self.imap = ImapClient(
            host=settings.imap_host,
            port=settings.imap_port,
            user=settings.imap_user,
            password=settings.imap_password,
            use_ssl=settings.imap_use_ssl,
        )

        self.smtp = SmtpClient(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
        )

        frontend = FrontendClient(base_url=settings.frontend_url)
        self.processor = JobProcessor(frontend_client=frontend)

    async def start(self) -> None:
        """Start the emailer service."""
        logger.info("Emailer service starting...")

        # Use an Event instead of a boolean flag for shutdown signaling.
        # asyncio.Event.wait() can be interrupted immediately when set(),
        # unlike asyncio.sleep() which blocks for the full duration.
        self._shutdown_event = asyncio.Event()
        self.semaphore = asyncio.Semaphore(self.settings.max_concurrent_jobs)

        # Connect to IMAP
        await self.imap.connect()

        logger.info(
            f"Monitoring folder: {self.settings.imap_folder_inbox} "
            f"(poll interval: {self.settings.poll_interval_seconds}s)"
        )

        try:
            while not self._shutdown_event.is_set():
                await self._poll_and_process()
                # Wait for shutdown signal or poll interval (whichever comes first).
                # Using wait_for with timeout instead of sleep() allows immediate
                # response to ctrl-c/SIGTERM without waiting for poll interval.
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.settings.poll_interval_seconds,
                    )
                except asyncio.TimeoutError:
                    pass  # Timeout is expected - continue polling
        finally:
            await self.imap.disconnect()
            logger.info("Emailer service stopped.")

    async def stop(self) -> None:
        """Stop the emailer service."""
        logger.info("Stopping emailer service...")
        # Setting the event wakes up the wait_for() call immediately,
        # allowing graceful shutdown without waiting for poll interval.
        self._shutdown_event.set()

    async def _poll_and_process(self) -> None:
        """Poll for new emails and process them."""
        try:
            emails = await self.imap.fetch_unseen(self.settings.imap_folder_inbox)

            if emails:
                logger.info(f"Found {len(emails)} new email(s)")

            tasks = []
            for email in emails:
                # Mark as seen immediately
                await self.imap.mark_seen(email.msg_num)
                # Process concurrently with semaphore
                task = asyncio.create_task(self._process_email_with_semaphore(email))
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error during poll: {e}")

    async def _process_email_with_semaphore(self, email: EmailMessage) -> None:
        """Process email with concurrency limit."""
        async with self.semaphore:
            await self._process_email(email)

    async def _process_email(self, email: EmailMessage) -> None:
        """Process a single email."""
        logger.info(f"Processing email {email.msg_num} from {email.sender}")

        # Extract URLs from both text and HTML
        urls = []
        if email.body_text:
            urls.extend(extract_urls(email.body_text, is_html=False))
        if email.body_html:
            urls.extend(extract_urls(email.body_html, is_html=True))

        # Deduplicate
        urls = list(dict.fromkeys(urls))

        if not urls:
            # No transcribable URLs found
            await self._handle_no_urls(email)
            return

        # Resolve tag from subject
        try:
            available_tags = await self.processor.frontend.get_tags()
        except Exception as e:
            logger.warning(f"Failed to fetch tags, using default: {e}")
            available_tags = set()

        tag = resolve_tag(
            subject=email.subject,
            available_tags=available_tags,
            default=self.settings.default_tag,
        )
        logger.info(f"Resolved tag '{tag}' from subject: {email.subject}")

        # Fetch tag config for destination email resolution
        tag_config = None
        try:
            tag_config = await self.processor.frontend.get_tag_config(tag)
        except Exception as e:
            logger.warning(f"Failed to fetch tag config for '{tag}': {e}")

        # Process each URL
        results = []
        for url in urls:
            result = await self.processor.process_url(url, tag=tag)
            results.append(result)
            await self._send_result_email(email, result, tag_config=tag_config)

        # Determine final folder and move
        any_success = any(r.success for r in results)
        target_folder = (
            self.settings.imap_folder_done if any_success
            else self.settings.imap_folder_error
        )
        try:
            await self.imap.move_to_folder(email.msg_num, target_folder)
        except Exception as e:
            logger.error(
                f"Failed to move email {email.msg_num} to {target_folder}: {e}"
            )

    async def _handle_no_urls(self, email: EmailMessage) -> None:
        """Handle email with no transcribable URLs."""
        subject, body = format_no_urls_email()

        await self.smtp.send_email(
            from_addr=self.settings.from_email_address,
            to_addr=email.sender,
            subject=subject,
            body=body,
        )

        try:
            await self.imap.move_to_folder(email.msg_num, self.settings.imap_folder_error)
        except Exception as e:
            logger.error(
                f"Failed to move email {email.msg_num} to "
                f"{self.settings.imap_folder_error}: {e}"
            )
        logger.info(f"No URLs in email {email.msg_num}, notified sender")

    async def _send_result_email(
        self, email: EmailMessage, result: JobResult, tag_config: dict | None = None
    ) -> None:
        """Send result or error email based on job result."""
        if result.success:
            subject, html_body, text_body = format_success_email(
                url=result.url,
                title=result.title or "Untitled",
                duration_seconds=result.duration_seconds or 0,
                summary=result.summary or "",
                transcript=result.transcript or "",
            )
            # Use tag's destination_emails if set, otherwise reply to sender
            destination_emails = tag_config.get("destination_emails", []) if tag_config else []
            if destination_emails:
                recipients = destination_emails
            else:
                recipients = [email.sender]

            for to_addr in recipients:
                await self.smtp.send_email(
                    from_addr=self.settings.from_email_address,
                    to_addr=to_addr,
                    subject=subject,
                    body=text_body,
                    html_body=html_body,
                )
        else:
            subject, body = format_error_email(
                url=result.url,
                error_message=result.error or "Unknown error",
            )
            await self.smtp.send_email(
                from_addr=self.settings.from_email_address,
                to_addr=email.sender,
                subject=subject,
                body=body,
            )


async def main() -> None:
    """Main entry point."""
    settings = get_settings()
    service = EmailerService(settings)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        asyncio.create_task(service.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
