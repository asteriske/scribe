"""Apple Podcasts show notes scraper."""

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class ApplePodcastsScraper:
    """Scraper for extracting show notes from Apple Podcasts pages."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def is_apple_podcasts_url(self, url: str) -> bool:
        """Check if the URL is an Apple Podcasts URL."""
        return "podcasts.apple.com" in url.lower()

    def fetch_show_notes(self, url: str) -> Optional[str]:
        """Fetch and extract show notes from an Apple Podcasts URL.

        Args:
            url: The Apple Podcasts episode URL.

        Returns:
            Extracted show notes text, or None if extraction fails.
        """
        html_content = self._fetch_page(url)
        if not html_content:
            return None
        return self._extract_content(html_content)

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch the HTML content of a page with retry logic.

        Args:
            url: The URL to fetch.

        Returns:
            HTML content as string, or None if all retries fail.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                    response = client.get(url, headers=headers, follow_redirects=True)
                    response.raise_for_status()
                    return response.text
            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(f"Server error {e.response.status_code} (attempt {attempt + 1}/{self.max_retries})")
                else:
                    logger.error(f"HTTP error {e.response.status_code} fetching {url}")
                    return None
            except httpx.RequestError as e:
                logger.warning(f"Request error: {e} (attempt {attempt + 1}/{self.max_retries})")

        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    def _extract_content(self, html: str) -> Optional[str]:
        """Extract show notes content from HTML.

        Args:
            html: The HTML content to parse.

        Returns:
            Extracted text content, or None if extraction fails.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            content_parts = []

            # Extract meta description
            meta_desc = soup.find("meta", {"name": "description"})
            if meta_desc and meta_desc.get("content"):
                content_parts.append(meta_desc["content"])

            # Try various selectors for show notes content
            desc_selectors = [
                "section.product-hero-desc",
                "div.product-hero-desc",
                "[data-testid='description']",
                ".episode-description",
                ".show-notes",
            ]

            for selector in desc_selectors:
                desc_section = soup.select_one(selector)
                if desc_section:
                    text = desc_section.get_text(separator="\n", strip=True)
                    if text and text not in content_parts:
                        content_parts.append(text)

            # Look for timestamp patterns (e.g., "12:34" or "1:23:45")
            timestamp_pattern = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")
            for element in soup.find_all(string=timestamp_pattern):
                parent = element.find_parent()
                if parent:
                    text = parent.get_text(strip=True)
                    if text and len(text) < 500 and text not in content_parts:
                        content_parts.append(text)

            if content_parts:
                return "\n\n".join(content_parts)

            # Fallback: extract body text
            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
                if len(text) > 5000:
                    text = text[:5000] + "..."
                return text if text else None

            return None
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return None
