# Episode Sources Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a pipeline that monitors an IMAP folder for podcast-related emails, stores their text content in the frontend DB, extracts Apple Podcasts/YouTube URLs, and triggers the transcription/summarization pipeline.

**Architecture:** The frontend gets a new `EpisodeSource` model, migration, and POST endpoint. The emailer gets new config settings, a new processor module, and a second folder check in its poll loop. The emailer reuses existing `JobProcessor` for transcription and `FrontendClient` for API calls.

**Tech Stack:** SQLAlchemy (model/migration), FastAPI (endpoint), Pydantic (request/response models), httpx (API client), html2text (HTML-to-text conversion)

**Design doc:** `docs/plans/2026-02-09-episode-sources-design.md`

---

### Task 1: Frontend — EpisodeSource model and migration

**Files:**
- Modify: `frontend/frontend/core/models.py`
- Modify: `frontend/frontend/core/migrations.py`
- Test: `frontend/tests/test_episode_source_model.py`

**Step 1: Write the failing test**

Create `frontend/tests/test_episode_source_model.py`:

```python
"""Tests for EpisodeSource model and migration."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from frontend.core.database import init_db
from frontend.core.models import Base, Transcription, EpisodeSource
from frontend.core.migrations import create_episode_sources_table_if_missing


@pytest.fixture
def engine():
    """Create in-memory test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session."""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


class TestEpisodeSourceModel:
    """Tests for the EpisodeSource SQLAlchemy model."""

    def test_create_episode_source(self, session):
        """Test creating an episode source linked to a transcription."""
        # Create a transcription first
        transcription = Transcription(
            id="test_123",
            source_type="apple_podcasts",
            source_url="https://podcasts.apple.com/test",
            status="completed",
        )
        session.add(transcription)
        session.commit()

        # Create episode source
        es = EpisodeSource(
            id="es_abc123",
            transcription_id="test_123",
            email_subject="New episode: Test Podcast",
            email_from="newsletter@example.com",
            source_text="This week we discuss testing.",
            matched_url="https://podcasts.apple.com/test",
        )
        session.add(es)
        session.commit()

        # Verify it was saved
        result = session.query(EpisodeSource).filter_by(id="es_abc123").first()
        assert result is not None
        assert result.transcription_id == "test_123"
        assert result.email_subject == "New episode: Test Podcast"
        assert result.source_text == "This week we discuss testing."
        assert result.matched_url == "https://podcasts.apple.com/test"
        assert result.created_at is not None

    def test_to_dict(self, session):
        """Test to_dict serialization."""
        transcription = Transcription(
            id="test_456",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=test",
            status="completed",
        )
        session.add(transcription)
        session.commit()

        es = EpisodeSource(
            id="es_def456",
            transcription_id="test_456",
            email_subject="Check this out",
            email_from="user@example.com",
            source_text="Great episode about Python.",
            matched_url="https://youtube.com/watch?v=test",
        )
        session.add(es)
        session.commit()

        d = es.to_dict()
        assert d["id"] == "es_def456"
        assert d["transcription_id"] == "test_456"
        assert d["email_subject"] == "Check this out"
        assert d["email_from"] == "user@example.com"
        assert d["source_text"] == "Great episode about Python."
        assert d["matched_url"] == "https://youtube.com/watch?v=test"
        assert "created_at" in d

    def test_cascade_delete(self, session):
        """Test that deleting a transcription deletes linked episode sources."""
        transcription = Transcription(
            id="test_789",
            source_type="apple_podcasts",
            source_url="https://podcasts.apple.com/cascade",
            status="completed",
        )
        session.add(transcription)
        session.commit()

        es = EpisodeSource(
            id="es_ghi789",
            transcription_id="test_789",
            source_text="Will be deleted.",
            matched_url="https://podcasts.apple.com/cascade",
        )
        session.add(es)
        session.commit()

        session.delete(transcription)
        session.commit()

        result = session.query(EpisodeSource).filter_by(id="es_ghi789").first()
        assert result is None

    def test_relationship_from_transcription(self, session):
        """Test accessing episode_sources from a transcription."""
        transcription = Transcription(
            id="test_rel",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=rel",
            status="completed",
        )
        session.add(transcription)
        session.commit()

        es = EpisodeSource(
            id="es_rel",
            transcription_id="test_rel",
            source_text="Relationship test.",
            matched_url="https://youtube.com/watch?v=rel",
        )
        session.add(es)
        session.commit()

        session.refresh(transcription)
        assert len(transcription.episode_sources) == 1
        assert transcription.episode_sources[0].id == "es_rel"


class TestEpisodeSourceMigration:
    """Tests for the episode_sources migration."""

    def test_migration_creates_table(self):
        """Test that migration creates episode_sources table."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Only create transcriptions table (simulate old DB)
        Base.metadata.tables["transcriptions"].create(engine)

        inspector = inspect(engine)
        assert "episode_sources" not in inspector.get_table_names()

        create_episode_sources_table_if_missing(engine)

        inspector = inspect(engine)
        assert "episode_sources" in inspector.get_table_names()

    def test_migration_is_idempotent(self):
        """Test that running migration twice doesn't error."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.tables["transcriptions"].create(engine)

        create_episode_sources_table_if_missing(engine)
        create_episode_sources_table_if_missing(engine)  # Should not raise
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && source venv/bin/activate && python -m pytest tests/test_episode_source_model.py -v`
Expected: FAIL — `ImportError: cannot import name 'EpisodeSource' from 'frontend.core.models'`

