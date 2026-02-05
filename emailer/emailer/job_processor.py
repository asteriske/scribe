"""Process transcription jobs from URLs."""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from emailer.frontend_client import FrontendClient, HTML_SUMMARY_SUFFIX

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    """Result of processing a URL."""

    url: str
    success: bool
    title: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    duration_seconds: Optional[int] = None
    error: Optional[str] = None
    creator_notes: Optional[str] = None


class JobProcessor:
    """Process transcription jobs."""

    def __init__(self, frontend_client: FrontendClient):
        self.frontend = frontend_client

    async def _process_existing(self, url: str, transcription_id: str) -> JobResult:
        """Process an existing transcription (handle 409 case)."""
        result = await self.frontend.wait_for_completion(transcription_id)

        if result.status == "failed":
            return JobResult(
                url=url,
                success=False,
                error=result.error or "Transcription failed",
            )

        # Get transcript and generate summary
        logger.info(f"Fetching transcript for: {transcription_id}")
        transcript = await self.frontend.get_transcript_text(transcription_id)

        logger.info(f"Generating summary for existing: {transcription_id}")
        summary = await self.frontend.generate_summary(
            transcription_id,
            system_prompt_suffix=HTML_SUMMARY_SUFFIX,
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

    async def process_url(self, url: str, tag: str | None = None) -> JobResult:
        """
        Process a single URL through transcription and summarization.

        Args:
            url: URL to process
            tag: Optional tag to apply to the transcription

        Returns:
            JobResult with success status and data or error
        """
        job_start = time.monotonic()
        current_step = "initializing"
        transcription_id = None
        try:
            # Submit for transcription
            current_step = "submitting URL"
            logger.info(f"[{url}] Step 1/4: Submitting URL")
            transcription_id = await self.frontend.submit_url(url, tag=tag)

            # Wait for completion
            current_step = "waiting for transcription"
            logger.info(f"[{url}] Step 2/4: Waiting for transcription {transcription_id}")
            result = await self.frontend.wait_for_completion(transcription_id)

            if result.status == "failed":
                elapsed = time.monotonic() - job_start
                logger.error(f"[{url}] Failed after {elapsed:.1f}s: {result.error}")
                return JobResult(
                    url=url,
                    success=False,
                    error=result.error or "Transcription failed",
                )

            # Get transcript and generate summary
            current_step = "fetching transcript"
            logger.info(f"[{url}] Step 3/4: Fetching transcript for {transcription_id}")
            transcript = await self.frontend.get_transcript_text(transcription_id)

            current_step = "generating summary"
            logger.info(f"[{url}] Step 4/4: Generating summary for {transcription_id}")
            summary = await self.frontend.generate_summary(
                transcription_id,
                system_prompt_suffix=HTML_SUMMARY_SUFFIX,
            )

            elapsed = time.monotonic() - job_start
            logger.info(f"[{url}] Completed successfully in {elapsed:.1f}s")
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
            # Handle 409 Conflict - transcription already exists
            if e.response.status_code == 409:
                try:
                    data = e.response.json()
                    existing_id = data.get("existing_id")
                    if existing_id:
                        logger.info(f"[{url}] Transcription already exists: {existing_id}")
                        return await self._process_existing(url, existing_id)
                except httpx.HTTPStatusError as inner_e:
                    # Re-raise to be handled below with correct error
                    e = inner_e
                except Exception as inner_e:
                    logger.error(f"[{url}] Error processing existing transcription: {inner_e}")
                    return JobResult(url=url, success=False, error=str(inner_e))

            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_msg = e.response.text or error_msg
            except Exception:
                pass
            logger.error(f"[{url}] HTTP error during '{current_step}' after {elapsed:.1f}s: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)

        except TimeoutError as e:
            elapsed = time.monotonic() - job_start
            logger.error(f"[{url}] Timeout during '{current_step}' after {elapsed:.1f}s: {e}")
            return JobResult(url=url, success=False, error=str(e))

        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - job_start
            error_msg = f"Request timed out during '{current_step}': {type(e).__name__}"
            logger.error(f"[{url}] HTTP timeout after {elapsed:.1f}s: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)

        except Exception as e:
            elapsed = time.monotonic() - job_start
            error_msg = str(e) or f"Unexpected error: {type(e).__name__}"
            logger.error(f"[{url}] Error during '{current_step}' after {elapsed:.1f}s: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)
