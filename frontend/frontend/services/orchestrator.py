"""Orchestration service for coordinating transcription workflow."""

import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, NamedTuple
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

from frontend.core.config import settings
from frontend.core.models import Transcription
from frontend.services.downloader import Downloader
from frontend.services.transcriber_client import TranscriberClient
from frontend.services.storage import StorageManager
from frontend.utils.url_parser import parse_url

logger = logging.getLogger(__name__)


class OrchestrationResult(NamedTuple):
    """Result of orchestration process."""
    success: bool
    transcription_id: Optional[str] = None
    error: Optional[str] = None


class Orchestrator:
    """Coordinates the complete transcription workflow."""

    def __init__(
        self,
        db_engine: Engine = None,
        audio_cache_dir: Path = None,
        transcriptions_dir: Path = None
    ):
        """
        Initialize orchestrator.

        Args:
            db_engine: Database engine (defaults to creating from settings)
            audio_cache_dir: Audio cache directory
            transcriptions_dir: Transcriptions storage directory
        """
        # Database
        if db_engine is None:
            db_engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False}
            )
        self.engine = db_engine
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Services
        self.downloader = Downloader(audio_cache_dir=audio_cache_dir)
        self.transcriber_client = TranscriberClient()
        self.storage = StorageManager(base_dir=transcriptions_dir)

    async def process_url(self, url: str) -> OrchestrationResult:
        """
        Process a URL through complete transcription workflow.

        Workflow:
        1. Parse URL and generate ID
        2. Check for duplicate
        3. Create database record
        4. Download audio
        5. Submit to transcriber
        6. Poll for completion
        7. Save results
        8. Update database

        Args:
            url: Source URL to process

        Returns:
            OrchestrationResult with success status and transcription ID
        """
        try:
            # Parse URL
            logger.info(f"Processing URL: {url}")
            url_info = parse_url(url)
            transcription_id = url_info.id

            with self.SessionLocal() as session:
                # Check for duplicate
                existing = session.query(Transcription).filter_by(source_url=url).first()
                if existing:
                    logger.info(f"URL already processed: {transcription_id}")
                    return OrchestrationResult(
                        success=False,
                        transcription_id=transcription_id,
                        error="URL already transcribed"
                    )

                # Create job record
                transcription = self._create_job_record(
                    session=session,
                    transcription_id=transcription_id,
                    url=url,
                    source_type=url_info.source_type.value
                )
                session.commit()

            # Download audio
            await self._update_status(transcription_id, "downloading", 10)
            download_result = self.downloader.download(url, transcription_id)

            if not download_result.success:
                await self._mark_failed(transcription_id, f"Download failed: {download_result.error}")
                return OrchestrationResult(
                    success=False,
                    transcription_id=transcription_id,
                    error=download_result.error
                )

            # Update with download metadata
            await self._update_metadata(transcription_id, download_result.metadata)

            # Submit to transcriber
            await self._update_status(transcription_id, "transcribing", 50)
            transcribe_result = self.transcriber_client.submit_job(download_result.audio_path)

            if not transcribe_result.success:
                await self._mark_failed(transcription_id, f"Transcription failed: {transcribe_result.error}")
                return OrchestrationResult(
                    success=False,
                    transcription_id=transcription_id,
                    error=transcribe_result.error
                )

            # Poll for completion
            job_id = transcribe_result.job_id
            final_result = await self.transcriber_client.wait_for_completion(job_id)

            if not final_result.success or final_result.status == 'failed':
                error = final_result.error or "Transcription failed"
                await self._mark_failed(transcription_id, error)
                return OrchestrationResult(
                    success=False,
                    transcription_id=transcription_id,
                    error=error
                )

            # Save transcription results
            await self._update_status(transcription_id, "completed", 90)
            await self._save_results(transcription_id, download_result.metadata, final_result.result)

            await self._update_status(transcription_id, "completed", 100)
            logger.info(f"Successfully processed {transcription_id}")

            return OrchestrationResult(
                success=True,
                transcription_id=transcription_id
            )

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            return OrchestrationResult(
                success=False,
                error=str(e)
            )

    def _create_job_record(
        self,
        session: Session,
        transcription_id: str,
        url: str,
        source_type: str
    ) -> Transcription:
        """Create initial job record in database."""
        transcription = Transcription(
            id=transcription_id,
            source_type=source_type,
            source_url=url,
            status='pending',
            progress=0
        )
        session.add(transcription)
        return transcription

    async def _update_status(self, transcription_id: str, status: str, progress: int):
        """Update job status and progress."""
        with self.SessionLocal() as session:
            transcription = session.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.status = status
                transcription.progress = progress

                if status == "downloading" and not transcription.started_at:
                    transcription.started_at = datetime.now(timezone.utc)
                elif status == "completed":
                    transcription.transcribed_at = datetime.now(timezone.utc)

                session.commit()
                logger.info(f"{transcription_id}: {status} ({progress}%)")

    async def _update_metadata(self, transcription_id: str, metadata: dict):
        """Update transcription with download metadata."""
        with self.SessionLocal() as session:
            transcription = session.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.title = metadata.get('title')
                transcription.channel = metadata.get('channel')
                transcription.duration_seconds = metadata.get('duration_seconds')
                transcription.thumbnail_url = metadata.get('thumbnail_url')
                transcription.upload_date = metadata.get('upload_date')
                transcription.audio_format = metadata.get('format')

                # Set audio cache expiration
                transcription.audio_cached_until = datetime.now(timezone.utc) + timedelta(days=settings.audio_cache_days)

                session.commit()

    async def _save_results(self, transcription_id: str, metadata: dict, transcription_data: dict):
        """Save transcription results to file and database."""
        # Get the transcription record to extract source info
        with self.SessionLocal() as session:
            transcription = session.query(Transcription).filter_by(id=transcription_id).first()

            # Build full transcription JSON
            full_data = {
                "id": transcription_id,
                "source": {
                    "type": transcription.source_type,  # Get from DB record
                    "url": transcription.source_url,     # Get from DB record
                    "title": metadata.get('title'),
                    "channel": metadata.get('channel'),
                    "upload_date": metadata.get('upload_date'),
                    "thumbnail": metadata.get('thumbnail_url')
                },
                "transcription": transcription_data,
                "full_text": self._extract_full_text(transcription_data),
                "metadata": {
                    "word_count": self._count_words(transcription_data),
                    "segments_count": len(transcription_data.get('segments', []))
                }
            }

            # Save to file
            path = self.storage.save_transcription(transcription_id, full_data)

            # Update database with results
            transcription.transcription_path = str(path)
            transcription.language = transcription_data.get('language')
            transcription.word_count = full_data['metadata']['word_count']
            transcription.segments_count = full_data['metadata']['segments_count']
            transcription.full_text = full_data['full_text']
            transcription.model_used = 'whisper-medium-mlx'

            session.commit()

    async def _mark_failed(self, transcription_id: str, error: str):
        """Mark job as failed with error message."""
        with self.SessionLocal() as session:
            transcription = session.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.status = 'failed'
                transcription.error_message = error
                session.commit()
                logger.error(f"{transcription_id}: {error}")

    def _extract_full_text(self, transcription_data: dict) -> str:
        """Extract full text from segments."""
        segments = transcription_data.get('segments', [])
        return ' '.join(segment.get('text', '').strip() for segment in segments)

    def _count_words(self, transcription_data: dict) -> int:
        """Count total words in transcription."""
        full_text = self._extract_full_text(transcription_data)
        return len(full_text.split())
