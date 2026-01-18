"""Extract transcribable URLs from email content."""

import re
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Patterns for transcribable URLs
TRANSCRIBABLE_PATTERNS = [
    r"youtube\.com/watch",
    r"youtube\.com/live/",
    r"youtu\.be/",
    r"podcasts\.apple\.com/",
    r"podcastaddict\.com/.+/episode/",
]

# File extensions for direct audio URLs
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac"}

# URL regex pattern
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\)\]]+",
    re.IGNORECASE
)


def is_transcribable_url(url: str) -> bool:
    """
    Check if a URL is transcribable.

    Args:
        url: URL to check

    Returns:
        True if the URL is a supported transcribable source
    """
    # Check known patterns
    for pattern in TRANSCRIBABLE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True

    # Check for direct audio file URLs
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    for ext in AUDIO_EXTENSIONS:
        if path_lower.endswith(ext):
            return True

    return False


def extract_urls(body: str, is_html: bool = False) -> List[str]:
    """
    Extract transcribable URLs from email body.

    Args:
        body: Email body content
        is_html: Whether the body is HTML content

    Returns:
        List of unique transcribable URLs found in the body
    """
    if not body:
        return []

    urls = set()

    if is_html:
        # Parse HTML and extract URLs from href attributes and text
        soup = BeautifulSoup(body, "html.parser")

        # Get URLs from anchor tags
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if is_transcribable_url(href):
                urls.add(href)

        # Also search text content for URLs
        text = soup.get_text()
        for match in URL_PATTERN.findall(text):
            # Clean trailing punctuation
            clean_url = match.rstrip(".,;:!?)")
            if is_transcribable_url(clean_url):
                urls.add(clean_url)
    else:
        # Plain text - use regex to find URLs
        for match in URL_PATTERN.findall(body):
            # Clean trailing punctuation
            clean_url = match.rstrip(".,;:!?)")
            if is_transcribable_url(clean_url):
                urls.add(clean_url)

    return list(urls)
