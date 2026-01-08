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


def test_export_to_txt_paragraph_formatting(temp_storage):
    """Test that TXT export combines fragments and creates paragraphs at gaps"""
    transcription_data = {
        "transcription": {
            "segments": [
                # First paragraph - fragments combined into sentences
                {"id": 0, "start": 0.0, "end": 1.5, "text": "So today we're going to talk about"},
                {"id": 1, "start": 1.5, "end": 3.0, "text": "machine learning."},
                {"id": 2, "start": 3.0, "end": 4.5, "text": "It's very interesting."},
                # 3 second gap here - should start new paragraph
                {"id": 3, "start": 7.5, "end": 9.0, "text": "Let me start with the basics."},
            ]
        }
    }

    temp_storage.save_transcription("test_paragraphs", transcription_data)
    txt_content = temp_storage.export_to_txt("test_paragraphs")

    # Should have two paragraphs separated by blank line
    paragraphs = txt_content.split('\n\n')
    assert len(paragraphs) == 2

    # First paragraph combines fragments
    assert paragraphs[0] == "So today we're going to talk about machine learning. It's very interesting."

    # Second paragraph after the gap
    assert paragraphs[1] == "Let me start with the basics."


def test_export_to_txt_no_paragraph_break_small_gap(temp_storage):
    """Test that small gaps (<2s) don't create paragraph breaks"""
    transcription_data = {
        "transcription": {
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.0, "text": "First sentence."},
                # 1 second gap - should NOT start new paragraph
                {"id": 1, "start": 3.0, "end": 5.0, "text": "Second sentence."},
            ]
        }
    }

    temp_storage.save_transcription("test_small_gap", transcription_data)
    txt_content = temp_storage.export_to_txt("test_small_gap")

    # Should be one paragraph (no double newline)
    assert '\n\n' not in txt_content
    assert txt_content == "First sentence. Second sentence."


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