**Step 3: Write the EpisodeSource model**

Add to `frontend/frontend/core/models.py` after the `Summary` class (before the indexes section):

```python
class EpisodeSource(Base):
    """Episode source record linking email content to a transcription."""

    __tablename__ = 'episode_sources'

    id = Column(String, primary_key=True)  # e.g., 'es_abc123'
    transcription_id = Column(String, ForeignKey('transcriptions.id'), nullable=False)
    email_subject = Column(String)
    email_from = Column(String)
    source_text = Column(Text, nullable=False)
    matched_url = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    transcription = relationship("Transcription", back_populates="episode_sources")

    def __repr__(self):
        return f"<EpisodeSource {self.id} for {self.transcription_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'transcription_id': self.transcription_id,
            'email_subject': self.email_subject,
            'email_from': self.email_from,
            'source_text': self.source_text,
            'matched_url': self.matched_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

Add the reverse relationship to the `Transcription` class (after the `summaries` relationship):

```python
    episode_sources = relationship("EpisodeSource", back_populates="transcription", cascade="all, delete-orphan")
```

Add the index after the existing Summary indexes:

```python
# Indexes for EpisodeSource
Index('idx_episode_sources_transcription_id', EpisodeSource.transcription_id)
```

**Step 4: Write the migration**

Add to `frontend/frontend/core/migrations.py`:

```python
def create_episode_sources_table_if_missing(engine):
    """Create episode_sources table if it doesn't exist."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if 'episode_sources' not in tables:
        logger.info("Creating episode_sources table")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE episode_sources (
                    id TEXT PRIMARY KEY,
                    transcription_id TEXT NOT NULL,
                    email_subject TEXT,
                    email_from TEXT,
                    source_text TEXT NOT NULL,
                    matched_url TEXT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transcription_id) REFERENCES transcriptions (id)
                )
            """))
            conn.execute(text(
                "CREATE INDEX idx_episode_sources_transcription_id ON episode_sources (transcription_id)"
            ))
            conn.commit()
        logger.info("episode_sources table created successfully")
    else:
        logger.debug("episode_sources table already exists")
```

Add the call in `run_migrations()`:

```python
def run_migrations(engine):
    """Run all pending migrations."""
    logger.info("Running database migrations")
    add_tags_column_if_missing(engine)
    create_summaries_table_if_missing(engine)
    add_source_context_column_if_missing(engine)
    create_episode_sources_table_if_missing(engine)
    logger.info("Migrations complete")
```

**Step 5: Run test to verify it passes**

Run: `cd frontend && source venv/bin/activate && python -m pytest tests/test_episode_source_model.py -v`
Expected: All 6 tests PASS

**Step 6: Commit**

```bash
git add frontend/frontend/core/models.py frontend/frontend/core/migrations.py frontend/tests/test_episode_source_model.py
git commit -m "feat: add EpisodeSource model and migration"
```

---

### Task 2: Frontend — POST /api/episode-sources endpoint

**Files:**
- Modify: `frontend/frontend/api/models.py`
- Modify: `frontend/frontend/api/routes.py`
- Test: `frontend/tests/test_episode_source_api.py`

**Step 1: Write the failing test**

Create `frontend/tests/test_episode_source_api.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && source venv/bin/activate && python -m pytest tests/test_episode_source_api.py -v`
Expected: FAIL — endpoint does not exist (404)

**Step 3: Add Pydantic models**

Add to `frontend/frontend/api/models.py` after the `SummaryListResponse` class:

```python
# Episode Source Models

class EpisodeSourceRequest(BaseModel):
    """Request to create an episode source record."""
    transcription_id: str = Field(..., description="ID of the linked transcription")
    email_subject: Optional[str] = Field(None, description="Original email subject")
    email_from: Optional[str] = Field(None, description="Sender email address")
    source_text: str = Field(..., description="Plain text content of the email")
    matched_url: str = Field(..., description="URL extracted from the email")


class EpisodeSourceResponse(BaseModel):
    """Response for an episode source record."""
    id: str
    transcription_id: str
    email_subject: Optional[str] = None
    email_from: Optional[str] = None
    source_text: str
    matched_url: str
    created_at: Optional[datetime] = None
```

**Step 4: Add the endpoint**

Add to `frontend/frontend/api/routes.py`. Add imports at the top:

```python
from frontend.api.models import EpisodeSourceRequest, EpisodeSourceResponse
from frontend.core.models import EpisodeSource
```

Add the endpoint (after the summary endpoints section):

```python
# Episode Source endpoints

@router.post(
    "/episode-sources",
    response_model=EpisodeSourceResponse,
    status_code=201,
    responses={
        404: {"model": ErrorResponse, "description": "Transcription not found"},
    },
)
async def create_episode_source(
    request: EpisodeSourceRequest,
    db: Session = Depends(get_db),
):
    """Create an episode source record linking email content to a transcription."""
    import uuid

    # Verify transcription exists
    transcription = db.query(Transcription).filter(
        Transcription.id == request.transcription_id
    ).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    episode_source = EpisodeSource(
        id=f"es_{uuid.uuid4().hex[:8]}",
        transcription_id=request.transcription_id,
        email_subject=request.email_subject,
        email_from=request.email_from,
        source_text=request.source_text,
        matched_url=request.matched_url,
    )
    db.add(episode_source)
    db.commit()
    db.refresh(episode_source)

    return EpisodeSourceResponse(**episode_source.to_dict())
