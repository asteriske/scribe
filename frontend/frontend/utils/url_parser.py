"""URL parsing and ID generation utilities."""

import hashlib
import re
from enum import Enum
from typing import NamedTuple, Optional
from urllib.parse import urlparse


class SourceType(str, Enum):
    """Source type enumeration."""
    YOUTUBE = "youtube"
    APPLE_PODCASTS = "apple_podcasts"
    DIRECT_AUDIO = "direct_audio"


class URLInfo(NamedTuple):
    """Parsed URL information."""
    source_type: SourceType
    original_url: str
    id: str
    video_id: Optional[str] = None
    podcast_id: Optional[str] = None


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL.

    Supports:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def extract_apple_podcast_id(url: str) -> Optional[str]:
    """
    Extract Apple Podcasts episode ID from URL.

    Supports:
    - https://podcasts.apple.com/us/podcast/name/id123?i=1000456
    """
    match = re.search(r'[?&]i=(\d+)', url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Fallback to podcast show ID
    match = re.search(r'/id(\d+)', url, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def generate_id(url: str) -> str:
    """
    Generate deterministic ID from URL.

    Examples:
    - youtube.com/watch?v=abc123 → 'youtube_abc123'
    - youtu.be/abc123 → 'youtube_abc123'
    - podcasts.apple.com/.../id123 → 'apple_podcasts_123'
    - example.com/audio.mp3 → 'direct_audio_<hash>'
    """
    # YouTube
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        video_id = extract_youtube_id(url)
        if video_id:
            return f'youtube_{video_id}'

    # Apple Podcasts
    elif 'podcasts.apple.com' in url_lower:
        podcast_id = extract_apple_podcast_id(url)
        if podcast_id:
            return f'apple_podcasts_{podcast_id}'

    # Direct audio URL - use hash (MD5 is sufficient for ID generation, not security)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f'direct_audio_{url_hash}'


def parse_url(url: str) -> URLInfo:
    """
    Parse URL and extract metadata.

    Args:
        url: Source URL to parse

    Returns:
        URLInfo with source type, ID, and extracted metadata

    Raises:
        ValueError: If URL is invalid or unsupported
    """
    # Basic URL validation
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    # Check domain (case-insensitive)
    url_lower = url.lower()

    # YouTube
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        video_id = extract_youtube_id(url)
        if not video_id:
            raise ValueError(f"Could not extract YouTube video ID from: {url}")

        return URLInfo(
            source_type=SourceType.YOUTUBE,
            original_url=url,
            id=f'youtube_{video_id}',
            video_id=video_id
        )

    # Apple Podcasts
    elif 'podcasts.apple.com' in url_lower:
        podcast_id = extract_apple_podcast_id(url)
        if not podcast_id:
            raise ValueError(f"Could not extract Apple Podcasts ID from: {url}")

        return URLInfo(
            source_type=SourceType.APPLE_PODCASTS,
            original_url=url,
            id=f'apple_podcasts_{podcast_id}',
            podcast_id=podcast_id
        )

    # Direct audio URL
    else:
        # Validate it looks like an audio file
        path = parsed.path.lower()
        audio_extensions = ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac']
        if not any(path.endswith(ext) for ext in audio_extensions):
            # Still allow it, but warn in logs
            pass

        # MD5 is sufficient for ID generation (not used for security)
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return URLInfo(
            source_type=SourceType.DIRECT_AUDIO,
            original_url=url,
            id=f'direct_audio_{url_hash}'
        )
