"""Transcriber service client for submitting jobs and checking status."""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, NamedTuple

import httpx

from frontend.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptionResult(NamedTuple):
    """Result of a transcription operation."""

    success: bool
    job_id: Optional[str] = None
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TranscriberClient:
    """Client for interacting with the transcriber service."""

    def __init__(
        self, base_url: str = None, timeout: int = None
    ):
        """
        Initialize transcriber client.

        Args:
            base_url: Base URL of transcriber service (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = (base_url or settings.transcriber_url).rstrip('/')
        self.timeout = timeout if timeout is not None else settings.transcriber_timeout

    def health_check(self) -> bool:
        """
        Check if transcriber service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def submit_job(
        self, audio_path: Path, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Submit transcription job to the service.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., "en", "es")

        Returns:
            TranscriptionResult with job_id and status='queued' on success
        """
        try:
            audio_path = Path(audio_path)

            if not audio_path.exists():
                error = f"Audio file not found: {audio_path}"
                logger.error(error)
                return TranscriptionResult(success=False, error=error)

            # Prepare multipart form data
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'file': (audio_path.name, audio_file, 'audio/m4a')
                }
                data = {}
                if language:
                    data['language'] = language

                # Submit job to transcriber service
                with httpx.Client(timeout=self.timeout) as client:
                    logger.info(f"Submitting transcription job for {audio_path.name}")
                    response = client.post(
                        f"{self.base_url}/transcribe",
                        files=files,
                        data=data
                    )

                    if response.status_code == 202:
                        result = response.json()
                        job_id = result.get('job_id')
                        logger.info(f"Job submitted successfully: {job_id}")
                        return TranscriptionResult(
                            success=True,
                            job_id=job_id,
                            status='queued'
                        )
                    else:
                        error = (
                            f"Job submission failed with status {response.status_code}: "
                            f"{response.text}"
                        )
                        logger.error(error)
                        return TranscriptionResult(success=False, error=error)

        except Exception as e:
            error = f"Failed to submit job: {str(e)}"
            logger.error(error, exc_info=True)
            return TranscriptionResult(success=False, error=error)

    def check_status(self, job_id: str) -> TranscriptionResult:
        """
        Check status of a transcription job.

        Args:
            job_id: Job ID returned from submit_job

        Returns:
            TranscriptionResult with status and result (if completed)
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                logger.debug(f"Checking status for job {job_id}")
                response = client.get(f"{self.base_url}/jobs/{job_id}")

                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    result = data.get('result')

                    logger.debug(f"Job {job_id} status: {status}")
                    return TranscriptionResult(
                        success=True,
                        job_id=job_id,
                        status=status,
                        result=result
                    )

                elif response.status_code == 404:
                    error = f"Job not found: {job_id}"
                    logger.error(error)
                    return TranscriptionResult(success=False, error=error)

                else:
                    error = (
                        f"Status check failed with status {response.status_code}: "
                        f"{response.text}"
                    )
                    logger.error(error)
                    return TranscriptionResult(success=False, error=error)

        except Exception as e:
            error = f"Failed to check status: {str(e)}"
            logger.error(error, exc_info=True)
            return TranscriptionResult(success=False, error=error)

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: int = 5,
        max_wait: int = 600
    ) -> TranscriptionResult:
        """
        Wait for a job to complete by polling status.

        Args:
            job_id: Job ID to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            TranscriptionResult with final status and result
        """
        logger.info(
            f"Waiting for job {job_id} completion "
            f"(poll_interval={poll_interval}s, max_wait={max_wait}s)"
        )

        elapsed = 0
        while elapsed < max_wait:
            # Check job status
            result = self.check_status(job_id)

            if not result.success:
                return result

            status = result.status

            # Check if job is complete
            if status == "completed":
                logger.info(f"Job {job_id} completed successfully")
                return result

            elif status == "failed":
                error = f"Job {job_id} failed"
                logger.error(error)
                return TranscriptionResult(
                    success=False,
                    job_id=job_id,
                    status=status,
                    error=error
                )

            elif status in ["pending", "processing", "queued"]:
                # Job still in progress, wait and retry
                logger.debug(f"Job {job_id} status: {status}, waiting {poll_interval}s")
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            else:
                # Unknown status
                error = f"Unknown job status: {status}"
                logger.error(error)
                return TranscriptionResult(
                    success=False,
                    job_id=job_id,
                    status=status,
                    error=error
                )

        # Timeout reached
        error = f"Job {job_id} did not complete within {max_wait} seconds"
        logger.error(error)
        return TranscriptionResult(
            success=False,
            job_id=job_id,
            error=error
        )
