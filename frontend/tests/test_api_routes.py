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


def test_update_transcription_tags(client, db_session):
    """Test PATCH /api/transcriptions/{id} updates tags."""
    from frontend.core.models import Transcription
    import json

    # Create a transcription
    t = Transcription(
        id="test123",
        source_type="youtube",
        source_url="https://youtube.com/test",
        status="completed",
        tags=json.dumps(["old", "tags"])
    )
    db_session.add(t)
    db_session.commit()

    # Update tags
    response = client.patch(
        "/api/transcriptions/test123",
        json={"tags": ["new", "tags", "updated"]}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tags"] == ["new", "tags", "updated"]

    # Verify in database
    db_session.refresh(t)
    assert json.loads(t.tags) == ["new", "tags", "updated"]


def test_update_transcription_tags_normalizes(client, db_session):
    """Test PATCH endpoint normalizes tags."""
    from frontend.core.models import Transcription
    import json

    t = Transcription(
        id="test124",
        source_type="youtube",
        source_url="https://youtube.com/test2",
        status="completed",
        tags=json.dumps([])
    )
    db_session.add(t)
    db_session.commit()

    # Send tags that need normalization
    response = client.patch(
        "/api/transcriptions/test124",
        json={"tags": ["Kindle", " FORMAT ", "kindle", "Review"]}
    )

    assert response.status_code == 200
    data = response.json()
    # Should be normalized: lowercase, no duplicates
    assert data["tags"] == ["kindle", "format", "review"]


def test_update_transcription_tags_not_found(client, db_session):
    """Test PATCH returns 404 for non-existent transcription."""
    response = client.patch(
        "/api/transcriptions/nonexistent",
        json={"tags": ["test"]}
    )
    assert response.status_code == 404


def test_update_transcription_tags_invalid(client, db_session):
    """Test PATCH returns 400 for invalid tags."""
    from frontend.core.models import Transcription
    import json

    t = Transcription(
        id="test125",
        source_type="youtube",
        source_url="https://youtube.com/test3",
        status="completed",
        tags=json.dumps([])
    )
    db_session.add(t)
    db_session.commit()

    # Send invalid tags (with spaces/special chars)
    response = client.patch(
        "/api/transcriptions/test125",
        json={"tags": ["invalid tag!", "another@bad"]}
    )

    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_transcribe_url_with_tags(client, db_session, monkeypatch):
    """Test POST /api/transcribe accepts and stores tags."""
    import json
    from unittest.mock import MagicMock
    from frontend.core.models import Transcription
    from frontend.utils.url_parser import URLInfo, SourceType
    import frontend.api.routes as routes

    # Mock parse_url
    mock_url_info = URLInfo(
        id="youtube_test123",
        source_type=SourceType.YOUTUBE,
        original_url="https://youtube.com/watch?v=new"
    )
    monkeypatch.setattr(routes, 'parse_url', lambda x: mock_url_info)

    # Mock Orchestrator
    mock_orchestrator = MagicMock()
    monkeypatch.setattr(routes, 'Orchestrator', lambda: mock_orchestrator)

    response = client.post(
        "/api/transcribe",
        json={
            "url": "https://youtube.com/watch?v=new",
            "tags": ["kindle", "work"]
        }
    )

    assert response.status_code == 202
    data = response.json()
    assert data["tags"] == ["kindle", "work"]

    # Verify in database
    t = db_session.query(Transcription).filter_by(id="youtube_test123").first()
    assert t is not None
    assert json.loads(t.tags) == ["kindle", "work"]


def test_transcribe_url_normalizes_tags(client, db_session, monkeypatch):
    """Test POST /api/transcribe normalizes tags."""
    import json
    from unittest.mock import MagicMock
    from frontend.core.models import Transcription
    from frontend.utils.url_parser import URLInfo, SourceType
    import frontend.api.routes as routes

    # Mock parse_url
    mock_url_info = URLInfo(
        id="youtube_normalize",
        source_type=SourceType.YOUTUBE,
        original_url="https://youtube.com/watch?v=normalize"
    )
    monkeypatch.setattr(routes, 'parse_url', lambda x: mock_url_info)

    # Mock Orchestrator
    mock_orchestrator = MagicMock()
    monkeypatch.setattr(routes, 'Orchestrator', lambda: mock_orchestrator)

    response = client.post(
        "/api/transcribe",
        json={
            "url": "https://youtube.com/watch?v=normalize",
            "tags": ["Kindle", " FORMAT ", "Kindle"]
        }
    )

    assert response.status_code == 202
    data = response.json()
    assert data["tags"] == ["kindle", "format"]
