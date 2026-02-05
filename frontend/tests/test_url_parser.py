"""Test URL parsing and ID generation."""
import pytest
from frontend.utils.url_parser import (
    parse_url,
    generate_id,
    extract_youtube_id,
    extract_apple_podcast_id,
    extract_podcast_addict_id,
    SourceType
)


def test_parse_youtube_watch_url():
    """Test parsing standard YouTube watch URL"""
    info = parse_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
    assert info.source_type == SourceType.YOUTUBE
    assert info.video_id == "dQw4w9WgXcQ"
    assert info.id == "youtube_dQw4w9WgXcQ"


def test_parse_youtube_short_url():
    """Test parsing YouTube short URL"""
    info = parse_url("https://youtu.be/jNQXAC9IVRw")
    assert info.source_type == SourceType.YOUTUBE
    assert info.video_id == "jNQXAC9IVRw"
    assert info.id == "youtube_jNQXAC9IVRw"


def test_parse_apple_podcasts_url():
    """Test parsing Apple Podcasts URL"""
    url = "https://podcasts.apple.com/us/podcast/the-indicator/id1320118593?i=1000641234567"
    info = parse_url(url)
    assert info.source_type == SourceType.APPLE_PODCASTS
    assert info.id.startswith("apple_podcasts_")


def test_parse_direct_audio_url():
    """Test parsing direct audio URL"""
    info = parse_url("https://example.com/audio/file.mp3")
    assert info.source_type == SourceType.DIRECT_AUDIO
    assert info.id.startswith("direct_audio_")


def test_generate_id_deterministic():
    """Test ID generation is deterministic"""
    url = "https://youtube.com/watch?v=9bZkp7q19f0"
    id1 = generate_id(url)
    id2 = generate_id(url)
    assert id1 == id2
    assert id1 == "youtube_9bZkp7q19f0"


def test_invalid_url():
    """Test invalid URL raises error"""
    with pytest.raises(ValueError, match="Invalid URL"):
        parse_url("not a url")


def test_youtube_case_insensitive():
    """Test YouTube URLs are case-insensitive"""
    info = parse_url("https://YouTube.com/watch?v=dQw4w9WgXcQ")
    assert info.source_type == SourceType.YOUTUBE
    assert info.video_id == "dQw4w9WgXcQ"
    assert info.id == "youtube_dQw4w9WgXcQ"


def test_apple_podcasts_case_insensitive():
    """Test Apple Podcasts URLs are case-insensitive"""
    url = "https://Podcasts.Apple.com/us/podcast/the-indicator/id1320118593?i=1000641234567"
    info = parse_url(url)
    assert info.source_type == SourceType.APPLE_PODCASTS
    assert info.id == "apple_podcasts_1000641234567"


def test_parse_podcast_addict_url():
    """Test parsing Podcast Addict URL"""
    url = "https://podcastaddict.com/hard-fork/episode/215066511"
    info = parse_url(url)
    assert info.source_type == SourceType.PODCAST_ADDICT
    assert info.podcast_id == "215066511"
    assert info.id == "podcast_addict_215066511"


def test_podcast_addict_case_insensitive():
    """Test Podcast Addict URLs are case-insensitive"""
    url = "https://PodcastAddict.com/Hard-Fork/episode/215066511"
    info = parse_url(url)
    assert info.source_type == SourceType.PODCAST_ADDICT
    assert info.id == "podcast_addict_215066511"


def test_spotify_url_rejected():
    """Test Spotify URLs are rejected with helpful message"""
    with pytest.raises(ValueError, match="Spotify URLs are not supported"):
        parse_url("https://open.spotify.com/episode/2309CSMAUfOyJprXS6wq8g")


def test_spotify_url_rejected_case_insensitive():
    """Test Spotify URL rejection is case-insensitive"""
    with pytest.raises(ValueError, match="DRM restrictions"):
        parse_url("https://Open.Spotify.com/episode/abc123")
