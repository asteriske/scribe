"""Downloader service for audio from various sources."""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, NamedTuple

from frontend.core.config import settings
from frontend.services.apple_podcasts_scraper import ApplePodcastsScraper

logger = logging.getLogger(__name__)


class DownloadResult(NamedTuple):
    """Result of a download operation."""

    success: bool
    audio_path: Optional[Path]
    metadata: Optional[Dict[str, Any]]
    error: Optional[str]


class Downloader:
    """Downloads audio from YouTube, Apple Podcasts, and direct URLs."""

    def __init__(self, audio_cache_dir: Path = None):
        """
        Initialize downloader.

        Args:
            audio_cache_dir: Directory for cached audio files (defaults to settings)
        """
        self.audio_cache_dir = audio_cache_dir or settings.audio_cache_dir
        self.audio_cache_dir = Path(self.audio_cache_dir)
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, transcription_id: str) -> DownloadResult:
        """
        Download audio from URL.

        Args:
            url: Source URL (YouTube, Apple Podcasts, or direct URL)
            transcription_id: Unique transcription ID

        Returns:
            DownloadResult with success status, audio path, metadata, or error
        """
        try:
            import yt_dlp
        except ImportError:
            error = "yt-dlp not installed. Install with: pip install yt-dlp"
            logger.error(error)
            return DownloadResult(
                success=False, audio_path=None, metadata=None, error=error
            )

        try:
            # Build yt-dlp options
            ydl_opts = self._build_yt_dlp_options(transcription_id)

            # Download with yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to check file size
                logger.info(f"Extracting info for {url}")
                info = ydl.extract_info(url, download=False)

                # Check file size if available
                filesize = info.get('filesize') or info.get('filesize_approx')
                if filesize:
                    size_mb = filesize / (1024 * 1024)
                    if size_mb > settings.max_audio_size_mb:
                        error = (
                            f"File size ({size_mb:.1f} MB) exceeds maximum "
                            f"allowed size ({settings.max_audio_size_mb} MB)"
                        )
                        logger.error(error)
                        return DownloadResult(
                            success=False, audio_path=None, metadata=None, error=error
                        )

                # Download the audio
                logger.info(f"Downloading audio from {url}")
                info = ydl.extract_info(url, download=True)

            # Find the downloaded audio file
            audio_path = self._find_audio_file(transcription_id)
            if not audio_path:
                error = f"Downloaded audio file not found for {transcription_id}"
                logger.error(error)
                return DownloadResult(
                    success=False, audio_path=None, metadata=None, error=error
                )

            # Verify file size on disk
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.max_audio_size_mb:
                error = (
                    f"Downloaded file size ({file_size_mb:.1f} MB) exceeds maximum "
                    f"allowed size ({settings.max_audio_size_mb} MB)"
                )
                logger.error(error)
                # Clean up the file
                audio_path.unlink()
                return DownloadResult(
                    success=False, audio_path=None, metadata=None, error=error
                )

            # Extract metadata
            metadata = self._extract_metadata(info)

            logger.info(
                f"Successfully downloaded audio to {audio_path} "
                f"({file_size_mb:.1f} MB)"
            )
            return DownloadResult(
                success=True, audio_path=audio_path, metadata=metadata, error=None
            )

        except Exception as e:
            error_str = str(e)

            # Check if this is an Apple Podcasts URL and yt-dlp failed
            if self._is_apple_podcasts_url(url) and "Unable to extract" in error_str:
                logger.warning(f"yt-dlp Apple Podcasts extractor failed, trying fallback: {error_str}")
                return self._download_apple_podcasts_fallback(url, transcription_id)

            error = f"Download failed: {error_str}"
            logger.error(error, exc_info=True)
            return DownloadResult(
                success=False, audio_path=None, metadata=None, error=error
            )

    def _is_apple_podcasts_url(self, url: str) -> bool:
        """Check if URL is an Apple Podcasts URL."""
        return "podcasts.apple.com" in url.lower()

    def _download_apple_podcasts_fallback(self, url: str, transcription_id: str) -> DownloadResult:
        """Fallback download for Apple Podcasts when yt-dlp extractor fails.

        Scrapes the page to find the direct audio URL and downloads via yt-dlp generic extractor.

        Args:
            url: Apple Podcasts episode URL
            transcription_id: Unique transcription ID

        Returns:
            DownloadResult with success status, audio path, metadata, or error
        """
        try:
            import yt_dlp
        except ImportError:
            return DownloadResult(
                success=False, audio_path=None, metadata=None,
                error="yt-dlp not installed"
            )

        try:
            # Use our scraper to extract the audio URL
            scraper = ApplePodcastsScraper()
            audio_url = scraper.extract_audio_url(url)

            if not audio_url:
                error = "Could not extract audio URL from Apple Podcasts page"
                logger.error(error)
                return DownloadResult(
                    success=False, audio_path=None, metadata=None, error=error
                )

            logger.info(f"Found direct audio URL, downloading: {audio_url[:100]}...")

            # Download using the direct URL
            ydl_opts = self._build_yt_dlp_options(transcription_id)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(audio_url, download=True)

            # Find the downloaded file
            audio_path = self._find_audio_file(transcription_id)
            if not audio_path:
                error = f"Downloaded audio file not found for {transcription_id}"
                logger.error(error)
                return DownloadResult(
                    success=False, audio_path=None, metadata=None, error=error
                )

            # Verify file size
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.max_audio_size_mb:
                error = f"File size ({file_size_mb:.1f} MB) exceeds maximum"
                audio_path.unlink()
                return DownloadResult(
                    success=False, audio_path=None, metadata=None, error=error
                )

            metadata = self._extract_metadata(info)
            logger.info(f"Successfully downloaded via fallback to {audio_path} ({file_size_mb:.1f} MB)")

            return DownloadResult(
                success=True, audio_path=audio_path, metadata=metadata, error=None
            )

        except Exception as e:
            error = f"Fallback download failed: {str(e)}"
            logger.error(error, exc_info=True)
            return DownloadResult(
                success=False, audio_path=None, metadata=None, error=error
            )

    def _build_yt_dlp_options(self, transcription_id: str) -> Dict[str, Any]:
        """
        Build yt-dlp options for downloading audio.

        Args:
            transcription_id: Unique transcription ID

        Returns:
            Dictionary of yt-dlp options
        """
        output_template = str(self.audio_cache_dir / f"{transcription_id}.%(ext)s")

        return {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'socket_timeout': settings.download_timeout,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                }
            ],
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
        }

    def _find_audio_file(self, transcription_id: str) -> Optional[Path]:
        """
        Find downloaded audio file with common extensions.

        Args:
            transcription_id: Unique transcription ID

        Returns:
            Path to audio file or None if not found
        """
        # Common audio extensions that yt-dlp might produce
        extensions = ['m4a', 'mp3', 'webm', 'opus', 'wav', 'aac']

        for ext in extensions:
            audio_path = self.audio_cache_dir / f"{transcription_id}.{ext}"
            if audio_path.exists():
                return audio_path

        return None

    def _extract_metadata(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from yt-dlp info dict.

        Args:
            info: yt-dlp info dictionary

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'title': info.get('title'),
            'channel': info.get('channel') or info.get('uploader'),
            'duration_seconds': info.get('duration'),
            'upload_date': info.get('upload_date'),
            'thumbnail_url': info.get('thumbnail'),
            'description': info.get('description'),
            'format': info.get('format'),
        }

        return metadata

    def delete_audio(self, transcription_id: str) -> bool:
        """
        Delete cached audio file.

        Args:
            transcription_id: Unique transcription ID

        Returns:
            True if deleted, False if not found or error occurs
        """
        try:
            audio_path = self._find_audio_file(transcription_id)
            if audio_path and audio_path.exists():
                audio_path.unlink()
                logger.info(f"Deleted audio file {audio_path}")
                return True

            logger.warning(f"Audio file not found for {transcription_id}")
            return False
        except (IOError, PermissionError) as e:
            logger.error(f"Failed to delete audio file {transcription_id}: {e}")
            return False
