"""Tests for transcriber API."""

import pytest
from fastapi.testclient import TestClient

from transcriber.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Scribe Transcriber"
    assert "version" in data
    assert "model" in data


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code in [200, 503]  # May be unhealthy if model not loaded
    data = response.json()
    assert "status" in data
    assert "model" in data
    assert "queue" in data


def test_models_endpoint():
    """Test models list endpoint."""
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
    assert "available" in data
    assert isinstance(data["available"], list)
    assert len(data["available"]) > 0


def test_transcribe_invalid_task():
    """Test transcription with invalid task parameter."""
    response = client.post(
        "/transcribe",
        files={"file": ("test.mp3", b"fake audio content", "audio/mpeg")},
        data={"task": "invalid_task"},
    )
    assert response.status_code == 400
    assert "Invalid task" in response.json()["detail"]


def test_transcribe_invalid_format():
    """Test transcription with unsupported audio format."""
    response = client.post(
        "/transcribe",
        files={"file": ("test.txt", b"not audio", "text/plain")},
    )
    assert response.status_code == 400
    assert "Invalid audio format" in response.json()["detail"]


def test_get_nonexistent_job():
    """Test querying non-existent job."""
    response = client.get("/jobs/nonexistent-job-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