```

**Step 5: Run test to verify it passes**

Run: `cd frontend && source venv/bin/activate && python -m pytest tests/test_episode_source_api.py -v`
Expected: All 4 tests PASS

**Step 6: Run all frontend tests to check for regressions**

Run: `cd frontend && source venv/bin/activate && python -m pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/test_orchestrator.py`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add frontend/frontend/api/models.py frontend/frontend/api/routes.py frontend/tests/test_episode_source_api.py
git commit -m "feat: add POST /api/episode-sources endpoint"
```

---

### Task 3: Emailer — Config and URL filtering

**Files:**
- Modify: `emailer/emailer/config.py`
- Create: `emailer/emailer/episode_source_urls.py`
- Test: `emailer/tests/test_episode_source_urls.py`
- Modify: `emailer/tests/test_config.py`

**Step 1: Write the failing test for URL filtering**

Create `emailer/tests/test_episode_source_urls.py`:

```python
"""Tests for episode source URL extraction."""
import pytest
from emailer.episode_source_urls import extract_episode_source_urls


class TestExtractEpisodeSourceUrls:
    """Tests for extracting Apple Podcasts and YouTube URLs only."""

    def test_apple_podcasts_url(self):
        """Test extracting Apple Podcasts URL from text."""
        text = "Check out https://podcasts.apple.com/us/podcast/ep123 today!"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == ["https://podcasts.apple.com/us/podcast/ep123"]

    def test_youtube_watch_url(self):
        """Test extracting YouTube watch URL."""
        text = "Watch https://youtube.com/watch?v=abc123"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == ["https://youtube.com/watch?v=abc123"]

    def test_youtube_short_url(self):
        """Test extracting youtu.be short URL."""
        text = "See https://youtu.be/abc123"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == ["https://youtu.be/abc123"]

    def test_youtube_live_url(self):
        """Test extracting YouTube live URL."""
        text = "Live at https://youtube.com/live/abc123"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == ["https://youtube.com/live/abc123"]

    def test_ignores_direct_audio_urls(self):
        """Test that direct audio URLs are not included."""
        text = "Download https://example.com/episode.mp3"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == []

    def test_ignores_podcast_addict_urls(self):
        """Test that Podcast Addict URLs are not included."""
        text = "Listen at https://podcastaddict.com/show/episode/12345"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == []

    def test_ignores_non_transcribable_urls(self):
        """Test that random URLs are not included."""
        text = "Visit https://example.com and https://google.com"
        urls = extract_episode_source_urls(text, is_html=False)
        assert urls == []

    def test_multiple_urls_returns_all(self):
        """Test that all matching URLs are returned."""
        text = (
            "Apple: https://podcasts.apple.com/test "
            "YouTube: https://youtube.com/watch?v=abc"
        )
        urls = extract_episode_source_urls(text, is_html=False)
        assert len(urls) == 2

    def test_html_extracts_from_hrefs(self):
        """Test extracting URLs from HTML anchor tags."""
        html = '<a href="https://podcasts.apple.com/us/podcast/ep1">Listen</a>'
        urls = extract_episode_source_urls(html, is_html=True)
        assert urls == ["https://podcasts.apple.com/us/podcast/ep1"]

    def test_html_ignores_non_matching_hrefs(self):
        """Test that non-matching hrefs are ignored."""
        html = '<a href="https://example.com/page">Link</a>'
        urls = extract_episode_source_urls(html, is_html=True)
        assert urls == []

    def test_deduplicates_urls(self):
        """Test that duplicate URLs are removed."""
        text = (
            "https://podcasts.apple.com/test "
            "https://podcasts.apple.com/test"
        )
        urls = extract_episode_source_urls(text, is_html=False)
        assert len(urls) == 1

    def test_empty_input(self):
        """Test empty input returns empty list."""
        assert extract_episode_source_urls("", is_html=False) == []
        assert extract_episode_source_urls("", is_html=True) == []
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/test_episode_source_urls.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'emailer.episode_source_urls'`

**Step 3: Implement the URL filter module**

Create `emailer/emailer/episode_source_urls.py`:

```python
"""Extract Apple Podcasts and YouTube URLs from email content."""

import re
from typing import List

from bs4 import BeautifulSoup

# Only Apple Podcasts and YouTube patterns
EPISODE_SOURCE_PATTERNS = [
    r"youtube\.com/watch",
    r"youtube\.com/live/",
    r"youtu\.be/",
    r"podcasts\.apple\.com/",
]

# URL regex pattern (reused from url_extractor)
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\)\]]+",
    re.IGNORECASE,
)


def _is_episode_source_url(url: str) -> bool:
    """Check if a URL is an Apple Podcasts or YouTube URL."""
    for pattern in EPISODE_SOURCE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def extract_episode_source_urls(body: str, is_html: bool = False) -> List[str]:
    """
    Extract Apple Podcasts and YouTube URLs from email content.

    Args:
        body: Email body content
        is_html: Whether the body is HTML

    Returns:
        List of unique matching URLs
    """
    if not body:
        return []

    urls = set()

    if is_html:
        soup = BeautifulSoup(body, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if _is_episode_source_url(href):
                urls.add(href)
        text = soup.get_text()
        for match in URL_PATTERN.findall(text):
            clean_url = match.rstrip(".,;:!?)")
            if _is_episode_source_url(clean_url):
                urls.add(clean_url)
    else:
        for match in URL_PATTERN.findall(body):
            clean_url = match.rstrip(".,;:!?)")
            if _is_episode_source_url(clean_url):
                urls.add(clean_url)

    return list(urls)
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/test_episode_source_urls.py -v`
Expected: All 12 tests PASS

