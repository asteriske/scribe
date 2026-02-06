"""Client for frontend API communication."""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

HTML_SUMMARY_SUFFIX = """Format your response using valid HTML elements (headings, paragraphs, lists, tables, etc.). Do not include <html>, <head>, or <body> tags - only the inner content."""


@dataclass
class TranscriptionResult:
    """Result from a transcription job."""

    transcription_id: str
    status: str
    title: Optional[str] = None
    full_text: Optional[str] = None
    duration_seconds: Optional[int] = None
    error: Optional[str] = None
    source_context: Optional[str] = None


class FrontendClient:
    """Client for communicating with the frontend API."""

    def __init__(self, base_url: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def submit_url(self, url: str, tag: str | None = None) -> str:
        """
        Submit a URL for transcription.

        Args:
            url: URL to transcribe
            tag: Optional tag to apply to the transcription

        Returns:
            Transcription ID

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        logger.debug(f"POST /api/transcribe starting for {url}")
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {"url": url}
            if tag:
                payload["tags"] = [tag]
            response = await client.post(
                f"{self.base_url}/api/transcribe",
                json=payload,
            )
            elapsed = time.monotonic() - start
            response.raise_for_status()
            data = response.json()
            logger.info(f"Submitted URL for transcription: {url} -> {data['id']} ({elapsed:.2f}s)")
            return data["id"]

    async def get_tags(self) -> set[str]:
        """
        Fetch available tags from frontend config.

        Returns:
            Set of tag names

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        logger.debug("GET /api/config/tags starting")
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/config/tags")
            elapsed = time.monotonic() - start
            response.raise_for_status()
            data = response.json()
            logger.debug(f"GET /api/config/tags completed ({elapsed:.2f}s)")
            return set(data.get("tags", {}).keys())

    async def get_tag_config(self, tag_name: str) -> dict | None:
        """
        Fetch configuration for a specific tag.

        Args:
            tag_name: Name of the tag to fetch config for

        Returns:
            Tag configuration dict or None if tag not found
        """
        logger.debug(f"GET /api/tags/{tag_name} starting")
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags/{tag_name}")
                elapsed = time.monotonic() - start
                response.raise_for_status()
                logger.debug(f"GET /api/tags/{tag_name} completed ({elapsed:.2f}s)")
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise

    async def get_transcription(self, transcription_id: str) -> TranscriptionResult:
        """
        Get transcription status and result.

        Args:
            transcription_id: ID of the transcription

        Returns:
            TranscriptionResult with current status and data
        """
        logger.debug(f"GET /api/transcriptions/{transcription_id} starting")
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/api/transcriptions/{transcription_id}"
            )
            elapsed = time.monotonic() - start
            response.raise_for_status()
            data = response.json()
            logger.debug(f"GET /api/transcriptions/{transcription_id} completed: status={data['status']} ({elapsed:.2f}s)")

            result = TranscriptionResult(
                transcription_id=data["id"],
                status=data["status"],
            )

            # Extract source info if available
            if "source" in data:
                result.title = data["source"].get("title")

            # Extract source_context if available
            result.source_context = data.get("source_context")

            # Extract transcription data if completed
            if "transcription" in data and data["transcription"]:
                result.full_text = data["transcription"].get("full_text")
                duration = data["transcription"].get("duration")
                if duration:
                    result.duration_seconds = int(duration)

            # Extract error if failed
            if data["status"] == "failed":
                result.error = data.get("error", "Unknown error")

            return result

    async def get_transcript_text(self, transcription_id: str) -> str:
        """
        Get the full transcript text.

        Args:
            transcription_id: ID of the transcription

        Returns:
            Full transcript text
        """
        logger.debug(f"GET /api/transcriptions/{transcription_id}/export/txt starting")
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/api/transcriptions/{transcription_id}/export/txt"
            )
            elapsed = time.monotonic() - start
            response.raise_for_status()
            logger.debug(f"GET /api/transcriptions/{transcription_id}/export/txt completed ({elapsed:.2f}s)")
            return response.text

    async def generate_summary(
        self,
        transcription_id: str,
        system_prompt_suffix: str | None = None,
    ) -> str:
        """
        Generate a summary for a transcription.

        Args:
            transcription_id: ID of the transcription
            system_prompt_suffix: Optional suffix to append to system prompt

        Returns:
            Summary text

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        logger.debug(f"POST /api/summaries starting for {transcription_id}")
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=360.0) as client:  # Longer timeout for LLM (must exceed summarizer's 300s)
            payload = {"transcription_id": transcription_id}
            if system_prompt_suffix:
                payload["system_prompt_suffix"] = system_prompt_suffix

            response = await client.post(
                f"{self.base_url}/api/summaries",
                json=payload,
            )
            elapsed = time.monotonic() - start
            response.raise_for_status()
            data = response.json()
            logger.info(f"Generated summary for {transcription_id} ({elapsed:.2f}s)")
            return data["summary_text"]

    async def wait_for_completion(
        self,
        transcription_id: str,
        poll_interval: float = 5.0,
        max_wait: float = 3600.0,
    ) -> TranscriptionResult:
        """
        Wait for a transcription to complete.

        Args:
            transcription_id: ID of the transcription
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            Final TranscriptionResult

        Raises:
            TimeoutError: If max_wait exceeded
        """
        import asyncio

        logger.info(f"Waiting for transcription {transcription_id} (max_wait={max_wait}s)")
        start = time.monotonic()
        poll_count = 0
        while (time.monotonic() - start) < max_wait:
            poll_count += 1
            result = await self.get_transcription(transcription_id)

            if result.status in ("completed", "failed"):
                total_elapsed = time.monotonic() - start
                logger.info(f"Transcription {transcription_id} {result.status} after {total_elapsed:.1f}s ({poll_count} polls)")
                return result

            await asyncio.sleep(poll_interval)

        total_elapsed = time.monotonic() - start
        raise TimeoutError(
            f"Transcription {transcription_id} did not complete within {total_elapsed:.1f}s ({poll_count} polls)"
        )
