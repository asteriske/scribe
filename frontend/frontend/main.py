"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from frontend.core.config import settings
from frontend.core.database import init_db, get_engine
from frontend.api.routes import router as api_router, web_router
from frontend.api.websocket import websocket_endpoint

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting frontend service")

    # Create data directories first (database file needs its parent directory)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.transcriptions_dir.mkdir(parents=True, exist_ok=True)
    settings.audio_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database
    engine = get_engine()
    init_db(engine)
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down frontend service")


app = FastAPI(
    title="Scribe Frontend API",
    description="Web interface and orchestration for Scribe transcription service",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(web_router)
app.include_router(api_router)


@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
    """WebSocket endpoint."""
    await websocket_endpoint(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "frontend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