**Step 5: Add config settings**

Add to `emailer/emailer/config.py` in the `Settings` class, after the existing folder settings:

```python
    # Episode Sources Folder Names
    imap_folder_episode_sources: str = "EpisodeSources"
    imap_folder_episode_sources_done: str = "EpisodeSourcesDone"
    imap_folder_episode_sources_error: str = "EpisodeSourcesError"

    # Episode Sources
    episode_sources_return_address: str = "scribe_newsletters@patrickmccarthy.cc"
```

**Step 6: Run all emailer tests to check for regressions**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS (config tests should still pass since pydantic-settings allows optional fields with defaults)

**Step 7: Commit**

```bash
git add emailer/emailer/episode_source_urls.py emailer/tests/test_episode_source_urls.py emailer/emailer/config.py
git commit -m "feat: add episode source URL filter and config settings"
```

---

### Task 4: Emailer — FrontendClient.create_episode_source method

**Files:**
- Modify: `emailer/emailer/frontend_client.py`
- Modify: `emailer/tests/test_frontend_client.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_frontend_client.py`:

```python
class TestCreateEpisodeSource:
    """Tests for create_episode_source method."""

    @pytest.mark.asyncio
    async def test_create_episode_source(self):
        """Test posting an episode source to the frontend API."""
        client = FrontendClient(base_url="http://localhost:8000")

        mock_response = httpx.Response(
            status_code=201,
            json={
                "id": "es_abc123",
                "transcription_id": "test_123",
                "email_subject": "New episode",
                "email_from": "news@example.com",
                "source_text": "Episode about testing.",
                "matched_url": "https://podcasts.apple.com/test",
                "created_at": "2026-02-09T12:00:00",
            },
            request=httpx.Request("POST", "http://localhost:8000/api/episode-sources"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await client.create_episode_source(
                transcription_id="test_123",
                email_subject="New episode",
                email_from="news@example.com",
                source_text="Episode about testing.",
                matched_url="https://podcasts.apple.com/test",
            )
            assert result == "es_abc123"

    @pytest.mark.asyncio
    async def test_create_episode_source_minimal(self):
        """Test posting with only required fields."""
        client = FrontendClient(base_url="http://localhost:8000")

        mock_response = httpx.Response(
            status_code=201,
            json={
                "id": "es_def456",
                "transcription_id": "test_456",
                "email_subject": None,
                "email_from": None,
                "source_text": "Content only.",
                "matched_url": "https://youtu.be/abc",
                "created_at": "2026-02-09T12:00:00",
            },
            request=httpx.Request("POST", "http://localhost:8000/api/episode-sources"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await client.create_episode_source(
                transcription_id="test_456",
                source_text="Content only.",
                matched_url="https://youtu.be/abc",
            )
            assert result == "es_def456"
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/test_frontend_client.py::TestCreateEpisodeSource -v`
Expected: FAIL — `AttributeError: 'FrontendClient' object has no attribute 'create_episode_source'`

**Step 3: Implement the method**

Add to `emailer/emailer/frontend_client.py` in the `FrontendClient` class (after `generate_summary`):

```python
    async def create_episode_source(
        self,
        transcription_id: str,
        source_text: str,
        matched_url: str,
        email_subject: str | None = None,
        email_from: str | None = None,
    ) -> str:
        """
        Create an episode source record in the frontend DB.

        Args:
            transcription_id: ID of the linked transcription
            source_text: Plain text content of the email
            matched_url: URL that was extracted and processed
            email_subject: Original email subject
            email_from: Sender email address

        Returns:
            Episode source ID

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        logger.debug(f"POST /api/episode-sources starting for {transcription_id}")
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "transcription_id": transcription_id,
                "source_text": source_text,
                "matched_url": matched_url,
            }
            if email_subject is not None:
                payload["email_subject"] = email_subject
            if email_from is not None:
                payload["email_from"] = email_from

            response = await client.post(
                f"{self.base_url}/api/episode-sources",
                json=payload,
            )
            elapsed = time.monotonic() - start
            response.raise_for_status()
            data = response.json()
            logger.info(f"Created episode source {data['id']} for {transcription_id} ({elapsed:.2f}s)")
            return data["id"]
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/test_frontend_client.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/frontend_client.py emailer/tests/test_frontend_client.py
git commit -m "feat: add FrontendClient.create_episode_source method"
```

---

### Task 5: Emailer — Episode source processor

**Files:**
- Create: `emailer/emailer/episode_source_processor.py`
- Test: `emailer/tests/test_episode_source_processor.py`

**Step 1: Write the failing test**

Create `emailer/tests/test_episode_source_processor.py`:

