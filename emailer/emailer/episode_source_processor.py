"""Process episode source emails."""

import logging
import time
from typing import Optional

import html2text
import httpx

from emailer.episode_source_urls import extract_episode_source_urls
from emailer.frontend_client import FrontendClient, HTML_SUMMARY_SUFFIX
from emailer.imap_client import EmailMessage
from emailer.job_processor import JobResult

logger = logging.getLogger(__name__)


def _html_to_plain_text(html_content: str) -> str:
    """Convert HTML to readable plain text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    return h.handle(html_content).strip()


class EpisodeSourceProcessor:
    """Process episode source emails: extract URL, transcribe, store source."""

    def __init__(self, frontend_client: FrontendClient):
        self.frontend = frontend_client

    async def process_email(self, email: EmailMessage) -> JobResult:
        """
        Process an episode source email.

        Extracts Apple Podcasts/YouTube URL, submits for transcription,
        stores the email content as an episode source record.

        Args:
            email: The email message to process

        Returns:
            JobResult with success/failure and transcription data
        """
        job_start = time.monotonic()

        # Extract URLs from both text and HTML
        urls = []
        if email.body_text:
            urls.extend(extract_episode_source_urls(email.body_text, is_html=False))
        if email.body_html:
            urls.extend(extract_episode_source_urls(email.body_html, is_html=True))

        # Deduplicate while preserving order
        urls = list(dict.fromkeys(urls))

        if not urls:
            return JobResult(
                url="",
                success=False,
                error="No Apple Podcasts or YouTube URL found in email",
            )

        logger.info(f"[episode-source] Found {len(urls)} candidate URL(s): {urls}")

        # Get plain text content for storage
        if email.body_text:
            source_text = email.body_text
        elif email.body_html:
            source_text = _html_to_plain_text(email.body_html)
        else:
            source_text = ""

        # Try each URL in order, falling back to the next on failure
        last_error = None
        for i, url in enumerate(urls):
            logger.info(f"[episode-source] Trying URL {i + 1}/{len(urls)}: {url}")
            result = await self._try_url(url, email, source_text, job_start)
            if result.success:
                return result
            last_error = result.error
            if len(urls) > 1:
                logger.warning(f"[episode-source] URL {i + 1} failed: {last_error}")

        # All URLs failed
        return JobResult(
            url=urls[0],
            success=False,
            error=last_error or "All URLs failed",
        )

    async def _try_url(
        self,
        url: str,
        email: EmailMessage,
        source_text: str,
        job_start: float,
    ) -> JobResult:
        """Try to process a single URL. Returns JobResult (success or failure)."""
        current_step = "initializing"
        try:
            # Submit for transcription with "digest" tag
            current_step = "submitting URL"
            logger.info(f"[episode-source] Step 1/5: Submitting {url}")
            transcription_id = await self.frontend.submit_url(url, tag="digest")

            # Wait for completion
            current_step = "waiting for transcription"
            logger.info(f"[episode-source] Step 2/5: Waiting for {transcription_id}")
            result = await self.frontend.wait_for_completion(transcription_id)

            if result.status == "failed":
                elapsed = time.monotonic() - job_start
                logger.error(f"[episode-source] Failed after {elapsed:.1f}s: {result.error}")
                return JobResult(
                    url=url,
                    success=False,
                    error=result.error or "Transcription failed",
                )

            # Get transcript
            current_step = "fetching transcript"
            logger.info(f"[episode-source] Step 3/5: Fetching transcript for {transcription_id}")
            transcript = await self.frontend.get_transcript_text(transcription_id)

            # Generate summary
            current_step = "generating summary"
            logger.info(f"[episode-source] Step 4/5: Generating summary for {transcription_id}")
            summary = await self.frontend.generate_summary(
                transcription_id,
                system_prompt_suffix=HTML_SUMMARY_SUFFIX,
            )

            # Store episode source record
            current_step = "storing episode source"
            logger.info(f"[episode-source] Step 5/5: Storing episode source for {transcription_id}")
            await self.frontend.create_episode_source(
                transcription_id=transcription_id,
                source_text=source_text,
                matched_url=url,
                email_subject=email.subject or None,
                email_from=email.sender or None,
            )

            elapsed = time.monotonic() - job_start
            logger.info(f"[episode-source] Completed successfully in {elapsed:.1f}s")
            return JobResult(
                url=url,
                success=True,
                title=result.title,
                summary=summary,
                transcript=transcript,
                duration_seconds=result.duration_seconds,
                creator_notes=result.source_context,
            )

        except httpx.HTTPStatusError as e:
            elapsed = time.monotonic() - job_start
            if e.response.status_code == 409:
                try:
                    data = e.response.json()
                    existing_id = data.get("existing_id")
                    if existing_id:
                        logger.info(f"[episode-source] Transcription exists: {existing_id}")
                        return await self._process_existing(url, existing_id, email, source_text)
                except Exception as inner_e:
                    logger.error(f"[episode-source] Error processing existing: {inner_e}")
                    return JobResult(url=url, success=False, error=str(inner_e))

            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_msg = e.response.text or error_msg
            except Exception:
                pass
            logger.error(f"[episode-source] HTTP error during '{current_step}' after {elapsed:.1f}s: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)

        except TimeoutError as e:
            elapsed = time.monotonic() - job_start
            logger.error(f"[episode-source] Timeout during '{current_step}' after {elapsed:.1f}s")
            return JobResult(url=url, success=False, error=str(e))

        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - job_start
            error_msg = f"Request timed out during '{current_step}': {type(e).__name__}"
            logger.error(f"[episode-source] {error_msg} after {elapsed:.1f}s")
            return JobResult(url=url, success=False, error=error_msg)

        except Exception as e:
            elapsed = time.monotonic() - job_start
            error_msg = str(e) or f"Unexpected error: {type(e).__name__}"
            logger.error(f"[episode-source] Error during '{current_step}' after {elapsed:.1f}s: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)

    async def _process_existing(
        self,
        url: str,
        transcription_id: str,
        email: EmailMessage,
        source_text: str,
    ) -> JobResult:
        """Process when transcription already exists (409 case)."""
        result = await self.frontend.wait_for_completion(transcription_id)

        if result.status == "failed":
            return JobResult(
                url=url,
                success=False,
                error=result.error or "Transcription failed",
            )

        transcript = await self.frontend.get_transcript_text(transcription_id)
        summary = await self.frontend.generate_summary(
            transcription_id,
            system_prompt_suffix=HTML_SUMMARY_SUFFIX,
        )

        await self.frontend.create_episode_source(
            transcription_id=transcription_id,
            source_text=source_text,
            matched_url=url,
            email_subject=email.subject or None,
            email_from=email.sender or None,
        )

        return JobResult(
            url=url,
            success=True,
            title=result.title,
            summary=summary,
            transcript=transcript,
            duration_seconds=result.duration_seconds,
            creator_notes=result.source_context,
        )
