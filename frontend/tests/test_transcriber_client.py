"""Test transcriber client service."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from frontend.services.transcriber_client import TranscriberClient, TranscriptionResult


@pytest.fixture
def client():
    """Create transcriber client"""
    return TranscriberClient(base_url="http://localhost:8001")


def test_client_initialization(client):
    """Test client initializes correctly"""
    assert client.base_url == "http://localhost:8001"
    assert client.timeout == 300


@patch('frontend.services.transcriber_client.httpx.Client')
def test_submit_job_success(mock_client_class, client, tmp_path):
    """Test successful job submission"""
    # Create mock response
    mock_response = Mock()
    mock_response.status_code = 202
    mock_response.json.return_value = {"job_id": "test_job_123"}

    # Create mock context manager
    mock_http_client = Mock()
    mock_http_client.post.return_value = mock_response

    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_http_client)
    mock_context.__exit__ = Mock(return_value=False)
    mock_client_class.return_value = mock_context

    # Create test audio file
    audio_file = tmp_path / "test.m4a"
    audio_file.write_bytes(b"fake audio data")

    # Submit job
    result = client.submit_job(audio_file, language="en")

    assert result.success
    assert result.job_id == "test_job_123"
    assert result.status == 'queued'


@patch('frontend.services.transcriber_client.httpx.Client')
def test_check_status_completed(mock_client_class, client):
    """Test checking completed job status"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "job_id": "test_job_123",
        "status": "completed",
        "result": {
            "language": "en",
            "duration": 120.5,
            "segments": []
        }
    }

    # Create mock context manager
    mock_http_client = Mock()
    mock_http_client.get.return_value = mock_response

    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_http_client)
    mock_context.__exit__ = Mock(return_value=False)
    mock_client_class.return_value = mock_context

    result = client.check_status("test_job_123")

    assert result.success
    assert result.status == "completed"
    assert result.result is not None


@patch('frontend.services.transcriber_client.httpx.Client')
def test_health_check(mock_client_class, client):
    """Test health check endpoint"""
    mock_response = Mock()
    mock_response.status_code = 200

    # Create mock context manager
    mock_http_client = Mock()
    mock_http_client.get.return_value = mock_response

    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_http_client)
    mock_context.__exit__ = Mock(return_value=False)
    mock_client_class.return_value = mock_context

    result = client.health_check()
    assert result is True
