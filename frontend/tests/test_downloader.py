# frontend/tests/test_downloader.py
"""Test downloader service."""
import pytest
from pathlib import Path
from frontend.services.downloader import Downloader, DownloadResult


@pytest.fixture
def temp_downloader(tmp_path):
    """Create downloader with temp directory"""
    return Downloader(audio_cache_dir=tmp_path)


def test_downloader_initialization(temp_downloader):
    """Test downloader initializes correctly"""
    assert temp_downloader.audio_cache_dir.exists()


@pytest.mark.skip(reason="Requires network access and yt-dlp")
def test_download_youtube_video(temp_downloader):
    """Test downloading YouTube video (requires network)"""
    # Use a short test video
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video
    result = temp_downloader.download(url, "youtube_test")

    assert result.success
    assert result.audio_path.exists()
    assert result.metadata is not None
    assert result.metadata.get('title')
    assert result.metadata.get('duration_seconds')


def test_build_yt_dlp_options(temp_downloader):
    """Test yt-dlp options are configured correctly"""
    options = temp_downloader._build_yt_dlp_options("test_id")

    assert 'format' in options
    assert 'outtmpl' in options
    assert 'audio' in options['format']
    assert options['postprocessors'][0]['key'] == 'FFmpegExtractAudio'
