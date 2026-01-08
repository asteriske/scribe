"""Storage manager for transcription files."""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from frontend.core.config import settings

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages transcription file storage and exports."""

    def __init__(self, base_dir: Path = None):
        """
        Initialize storage manager.

        Args:
            base_dir: Base directory for transcriptions (defaults to settings)
        """
        self.base_dir = base_dir or settings.transcriptions_dir
        self.base_dir = Path(self.base_dir)

    def get_transcription_path(self, transcription_id: str) -> Path:
        """
        Get path for transcription JSON file.

        Uses year/month structure: transcriptions/2026/01/youtube_abc123.json

        Args:
            transcription_id: Transcription ID

        Returns:
            Path to transcription file
        """
        now = datetime.now(timezone.utc)
        year_month_dir = self.base_dir / str(now.year) / f"{now.month:02d}"
        return year_month_dir / f"{transcription_id}.json"

    def save_transcription(self, transcription_id: str, data: Dict[str, Any]) -> Path:
        """
        Save transcription data to JSON file.

        Args:
            transcription_id: Transcription ID
            data: Transcription data dictionary

        Returns:
            Path to saved file

        Raises:
            IOError: If file cannot be written
            PermissionError: If insufficient permissions
        """
        path = self.get_transcription_path(transcription_id)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved transcription to {path}")
            return path
        except (IOError, PermissionError) as e:
            logger.error(f"Failed to save transcription {transcription_id}: {e}")
            raise

    def load_transcription(self, transcription_id: str) -> Optional[Dict[str, Any]]:
        """
        Load transcription data from JSON file.

        Args:
            transcription_id: Transcription ID

        Returns:
            Transcription data or None if not found or if error occurs
        """
        try:
            # Try current year/month first
            path = self.get_transcription_path(transcription_id)

            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)

            # Search all subdirectories if not found
            for json_file in self.base_dir.rglob(f"{transcription_id}.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    return json.load(f)

            logger.warning(f"Transcription {transcription_id} not found")
            return None
        except (IOError, PermissionError) as e:
            logger.error(f"Failed to read transcription {transcription_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in transcription {transcription_id}: {e}")
            return None

    def export_to_txt(self, transcription_id: str) -> Optional[str]:
        """
        Export transcription to plain text format.

        Combines segments into readable paragraphs:
        - Fragments joined with spaces until sentence-ending punctuation (. ? !)
        - Paragraph breaks inserted at 2+ second gaps between segments

        Args:
            transcription_id: Transcription ID

        Returns:
            Plain text content or None if not found
        """
        data = self.load_transcription(transcription_id)
        if not data:
            return None

        segments = data.get('transcription', {}).get('segments', [])
        if not segments:
            return ''

        paragraphs = []
        current_sentence = []

        for i, segment in enumerate(segments):
            text = segment['text'].strip()
            current_sentence.append(text)

            # Check if sentence ends
            if text and text[-1] in '.?!':
                # Check for paragraph break (2+ second gap to next segment)
                if i + 1 < len(segments):
                    gap = segments[i + 1]['start'] - segment['end']
                    if gap >= 2.0:
                        # End paragraph
                        paragraphs.append(' '.join(current_sentence))
                        current_sentence = []

        # Don't forget remaining text
        if current_sentence:
            paragraphs.append(' '.join(current_sentence))

        return '\n\n'.join(paragraphs)

    def export_to_srt(self, transcription_id: str) -> Optional[str]:
        """
        Export transcription to SRT subtitle format.

        Args:
            transcription_id: Transcription ID

        Returns:
            SRT formatted content or None if not found
        """
        data = self.load_transcription(transcription_id)
        if not data:
            return None

        segments = data.get('transcription', {}).get('segments', [])
        srt_lines = []

        for segment in segments:
            # Subtitle number
            srt_lines.append(str(segment['id'] + 1))

            # Timestamp
            start = self._format_srt_timestamp(segment['start'])
            end = self._format_srt_timestamp(segment['end'])
            srt_lines.append(f"{start} --> {end}")

            # Text
            srt_lines.append(segment['text'].strip())

            # Blank line
            srt_lines.append('')

        return '\n'.join(srt_lines)

    def _format_srt_timestamp(self, seconds: float) -> str:
        """
        Format seconds to SRT timestamp format (HH:MM:SS,mmm).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def delete_transcription(self, transcription_id: str) -> bool:
        """
        Delete transcription file.

        Args:
            transcription_id: Transcription ID

        Returns:
            True if deleted, False if not found or error occurs
        """
        try:
            # Search for the file
            for json_file in self.base_dir.rglob(f"{transcription_id}.json"):
                json_file.unlink()
                logger.info(f"Deleted transcription {transcription_id}")
                return True

            logger.warning(f"Transcription {transcription_id} not found for deletion")
            return False
        except (IOError, PermissionError) as e:
            logger.error(f"Failed to delete transcription {transcription_id}: {e}")
            return False