```python
"""Tests for episode source email processing."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from emailer.episode_source_processor import EpisodeSourceProcessor
from emailer.imap_client import EmailMessage
from emailer.job_processor import JobResult


class TestEpisodeSourceProcessor:
    """Tests for EpisodeSourceProcessor."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        frontend = AsyncMock()
        p = EpisodeSourceProcessor(frontend_client=frontend)
        return p

    @pytest.mark.asyncio
    async def test_process_email_with_apple_podcasts_url(self, processor):
        """Test processing email containing Apple Podcasts URL."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_123")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed",
                title="Test Podcast",
                duration_seconds=1200,
                source_context="Show notes here",
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="Transcript text")
        processor.frontend.generate_summary = AsyncMock(return_value="Summary text")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_abc")

        email = EmailMessage(
            msg_num="1",
            sender="newsletter@example.com",
            subject="New Episode: Testing 101",
            body_text="Check out our latest episode https://podcasts.apple.com/us/podcast/ep1 about testing",
            body_html=None,
        )

        result = await processor.process_email(email)

        assert result.success
        assert result.url == "https://podcasts.apple.com/us/podcast/ep1"
        assert result.title == "Test Podcast"
        processor.frontend.submit_url.assert_called_once_with(
            "https://podcasts.apple.com/us/podcast/ep1", tag="digest"
        )
        processor.frontend.create_episode_source.assert_called_once()
        call_kwargs = processor.frontend.create_episode_source.call_args.kwargs
        assert call_kwargs["transcription_id"] == "trans_123"
        assert "Check out our latest episode" in call_kwargs["source_text"]
        assert call_kwargs["matched_url"] == "https://podcasts.apple.com/us/podcast/ep1"
        assert call_kwargs["email_subject"] == "New Episode: Testing 101"
        assert call_kwargs["email_from"] == "newsletter@example.com"

    @pytest.mark.asyncio
    async def test_process_email_with_youtube_url(self, processor):
        """Test processing email containing YouTube URL."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_456")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed",
                title="YouTube Video",
                duration_seconds=600,
                source_context=None,
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="Transcript")
        processor.frontend.generate_summary = AsyncMock(return_value="Summary")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_def")

        email = EmailMessage(
            msg_num="2",
            sender="user@example.com",
            subject="Check this video",
            body_text="Watch https://youtube.com/watch?v=abc123",
            body_html=None,
        )

        result = await processor.process_email(email)

        assert result.success
        assert result.url == "https://youtube.com/watch?v=abc123"

    @pytest.mark.asyncio
    async def test_process_email_no_matching_urls(self, processor):
        """Test processing email with no Apple Podcasts or YouTube URLs."""
        email = EmailMessage(
            msg_num="3",
            sender="user@example.com",
            subject="Random email",
            body_text="Visit https://example.com for more info",
            body_html=None,
        )

        result = await processor.process_email(email)

        assert not result.success
        assert "No Apple Podcasts or YouTube URL" in result.error

    @pytest.mark.asyncio
    async def test_process_email_uses_first_url(self, processor):
        """Test that only the first matching URL is processed."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_789")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed",
                title="First",
                duration_seconds=300,
                source_context=None,
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="Transcript")
        processor.frontend.generate_summary = AsyncMock(return_value="Summary")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_ghi")

        email = EmailMessage(
            msg_num="4",
            sender="user@example.com",
            subject="Two episodes",
            body_text=(
                "First: https://podcasts.apple.com/ep1 "
                "Second: https://podcasts.apple.com/ep2"
            ),
            body_html=None,
        )

        result = await processor.process_email(email)

        assert result.success
        # Should have submitted only once (first URL)
        processor.frontend.submit_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_email_prefers_html_for_urls(self, processor):
        """Test that HTML body is searched for URLs when present."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_html")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed", title="HTML", duration_seconds=100, source_context=None,
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="T")
        processor.frontend.generate_summary = AsyncMock(return_value="S")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_html")

        email = EmailMessage(
            msg_num="5",
            sender="user@example.com",
            subject="HTML email",
            body_text=None,
            body_html='<a href="https://podcasts.apple.com/html-ep">Listen</a>',
        )

        result = await processor.process_email(email)

        assert result.success
        assert result.url == "https://podcasts.apple.com/html-ep"

    @pytest.mark.asyncio
    async def test_process_email_converts_html_to_plain_text(self, processor):
        """Test that HTML body is converted to plain text for source_text."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_conv")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="completed", title="Conv", duration_seconds=100, source_context=None,
            )
        )
        processor.frontend.get_transcript_text = AsyncMock(return_value="T")
        processor.frontend.generate_summary = AsyncMock(return_value="S")
        processor.frontend.create_episode_source = AsyncMock(return_value="es_conv")

        email = EmailMessage(
            msg_num="6",
            sender="user@example.com",
            subject="HTML only",
            body_text=None,
            body_html='<p>Great episode about <b>testing</b>.</p><a href="https://podcasts.apple.com/conv">Listen</a>',
        )

        result = await processor.process_email(email)

        assert result.success
        call_kwargs = processor.frontend.create_episode_source.call_args.kwargs
        # Should contain plain text, not HTML tags
        assert "<p>" not in call_kwargs["source_text"]
        assert "testing" in call_kwargs["source_text"]

    @pytest.mark.asyncio
    async def test_process_email_transcription_failure(self, processor):
        """Test handling when transcription fails."""
        processor.frontend.submit_url = AsyncMock(return_value="trans_fail")
        processor.frontend.wait_for_completion = AsyncMock(
            return_value=MagicMock(
                status="failed",
                error="Audio download failed",
            )
        )

        email = EmailMessage(
            msg_num="7",
            sender="user@example.com",
            subject="Will fail",
            body_text="https://podcasts.apple.com/fail",
            body_html=None,
        )

        result = await processor.process_email(email)

        assert not result.success
        assert "Audio download failed" in result.error
        # Should not create episode source on failure
        processor.frontend.create_episode_source.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/test_episode_source_processor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'emailer.episode_source_processor'`

**Step 3: Implement the processor**

