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
    UpdateTagsRequest,
    SummaryRequest,
    SummaryResponse,
    SummaryListResponse,
    TagConfigRequest,
    TagConfigResponse,
    DefaultConfigResponse,
    AllTagConfigsResponse,
    SecretRequest,
    SecretListResponse
)
from frontend.core.database import get_db
from frontend.core.models import Transcription, Summary
from frontend.services.orchestrator import Orchestrator
from frontend.services.summarizer import SummarizerService
from frontend.services.config_manager import ConfigManager
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


# =============================================================================
# Summary API Endpoints
# =============================================================================

@router.get("/summaries", response_model=SummaryListResponse)
async def list_summaries(
    transcription_id: str = Query(..., description="Transcription ID to list summaries for"),
    db: Session = Depends(get_db)
):
    """List all summaries for a transcription."""
    summarizer = SummarizerService()
    summaries = summarizer.get_summaries_for_transcription(db, transcription_id)
    return SummaryListResponse(
        items=[SummaryResponse(**s.to_dict()) for s in summaries]
    )


@router.get("/summaries/{summary_id}", response_model=SummaryResponse)
async def get_summary(summary_id: str, db: Session = Depends(get_db)):
    """Get a specific summary by ID."""
    summarizer = SummarizerService()
    summary = summarizer.get_summary(db, summary_id)

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    return SummaryResponse(**summary.to_dict())


@router.post(
    "/summaries",
    response_model=SummaryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Transcription not found"},
        400: {"model": ErrorResponse, "description": "Transcription not completed or API error"}
    }
)
async def create_summary(
    request: SummaryRequest,
    db: Session = Depends(get_db)
):
    """Generate and save a new summary for a transcription."""
    summarizer = SummarizerService()
    result = summarizer.generate_summary(
        db=db,
        transcription_id=request.transcription_id,
        api_endpoint=request.api_endpoint,
        model=request.model,
        api_key=request.api_key,
        system_prompt=request.system_prompt
    )

    if not result.success:
        if "not found" in result.error.lower():
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    return SummaryResponse(**result.summary.to_dict())


@router.get("/summaries/{summary_id}/export/{format}")
async def export_summary(
    summary_id: str,
    format: str,
    db: Session = Depends(get_db)
):
    """Export summary in specified format (txt or json)."""
    from fastapi.responses import PlainTextResponse, JSONResponse

    summarizer = SummarizerService()
    result = summarizer.export_summary(db, summary_id, format)

    if not result:
        raise HTTPException(status_code=404, detail="Summary not found or invalid format")

    content, content_type = result

    if format == "txt":
        return PlainTextResponse(content, headers={
            "Content-Disposition": f"attachment; filename={summary_id}.txt"
        })
    elif format == "json":
        return JSONResponse(json.loads(content), headers={
            "Content-Disposition": f"attachment; filename={summary_id}.json"
        })
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use txt or json")


@router.delete("/summaries/{summary_id}")
async def delete_summary(summary_id: str, db: Session = Depends(get_db)):
    """Delete a summary."""
    summarizer = SummarizerService()
    success = summarizer.delete_summary(db, summary_id)

    if not success:
        raise HTTPException(status_code=404, detail="Summary not found")

    return {"message": "Summary deleted successfully"}


# =============================================================================
# Tag Configuration API Endpoints
# =============================================================================

@router.get("/config/tags", response_model=AllTagConfigsResponse)
async def get_all_tag_configs():
    """Get all tag configurations."""
    config_manager = ConfigManager()
    configs = config_manager.get_all_tag_configs()

    default_config = configs.get("default", {})
    tags_config = configs.get("tags", {})

    return AllTagConfigsResponse(
        default=DefaultConfigResponse(**default_config),
        tags={
            name: TagConfigResponse(tag_name=name, **config)
            for name, config in tags_config.items()
        }
    )


@router.get("/config/tags/default", response_model=DefaultConfigResponse)
async def get_default_config():
    """Get default configuration."""
    config_manager = ConfigManager()
    config = config_manager.get_default_config()
    return DefaultConfigResponse(**config)


