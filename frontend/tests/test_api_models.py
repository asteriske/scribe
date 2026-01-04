"""Test API models."""
from frontend.api.models import TranscribeRequest, TranscriptionResponse


def test_transcribe_request_validation():
    """Test request validation"""
    req = TranscribeRequest(url="https://youtube.com/watch?v=test123")
    assert req.url == "https://youtube.com/watch?v=test123"


def test_transcription_response():
    """Test response model"""
    resp = TranscriptionResponse(
        id="youtube_test",
        status="completed",
        progress=100,
        source={
            "type": "youtube",
            "url": "https://youtube.com/watch?v=test123",
            "id": "youtube_test"
        }
    )
    assert resp.id == "youtube_test"
    assert resp.status == "completed"
