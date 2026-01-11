"""Main FastAPI application."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from frontend.core.config import settings
from frontend.core.database import init_db, get_engine
from frontend.api.routes import router as api_router, web_router
from frontend.api.websocket import websocket_endpoint
from frontend.utils.cleanup import CleanupService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request timing for API endpoints."""

    async def dispatch(self, request: Request, call_next):
        # Only log API requests
        if request.url.path.startswith("/api/"):
            start = time.monotonic()
            logger.debug(f"Request started: {request.method} {request.url.path}")

            response = await call_next(request)

            elapsed = time.monotonic() - start
            # Log slow requests (>1s) at INFO level, others at DEBUG
            if elapsed > 1.0:
                logger.info(f"Request completed: {request.method} {request.url.path} -> {response.status_code} ({elapsed:.2f}s) [SLOW]")
            else:
                logger.debug(f"Request completed: {request.method} {request.url.path} -> {response.status_code} ({elapsed:.2f}s)")

            return response
        else:
            return await call_next(request)


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

    # Run database migrations
    from frontend.core.migrations import run_migrations
    run_migrations(engine)

    # Start cleanup task
    cleanup_service = CleanupService()
    cleanup_task = asyncio.create_task(run_periodic_cleanup(cleanup_service))

    yield

    # Shutdown
    cleanup_task.cancel()
    logger.info("Shutting down frontend service")


async def run_periodic_cleanup(cleanup_service: CleanupService):
    """Run cleanup tasks periodically."""
    while True:
        try:
            # Run every 6 hours
            await asyncio.sleep(6 * 60 * 60)
            await cleanup_service.run_cleanup()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


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

# Request timing middleware for debugging
app.add_middleware(RequestTimingMiddleware)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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
