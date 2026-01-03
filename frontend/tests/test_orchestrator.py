"""Test orchestrator service."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from frontend.core.models import Base, Transcription
from frontend.core.database import init_db
from frontend.services.orchestrator import Orchestrator, OrchestrationResult


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return engine


@pytest.fixture
def orchestrator(test_db, tmp_path):
    """Create orchestrator with test database"""
    orch = Orchestrator(
        db_engine=test_db,
        audio_cache_dir=tmp_path / "audio",
        transcriptions_dir=tmp_path / "transcriptions"
    )
    return orch


def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly"""
    assert orchestrator.downloader is not None
    assert orchestrator.transcriber_client is not None
    assert orchestrator.storage is not None


@patch('frontend.services.orchestrator.Downloader')
@patch('frontend.services.orchestrator.TranscriberClient')
async def test_process_url_full_workflow(
    mock_transcriber_class,
    mock_downloader_class,
    orchestrator,
    test_db
):
    """Test complete orchestration workflow"""
    # Mock downloader
    mock_downloader = Mock()
    mock_downloader.download.return_value = Mock(
        success=True,
        audio_path=Path("/tmp/test.m4a"),
        metadata={'title': 'Test Video', 'duration_seconds': 120}
    )
    mock_downloader_class.return_value = mock_downloader
    orchestrator.downloader = mock_downloader

    # Mock transcriber
    mock_transcriber = Mock()
    mock_transcriber.submit_job.return_value = Mock(
        success=True,
        job_id='job_123'
    )
    mock_transcriber.wait_for_completion = AsyncMock(return_value=Mock(
        success=True,
        status='completed',
        result={'language': 'en', 'segments': []}
    ))
    mock_transcriber_class.return_value = mock_transcriber
    orchestrator.transcriber_client = mock_transcriber

    # Process URL
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    result = await orchestrator.process_url(url)

    assert result.success
    assert result.transcription_id == "youtube_dQw4w9WgXcQ"


def test_create_job_record(orchestrator, test_db):
    """Test creating job record in database"""
    with Session(test_db) as session:
        transcription = orchestrator._create_job_record(
            session=session,
            transcription_id="youtube_test",
            url="https://youtube.com/watch?v=test",
            source_type="youtube"
        )

        assert transcription.id == "youtube_test"
        assert transcription.status == "pending"
        assert transcription.progress == 0
