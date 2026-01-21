"""Tests for the SummarizerService."""
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from frontend.core.database import init_db
from frontend.core.models import Transcription
from frontend.services.summarizer import SummarizerService


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    init_db(engine)
    return engine


@pytest.fixture
def mock_db(test_db):
    """Create a database session for tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_transcription(mock_db):
    """Create a completed transcription for testing."""
    transcription = Transcription(
        id="test_trans_123",
        source_type="youtube",
        source_url="https://youtube.com/watch?v=test123",
        status="completed",
        tags=json.dumps(["test-tag"])
    )
    mock_db.add(transcription)
    mock_db.commit()
    return transcription


def test_generate_summary_appends_suffix(mock_db, mock_transcription):
    """Test that system_prompt_suffix is appended to the resolved prompt."""
    with patch.object(SummarizerService, '_call_llm_api') as mock_llm:
        mock_llm.return_value = ("Summary text", {"prompt_tokens": 100}, None)

        # Mock the storage manager to return transcription data
        mock_storage = MagicMock()
        mock_storage.load_transcription.return_value = {
            'transcription': {
                'segments': [
                    {'text': 'Hello world.'},
                    {'text': 'This is a test.'}
                ]
            }
        }

        # Mock the config manager to return a resolved config
        mock_config = MagicMock()
        mock_resolved = MagicMock()
        mock_resolved.api_endpoint = "http://test.com/v1"
        mock_resolved.model = "test-model"
        mock_resolved.api_key = "test-key"
        mock_resolved.system_prompt = "You are a helpful assistant."
        mock_resolved.config_source = "default"
        mock_config.resolve_config_for_transcription.return_value = mock_resolved

        service = SummarizerService(
            config_manager=mock_config,
            storage_manager=mock_storage
        )
        result = service.generate_summary(
            db=mock_db,
            transcription_id=mock_transcription.id,
            system_prompt_suffix="Format using HTML elements."
        )

        # Verify the suffix was appended to the prompt
        call_args = mock_llm.call_args
        system_prompt_used = call_args[0][3]  # 4th positional arg is system_prompt
        assert "You are a helpful assistant." in system_prompt_used
        assert "Format using HTML elements." in system_prompt_used
        # Verify the suffix comes after the base prompt
        assert system_prompt_used.index("You are a helpful assistant.") < system_prompt_used.index("Format using HTML elements.")
