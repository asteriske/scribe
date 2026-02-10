"""Tests for POST /api/episode-sources endpoint."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from frontend.core.database import get_db, init_db
from frontend.core.models import Transcription, EpisodeSource
from frontend.api.routes import router as api_router


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    return engine


@pytest.fixture
def test_app(test_db):
    """Create test FastAPI app."""
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
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def db_session(test_db):
    """Create a database session."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_transcription(db_session):
    """Create a sample transcription in the DB."""
    t = Transcription(
        id="test_trans_1",
        source_type="apple_podcasts",
        source_url="https://podcasts.apple.com/test/ep1",
        status="completed",
    )
    db_session.add(t)
    db_session.commit()
    return t


class TestCreateEpisodeSource:
    """Tests for POST /api/episode-sources."""

    def test_create_episode_source(self, client, sample_transcription):
        """Test creating an episode source."""
        response = client.post("/api/episode-sources", json={
            "transcription_id": "test_trans_1",
            "email_subject": "New episode: Great Podcast",
            "email_from": "newsletter@example.com",
            "source_text": "This week we discuss testing in Python.",
            "matched_url": "https://podcasts.apple.com/test/ep1",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["transcription_id"] == "test_trans_1"
        assert data["email_subject"] == "New episode: Great Podcast"
        assert data["source_text"] == "This week we discuss testing in Python."
        assert data["matched_url"] == "https://podcasts.apple.com/test/ep1"
        assert data["id"].startswith("es_")

    def test_create_episode_source_minimal(self, client, sample_transcription):
        """Test creating with only required fields."""
        response = client.post("/api/episode-sources", json={
            "transcription_id": "test_trans_1",
            "source_text": "Minimal content.",
            "matched_url": "https://podcasts.apple.com/test/ep1",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email_subject"] is None
        assert data["email_from"] is None

    def test_create_episode_source_transcription_not_found(self, client):
        """Test 404 when transcription doesn't exist."""
        response = client.post("/api/episode-sources", json={
            "transcription_id": "nonexistent",
            "source_text": "Some text.",
            "matched_url": "https://podcasts.apple.com/test/nope",
        })
        assert response.status_code == 404

    def test_create_episode_source_persists(self, client, db_session, sample_transcription):
        """Test that created record is in the database."""
        client.post("/api/episode-sources", json={
            "transcription_id": "test_trans_1",
            "source_text": "Persisted content.",
            "matched_url": "https://podcasts.apple.com/test/ep1",
        })
        result = db_session.query(EpisodeSource).first()
        assert result is not None
        assert result.source_text == "Persisted content."
