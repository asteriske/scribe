"""Test WebSocket handler."""
import pytest
from fastapi.testclient import TestClient
from frontend.main import app


def test_websocket_connection():
    """Test WebSocket connection"""
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Should connect successfully
        data = websocket.receive_json()
        assert data["type"] == "connected"
