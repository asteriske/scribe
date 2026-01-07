"""Client for frontend API communication."""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result from a transcription job."""

    transcription_id: str
    status: str
    title: Optional[str] = None
    full_text: Optional[str] = None
    duration_seconds: Optional[int] = None
    error: Optional[str] = None


class FrontendClient:
    """Client for communicating with the frontend API."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def submit_url(self, url: str) -> str:
        """
        Submit a URL for transcription.

        Args:
            url: URL to transcribe

        Returns:
            Transcription ID

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/transcribe",
                json={"url": url},
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Submitted URL for transcription: {url} -> {data['id']}")
            return data["id"]

    async def get_transcription(self, transcription_id: str) -> TranscriptionResult:
        """
        Get transcription status and result.

        Args:
            transcription_id: ID of the transcription

        Returns:
            TranscriptionResult with current status and data
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/api/transcriptions/{transcription_id}"
            )
            response.raise_for_status()
            data = response.json()

            result = TranscriptionResult(
                transcription_id=data["id"],
                status=data["status"],
            )

            # Extract source info if available
            if "source" in data:
                result.title = data["source"].get("title")

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

    async def generate_summary(self, transcription_id: str) -> str:
        """
        Generate a summary for a transcription.

        Args:
            transcription_id: ID of the transcription

        Returns:
            Summary text

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for LLM
            response = await client.post(
                f"{self.base_url}/api/summaries",
                json={"transcription_id": transcription_id},
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Generated summary for {transcription_id}")
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

        elapsed = 0.0
        while elapsed < max_wait:
            result = await self.get_transcription(transcription_id)

            if result.status in ("completed", "failed"):
                return result

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"Transcription {transcription_id} did not complete within {max_wait}s"
        )
