# frontend/tests/test_storage.py
"""Test storage manager service."""
import pytest
import json
from pathlib import Path
from datetime import datetime, timezone
from frontend.services.storage import StorageManager


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory"""
    storage = StorageManager(base_dir=tmp_path)
    return storage


def test_save_and_load_transcription(temp_storage):
    """Test saving and loading transcription JSON"""
    transcription_data = {
        "id": "youtube_test123",
        "source": {
            "type": "youtube",
            "url": "https://youtube.com/watch?v=test123",
            "title": "Test Video"
        },
        "transcription": {
            "language": "en",
            "duration": 120.5,
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world"}
            ]
        }
    }

    # Save
    path = temp_storage.save_transcription("youtube_test123", transcription_data)
    assert path.exists()

    # Load
    loaded = temp_storage.load_transcription("youtube_test123")
    assert loaded["id"] == "youtube_test123"
    assert loaded["source"]["title"] == "Test Video"


def test_export_to_txt(temp_storage):
    """Test exporting transcription to TXT format"""
    transcription_data = {
        "transcription": {
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world"},
                {"id": 1, "start": 2.5, "end": 5.0, "text": "This is a test"}
            ]
        }
    }

    path = temp_storage.save_transcription("test_id", transcription_data)
    txt_content = temp_storage.export_to_txt("test_id")

    assert "Hello world" in txt_content
    assert "This is a test" in txt_content


def test_export_to_srt(temp_storage):
    """Test exporting transcription to SRT format"""
    transcription_data = {
        "transcription": {
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world"},
                {"id": 1, "start": 2.5, "end": 5.0, "text": "This is a test"}
            ]
        }
    }

    path = temp_storage.save_transcription("test_id", transcription_data)
    srt_content = temp_storage.export_to_srt("test_id")

    # Check SRT format
    assert "1\n" in srt_content  # First subtitle number
    assert "00:00:00,000 --> 00:00:02,500" in srt_content
    assert "Hello world" in srt_content
    assert "2\n" in srt_content  # Second subtitle number
    assert "This is a test" in srt_content


def test_get_transcription_path(temp_storage):
    """Test getting transcription file path"""
    path = temp_storage.get_transcription_path("youtube_test123")
    assert "youtube_test123.json" in str(path)
    # Check year/month directory structure (dynamic date)
    now = datetime.now(timezone.utc)
    assert f"/{now.year}/" in str(path)
    assert f"/{now.month:02d}/" in str(path)


def test_delete_transcription(temp_storage):
    """Test deleting transcription files"""
    data = {"id": "test_delete", "transcription": {"segments": []}}
    path = temp_storage.save_transcription("test_delete", data)
    assert path.exists()

    result = temp_storage.delete_transcription("test_delete")
    assert result is True
    assert not path.exists()

    # Test deleting non-existent file
    result = temp_storage.delete_transcription("nonexistent")
    assert result is False
