"""API routes for frontend service."""

import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path

from frontend.api.models import (
    TranscribeRequest,
    TranscriptionResponse,
    TranscriptionListResponse,
    ErrorResponse,
    UpdateTagsRequest
)
from frontend.core.database import get_db
from frontend.core.models import Transcription
from frontend.services.orchestrator import Orchestrator
from frontend.utils.url_parser import parse_url
from frontend.utils.tag_validator import normalize_tags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])
web_router = APIRouter(tags=["web"])

template_dir = Path(__file__).parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# Add template filter
def format_time(seconds):
    """Format seconds to MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

templates.env.filters['format_time'] = format_time


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/tags")
async def get_all_tags(db: Session = Depends(get_db)):
    """
    Get all unique tags used across all transcriptions.

    Returns tags sorted alphabetically.
    """
    # Get all transcriptions with tags
    transcriptions = db.query(Transcription).all()

    # Collect all unique tags
    all_tags = set()
    for t in transcriptions:
        if t.tags:
            try:
                if isinstance(t.tags, str):
                    tags = json.loads(t.tags)
                else:
                    tags = t.tags
                all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                continue

    # Return sorted list
    return {"tags": sorted(all_tags)}


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=202,
    responses={
        409: {"model": ErrorResponse, "description": "URL already transcribed"},
        400: {"model": ErrorResponse, "description": "Invalid URL"}
    }
)
async def transcribe_url(
    request: TranscribeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submit a URL for transcription.

    The transcription job will be processed in the background.
    """
    try:
        # Parse and validate URL
        url_info = parse_url(request.url)

        # Check for duplicate
        existing = db.query(Transcription).filter_by(source_url=request.url).first()
        if existing:
            return JSONResponse(
                status_code=409,
                content=jsonable_encoder(ErrorResponse(
                    detail="This URL has already been transcribed",
                    existing_id=existing.id
                ))
            )

        # Normalize tags
        normalized_tags = normalize_tags(request.tags) if request.tags else []

        # Create pending record
        transcription = Transcription(
            id=url_info.id,
            source_type=url_info.source_type.value,
            source_url=request.url,
            status='pending',
            progress=0,
            tags=json.dumps(normalized_tags)
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)

        # Create orchestrator and start processing in background
        orchestrator = Orchestrator()
        background_tasks.add_task(orchestrator.process_url, request.url)

        return TranscriptionResponse(**transcription.to_dict())

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting transcription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/transcriptions", response_model=TranscriptionListResponse)
async def list_transcriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all transcriptions with pagination and optional filtering.
    """
    query = db.query(Transcription)

    # Filter by status
    if status:
        query = query.filter(Transcription.status == status)

    # Full-text search
    if search:
        # Get total count first
        count_query = text("""
            SELECT COUNT(*) as count
            FROM transcriptions t
            JOIN transcriptions_fts fts ON t.rowid = fts.rowid
            WHERE transcriptions_fts MATCH :search
        """)
        total = db.execute(count_query, {"search": search}).scalar()

        # Get paginated results
        fts_query = text("""
            SELECT t.*
            FROM transcriptions t
            JOIN transcriptions_fts fts ON t.rowid = fts.rowid
            WHERE transcriptions_fts MATCH :search
            ORDER BY rank
            LIMIT :limit OFFSET :skip
        """)
        results = db.execute(fts_query, {"search": search, "limit": limit, "skip": skip}).fetchall()

        # Convert to Transcription objects
        items = [db.query(Transcription).filter_by(id=row.id).first() for row in results]

        # Apply status filter if provided
        if status:
            items = [item for item in items if item and item.status == status]
            # Note: This filters after pagination, which is not ideal but matches current behavior
            # Better would be to include status in the SQL WHERE clause
    else:
        # Regular query
        total = query.count()
        items = query.order_by(Transcription.created_at.desc()).offset(skip).limit(limit).all()

    return TranscriptionListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[TranscriptionResponse(**t.to_dict()) for t in items]
    )


@router.get("/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(transcription_id: str, db: Session = Depends(get_db)):
    """Get a single transcription by ID."""
    transcription = db.query(Transcription).filter_by(id=transcription_id).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    return TranscriptionResponse(**transcription.to_dict())


@router.patch(
    "/transcriptions/{transcription_id}",
    response_model=TranscriptionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Transcription not found"},
        400: {"model": ErrorResponse, "description": "Invalid tags"}
    }
)
async def update_transcription_tags(
    transcription_id: str,
    request: UpdateTagsRequest,
    db: Session = Depends(get_db)
):
    """
    Update tags for a transcription.

    Replaces existing tags completely.
    """
    # Find transcription
    transcription = db.query(Transcription).filter_by(id=transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Normalize and validate tags
    normalized_tags = normalize_tags(request.tags)

    # Check if any tags were invalid (filtered out)
    if request.tags and not normalized_tags:
        raise HTTPException(
            status_code=400,
            detail="All provided tags are invalid. Tags must be lowercase alphanumeric with hyphens/underscores only."
        )

    # Update tags
    transcription.tags = json.dumps(normalized_tags)
    db.commit()
    db.refresh(transcription)

    return TranscriptionResponse(**transcription.to_dict())


@router.delete("/transcriptions/{transcription_id}")
async def delete_transcription(transcription_id: str, db: Session = Depends(get_db)):
    """Delete a transcription and its files."""
    transcription = db.query(Transcription).filter_by(id=transcription_id).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Delete files first (storage manager will handle this)
    from frontend.services.storage import StorageManager
    from frontend.services.downloader import Downloader

    storage = StorageManager()
    downloader = Downloader()

    storage.delete_transcription(transcription_id)
    downloader.delete_audio(transcription_id)

    # Then delete from database
    db.delete(transcription)
    db.commit()

    return {"message": "Transcription deleted successfully"}


@router.get("/transcriptions/{transcription_id}/export/{format}")
async def export_transcription(
    transcription_id: str,
    format: str,
    db: Session = Depends(get_db)
):
    """Export transcription in specified format (txt, srt, json)."""
    from fastapi.responses import PlainTextResponse, JSONResponse
    from frontend.services.storage import StorageManager

    transcription = db.query(Transcription).filter_by(id=transcription_id).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription.status != 'completed':
        raise HTTPException(status_code=400, detail="Transcription not completed yet")

    storage = StorageManager()

    if format == 'txt':
        content = storage.export_to_txt(transcription_id)
        if not content:
            raise HTTPException(status_code=404, detail="Transcription file not found")
        return PlainTextResponse(content, headers={
            "Content-Disposition": f"attachment; filename={transcription_id}.txt"
        })

    elif format == 'srt':
        content = storage.export_to_srt(transcription_id)
        if not content:
            raise HTTPException(status_code=404, detail="Transcription file not found")
        return PlainTextResponse(content, headers={
            "Content-Disposition": f"attachment; filename={transcription_id}.srt"
        })

    elif format == 'json':
        content = storage.load_transcription(transcription_id)
        if not content:
            raise HTTPException(status_code=404, detail="Transcription file not found")
        return JSONResponse(content, headers={
            "Content-Disposition": f"attachment; filename={transcription_id}.json"
        })

    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use txt, srt, or json")


@web_router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@web_router.get("/transcriptions/{transcription_id}", response_class=HTMLResponse)
async def view_transcription(
    request: Request,
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """View transcription detail page."""
    transcription = db.query(Transcription).filter_by(id=transcription_id).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Load full transcription data
    from frontend.services.storage import StorageManager
    storage = StorageManager()

    try:
        data = storage.load_transcription(transcription_id) if transcription.status == 'completed' else None
    except Exception as e:
        logger.error(f"Failed to load transcription data for {transcription_id}: {e}")
        data = None

    segments = data.get('transcription', {}).get('segments', []) if data else []

    return templates.TemplateResponse("transcription.html", {
        "request": request,
        "transcription": transcription,
        "segments": segments
    })
