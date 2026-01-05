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


def test_transcribe_request_with_tags():
    """Test TranscribeRequest accepts optional tags."""
    request = TranscribeRequest(
        url="https://youtube.com/watch?v=test",
        tags=["kindle", "format"]
    )
    assert request.tags == ["kindle", "format"]


def test_transcribe_request_tags_optional():
    """Test TranscribeRequest tags defaults to empty list."""
    request = TranscribeRequest(url="https://youtube.com/watch?v=test")
    assert request.tags == []


def test_transcription_response_includes_tags():
    """Test TranscriptionResponse includes tags."""
    response = TranscriptionResponse(
        id="test123",
        status="completed",
        tags=["work", "review"]
    )
    assert response.tags == ["work", "review"]


def test_update_tags_request():
    """Test UpdateTagsRequest model."""
    from frontend.api.models import UpdateTagsRequest
    request = UpdateTagsRequest(tags=["new", "tags"])
    assert request.tags == ["new", "tags"]
