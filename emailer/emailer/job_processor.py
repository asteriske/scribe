"""Process transcription jobs from URLs."""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from emailer.frontend_client import FrontendClient

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
        summary = await self.frontend.generate_summary(transcription_id)

        return JobResult(
            url=url,
            success=True,
            title=result.title,
            summary=summary,
            transcript=transcript,
            duration_seconds=result.duration_seconds,
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
        try:
            # Submit for transcription
            logger.info(f"Submitting URL: {url}")
            transcription_id = await self.frontend.submit_url(url, tag=tag)

            # Wait for completion
            logger.info(f"Waiting for transcription: {transcription_id}")
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

            logger.info(f"Generating summary for: {transcription_id}")
            summary = await self.frontend.generate_summary(transcription_id)

            return JobResult(
                url=url,
                success=True,
                title=result.title,
                summary=summary,
                transcript=transcript,
                duration_seconds=result.duration_seconds,
            )

        except httpx.HTTPStatusError as e:
            # Handle 409 Conflict - transcription already exists
            if e.response.status_code == 409:
                try:
                    data = e.response.json()
                    existing_id = data.get("existing_id")
                    if existing_id:
                        logger.info(f"Transcription already exists: {existing_id}")
                        return await self._process_existing(url, existing_id)
                except httpx.HTTPStatusError as inner_e:
                    # Re-raise to be handled below with correct error
                    e = inner_e
                except Exception as inner_e:
                    logger.error(f"Error processing existing transcription {url}: {inner_e}")
                    return JobResult(url=url, success=False, error=str(inner_e))

            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_msg = e.response.text or error_msg
            except Exception:
                pass
            logger.error(f"HTTP error processing {url}: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)

        except TimeoutError as e:
            logger.error(f"Timeout processing {url}: {e}")
            return JobResult(url=url, success=False, error=str(e))

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return JobResult(url=url, success=False, error=str(e))
