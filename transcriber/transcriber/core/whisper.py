"""Whisper model wrapper for MLX."""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import mlx_whisper

from .config import settings

logger = logging.getLogger(__name__)


class WhisperModel:
    """Wrapper for MLX Whisper model."""

    def __init__(self):
        """Initialize the Whisper model wrapper."""
        self.model_name = settings.whisper_model
        self.model = None
        self._is_loaded = False

    def load(self) -> None:
        """Load the Whisper model into memory."""
        if self._is_loaded:
            logger.info(f"Model {self.model_name} already loaded")
            return

        logger.info(f"Loading Whisper model: {self.model_name}")
        try:
            # MLX Whisper loads model automatically on first use
            # We just need to verify it's available
            self._is_loaded = True
            logger.info(f"Model {self.model_name} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> Dict:
        """
        Transcribe audio file using Whisper.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es'). None for auto-detect.
            task: Either 'transcribe' or 'translate'

        Returns:
            Dictionary containing transcription results with segments and metadata
        """
        if not self._is_loaded:
            self.load()

        logger.info(f"Transcribing {audio_path}")
        logger.debug(f"Parameters: language={language}, task={task}")

        try:
            # Transcribe using MLX Whisper
            # Convert model name to HuggingFace repo path
            model_repo = f"mlx-community/whisper-{self.model_name}"
            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo=model_repo,
                language=language,
                task=task,
                fp16=(settings.compute_type == "float16"),
                condition_on_previous_text=settings.condition_on_previous_text,
                compression_ratio_threshold=settings.compression_ratio_threshold,
                no_speech_threshold=settings.no_speech_threshold,
                logprob_threshold=settings.logprob_threshold,
                temperature=self._parse_temperature(settings.temperature),
                hallucination_silence_threshold=settings.hallucination_silence_threshold,
                word_timestamps=settings.hallucination_silence_threshold is not None,
                initial_prompt=settings.initial_prompt,
            )

            # Extract metadata
            duration = self._get_audio_duration(result)
            num_segments = len(result.get("segments", []))

            logger.info(
                f"Transcription complete: {num_segments} segments, {duration:.1f}s duration"
            )

            return {
                "language": result.get("language", language or "unknown"),
                "duration": duration,
                "segments": result.get("segments", []),
                "text": result.get("text", ""),
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    @staticmethod
    def _parse_temperature(temp_str: str) -> Union[float, Tuple[float, ...]]:
        """Parse comma-separated temperature string into a float or tuple."""
        temps = tuple(float(t) for t in temp_str.split(","))
        return temps[0] if len(temps) == 1 else temps

    def _get_audio_duration(self, result: Dict) -> float:
        """Extract audio duration from transcription result."""
        segments = result.get("segments", [])
        if not segments:
            return 0.0
        # Duration is the end time of the last segment
        return segments[-1].get("end", 0.0)

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded

    def unload(self) -> None:
        """Unload the model from memory."""
        if self._is_loaded:
            logger.info(f"Unloading model {self.model_name}")
            self.model = None
            self._is_loaded = False


# Global model instance
whisper_model = WhisperModel()
