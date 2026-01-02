"""Job queue management for transcription tasks."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel

from .config import settings
from .whisper import whisper_model

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionJob(BaseModel):
    """Transcription job model."""

    job_id: str
    audio_path: str
    model: str
    language: Optional[str] = None
    task: str = "transcribe"
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


class JobQueue:
    """Manages transcription job queue."""

    def __init__(self):
        """Initialize job queue."""
        self.jobs: Dict[str, TranscriptionJob] = {}
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=settings.queue_size)
        self.current_job_id: Optional[str] = None
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the job queue worker."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Job queue worker started")

    async def stop(self):
        """Stop the job queue worker."""
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("Job queue worker stopped")

    async def submit_job(
        self,
        audio_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> str:
        """
        Submit a new transcription job.

        Args:
            audio_path: Path to audio file
            model: Whisper model to use (defaults to config)
            language: Language code or None for auto-detect
            task: 'transcribe' or 'translate'

        Returns:
            Job ID

        Raises:
            asyncio.QueueFull: If queue is full
        """
        job_id = str(uuid.uuid4())
        job = TranscriptionJob(
            job_id=job_id,
            audio_path=audio_path,
            model=model or settings.whisper_model,
            language=language,
            task=task,
            created_at=datetime.utcnow(),
        )

        # Add to jobs dictionary
        self.jobs[job_id] = job

        # Add to queue (this will raise QueueFull if full)
        try:
            await self.queue.put(job_id)
            logger.info(f"Job {job_id} submitted to queue")
        except asyncio.QueueFull:
            # Remove from jobs dict if queue is full
            del self.jobs[job_id]
            logger.warning("Job queue is full")
            raise

        return job_id

    def get_job(self, job_id: str) -> Optional[TranscriptionJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)

    def get_queue_position(self, job_id: str) -> Optional[int]:
        """Get position of job in queue (0-indexed)."""
        job = self.jobs.get(job_id)
        if not job or job.status != JobStatus.QUEUED:
            return None

        # Count queued jobs before this one
        position = 0
        for jid in list(self.jobs.keys()):
            j = self.jobs[jid]
            if j.status == JobStatus.QUEUED and j.created_at < job.created_at:
                position += 1

        return position

    async def _worker(self):
        """Background worker that processes jobs from the queue."""
        logger.info("Job queue worker running")

        while True:
            try:
                # Get next job from queue
                job_id = await self.queue.get()
                job = self.jobs.get(job_id)

                if not job:
                    logger.warning(f"Job {job_id} not found")
                    continue

                # Process the job
                self.current_job_id = job_id
                await self._process_job(job)
                self.current_job_id = None

                # Mark queue task as done
                self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("Worker task cancelled")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

    async def _process_job(self, job: TranscriptionJob):
        """Process a single transcription job."""
        logger.info(f"Processing job {job.job_id}")

        # Update status
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()

        try:
            # Transcribe (run in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                whisper_model.transcribe,
                job.audio_path,
                job.language,
                job.task,
            )

            # Update job with result
            job.status = JobStatus.COMPLETED
            job.result = result
            job.progress = 100
            job.completed_at = datetime.utcnow()

            logger.info(f"Job {job.job_id} completed successfully")

        except Exception as e:
            # Handle failure
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()

            logger.error(f"Job {job.job_id} failed: {e}")

    async def cleanup_old_jobs(self):
        """Remove completed/failed jobs older than retention period."""
        cutoff = datetime.utcnow() - timedelta(hours=settings.job_retention_hours)
        removed = 0

        for job_id in list(self.jobs.keys()):
            job = self.jobs[job_id]
            if (
                job.status in [JobStatus.COMPLETED, JobStatus.FAILED]
                and job.completed_at
                and job.completed_at < cutoff
            ):
                del self.jobs[job_id]
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old jobs")

    @property
    def stats(self) -> Dict:
        """Get queue statistics."""
        return {
            "total_jobs": len(self.jobs),
            "queued": sum(1 for j in self.jobs.values() if j.status == JobStatus.QUEUED),
            "processing": sum(1 for j in self.jobs.values() if j.status == JobStatus.PROCESSING),
            "completed": sum(1 for j in self.jobs.values() if j.status == JobStatus.COMPLETED),
            "failed": sum(1 for j in self.jobs.values() if j.status == JobStatus.FAILED),
            "current_job": self.current_job_id,
            "queue_size": self.queue.qsize(),
            "queue_max_size": settings.queue_size,
        }


# Global job queue instance
job_queue = JobQueue()
