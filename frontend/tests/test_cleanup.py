"""Test cleanup service."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from frontend.core.models import Base, Transcription
from frontend.core.database import init_db
from frontend.utils.cleanup import CleanupService


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return engine


@pytest.fixture
def cleanup_service(test_db, tmp_path):
    """Create cleanup service"""
    return CleanupService(
        db_engine=test_db,
        audio_cache_dir=tmp_path / "audio"
    )


def test_find_expired_audio(cleanup_service, test_db):
    """Test finding expired audio files"""
    with Session(test_db) as session:
        # Create transcriptions with different expiry dates
        t1 = Transcription(
            id="expired_1",
            source_type="youtube",
            source_url="https://youtube.com/1",
            status="completed",
            audio_path="/path/to/audio1.m4a",
            audio_cached_until=datetime.utcnow() - timedelta(days=1)  # Expired
        )
        t2 = Transcription(
            id="valid_1",
            source_type="youtube",
            source_url="https://youtube.com/2",
            status="completed",
            audio_path="/path/to/audio2.m4a",
            audio_cached_until=datetime.utcnow() + timedelta(days=1)  # Valid
        )
        session.add_all([t1, t2])
        session.commit()

    expired = cleanup_service._find_expired_audio()
    assert len(expired) == 1
    assert expired[0].id == "expired_1"


async def test_cleanup_expired_audio(cleanup_service, test_db, tmp_path):
    """Test cleanup of expired audio"""
    # Create test audio file
    audio_file = tmp_path / "audio" / "test.m4a"
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    audio_file.write_text("fake audio")

    with Session(test_db) as session:
        t = Transcription(
            id="test",
            source_type="youtube",
            source_url="https://youtube.com/test",
            status="completed",
            audio_path=str(audio_file),
            audio_cached_until=datetime.utcnow() - timedelta(days=1)
        )
        session.add(t)
        session.commit()

    # Run cleanup
    count = await cleanup_service.cleanup_expired_audio()
    assert count == 1
    assert not audio_file.exists()
