"""WebSocket handler for real-time progress updates."""

import logging
import json
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect

from frontend.core.database import get_session_maker
from frontend.core.models import Transcription

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = set()

        # Iterate over a copy to avoid modification during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time progress updates.

    Messages sent to clients:
    - {"type": "connected"}
    - {"type": "status", "id": "...", "status": "...", "progress": ...}
    - {"type": "completed", "id": "...", "transcription": {...}}
    - {"type": "error", "id": "...", "error": "..."}
    """
    await manager.connect(websocket)

    try:
        # Send connection confirmation
        await manager.send_personal(websocket, {"type": "connected"})

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()

            # Handle client messages
            try:
                message = json.loads(data)

                if message.get("type") == "ping":
                    await manager.send_personal(websocket, {"type": "pong"})

                elif message.get("type") == "subscribe":
                    transcription_id = message.get("id")
                    if not transcription_id:
                        await manager.send_personal(websocket, {
                            "type": "error",
                            "error": "Missing transcription ID in subscribe message"
                        })
                    else:
                        await send_status_update(websocket, transcription_id)

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def send_status_update(websocket: WebSocket, transcription_id: str):
    """Send status update for specific transcription."""
    SessionLocal = get_session_maker()

    with SessionLocal() as session:
        transcription = session.query(Transcription).filter_by(id=transcription_id).first()

        if transcription:
            message = {
                "type": "status",
                "id": transcription.id,
                "status": transcription.status,
                "progress": transcription.progress,
                "error": transcription.error_message
            }
            await manager.send_personal(websocket, message)
        else:
            await manager.send_personal(websocket, {
                "type": "error",
                "error": f"Transcription {transcription_id} not found"
            })


async def broadcast_progress(transcription_id: str, status: str, progress: int):
    """Broadcast progress update to all connected clients."""
    message = {
        "type": "status",
        "id": transcription_id,
        "status": status,
        "progress": progress
    }
    await manager.broadcast(message)


async def broadcast_completion(transcription_id: str):
    """Broadcast completion to all connected clients."""
    SessionLocal = get_session_maker()

    with SessionLocal() as session:
        transcription = session.query(Transcription).filter_by(id=transcription_id).first()

        if transcription:
            message = {
                "type": "completed",
                "id": transcription.id,
                "transcription": transcription.to_dict()
            }
            await manager.broadcast(message)


async def broadcast_error(transcription_id: str, error: str):
    """Broadcast error to all connected clients."""
    message = {
        "type": "error",
        "id": transcription_id,
        "error": error
    }
    await manager.broadcast(message)
