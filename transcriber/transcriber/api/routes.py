"""API routes for transcriber service."""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ..core.config import settings
from ..core.queue import JobStatus, job_queue
from ..core.whisper import whisper_model
from .models import (
    ErrorResponse,
    HealthResponse,
    JobStatusResponse,
    JobSubmitResponse,
    ModelsResponse,
    ModelInfo,
    TranscriptionResult,
    TranscriptionSegment,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/transcribe",
    response_model=JobSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        413: {"model": ErrorResponse, "description": "File too large"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Queue full"},
    },
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    model: Optional[str] = Form(None, description="Whisper model to use"),
    language: Optional[str] = Form(None, description="Language code (e.g., 'en')"),
    task: str = Form("transcribe", description="Task: 'transcribe' or 'translate'"),
):
    """
    Submit audio for transcription.

    Accepts audio file and queues it for transcription.
    Returns job ID for status tracking.
    """
    # Validate task
    if task not in ["transcribe", "translate"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid task. Must be 'transcribe' or 'translate'",
        )

    # Validate audio format
    allowed_formats = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio format. Supported: {', '.join(allowed_formats)}",
        )

    # Check file size (500MB max)
    max_size = 500 * 1024 * 1024  # 500MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start

    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB",
        )

    # Save uploaded file to temp location
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "scribe_transcriber"
    temp_dir.mkdir(exist_ok=True)

    temp_file = temp_dir / f"{file.filename}"
    try:
        with temp_file.open("wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Submit job to queue
    try:
        job_id = await job_queue.submit_job(
            audio_path=str(temp_file),
            model=model,
            language=language,
            task=task,
        )

        queue_position = job_queue.get_queue_position(job_id) or 0

        return JobSubmitResponse(
            job_id=job_id,
            status="queued",
            estimated_duration_seconds=None,  # Could estimate based on file size
            queue_position=queue_position,
        )

    except Exception as e:
        logger.error(f"Failed to submit job: {e}")
        # Clean up temp file
        temp_file.unlink(missing_ok=True)

        if "Queue is full" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Job queue is full. Try again later.",
            )

        raise HTTPException(status_code=500, detail="Failed to submit job")


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def get_job_status(job_id: str):
    """
    Get status and result of a transcription job.

    Returns current status, progress, and result if completed.
    """
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    # Build response
    response = JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )

    # Add queue position if queued
    if job.status == JobStatus.QUEUED:
        response.queue_position = job_queue.get_queue_position(job_id)

    # Add result if completed
    if job.status == JobStatus.COMPLETED and job.result:
        response.result = TranscriptionResult(
            language=job.result["language"],
            duration=job.result["duration"],
            segments=[
                TranscriptionSegment(**seg) for seg in job.result["segments"]
            ],
            text=job.result["text"],
        )

    # Add error if failed
    if job.status == JobStatus.FAILED:
        response.error = job.error

    return response


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unhealthy"},
    },
)
async def health_check():
    """
    Health check endpoint.

    Returns service status, model information, and queue statistics.
    """
    # Check model status
    model_status = {
        "name": settings.whisper_model,
        "loaded": whisper_model.is_loaded,
        "device": "mlx",
    }

    # Get queue stats
    queue_stats = job_queue.stats

    # Check if service is healthy
    is_healthy = True  # Could add more checks here

    status_code = 200 if is_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content=HealthResponse(
            status="healthy" if is_healthy else "unhealthy",
            model=model_status,
            queue=queue_stats,
        ).model_dump(),
    )


@router.get(
    "/models",
    response_model=ModelsResponse,
)
async def list_models():
    """
    List available Whisper models.

    Returns current model and list of all available models.
    """
    # Model sizes in MB (approximate)
    model_sizes = {
        "tiny": 75,
        "base": 142,
        "small": 466,
        "medium": 1462,
        "large-v3": 2938,
    }

    # Check which models are downloaded
    # MLX Whisper caches models in ~/.cache/huggingface
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

    available_models = []
    for name, size in model_sizes.items():
        # Simple check - could be more sophisticated
        downloaded = (cache_dir / f"models--mlx-community--whisper-{name}").exists()
        available_models.append(
            ModelInfo(
                name=name,
                size_mb=size,
                downloaded=downloaded,
            )
        )

    return ModelsResponse(
        current=settings.whisper_model,
        available=available_models,
    )
