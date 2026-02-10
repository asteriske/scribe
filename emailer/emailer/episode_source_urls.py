"""Extract Apple Podcasts and YouTube URLs from email content."""

import re
from typing import List

from bs4 import BeautifulSoup

EPISODE_SOURCE_PATTERNS = [
    r"youtube\.com/watch",
    r"youtube\.com/live/",
    r"youtu\.be/",
    r"podcasts\.apple\.com/",
]

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\)\]]+",
    re.IGNORECASE,
)


def _is_episode_source_url(url: str) -> bool:
    """Check if a URL is an Apple Podcasts or YouTube URL."""
    for pattern in EPISODE_SOURCE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def extract_episode_source_urls(body: str, is_html: bool = False) -> List[str]:
    """
    Extract Apple Podcasts and YouTube URLs from email content.

    Args:
        body: Email body content
        is_html: Whether the body is HTML

    Returns:
        List of unique matching URLs
    """
    if not body:
        return []

    urls = set()

    if is_html:
        soup = BeautifulSoup(body, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if _is_episode_source_url(href):
                urls.add(href)
        text = soup.get_text()
        for match in URL_PATTERN.findall(text):
            clean_url = match.rstrip(".,;:!?)")
            if _is_episode_source_url(clean_url):
                urls.add(clean_url)
    else:
        for match in URL_PATTERN.findall(body):
            clean_url = match.rstrip(".,;:!?)")
            if _is_episode_source_url(clean_url):
                urls.add(clean_url)

    return list(urls)