Create `emailer/emailer/episode_source_processor.py`:

```python
"""Process episode source emails."""

import logging
import time
from typing import Optional

import html2text
import httpx

from emailer.episode_source_urls import extract_episode_source_urls
from emailer.frontend_client import FrontendClient, HTML_SUMMARY_SUFFIX
from emailer.imap_client import EmailMessage
from emailer.job_processor import JobResult

logger = logging.getLogger(__name__)


def _html_to_plain_text(html_content: str) -> str:
    """Convert HTML to readable plain text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    return h.handle(html_content).strip()


class EpisodeSourceProcessor:
    """Process episode source emails: extract URL, transcribe, store source."""

    def __init__(self, frontend_client: FrontendClient):
        self.frontend = frontend_client

    async def process_email(self, email: EmailMessage) -> JobResult:
        """
        Process an episode source email.

        Extracts Apple Podcasts/YouTube URL, submits for transcription,
        stores the email content as an episode source record.

        Args:
            email: The email message to process

        Returns:
            JobResult with success/failure and transcription data
        """
        job_start = time.monotonic()

        # Extract URLs from both text and HTML
        urls = []
        if email.body_text:
            urls.extend(extract_episode_source_urls(email.body_text, is_html=False))
        if email.body_html:
            urls.extend(extract_episode_source_urls(email.body_html, is_html=True))

        # Deduplicate while preserving order
        urls = list(dict.fromkeys(urls))

        if not urls:
            return JobResult(
                url="",
                success=False,
                error="No Apple Podcasts or YouTube URL found in email",
            )

        # Use the first matching URL
        url = urls[0]
        logger.info(f"[episode-source] Processing URL: {url} (from {len(urls)} found)")

        # Get plain text content for storage
        if email.body_text:
            source_text = email.body_text
        elif email.body_html:
            source_text = _html_to_plain_text(email.body_html)
        else:
            source_text = ""

        current_step = "initializing"
        transcription_id = None
        try:
            # Submit for transcription with "digest" tag
            current_step = "submitting URL"
            logger.info(f"[episode-source] Step 1/5: Submitting {url}")
            transcription_id = await self.frontend.submit_url(url, tag="digest")

            # Wait for completion
            current_step = "waiting for transcription"
            logger.info(f"[episode-source] Step 2/5: Waiting for {transcription_id}")
            result = await self.frontend.wait_for_completion(transcription_id)

            if result.status == "failed":
                elapsed = time.monotonic() - job_start
                logger.error(f"[episode-source] Failed after {elapsed:.1f}s: {result.error}")
                return JobResult(
                    url=url,
                    success=False,
                    error=result.error or "Transcription failed",
                )

            # Get transcript
            current_step = "fetching transcript"
            logger.info(f"[episode-source] Step 3/5: Fetching transcript for {transcription_id}")
            transcript = await self.frontend.get_transcript_text(transcription_id)

            # Generate summary
            current_step = "generating summary"
            logger.info(f"[episode-source] Step 4/5: Generating summary for {transcription_id}")
            summary = await self.frontend.generate_summary(
                transcription_id,
                system_prompt_suffix=HTML_SUMMARY_SUFFIX,
            )

            # Store episode source record
            current_step = "storing episode source"
            logger.info(f"[episode-source] Step 5/5: Storing episode source for {transcription_id}")
            await self.frontend.create_episode_source(
                transcription_id=transcription_id,
                source_text=source_text,
                matched_url=url,
                email_subject=email.subject or None,
                email_from=email.sender or None,
            )

            elapsed = time.monotonic() - job_start
            logger.info(f"[episode-source] Completed successfully in {elapsed:.1f}s")
            return JobResult(
                url=url,
                success=True,
                title=result.title,
                summary=summary,
                transcript=transcript,
                duration_seconds=result.duration_seconds,
                creator_notes=result.source_context,
            )

        except httpx.HTTPStatusError as e:
            elapsed = time.monotonic() - job_start
            # Handle 409 Conflict - transcription already exists
            if e.response.status_code == 409:
                try:
                    data = e.response.json()
                    existing_id = data.get("existing_id")
                    if existing_id:
                        logger.info(f"[episode-source] Transcription exists: {existing_id}")
                        return await self._process_existing(url, existing_id, email, source_text)
                except Exception as inner_e:
                    logger.error(f"[episode-source] Error processing existing: {inner_e}")
                    return JobResult(url=url, success=False, error=str(inner_e))

            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_msg = e.response.text or error_msg
            except Exception:
                pass
            logger.error(f"[episode-source] HTTP error during '{current_step}' after {elapsed:.1f}s: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)

        except TimeoutError as e:
            elapsed = time.monotonic() - job_start
            logger.error(f"[episode-source] Timeout during '{current_step}' after {elapsed:.1f}s")
            return JobResult(url=url, success=False, error=str(e))

        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - job_start
            error_msg = f"Request timed out during '{current_step}': {type(e).__name__}"
            logger.error(f"[episode-source] {error_msg} after {elapsed:.1f}s")
            return JobResult(url=url, success=False, error=error_msg)

        except Exception as e:
            elapsed = time.monotonic() - job_start
            error_msg = str(e) or f"Unexpected error: {type(e).__name__}"
            logger.error(f"[episode-source] Error during '{current_step}' after {elapsed:.1f}s: {error_msg}")
            return JobResult(url=url, success=False, error=error_msg)

    async def _process_existing(
        self,
        url: str,
        transcription_id: str,
        email: EmailMessage,
        source_text: str,
    ) -> JobResult:
        """Process when transcription already exists (409 case)."""
        result = await self.frontend.wait_for_completion(transcription_id)

        if result.status == "failed":
            return JobResult(
                url=url,
                success=False,
                error=result.error or "Transcription failed",
            )

        transcript = await self.frontend.get_transcript_text(transcription_id)
        summary = await self.frontend.generate_summary(
            transcription_id,
            system_prompt_suffix=HTML_SUMMARY_SUFFIX,
        )

        # Still store the episode source
        await self.frontend.create_episode_source(
            transcription_id=transcription_id,
            source_text=source_text,
            matched_url=url,
            email_subject=email.subject or None,
            email_from=email.sender or None,
        )

        return JobResult(
            url=url,
            success=True,
            title=result.title,
            summary=summary,
            transcript=transcript,
            duration_seconds=result.duration_seconds,
            creator_notes=result.source_context,
        )
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/test_episode_source_processor.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add emailer/emailer/episode_source_processor.py emailer/tests/test_episode_source_processor.py
git commit -m "feat: add EpisodeSourceProcessor for email processing"
```