@router.put("/config/tags/default", response_model=DefaultConfigResponse)
async def update_default_config(request: TagConfigRequest):
    """Update default configuration."""
    config_manager = ConfigManager()
    success = config_manager.update_default_config(
        api_endpoint=request.api_endpoint,
        model=request.model,
        system_prompt=request.system_prompt,
        api_key_ref=request.api_key_ref
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update default config")

    return DefaultConfigResponse(
        api_endpoint=request.api_endpoint,
        model=request.model,
        api_key_ref=request.api_key_ref,
        system_prompt=request.system_prompt
    )


@router.post(
    "/config/tags",
    response_model=TagConfigResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Tag name required"}
    }
)
async def create_tag_config(request: TagConfigRequest):
    """Create a new tag configuration."""
    if not request.tag_name:
        raise HTTPException(status_code=400, detail="tag_name is required for creating a tag config")

    config_manager = ConfigManager()
    success = config_manager.create_tag_config(
        tag_name=request.tag_name,
        api_endpoint=request.api_endpoint,
        model=request.model,
        system_prompt=request.system_prompt,
        api_key_ref=request.api_key_ref
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to create tag config")

    return TagConfigResponse(
        tag_name=request.tag_name,
        api_endpoint=request.api_endpoint,
        model=request.model,
        api_key_ref=request.api_key_ref,
        system_prompt=request.system_prompt
    )


@router.put(
    "/config/tags/{tag_name}",
    response_model=TagConfigResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Tag config not found"}
    }
)
async def update_tag_config(tag_name: str, request: TagConfigRequest):
    """Update an existing tag configuration."""
    config_manager = ConfigManager()

    # Check if exists
    if not config_manager.get_tag_config(tag_name):
        raise HTTPException(status_code=404, detail=f"Tag config '{tag_name}' not found")

    success = config_manager.update_tag_config(
        tag_name=tag_name,
        api_endpoint=request.api_endpoint,
        model=request.model,
        system_prompt=request.system_prompt,
        api_key_ref=request.api_key_ref
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update tag config")

    return TagConfigResponse(
        tag_name=tag_name,
        api_endpoint=request.api_endpoint,
        model=request.model,
        api_key_ref=request.api_key_ref,
        system_prompt=request.system_prompt
    )


@router.delete("/config/tags/{tag_name}")
async def delete_tag_config(tag_name: str):
    """Delete a tag configuration."""
    config_manager = ConfigManager()
    success = config_manager.delete_tag_config(tag_name)

    if not success:
        raise HTTPException(status_code=404, detail=f"Tag config '{tag_name}' not found")

    return {"message": f"Tag config '{tag_name}' deleted successfully"}


# =============================================================================
# Secrets Management API Endpoints
# =============================================================================

@router.get("/config/secrets", response_model=SecretListResponse)
async def list_secrets():
    """List secret key names (not values)."""
    config_manager = ConfigManager()
    return SecretListResponse(keys=config_manager.list_secret_names())


@router.post("/config/secrets")
async def add_secret(request: SecretRequest):
    """Add or update a secret."""
    config_manager = ConfigManager()
    success = config_manager.add_secret(request.key_name, request.key_value)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save secret")

    return {"message": f"Secret '{request.key_name}' saved successfully"}


@router.delete("/config/secrets/{key_name}")
async def delete_secret(key_name: str):
    """Delete a secret."""
    config_manager = ConfigManager()
    success = config_manager.delete_secret(key_name)

    if not success:
        raise HTTPException(status_code=404, detail=f"Secret '{key_name}' not found")

    return {"message": f"Secret '{key_name}' deleted successfully"}


# =============================================================================
# Web Routes
# =============================================================================

@web_router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@web_router.get("/summarize", response_class=HTMLResponse)
async def summarize_page(
    request: Request,
    transcription_id: Optional[str] = Query(None)
):
    """Summarization interface."""
    return templates.TemplateResponse("summarize.html", {
        "request": request,
        "preselected_transcription_id": transcription_id
    })


@web_router.get("/settings/tags", response_class=HTMLResponse)
async def settings_tags_page(request: Request):
    """Tag configuration settings page."""
    return templates.TemplateResponse("settings_tags.html", {"request": request})


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
