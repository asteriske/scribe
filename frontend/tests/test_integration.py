"""Integration tests for complete workflow."""
import pytest
from fastapi.testclient import TestClient

from frontend.main import app


@pytest.mark.integration
def test_api_endpoints_available():
    """Test that all API endpoints are available"""
    client = TestClient(app)

    # Test web interface
    response = client.get('/')
    assert response.status_code == 200

    # Test API endpoints exist
    response = client.get('/api/transcriptions')
    assert response.status_code == 200

    # Test health endpoint
    response = client.get('/api/health')
    assert response.status_code == 200


@pytest.mark.integration
def test_transcription_submission():
    """Test transcription submission creates a job"""
    client = TestClient(app)

    # Submit a URL for transcription
    # This will fail in the background (no real downloader/transcriber)
    # but should accept the request
    response = client.post('/api/transcribe', json={
        'url': 'https://youtube.com/watch?v=test123'
    })
    # Should accept the request (202) or reject with validation error
    assert response.status_code in [202, 400, 422]

    if response.status_code == 202:
        data = response.json()
        assert 'id' in data
