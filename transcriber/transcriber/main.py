"""Main FastAPI application for transcriber service."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .api.routes import router
from .core.config import settings
from .core.queue import job_queue
from .core.whisper import whisper_model

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Add file handler if log file is specified
if settings.log_file:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().addHandler(file_handler)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for application startup and shutdown.

    Handles:
    - Loading Whisper model on startup
    - Starting job queue worker
    - Cleanup on shutdown
    """
    logger.info("Starting transcriber service...")

    # Load Whisper model
    try:
        whisper_model.load()
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        # Continue anyway - model will load on first use

    # Start job queue worker
    await job_queue.start()
    logger.info("Job queue worker started")

    logger.info("Transcriber service ready")

    yield

    # Shutdown
    logger.info("Shutting down transcriber service...")
    await job_queue.stop()
    whisper_model.unload()
    logger.info("Transcriber service stopped")


# Create FastAPI application
app = FastAPI(
    title="Scribe Transcriber Service",
    description="MLX-powered audio transcription service using Whisper",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware (for frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, tags=["transcription"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Scribe Transcriber",
        "version": "0.1.0",
        "model": settings.whisper_model,
        "status": "running",
        "docs": "/docs",
    }


def main():
    """Run the application with uvicorn."""
    logger.info(f"Starting server on {settings.host}:{settings.port}")

    uvicorn.run(
        "transcriber.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        reload=False,  # Set to True for development
    )


if __name__ == "__main__":
    main()
