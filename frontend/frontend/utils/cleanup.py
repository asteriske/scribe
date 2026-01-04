"""Cleanup service for expired audio and old jobs."""

import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine

from frontend.core.config import settings
from frontend.core.models import Transcription

logger = logging.getLogger(__name__)


class CleanupService:
    """Handles cleanup of expired audio files and old jobs."""

    def __init__(self, db_engine: Engine = None, audio_cache_dir: Path = None):
        """
        Initialize cleanup service.

        Args:
            db_engine: Database engine
            audio_cache_dir: Audio cache directory
        """
        if db_engine is None:
            db_engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False}
            )

        self.engine = db_engine
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.audio_cache_dir = Path(audio_cache_dir or settings.audio_cache_dir)

    def _find_expired_audio(self):
        """Find transcriptions with expired audio cache."""
        with self.SessionLocal() as session:
            expired = session.query(Transcription).filter(
                Transcription.audio_cached_until < datetime.utcnow(),
                Transcription.audio_path.isnot(None)
            ).all()

            return expired

    async def cleanup_expired_audio(self) -> int:
        """
        Delete expired audio files.

        Returns:
            Number of files deleted
        """
        expired = self._find_expired_audio()
        count = 0

        for transcription in expired:
            try:
                # Delete audio file
                audio_path = Path(transcription.audio_path)
                if audio_path.exists():
                    audio_path.unlink()
                    logger.info(f"Deleted expired audio: {audio_path}")
                    count += 1

                # Update database
                with self.SessionLocal() as session:
                    t = session.query(Transcription).filter_by(id=transcription.id).first()
                    if t:
                        t.audio_path = None
                        session.commit()

            except Exception as e:
                logger.error(f"Error deleting {transcription.audio_path}: {e}")

        if count > 0:
            logger.info(f"Cleaned up {count} expired audio files")

        return count

    async def cleanup_failed_jobs(self, max_age_days: int = 7) -> int:
        """
        Delete failed job records older than max_age_days.

        Args:
            max_age_days: Maximum age in days for failed jobs

        Returns:
            Number of jobs deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        with self.SessionLocal() as session:
            failed_jobs = session.query(Transcription).filter(
                Transcription.status == 'failed',
                Transcription.created_at < cutoff_date
            ).all()

            count = len(failed_jobs)

            for job in failed_jobs:
                session.delete(job)

            session.commit()

        if count > 0:
            logger.info(f"Deleted {count} old failed jobs")

        return count

    async def run_cleanup(self):
        """Run all cleanup tasks."""
        logger.info("Starting cleanup tasks")

        audio_count = await self.cleanup_expired_audio()
        failed_count = await self.cleanup_failed_jobs()

        logger.info(
            f"Cleanup complete: {audio_count} audio files, {failed_count} failed jobs"
        )

        return {
            'audio_files_deleted': audio_count,
            'failed_jobs_deleted': failed_count
        }
