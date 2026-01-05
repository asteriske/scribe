"""Pydantic models for API requests and responses."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field


class TranscribeRequest(BaseModel):
    """Request to transcribe a URL."""
    url: str = Field(..., description="URL to transcribe (YouTube, Apple Podcasts, or direct audio)")
    tags: List[str] = Field(default_factory=list, description="Optional tags for organization")


class TranscriptionResponse(BaseModel):
    """Response for transcription job."""
    id: str
    status: str
    progress: int = 0
    source: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    transcribed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    language: Optional[str] = None
    word_count: Optional[int] = None
    segments_count: Optional[int] = None
    error: Optional[str] = None
    model: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class UpdateTagsRequest(BaseModel):
    """Request to update transcription tags."""
    tags: List[str] = Field(..., description="Tags to set (replaces existing)")


class TranscriptionListResponse(BaseModel):
    """Response for list of transcriptions."""
    total: int
    skip: int
    limit: int
    items: List[TranscriptionResponse]


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    existing_id: Optional[str] = None
