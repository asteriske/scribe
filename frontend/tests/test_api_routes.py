"""Test API routes."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from frontend.core.database import get_db, init_db
from frontend.api.routes import router as api_router


@pytest.fixture
def test_db():
    """Create test database"""
    # Use StaticPool to ensure all connections share the same in-memory database
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    init_db(engine)
    return engine


@pytest.fixture
def test_app(test_db):
    """Create test FastAPI app without lifespan"""
    app = FastAPI()
    app.include_router(api_router)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_transcriptions_empty(client):
    """Test listing transcriptions when empty"""
    response = client.get("/api/transcriptions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.fixture
def db_session(test_db):
    """Create a database session for tests."""
    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_get_all_tags_empty(client, db_session):
    """Test GET /api/tags returns empty list when no tags exist."""
    response = client.get("/api/tags")
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    assert data["tags"] == []


def test_get_all_tags_with_transcriptions(client, db_session):
    """Test GET /api/tags returns all unique tags."""
    from frontend.core.models import Transcription
    import json

    # Create transcriptions with tags
    t1 = Transcription(
        id="test1",
        source_type="youtube",
        source_url="https://youtube.com/1",
        status="completed",
        tags=json.dumps(["kindle", "work"])
    )
    t2 = Transcription(
        id="test2",
        source_type="youtube",
        source_url="https://youtube.com/2",
        status="completed",
        tags=json.dumps(["format", "work", "review"])
    )
    t3 = Transcription(
        id="test3",
        source_type="youtube",
        source_url="https://youtube.com/3",
        status="completed",
        tags=json.dumps(["kindle"])
    )

    db_session.add_all([t1, t2, t3])
    db_session.commit()

    response = client.get("/api/tags")
    assert response.status_code == 200
    data = response.json()

    # Should return unique tags, sorted alphabetically
    assert set(data["tags"]) == {"kindle", "work", "format", "review"}
    assert data["tags"] == sorted(data["tags"])
