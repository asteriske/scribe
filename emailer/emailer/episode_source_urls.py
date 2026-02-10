"""Extract Apple Podcasts and YouTube URLs from email content."""

import logging
import re
from typing import List

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EPISODE_SOURCE_PATTERNS = [
    r"youtube\.com/watch",
    r"youtube\.com/live/",
    r"youtu\.be/",
    r"podcasts\.apple\.com/.*[?&]i=\d+",
]

# Link text patterns that suggest the href may redirect to a matching URL
LINK_TEXT_HINTS = [
    re.compile(r"apple\s*podcasts?", re.IGNORECASE),
    re.compile(r"youtube", re.IGNORECASE),
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


def _link_text_suggests_episode_source(text: str) -> bool:
    """Check if link text suggests the href points to an episode source."""
    for pattern in LINK_TEXT_HINTS:
        if pattern.search(text):
            return True
    return False


def _resolve_redirect(url: str) -> str | None:
    """Follow redirects to get the final URL. Returns None on failure."""
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.head(url)
            final_url = str(response.url)
            if final_url != url:
                logger.info(f"Resolved redirect: {url} -> {final_url}")
            return final_url
    except Exception as e:
        logger.warning(f"Failed to resolve redirect for {url}: {e}")
        return None


def extract_episode_source_urls(body: str, is_html: bool = False) -> List[str]:
    """
    Extract Apple Podcasts and YouTube URLs from email content.

    For HTML content, if a link's text suggests it points to Apple Podcasts
    or YouTube but the href is a redirect URL, the redirect is followed
    to resolve the actual destination.

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
            elif _link_text_suggests_episode_source(link.get_text()):
                # Link text says "Apple Podcasts" or "YouTube" but href
                # is a redirect (e.g. Substack, Mailchimp tracking links)
                resolved = _resolve_redirect(href)
                if resolved and _is_episode_source_url(resolved):
                    urls.add(resolved)
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