---

### Task 6: Emailer — Integrate into polling loop

**Files:**
- Modify: `emailer/emailer/main.py`
- Modify: `emailer/tests/test_main.py`

**Step 1: Write the failing tests**

Add to `emailer/tests/test_main.py`:

```python
class TestEpisodeSourceProcessing:
    """Tests for episode source email processing pipeline."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with episode source config."""
        settings = MagicMock()
        settings.imap_host = "imap.test.com"
        settings.imap_port = 993
        settings.imap_user = "test@test.com"
        settings.imap_password = "testpass"
        settings.imap_use_ssl = True
        settings.smtp_host = "smtp.test.com"
        settings.smtp_port = 587
        settings.smtp_user = "test@test.com"
        settings.smtp_password = "testpass"
        settings.smtp_use_tls = True
        settings.imap_folder_inbox = "ToScribe"
        settings.imap_folder_done = "ScribeDone"
        settings.imap_folder_error = "ScribeError"
        settings.imap_folder_episode_sources = "EpisodeSources"
        settings.imap_folder_episode_sources_done = "EpisodeSourcesDone"
        settings.imap_folder_episode_sources_error = "EpisodeSourcesError"
        settings.episode_sources_return_address = "newsletters@test.com"
        settings.poll_interval_seconds = 300
        settings.max_concurrent_jobs = 3
        settings.result_email_address = "results@test.com"
        settings.from_email_address = "scribe@test.com"
        settings.frontend_url = "http://localhost:8000"
        settings.default_tag = "email"
        return settings

    @pytest.mark.asyncio
    async def test_process_episode_source_email_success(self, mock_settings):
        """Test successful episode source email processing."""
        from emailer.job_processor import JobResult

        service = EmailerService(mock_settings)
        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.smtp.send_email = AsyncMock()

        service.episode_source_processor = AsyncMock()
        service.episode_source_processor.process_email = AsyncMock(
            return_value=JobResult(
                url="https://podcasts.apple.com/test",
                success=True,
                title="Test Podcast",
                summary="Summary",
                transcript="Transcript",
                duration_seconds=600,
            )
        )

        email = EmailMessage(
            msg_num="1",
            sender="newsletter@example.com",
            subject="New Episode: Testing",
            body_text="Listen at https://podcasts.apple.com/test",
            body_html=None,
        )

        await service._process_episode_source_email(email)

        # Should have sent result to configured return address
        service.smtp.send_email.assert_called()
        call_kwargs = service.smtp.send_email.call_args.kwargs
        assert call_kwargs["to_addr"] == "newsletters@test.com"
        assert "Scribe: New Episode: Testing" in call_kwargs["subject"]

        # Should move to done folder
        service.imap.move_to_folder.assert_called_with("1", "EpisodeSourcesDone")

    @pytest.mark.asyncio
    async def test_process_episode_source_email_no_urls(self, mock_settings):
        """Test episode source email with no matching URLs."""
        from emailer.job_processor import JobResult

        service = EmailerService(mock_settings)
        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.smtp.send_email = AsyncMock()

        service.episode_source_processor = AsyncMock()
        service.episode_source_processor.process_email = AsyncMock(
            return_value=JobResult(
                url="",
                success=False,
                error="No Apple Podcasts or YouTube URL found in email",
            )
        )

        email = EmailMessage(
            msg_num="2",
            sender="user@example.com",
            subject="Random email",
            body_text="No relevant URLs here",
            body_html=None,
        )

        await service._process_episode_source_email(email)

        # Should notify sender
        service.smtp.send_email.assert_called()
        call_kwargs = service.smtp.send_email.call_args.kwargs
        assert call_kwargs["to_addr"] == "user@example.com"

        # Should move to error folder
        service.imap.move_to_folder.assert_called_with("2", "EpisodeSourcesError")

    @pytest.mark.asyncio
    async def test_poll_checks_episode_sources_folder(self, mock_settings):
        """Test that polling checks both ToScribe and EpisodeSources folders."""
        service = EmailerService(mock_settings)
        service.imap = AsyncMock()
        service.smtp = AsyncMock()
        service.semaphore = asyncio.Semaphore(3)

        # No emails in either folder
        service.imap.fetch_unseen = AsyncMock(return_value=[])

        await service._poll_and_process()

        # Should have checked both folders
        calls = service.imap.fetch_unseen.call_args_list
        folders_checked = [call.args[0] for call in calls]
        assert "ToScribe" in folders_checked
        assert "EpisodeSources" in folders_checked
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/test_main.py::TestEpisodeSourceProcessing -v`
Expected: FAIL — `AttributeError: 'EmailerService' object has no attribute '_process_episode_source_email'`

