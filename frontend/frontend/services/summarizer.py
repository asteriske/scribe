"""Summarizer service for generating AI summaries via external APIs."""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import NamedTuple, Optional

import httpx
from sqlalchemy.orm import Session

from frontend.core.models import Summary, Transcription
from frontend.services.config_manager import ConfigManager
from frontend.services.storage import StorageManager

logger = logging.getLogger(__name__)

# API timeout in seconds
API_TIMEOUT = 60


class SummaryResult(NamedTuple):
    """Result of a summarization operation."""

    success: bool
    summary: Optional[Summary]
    error: Optional[str]


class SummarizerService:
    """Service for generating and managing AI summaries."""

    def __init__(
        self,
        config_manager: ConfigManager = None,
        storage_manager: StorageManager = None
    ):
        """
        Initialize summarizer service.

        Args:
            config_manager: Configuration manager instance
            storage_manager: Storage manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.storage_manager = storage_manager or StorageManager()

    def _generate_summary_id(self) -> str:
        """Generate a unique summary ID."""
        return f"sum_{uuid.uuid4().hex[:12]}"

    def _call_llm_api(
        self,
        api_endpoint: str,
        model: str,
        api_key: str,
        system_prompt: str,
        user_content: str
    ) -> tuple[Optional[str], Optional[dict], Optional[str]]:
        """
        Call an OpenAI-compatible LLM API.

        Args:
            api_endpoint: Base API endpoint URL
            model: Model name
            api_key: API key (can be empty)
            system_prompt: System prompt
            user_content: User message content (transcription text)

        Returns:
            Tuple of (summary_text, usage_stats, error)
        """
        url = f"{api_endpoint.rstrip('/')}/chat/completions"

        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }

        try:
            with httpx.Client(timeout=API_TIMEOUT) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                summary_text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                return summary_text, usage, None

        except httpx.TimeoutException:
            error = "API request timed out"
            logger.error(error)
            return None, None, error
        except httpx.HTTPStatusError as e:
            error = f"API returned error status {e.response.status_code}: {e.response.text}"
            logger.error(error)
            return None, None, error
        except httpx.RequestError as e:
            error = f"API request failed: {str(e)}"
            logger.error(error)
            return None, None, error
        except (KeyError, IndexError) as e:
            error = f"Unexpected API response format: {str(e)}"
            logger.error(error)
            return None, None, error

    def generate_summary(
        self,
        db: Session,
        transcription_id: str,
        api_endpoint: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> SummaryResult:
        """
        Generate a summary for a transcription.

        If config parameters are not provided, resolves them from tag configurations.

        Args:
            db: Database session
            transcription_id: ID of the transcription to summarize
            api_endpoint: Optional override for API endpoint
            model: Optional override for model
            api_key: Optional override for API key
            system_prompt: Optional override for system prompt

        Returns:
            SummaryResult with success status, summary object, and any error
        """
        # Get transcription from database
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription:
            return SummaryResult(False, None, "Transcription not found")

        if transcription.status != "completed":
            return SummaryResult(False, None, "Transcription is not complete")

        # Parse tags
        try:
            tags = json.loads(transcription.tags) if transcription.tags else []
        except json.JSONDecodeError:
            tags = []

        # Resolve configuration
        resolved = self.config_manager.resolve_config_for_transcription(tags)

        # Use provided values or fallback to resolved config
        final_endpoint = api_endpoint or resolved.api_endpoint
        final_model = model or resolved.model
        final_key = api_key if api_key is not None else resolved.api_key
        final_prompt = system_prompt or resolved.system_prompt
        config_source = resolved.config_source if not any([api_endpoint, model, api_key, system_prompt]) else "custom"

        # Load transcription text
        transcription_data = self.storage_manager.load_transcription(transcription_id)
        if not transcription_data:
            return SummaryResult(False, None, "Transcription file not found")

        # Extract full text from segments
        segments = transcription_data.get('transcription', {}).get('segments', [])
        full_text = ' '.join(segment['text'].strip() for segment in segments)

        if not full_text:
            return SummaryResult(False, None, "Transcription has no text content")

        # Call LLM API
        start_time = time.time()
        summary_text, usage, error = self._call_llm_api(
            final_endpoint,
            final_model,
            final_key,
            final_prompt,
            full_text
        )
        generation_time_ms = int((time.time() - start_time) * 1000)

        if error:
            return SummaryResult(False, None, error)

        # Create summary record
        summary = Summary(
            id=self._generate_summary_id(),
            transcription_id=transcription_id,
            api_endpoint=final_endpoint,
            model=final_model,
            api_key_used=bool(final_key),
            system_prompt=final_prompt,
            tags_at_time=json.dumps(tags),
            config_source=config_source,
            summary_text=summary_text,
            created_at=datetime.now(timezone.utc),
            generation_time_ms=generation_time_ms,
            prompt_tokens=usage.get("prompt_tokens") if usage else None,
            completion_tokens=usage.get("completion_tokens") if usage else None
        )

        try:
            db.add(summary)
            db.commit()
            db.refresh(summary)
            logger.info(f"Created summary {summary.id} for transcription {transcription_id}")
            return SummaryResult(True, summary, None)
        except Exception as e:
            db.rollback()
            error = f"Failed to save summary: {str(e)}"
            logger.error(error)
            return SummaryResult(False, None, error)

    def get_summary(self, db: Session, summary_id: str) -> Optional[Summary]:
        """Get a specific summary by ID."""
        return db.query(Summary).filter(Summary.id == summary_id).first()

    def get_summaries_for_transcription(
        self,
        db: Session,
        transcription_id: str
    ) -> list[Summary]:
        """Get all summaries for a transcription."""
        return db.query(Summary).filter(
            Summary.transcription_id == transcription_id
        ).order_by(Summary.created_at.desc()).all()

    def delete_summary(self, db: Session, summary_id: str) -> bool:
        """Delete a summary by ID."""
        summary = self.get_summary(db, summary_id)
        if not summary:
            return False

        try:
            db.delete(summary)
            db.commit()
            logger.info(f"Deleted summary {summary_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete summary {summary_id}: {e}")
            return False

    def export_summary(
        self,
        db: Session,
        summary_id: str,
        format: str
    ) -> Optional[tuple[str, str]]:
        """
        Export a summary in the specified format.

        Args:
            db: Database session
            summary_id: Summary ID
            format: Export format ('txt' or 'json')

        Returns:
            Tuple of (content, content_type) or None if not found
        """
        summary = self.get_summary(db, summary_id)
        if not summary:
            return None

        if format == "txt":
            return summary.summary_text, "text/plain"
        elif format == "json":
            content = json.dumps(summary.to_dict(), indent=2, ensure_ascii=False)
            return content, "application/json"
        else:
            return None
