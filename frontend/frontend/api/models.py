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


# Summary Models

class SummaryRequest(BaseModel):
    """Request to generate a summary."""
    transcription_id: str = Field(..., description="ID of the transcription to summarize")
    api_endpoint: Optional[str] = Field(None, description="Override API endpoint")
    model: Optional[str] = Field(None, description="Override model name")
    api_key: Optional[str] = Field(None, description="Override API key")
    system_prompt: Optional[str] = Field(None, description="Override system prompt")


class SummaryResponse(BaseModel):
    """Response for a summary."""
    id: str
    transcription_id: str
    api_endpoint: str
    model: str
    api_key_used: bool
    system_prompt: str
    tags_at_time: List[str] = Field(default_factory=list)
    config_source: Optional[str] = None
    summary_text: str
    created_at: Optional[datetime] = None
    generation_time_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class SummaryListResponse(BaseModel):
    """Response for list of summaries."""
    items: List[SummaryResponse]


# Tag Configuration Models

class TagConfigRequest(BaseModel):
    """Request to create or update a tag configuration."""
    tag_name: Optional[str] = Field(None, description="Tag name (required for create)")
    api_endpoint: str = Field(..., description="API endpoint URL")
    model: str = Field(..., description="Model name")
    api_key_ref: Optional[str] = Field(None, description="Reference to stored API key")
    system_prompt: str = Field(..., description="System prompt for summarization")


class TagConfigResponse(BaseModel):
    """Response for a tag configuration."""
    tag_name: str
    api_endpoint: str
    model: str
    api_key_ref: Optional[str] = None
    system_prompt: str


class DefaultConfigResponse(BaseModel):
    """Response for default configuration."""
    api_endpoint: str
    model: str
    api_key_ref: Optional[str] = None
    system_prompt: str


class TagConfigDetailResponse(BaseModel):
    """Response for single tag config lookup."""
    name: str
    api_endpoint: str
    model: str
    api_key_ref: Optional[str] = None
    system_prompt: str
    destination_email: Optional[str] = None


class AllTagConfigsResponse(BaseModel):
    """Response for all tag configurations."""
    default: DefaultConfigResponse
    tags: Dict[str, TagConfigResponse]


# Secrets Models

class SecretRequest(BaseModel):
    """Request to add or update a secret."""
    key_name: str = Field(..., description="Name of the API key")
    key_value: str = Field(..., description="API key value")


class SecretListResponse(BaseModel):
    """Response for list of secret names."""
    keys: List[str]