**Step 3: Modify main.py**

Add import at the top of `emailer/emailer/main.py`:

```python
from emailer.episode_source_processor import EpisodeSourceProcessor
```

In `EmailerService.__init__`, after the `self.processor` line, add:

```python
        self.episode_source_processor = EpisodeSourceProcessor(frontend_client=frontend)
```

Replace the `_poll_and_process` method:

```python
    async def _poll_and_process(self) -> None:
        """Poll for new emails and process them."""
        try:
            # Check main inbox
            emails = await self.imap.fetch_unseen(self.settings.imap_folder_inbox)
            if emails:
                logger.info(f"Found {len(emails)} new email(s) in {self.settings.imap_folder_inbox}")

            tasks = []
            for email in emails:
                await self.imap.mark_seen(email.msg_num)
                task = asyncio.create_task(self._process_email_with_semaphore(email))
                tasks.append(task)

            # Check episode sources inbox
            try:
                es_emails = await self.imap.fetch_unseen(self.settings.imap_folder_episode_sources)
                if es_emails:
                    logger.info(f"Found {len(es_emails)} new email(s) in {self.settings.imap_folder_episode_sources}")

                for email in es_emails:
                    await self.imap.mark_seen(email.msg_num)
                    task = asyncio.create_task(self._process_episode_source_with_semaphore(email))
                    tasks.append(task)
            except Exception as e:
                logger.error(f"Error checking episode sources folder: {e}")

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error during poll: {e}")
            if self.imap.is_connection_error(e):
                try:
                    await self.imap.reconnect()
                except Exception as reconnect_err:
                    logger.error(f"Reconnection failed: {reconnect_err}")
```

Add the new methods:

```python
    async def _process_episode_source_with_semaphore(self, email: EmailMessage) -> None:
        """Process episode source email with concurrency limit."""
        async with self.semaphore:
            await self._process_episode_source_email(email)

    async def _process_episode_source_email(self, email: EmailMessage) -> None:
        """Process a single episode source email."""
        logger.info(f"Processing episode source email {email.msg_num} from {email.sender}")

        result = await self.episode_source_processor.process_email(email)

        if result.success:
            subject, html_body, text_body = format_success_email(
                url=result.url,
                title=result.title or "Untitled",
                duration_seconds=result.duration_seconds or 0,
                summary=result.summary or "",
                transcript=result.transcript or "",
                creator_notes=result.creator_notes,
            )
            # Override subject to include original email subject
            subject = f"Scribe: {email.subject}" if email.subject else subject
            # Prepend matched URL verification line
            verification = f"Matched URL: {result.url}\n\n"
            text_body = verification + text_body

            await self.smtp.send_email(
                from_addr=self.settings.from_email_address,
                to_addr=self.settings.episode_sources_return_address,
                subject=subject,
                body=text_body,
                html_body=html_body,
            )

            target_folder = self.settings.imap_folder_episode_sources_done
        else:
            error_subject, error_body = format_error_email(
                url=result.url or "(no URL found)",
                error_message=result.error or "Unknown error",
            )
            await self.smtp.send_email(
                from_addr=self.settings.from_email_address,
                to_addr=email.sender,
                subject=error_subject,
                body=error_body,
            )
            target_folder = self.settings.imap_folder_episode_sources_error

        try:
            await self.imap.move_to_folder(email.msg_num, target_folder)
        except Exception as e:
            logger.error(
                f"Failed to move email {email.msg_num} to {target_folder}: {e}"
            )
```

Also update the `start` method log to mention both folders:

```python
        logger.info(
            f"Monitoring folders: {self.settings.imap_folder_inbox}, "
            f"{self.settings.imap_folder_episode_sources} "
            f"(poll interval: {self.settings.poll_interval_seconds}s)"
        )
```

**Step 4: Run the new tests to verify they pass**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/test_main.py::TestEpisodeSourceProcessing -v`
Expected: All 3 tests PASS

**Step 5: Run all emailer tests to check for regressions**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS. The existing `TestEmailerService` tests should still pass because `mock_settings` doesn't have the new attributes, but `EmailerService.__init__` accesses them — you may need to add the new settings to the existing `mock_settings` fixtures. If so, add these lines to each `mock_settings` fixture in `test_main.py`:

```python
        settings.imap_folder_episode_sources = "EpisodeSources"
        settings.imap_folder_episode_sources_done = "EpisodeSourcesDone"
        settings.imap_folder_episode_sources_error = "EpisodeSourcesError"
        settings.episode_sources_return_address = "newsletters@test.com"
```

**Step 6: Commit**

```bash
git add emailer/emailer/main.py emailer/tests/test_main.py
git commit -m "feat: integrate episode sources into emailer polling loop"
```

---

### Task 7: Final verification

**Step 1: Run all frontend tests**

Run: `cd frontend && source venv/bin/activate && python -m pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/test_orchestrator.py`
Expected: All tests PASS

**Step 2: Run all emailer tests**

Run: `cd emailer && source venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 3: Commit any remaining fixes and verify clean status**

Run: `git status`
Expected: Clean working tree on `feature/episode-sources` branch
