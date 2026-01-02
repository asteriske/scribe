"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TranscriptionSegment(BaseModel):
    """A single transcription segment."""

    id: int
    start: float
    end: float
    text: str


class TranscriptionResult(BaseModel):
    """Complete transcription result."""

    language: str
    duration: float
    segments: List[TranscriptionSegment]
    text: str


class JobSubmitResponse(BaseModel):
    """Response when submitting a new job."""

    job_id: str
    status: str
    estimated_duration_seconds: Optional[int] = None
    queue_position: int


class JobStatusResponse(BaseModel):
    """Response for job status query."""

    job_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    queue_position: Optional[int] = None
    result: Optional[TranscriptionResult] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model: Dict
    queue: Dict
    memory: Optional[Dict] = None


class ModelInfo(BaseModel):
    """Information about available model."""

    name: str
    size_mb: int
    downloaded: bool


class ModelsResponse(BaseModel):
    """Response listing available models."""

    current: str
    available: List[ModelInfo]


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
