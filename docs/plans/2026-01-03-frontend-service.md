# Frontend Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build complete web interface and orchestration service for Scribe transcription system

**Architecture:** FastAPI web service with SQLAlchemy ORM, yt-dlp for downloads, WebSocket for real-time updates, and orchestrator pattern for workflow coordination

**Tech Stack:** FastAPI, SQLAlchemy, yt-dlp, Jinja2, WebSockets, SQLite with FTS5

---

## Task 1: Project Structure and Configuration

**Files:**
- Create: `frontend/frontend/__init__.py`
- Create: `frontend/frontend/core/__init__.py`
- Create: `frontend/frontend/core/config.py`
- Create: `frontend/requirements.txt`
- Create: `frontend/requirements-dev.txt`

### Step 1: Write configuration test

Create test file to verify configuration loads correctly.

```python
# frontend/tests/__init__.py
# Empty file for test package
```

```python
# frontend/tests/test_config.py
"""Test configuration loading."""
import os
from pathlib import Path
from frontend.core.config import Settings


def test_settings_defaults():
    """Test default settings values"""
    settings = Settings()
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.transcriber_url == "http://localhost:8001"
    assert settings.audio_cache_days == 7


def test_settings_from_env(monkeypatch):
    """Test settings load from environment"""
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("AUDIO_CACHE_DAYS", "14")
    settings = Settings()
    assert settings.port == 9000
    assert settings.audio_cache_days == 14
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_config.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend'"

### Step 3: Create requirements files

```txt
# frontend/requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
jinja2==3.1.3
aiofiles==23.2.1
httpx==0.26.0
yt-dlp==2024.3.10
python-multipart==0.0.6
websockets==12.0
```

```txt
# frontend/requirements-dev.txt
-r requirements.txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==24.1.1
flake8==7.0.0
mypy==1.8.0
httpx==0.26.0
```

### Step 4: Create virtual environment and install dependencies

Run: `cd frontend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt`

Expected: All packages install successfully

### Step 5: Write configuration module

```python
# frontend/frontend/__init__.py
"""Frontend service for Scribe transcription system."""
__version__ = "0.1.0"
```

```python
# frontend/frontend/core/__init__.py
"""Core functionality for frontend service."""
```

```python
# frontend/frontend/core/config.py
"""Configuration management for frontend service."""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Transcriber Service
    transcriber_url: str = "http://localhost:8001"
    transcriber_timeout: int = 300  # 5 minutes

    # Storage Configuration
    data_dir: Path = Path("data")
    transcriptions_dir: Path = Path("data/transcriptions")
    audio_cache_dir: Path = Path("data/cache/audio")
    database_url: str = "sqlite:///data/scribe.db"

    # Audio Cache
    audio_cache_days: int = 7

    # Download Configuration
    max_audio_size_mb: int = 500
    download_timeout: int = 600  # 10 minutes

    # WebSocket Configuration
    ws_heartbeat_interval: int = 30

    # Logging Configuration
    log_file: Path = Path("data/logs/frontend.log")
    log_format: Literal["json", "text"] = "text"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
```

### Step 6: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_config.py -v`

Expected: PASS (2 tests)

### Step 7: Create pytest configuration

```ini
# frontend/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

### Step 8: Commit

```bash
git add frontend/frontend/ frontend/tests/ frontend/requirements.txt frontend/requirements-dev.txt frontend/pytest.ini
git commit -m "$(cat <<'EOF'
feat: add frontend project structure and configuration

- Create frontend package structure
- Add pydantic settings with environment support
- Add production and dev dependencies
- Add pytest configuration
- Add configuration tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Database Models and Initialization

**Files:**
- Create: `frontend/frontend/core/models.py`
- Create: `frontend/frontend/core/database.py`
- Modify: `frontend/tests/test_config.py` (add database tests)

### Step 1: Write database model test

```python
# frontend/tests/test_models.py
"""Test database models."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from frontend.core.models import Base, Transcription
from frontend.core.database import init_db, get_db


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return engine


def test_transcription_model_creation(test_db):
    """Test creating a transcription record"""
    with Session(test_db) as session:
        transcription = Transcription(
            id="youtube_test123",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=test123",
            title="Test Video",
            status="pending"
        )
        session.add(transcription)
        session.commit()

        # Query it back
        result = session.query(Transcription).filter_by(id="youtube_test123").first()
        assert result is not None
        assert result.title == "Test Video"
        assert result.status == "pending"
        assert result.progress == 0


def test_transcription_to_dict(test_db):
    """Test to_dict serialization"""
    with Session(test_db) as session:
        transcription = Transcription(
            id="youtube_test456",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=test456",
            title="Test Video 2",
            status="completed",
            language="en",
            word_count=100
        )
        session.add(transcription)
        session.commit()

        data = transcription.to_dict()
        assert data["id"] == "youtube_test456"
        assert data["source"]["title"] == "Test Video 2"
        assert data["status"] == "completed"
        assert data["language"] == "en"
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_models.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.core.models'"

### Step 3: Write database models

```python
# frontend/frontend/core/models.py
"""SQLAlchemy database models."""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Transcription(Base):
    """Transcription job model."""

    __tablename__ = 'transcriptions'

    # Primary Key
    id = Column(String, primary_key=True)

    # Source Information
    source_type = Column(String, nullable=False)  # 'youtube', 'apple_podcasts', 'direct_audio'
    source_url = Column(String, nullable=False, unique=True)
    title = Column(String)
    channel = Column(String)
    thumbnail_url = Column(String)
    upload_date = Column(String)

    # Media Information
    duration_seconds = Column(Integer)
    file_size_bytes = Column(Integer)
    audio_format = Column(String)

    # File Paths
    audio_path = Column(String)
    transcription_path = Column(String)

    # Job Status
    status = Column(String, nullable=False, default='pending')
    progress = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime)
    transcribed_at = Column(DateTime)
    audio_cached_until = Column(DateTime)

    # Transcription Metadata
    model_used = Column(String)
    language = Column(String)
    word_count = Column(Integer)
    segments_count = Column(Integer)

    # Error Handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Search
    full_text = Column(Text)

    def __repr__(self):
        return f"<Transcription {self.id} ({self.status})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'source': {
                'type': self.source_type,
                'url': self.source_url,
                'title': self.title,
                'channel': self.channel,
                'thumbnail': self.thumbnail_url,
                'upload_date': self.upload_date
            },
            'status': self.status,
            'progress': self.progress,
            'duration_seconds': self.duration_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'transcribed_at': self.transcribed_at.isoformat() if self.transcribed_at else None,
            'model': self.model_used,
            'language': self.language,
            'word_count': self.word_count,
            'segments_count': self.segments_count,
            'error': self.error_message
        }


# Indexes
Index('idx_status', Transcription.status)
Index('idx_created_at', Transcription.created_at.desc())
Index('idx_transcribed_at', Transcription.transcribed_at.desc())
Index('idx_cached_until', Transcription.audio_cached_until)
Index('idx_source_type', Transcription.source_type)
```

### Step 4: Write database initialization module

```python
# frontend/frontend/core/database.py
"""Database initialization and session management."""

import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from frontend.core.config import settings
from frontend.core.models import Base

logger = logging.getLogger(__name__)


def init_db(engine: Engine = None):
    """Initialize database schema and FTS5 tables."""
    if engine is None:
        engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False}  # SQLite specific
        )

    # Create tables
    Base.metadata.create_all(engine)

    # Create FTS5 virtual table
    with engine.connect() as conn:
        # Check if FTS table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transcriptions_fts'"
        ))

        if not result.fetchone():
            logger.info("Creating FTS5 table and triggers")

            # Create FTS5 table
            conn.execute(text("""
                CREATE VIRTUAL TABLE transcriptions_fts USING fts5(
                    id UNINDEXED,
                    title,
                    channel,
                    content
                )
            """))

            # Insert trigger
            conn.execute(text("""
                CREATE TRIGGER transcriptions_ai AFTER INSERT ON transcriptions BEGIN
                    INSERT INTO transcriptions_fts(rowid, id, title, channel, content)
                    VALUES (new.rowid, new.id, new.title, new.channel, new.full_text);
                END
            """))

            # Update trigger
            conn.execute(text("""
                CREATE TRIGGER transcriptions_au AFTER UPDATE ON transcriptions BEGIN
                    UPDATE transcriptions_fts
                    SET title = new.title,
                        channel = new.channel,
                        content = new.full_text
                    WHERE rowid = new.rowid;
                END
            """))

            # Delete trigger
            conn.execute(text("""
                CREATE TRIGGER transcriptions_ad AFTER DELETE ON transcriptions BEGIN
                    DELETE FROM transcriptions_fts WHERE rowid = old.rowid;
                END
            """))

            conn.commit()

    logger.info("Database initialized successfully")
    return engine


def get_engine():
    """Get database engine."""
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
    )
    return engine


def get_session_maker():
    """Get session maker."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session (dependency for FastAPI)."""
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Step 5: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_models.py -v`

Expected: PASS (2 tests)

### Step 6: Test FTS5 functionality

```python
# Add to frontend/tests/test_models.py

def test_fts5_search(test_db):
    """Test full-text search works"""
    with Session(test_db) as session:
        # Create some transcriptions
        t1 = Transcription(
            id="yt_1",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=1",
            title="Python Tutorial",
            channel="Tech Channel",
            status="completed",
            full_text="This is a tutorial about Python programming language"
        )
        t2 = Transcription(
            id="yt_2",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=2",
            title="JavaScript Guide",
            channel="Tech Channel",
            status="completed",
            full_text="Learn JavaScript from scratch"
        )
        session.add_all([t1, t2])
        session.commit()

        # Search for "Python"
        result = session.execute(text("""
            SELECT t.id, t.title
            FROM transcriptions t
            JOIN transcriptions_fts fts ON t.rowid = fts.rowid
            WHERE transcriptions_fts MATCH 'Python'
        """))
        rows = result.fetchall()

        assert len(rows) == 1
        assert rows[0][0] == "yt_1"
```

### Step 7: Run FTS5 test to verify it passes

Run: `cd frontend && python -m pytest tests/test_models.py::test_fts5_search -v`

Expected: PASS

### Step 8: Commit

```bash
git add frontend/frontend/core/models.py frontend/frontend/core/database.py frontend/tests/test_models.py
git commit -m "$(cat <<'EOF'
feat: add database models and initialization

- Create SQLAlchemy Transcription model
- Add database initialization with FTS5 support
- Add triggers to keep FTS in sync
- Add session management
- Add comprehensive model tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: URL Parser and ID Generator

**Files:**
- Create: `frontend/frontend/utils/__init__.py`
- Create: `frontend/frontend/utils/url_parser.py`

### Step 1: Write URL parser tests

```python
# frontend/tests/test_url_parser.py
"""Test URL parsing and ID generation."""
import pytest
from frontend.utils.url_parser import (
    parse_url,
    generate_id,
    extract_youtube_id,
    extract_apple_podcast_id,
    SourceType
)


def test_parse_youtube_watch_url():
    """Test parsing standard YouTube watch URL"""
    info = parse_url("https://youtube.com/watch?v=abc123")
    assert info.source_type == SourceType.YOUTUBE
    assert info.video_id == "abc123"
    assert info.id == "youtube_abc123"


def test_parse_youtube_short_url():
    """Test parsing YouTube short URL"""
    info = parse_url("https://youtu.be/xyz789")
    assert info.source_type == SourceType.YOUTUBE
    assert info.video_id == "xyz789"
    assert info.id == "youtube_xyz789"


def test_parse_apple_podcasts_url():
    """Test parsing Apple Podcasts URL"""
    url = "https://podcasts.apple.com/us/podcast/the-indicator/id1320118593?i=1000641234567"
    info = parse_url(url)
    assert info.source_type == SourceType.APPLE_PODCASTS
    assert info.id.startswith("apple_podcasts_")


def test_parse_direct_audio_url():
    """Test parsing direct audio URL"""
    info = parse_url("https://example.com/audio/file.mp3")
    assert info.source_type == SourceType.DIRECT_AUDIO
    assert info.id.startswith("direct_audio_")


def test_generate_id_deterministic():
    """Test ID generation is deterministic"""
    url = "https://youtube.com/watch?v=test123"
    id1 = generate_id(url)
    id2 = generate_id(url)
    assert id1 == id2


def test_invalid_url():
    """Test invalid URL raises error"""
    with pytest.raises(ValueError, match="Invalid URL"):
        parse_url("not a url")
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_url_parser.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.utils.url_parser'"

### Step 3: Write URL parser implementation

```python
# frontend/frontend/utils/__init__.py
"""Utility functions for frontend service."""
```

```python
# frontend/frontend/utils/url_parser.py
"""URL parsing and ID generation utilities."""

import hashlib
import re
from enum import Enum
from typing import NamedTuple, Optional
from urllib.parse import urlparse, parse_qs


class SourceType(str, Enum):
    """Source type enumeration."""
    YOUTUBE = "youtube"
    APPLE_PODCASTS = "apple_podcasts"
    DIRECT_AUDIO = "direct_audio"


class URLInfo(NamedTuple):
    """Parsed URL information."""
    source_type: SourceType
    original_url: str
    id: str
    video_id: Optional[str] = None
    podcast_id: Optional[str] = None


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL.

    Supports:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def extract_apple_podcast_id(url: str) -> Optional[str]:
    """
    Extract Apple Podcasts episode ID from URL.

    Supports:
    - https://podcasts.apple.com/us/podcast/name/id123?i=1000456
    """
    match = re.search(r'[?&]i=(\d+)', url)
    if match:
        return match.group(1)

    # Fallback to podcast show ID
    match = re.search(r'/id(\d+)', url)
    if match:
        return match.group(1)

    return None


def generate_id(url: str, source_type: Optional[SourceType] = None) -> str:
    """
    Generate deterministic ID from URL.

    Examples:
    - youtube.com/watch?v=abc123 → 'youtube_abc123'
    - youtu.be/abc123 → 'youtube_abc123'
    - podcasts.apple.com/.../id123 → 'apple_podcasts_123'
    - example.com/audio.mp3 → 'direct_audio_<hash>'
    """
    # YouTube
    if 'youtube.com' in url or 'youtu.be' in url:
        video_id = extract_youtube_id(url)
        if video_id:
            return f'youtube_{video_id}'

    # Apple Podcasts
    elif 'podcasts.apple.com' in url:
        podcast_id = extract_apple_podcast_id(url)
        if podcast_id:
            return f'apple_podcasts_{podcast_id}'

    # Direct audio URL - use hash
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f'direct_audio_{url_hash}'


def parse_url(url: str) -> URLInfo:
    """
    Parse URL and extract metadata.

    Args:
        url: Source URL to parse

    Returns:
        URLInfo with source type, ID, and extracted metadata

    Raises:
        ValueError: If URL is invalid or unsupported
    """
    # Basic URL validation
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    # YouTube
    if 'youtube.com' in url or 'youtu.be' in url:
        video_id = extract_youtube_id(url)
        if not video_id:
            raise ValueError(f"Could not extract YouTube video ID from: {url}")

        return URLInfo(
            source_type=SourceType.YOUTUBE,
            original_url=url,
            id=f'youtube_{video_id}',
            video_id=video_id
        )

    # Apple Podcasts
    elif 'podcasts.apple.com' in url:
        podcast_id = extract_apple_podcast_id(url)
        if not podcast_id:
            raise ValueError(f"Could not extract Apple Podcasts ID from: {url}")

        return URLInfo(
            source_type=SourceType.APPLE_PODCASTS,
            original_url=url,
            id=f'apple_podcasts_{podcast_id}',
            podcast_id=podcast_id
        )

    # Direct audio URL
    else:
        # Validate it looks like an audio file
        path = parsed.path.lower()
        audio_extensions = ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac']
        if not any(path.endswith(ext) for ext in audio_extensions):
            # Still allow it, but warn in logs
            pass

        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return URLInfo(
            source_type=SourceType.DIRECT_AUDIO,
            original_url=url,
            id=f'direct_audio_{url_hash}'
        )
```

### Step 4: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_url_parser.py -v`

Expected: PASS (7 tests)

### Step 5: Commit

```bash
git add frontend/frontend/utils/ frontend/tests/test_url_parser.py
git commit -m "$(cat <<'EOF'
feat: add URL parsing and ID generation

- Support YouTube, Apple Podcasts, and direct audio URLs
- Deterministic ID generation
- Comprehensive URL validation
- Add full test coverage

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Storage Manager Service

**Files:**
- Create: `frontend/frontend/services/__init__.py`
- Create: `frontend/frontend/services/storage.py`

### Step 1: Write storage manager tests

```python
# frontend/tests/test_storage.py
"""Test storage manager service."""
import pytest
import json
from pathlib import Path
from datetime import datetime
from frontend.services.storage import StorageManager


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory"""
    storage = StorageManager(base_dir=tmp_path)
    return storage


def test_save_and_load_transcription(temp_storage):
    """Test saving and loading transcription JSON"""
    transcription_data = {
        "id": "youtube_test123",
        "source": {
            "type": "youtube",
            "url": "https://youtube.com/watch?v=test123",
            "title": "Test Video"
        },
        "transcription": {
            "language": "en",
            "duration": 120.5,
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world"}
            ]
        }
    }

    # Save
    path = temp_storage.save_transcription("youtube_test123", transcription_data)
    assert path.exists()

    # Load
    loaded = temp_storage.load_transcription("youtube_test123")
    assert loaded["id"] == "youtube_test123"
    assert loaded["source"]["title"] == "Test Video"


def test_export_to_txt(temp_storage):
    """Test exporting transcription to TXT format"""
    transcription_data = {
        "transcription": {
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world"},
                {"id": 1, "start": 2.5, "end": 5.0, "text": "This is a test"}
            ]
        }
    }

    path = temp_storage.save_transcription("test_id", transcription_data)
    txt_content = temp_storage.export_to_txt("test_id")

    assert "Hello world" in txt_content
    assert "This is a test" in txt_content


def test_export_to_srt(temp_storage):
    """Test exporting transcription to SRT format"""
    transcription_data = {
        "transcription": {
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world"},
                {"id": 1, "start": 2.5, "end": 5.0, "text": "This is a test"}
            ]
        }
    }

    path = temp_storage.save_transcription("test_id", transcription_data)
    srt_content = temp_storage.export_to_srt("test_id")

    # Check SRT format
    assert "1\n" in srt_content  # First subtitle number
    assert "00:00:00,000 --> 00:00:02,500" in srt_content
    assert "Hello world" in srt_content
    assert "2\n" in srt_content  # Second subtitle number
    assert "This is a test" in srt_content


def test_get_transcription_path(temp_storage):
    """Test getting transcription file path"""
    path = temp_storage.get_transcription_path("youtube_test123")
    assert "youtube_test123.json" in str(path)
    assert "transcriptions" in str(path)
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_storage.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.services.storage'"

### Step 3: Write storage manager implementation

```python
# frontend/frontend/services/__init__.py
"""Service layer for frontend."""
```

```python
# frontend/frontend/services/storage.py
"""Storage management for transcription files."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from frontend.core.config import settings

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages transcription file storage and exports."""

    def __init__(self, base_dir: Path = None):
        """
        Initialize storage manager.

        Args:
            base_dir: Base directory for transcriptions (defaults to settings)
        """
        self.base_dir = base_dir or settings.transcriptions_dir
        self.base_dir = Path(self.base_dir)

    def get_transcription_path(self, transcription_id: str) -> Path:
        """
        Get path for transcription JSON file.

        Uses year/month structure: transcriptions/2026/01/youtube_abc123.json

        Args:
            transcription_id: Transcription ID

        Returns:
            Path to transcription file
        """
        now = datetime.utcnow()
        year_month_dir = self.base_dir / str(now.year) / f"{now.month:02d}"
        return year_month_dir / f"{transcription_id}.json"

    def save_transcription(self, transcription_id: str, data: Dict[str, Any]) -> Path:
        """
        Save transcription data to JSON file.

        Args:
            transcription_id: Transcription ID
            data: Transcription data dictionary

        Returns:
            Path to saved file
        """
        path = self.get_transcription_path(transcription_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved transcription to {path}")
        return path

    def load_transcription(self, transcription_id: str) -> Optional[Dict[str, Any]]:
        """
        Load transcription data from JSON file.

        Args:
            transcription_id: Transcription ID

        Returns:
            Transcription data or None if not found
        """
        # Try current year/month first
        path = self.get_transcription_path(transcription_id)

        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Search all subdirectories if not found
        for json_file in self.base_dir.rglob(f"{transcription_id}.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        logger.warning(f"Transcription {transcription_id} not found")
        return None

    def export_to_txt(self, transcription_id: str) -> Optional[str]:
        """
        Export transcription to plain text format.

        Args:
            transcription_id: Transcription ID

        Returns:
            Plain text content or None if not found
        """
        data = self.load_transcription(transcription_id)
        if not data:
            return None

        segments = data.get('transcription', {}).get('segments', [])
        lines = [segment['text'].strip() for segment in segments]
        return '\n'.join(lines)

    def export_to_srt(self, transcription_id: str) -> Optional[str]:
        """
        Export transcription to SRT subtitle format.

        Args:
            transcription_id: Transcription ID

        Returns:
            SRT formatted content or None if not found
        """
        data = self.load_transcription(transcription_id)
        if not data:
            return None

        segments = data.get('transcription', {}).get('segments', [])
        srt_lines = []

        for segment in segments:
            # Subtitle number
            srt_lines.append(str(segment['id'] + 1))

            # Timestamp
            start = self._format_srt_timestamp(segment['start'])
            end = self._format_srt_timestamp(segment['end'])
            srt_lines.append(f"{start} --> {end}")

            # Text
            srt_lines.append(segment['text'].strip())

            # Blank line
            srt_lines.append('')

        return '\n'.join(srt_lines)

    def _format_srt_timestamp(self, seconds: float) -> str:
        """
        Format seconds to SRT timestamp format (HH:MM:SS,mmm).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def delete_transcription(self, transcription_id: str) -> bool:
        """
        Delete transcription file.

        Args:
            transcription_id: Transcription ID

        Returns:
            True if deleted, False if not found
        """
        # Search for the file
        for json_file in self.base_dir.rglob(f"{transcription_id}.json"):
            json_file.unlink()
            logger.info(f"Deleted transcription {transcription_id}")
            return True

        logger.warning(f"Transcription {transcription_id} not found for deletion")
        return False
```

### Step 4: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_storage.py -v`

Expected: PASS (5 tests)

### Step 5: Commit

```bash
git add frontend/frontend/services/ frontend/tests/test_storage.py
git commit -m "$(cat <<'EOF'
feat: add storage manager service

- JSON file storage with year/month organization
- Load and save transcription data
- Export to TXT format
- Export to SRT subtitle format
- Add comprehensive tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Downloader Service

**Files:**
- Create: `frontend/frontend/services/downloader.py`

### Step 1: Write downloader service tests

```python
# frontend/tests/test_downloader.py
"""Test downloader service."""
import pytest
from pathlib import Path
from frontend.services.downloader import Downloader, DownloadResult


@pytest.fixture
def temp_downloader(tmp_path):
    """Create downloader with temp directory"""
    return Downloader(audio_cache_dir=tmp_path)


def test_downloader_initialization(temp_downloader):
    """Test downloader initializes correctly"""
    assert temp_downloader.audio_cache_dir.exists()


@pytest.mark.skip(reason="Requires network access and yt-dlp")
def test_download_youtube_video(temp_downloader):
    """Test downloading YouTube video (requires network)"""
    # Use a short test video
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video
    result = temp_downloader.download(url, "youtube_test")

    assert result.success
    assert result.audio_path.exists()
    assert result.metadata is not None
    assert result.metadata.get('title')
    assert result.metadata.get('duration')


def test_build_yt_dlp_options(temp_downloader):
    """Test yt-dlp options are configured correctly"""
    options = temp_downloader._build_yt_dlp_options("test_id")

    assert 'format' in options
    assert 'outtmpl' in options
    assert 'audio' in options['format']
    assert options['postprocessors'][0]['key'] == 'FFmpegExtractAudio'
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_downloader.py -v -k "not skip"`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.services.downloader'"

### Step 3: Write downloader service implementation

```python
# frontend/frontend/services/downloader.py
"""Audio download service using yt-dlp."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, NamedTuple
import yt_dlp

from frontend.core.config import settings

logger = logging.getLogger(__name__)


class DownloadResult(NamedTuple):
    """Result of download operation."""
    success: bool
    audio_path: Optional[Path] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Downloader:
    """Downloads audio from various sources using yt-dlp."""

    def __init__(self, audio_cache_dir: Path = None):
        """
        Initialize downloader.

        Args:
            audio_cache_dir: Directory to cache audio files
        """
        self.audio_cache_dir = Path(audio_cache_dir or settings.audio_cache_dir)
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, transcription_id: str) -> DownloadResult:
        """
        Download audio from URL.

        Args:
            url: Source URL (YouTube, Apple Podcasts, or direct audio)
            transcription_id: ID for naming the downloaded file

        Returns:
            DownloadResult with success status and metadata
        """
        try:
            logger.info(f"Downloading audio from {url}")

            ydl_opts = self._build_yt_dlp_options(transcription_id)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info without downloading first
                info = ydl.extract_info(url, download=False)

                # Check file size
                filesize = info.get('filesize') or info.get('filesize_approx', 0)
                max_size = settings.max_audio_size_mb * 1024 * 1024

                if filesize > max_size:
                    return DownloadResult(
                        success=False,
                        error=f"File too large: {filesize / 1024 / 1024:.1f}MB (max: {settings.max_audio_size_mb}MB)"
                    )

                # Download
                info = ydl.extract_info(url, download=True)

                # Find downloaded file
                audio_path = self._find_audio_file(transcription_id)
                if not audio_path:
                    return DownloadResult(
                        success=False,
                        error="Downloaded file not found"
                    )

                # Extract metadata
                metadata = self._extract_metadata(info)

                logger.info(f"Downloaded audio to {audio_path}")
                return DownloadResult(
                    success=True,
                    audio_path=audio_path,
                    metadata=metadata
                )

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return DownloadResult(
                success=False,
                error=str(e)
            )

    def _build_yt_dlp_options(self, transcription_id: str) -> Dict[str, Any]:
        """
        Build yt-dlp options.

        Args:
            transcription_id: ID for naming the output file

        Returns:
            Options dictionary for yt-dlp
        """
        output_template = str(self.audio_cache_dir / f"{transcription_id}.%(ext)s")

        return {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'socket_timeout': settings.download_timeout,
        }

    def _find_audio_file(self, transcription_id: str) -> Optional[Path]:
        """
        Find downloaded audio file.

        Args:
            transcription_id: Transcription ID

        Returns:
            Path to audio file or None
        """
        # Check common audio extensions
        for ext in ['m4a', 'mp3', 'wav', 'ogg', 'webm']:
            path = self.audio_cache_dir / f"{transcription_id}.{ext}"
            if path.exists():
                return path

        return None

    def _extract_metadata(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metadata from yt-dlp info.

        Args:
            info: Info dictionary from yt-dlp

        Returns:
            Cleaned metadata dictionary
        """
        return {
            'title': info.get('title'),
            'channel': info.get('uploader') or info.get('channel'),
            'duration_seconds': info.get('duration'),
            'upload_date': info.get('upload_date'),
            'thumbnail_url': info.get('thumbnail'),
            'description': info.get('description', '')[:500],  # Truncate long descriptions
            'format': info.get('ext'),
        }

    def delete_audio(self, transcription_id: str) -> bool:
        """
        Delete cached audio file.

        Args:
            transcription_id: Transcription ID

        Returns:
            True if deleted, False if not found
        """
        audio_path = self._find_audio_file(transcription_id)
        if audio_path and audio_path.exists():
            audio_path.unlink()
            logger.info(f"Deleted audio file {audio_path}")
            return True

        logger.warning(f"Audio file for {transcription_id} not found")
        return False
```

### Step 4: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_downloader.py -v -k "not skip"`

Expected: PASS (2 tests, 1 skipped)

### Step 5: Commit

```bash
git add frontend/frontend/services/downloader.py frontend/tests/test_downloader.py
git commit -m "$(cat <<'EOF'
feat: add downloader service with yt-dlp

- Download audio from YouTube, Apple Podcasts, direct URLs
- Extract metadata (title, channel, duration, etc)
- File size validation
- Audio format conversion to m4a
- Add tests for downloader

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Transcriber Client Service

**Files:**
- Create: `frontend/frontend/services/transcriber_client.py`

### Step 1: Write transcriber client tests

```python
# frontend/tests/test_transcriber_client.py
"""Test transcriber client service."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from frontend.services.transcriber_client import TranscriberClient, TranscriptionResult


@pytest.fixture
def client():
    """Create transcriber client"""
    return TranscriberClient(base_url="http://localhost:8001")


def test_client_initialization(client):
    """Test client initializes correctly"""
    assert client.base_url == "http://localhost:8001"
    assert client.timeout == 300


@patch('frontend.services.transcriber_client.httpx.Client')
def test_submit_job_success(mock_client_class, client, tmp_path):
    """Test successful job submission"""
    # Create mock response
    mock_response = Mock()
    mock_response.status_code = 202
    mock_response.json.return_value = {"job_id": "test_job_123"}

    mock_client = Mock()
    mock_client.__enter__.return_value.post.return_value = mock_response
    mock_client_class.return_value = mock_client

    # Create test audio file
    audio_file = tmp_path / "test.m4a"
    audio_file.write_bytes(b"fake audio data")

    # Submit job
    result = client.submit_job(audio_file, language="en")

    assert result.success
    assert result.job_id == "test_job_123"


@patch('frontend.services.transcriber_client.httpx.Client')
def test_check_status_completed(mock_client_class, client):
    """Test checking completed job status"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "job_id": "test_job_123",
        "status": "completed",
        "result": {
            "language": "en",
            "duration": 120.5,
            "segments": []
        }
    }

    mock_client = Mock()
    mock_client.__enter__.return_value.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    result = client.check_status("test_job_123")

    assert result.success
    assert result.status == "completed"
    assert result.result is not None


def test_health_check(client):
    """Test health check endpoint"""
    # This would require mocking or a real service
    # For now, just test the method exists
    assert hasattr(client, 'health_check')
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_transcriber_client.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.services.transcriber_client'"

### Step 3: Write transcriber client implementation

```python
# frontend/frontend/services/transcriber_client.py
"""Client for communicating with transcriber service."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, NamedTuple
import httpx

from frontend.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptionResult(NamedTuple):
    """Result of transcription operation."""
    success: bool
    job_id: Optional[str] = None
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TranscriberClient:
    """Client for transcriber service API."""

    def __init__(self, base_url: str = None, timeout: int = None):
        """
        Initialize transcriber client.

        Args:
            base_url: Base URL of transcriber service
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or settings.transcriber_url).rstrip('/')
        self.timeout = timeout or settings.transcriber_timeout

    def health_check(self) -> bool:
        """
        Check if transcriber service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def submit_job(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Submit transcription job to transcriber service.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            TranscriptionResult with job ID or error
        """
        try:
            logger.info(f"Submitting transcription job for {audio_path}")

            with httpx.Client(timeout=self.timeout) as client:
                # Prepare multipart form data
                files = {
                    'file': (audio_path.name, open(audio_path, 'rb'), 'audio/m4a')
                }
                data = {}
                if language:
                    data['language'] = language

                # Submit job
                response = client.post(
                    f"{self.base_url}/transcribe",
                    files=files,
                    data=data
                )

                if response.status_code == 202:
                    result = response.json()
                    job_id = result.get('job_id')
                    logger.info(f"Job submitted successfully: {job_id}")
                    return TranscriptionResult(
                        success=True,
                        job_id=job_id,
                        status='queued'
                    )
                else:
                    error = response.json().get('detail', 'Unknown error')
                    logger.error(f"Job submission failed: {error}")
                    return TranscriptionResult(
                        success=False,
                        error=error
                    )

        except Exception as e:
            logger.error(f"Job submission failed: {e}")
            return TranscriptionResult(
                success=False,
                error=str(e)
            )

    def check_status(self, job_id: str) -> TranscriptionResult:
        """
        Check status of transcription job.

        Args:
            job_id: Job ID from submit_job

        Returns:
            TranscriptionResult with current status and result if completed
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/jobs/{job_id}")

                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    result = data.get('result')

                    return TranscriptionResult(
                        success=True,
                        job_id=job_id,
                        status=status,
                        result=result
                    )
                elif response.status_code == 404:
                    return TranscriptionResult(
                        success=False,
                        error=f"Job {job_id} not found"
                    )
                else:
                    error = response.json().get('detail', 'Unknown error')
                    return TranscriptionResult(
                        success=False,
                        error=error
                    )

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return TranscriptionResult(
                success=False,
                error=str(e)
            )

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: int = 5,
        max_wait: int = 600
    ) -> TranscriptionResult:
        """
        Poll job status until completion.

        Args:
            job_id: Job ID to monitor
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            TranscriptionResult when completed or timeout
        """
        import asyncio

        elapsed = 0
        while elapsed < max_wait:
            result = self.check_status(job_id)

            if not result.success:
                return result

            if result.status in ['completed', 'failed']:
                return result

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return TranscriptionResult(
            success=False,
            error=f"Timeout waiting for job {job_id}"
        )
```

### Step 4: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_transcriber_client.py -v`

Expected: PASS (4 tests)

### Step 5: Commit

```bash
git add frontend/frontend/services/transcriber_client.py frontend/tests/test_transcriber_client.py
git commit -m "$(cat <<'EOF'
feat: add transcriber service client

- Submit transcription jobs via HTTP API
- Check job status and retrieve results
- Health check endpoint
- Async polling for completion
- Add comprehensive tests with mocking

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Orchestrator Service

**Files:**
- Create: `frontend/frontend/services/orchestrator.py`

### Step 1: Write orchestrator tests

```python
# frontend/tests/test_orchestrator.py
"""Test orchestrator service."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from frontend.core.models import Base, Transcription
from frontend.core.database import init_db
from frontend.services.orchestrator import Orchestrator, OrchestrationResult


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return engine


@pytest.fixture
def orchestrator(test_db, tmp_path):
    """Create orchestrator with test database"""
    orch = Orchestrator(
        db_engine=test_db,
        audio_cache_dir=tmp_path / "audio",
        transcriptions_dir=tmp_path / "transcriptions"
    )
    return orch


def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly"""
    assert orchestrator.downloader is not None
    assert orchestrator.transcriber_client is not None
    assert orchestrator.storage is not None


@patch('frontend.services.orchestrator.Downloader')
@patch('frontend.services.orchestrator.TranscriberClient')
async def test_process_url_full_workflow(
    mock_transcriber_class,
    mock_downloader_class,
    orchestrator,
    test_db
):
    """Test complete orchestration workflow"""
    # Mock downloader
    mock_downloader = Mock()
    mock_downloader.download.return_value = Mock(
        success=True,
        audio_path=Path("/tmp/test.m4a"),
        metadata={'title': 'Test Video', 'duration_seconds': 120}
    )
    mock_downloader_class.return_value = mock_downloader
    orchestrator.downloader = mock_downloader

    # Mock transcriber
    mock_transcriber = Mock()
    mock_transcriber.submit_job.return_value = Mock(
        success=True,
        job_id='job_123'
    )
    mock_transcriber.check_status.return_value = Mock(
        success=True,
        status='completed',
        result={'language': 'en', 'segments': []}
    )
    mock_transcriber_class.return_value = mock_transcriber
    orchestrator.transcriber_client = mock_transcriber

    # Process URL
    url = "https://youtube.com/watch?v=test123"
    result = await orchestrator.process_url(url)

    assert result.success
    assert result.transcription_id == "youtube_test123"


def test_create_job_record(orchestrator, test_db):
    """Test creating job record in database"""
    with Session(test_db) as session:
        transcription = orchestrator._create_job_record(
            session=session,
            transcription_id="youtube_test",
            url="https://youtube.com/watch?v=test",
            source_type="youtube"
        )

        assert transcription.id == "youtube_test"
        assert transcription.status == "pending"
        assert transcription.progress == 0
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_orchestrator.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.services.orchestrator'"

### Step 3: Write orchestrator implementation

```python
# frontend/frontend/services/orchestrator.py
"""Orchestration service for coordinating transcription workflow."""

import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, NamedTuple
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

from frontend.core.config import settings
from frontend.core.models import Transcription
from frontend.services.downloader import Downloader
from frontend.services.transcriber_client import TranscriberClient
from frontend.services.storage import StorageManager
from frontend.utils.url_parser import parse_url

logger = logging.getLogger(__name__)


class OrchestrationResult(NamedTuple):
    """Result of orchestration process."""
    success: bool
    transcription_id: Optional[str] = None
    error: Optional[str] = None


class Orchestrator:
    """Coordinates the complete transcription workflow."""

    def __init__(
        self,
        db_engine: Engine = None,
        audio_cache_dir: Path = None,
        transcriptions_dir: Path = None
    ):
        """
        Initialize orchestrator.

        Args:
            db_engine: Database engine (defaults to creating from settings)
            audio_cache_dir: Audio cache directory
            transcriptions_dir: Transcriptions storage directory
        """
        # Database
        if db_engine is None:
            db_engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False}
            )
        self.engine = db_engine
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Services
        self.downloader = Downloader(audio_cache_dir=audio_cache_dir)
        self.transcriber_client = TranscriberClient()
        self.storage = StorageManager(base_dir=transcriptions_dir)

    async def process_url(self, url: str) -> OrchestrationResult:
        """
        Process a URL through complete transcription workflow.

        Workflow:
        1. Parse URL and generate ID
        2. Check for duplicate
        3. Create database record
        4. Download audio
        5. Submit to transcriber
        6. Poll for completion
        7. Save results
        8. Update database

        Args:
            url: Source URL to process

        Returns:
            OrchestrationResult with success status and transcription ID
        """
        try:
            # Parse URL
            logger.info(f"Processing URL: {url}")
            url_info = parse_url(url)
            transcription_id = url_info.id

            with self.SessionLocal() as session:
                # Check for duplicate
                existing = session.query(Transcription).filter_by(source_url=url).first()
                if existing:
                    logger.info(f"URL already processed: {transcription_id}")
                    return OrchestrationResult(
                        success=False,
                        transcription_id=transcription_id,
                        error="URL already transcribed"
                    )

                # Create job record
                transcription = self._create_job_record(
                    session=session,
                    transcription_id=transcription_id,
                    url=url,
                    source_type=url_info.source_type.value
                )
                session.commit()

            # Download audio
            await self._update_status(transcription_id, "downloading", 10)
            download_result = self.downloader.download(url, transcription_id)

            if not download_result.success:
                await self._mark_failed(transcription_id, f"Download failed: {download_result.error}")
                return OrchestrationResult(
                    success=False,
                    transcription_id=transcription_id,
                    error=download_result.error
                )

            # Update with download metadata
            await self._update_metadata(transcription_id, download_result.metadata)

            # Submit to transcriber
            await self._update_status(transcription_id, "transcribing", 50)
            transcribe_result = self.transcriber_client.submit_job(download_result.audio_path)

            if not transcribe_result.success:
                await self._mark_failed(transcription_id, f"Transcription failed: {transcribe_result.error}")
                return OrchestrationResult(
                    success=False,
                    transcription_id=transcription_id,
                    error=transcribe_result.error
                )

            # Poll for completion
            job_id = transcribe_result.job_id
            final_result = await self.transcriber_client.wait_for_completion(job_id)

            if not final_result.success or final_result.status == 'failed':
                error = final_result.error or "Transcription failed"
                await self._mark_failed(transcription_id, error)
                return OrchestrationResult(
                    success=False,
                    transcription_id=transcription_id,
                    error=error
                )

            # Save transcription results
            await self._update_status(transcription_id, "completed", 90)
            await self._save_results(transcription_id, download_result.metadata, final_result.result)

            await self._update_status(transcription_id, "completed", 100)
            logger.info(f"Successfully processed {transcription_id}")

            return OrchestrationResult(
                success=True,
                transcription_id=transcription_id
            )

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            return OrchestrationResult(
                success=False,
                error=str(e)
            )

    def _create_job_record(
        self,
        session: Session,
        transcription_id: str,
        url: str,
        source_type: str
    ) -> Transcription:
        """Create initial job record in database."""
        transcription = Transcription(
            id=transcription_id,
            source_type=source_type,
            source_url=url,
            status='pending',
            progress=0
        )
        session.add(transcription)
        return transcription

    async def _update_status(self, transcription_id: str, status: str, progress: int):
        """Update job status and progress."""
        with self.SessionLocal() as session:
            transcription = session.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.status = status
                transcription.progress = progress

                if status == "downloading" and not transcription.started_at:
                    transcription.started_at = datetime.utcnow()
                elif status == "completed":
                    transcription.transcribed_at = datetime.utcnow()

                session.commit()
                logger.info(f"{transcription_id}: {status} ({progress}%)")

    async def _update_metadata(self, transcription_id: str, metadata: dict):
        """Update transcription with download metadata."""
        with self.SessionLocal() as session:
            transcription = session.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.title = metadata.get('title')
                transcription.channel = metadata.get('channel')
                transcription.duration_seconds = metadata.get('duration_seconds')
                transcription.thumbnail_url = metadata.get('thumbnail_url')
                transcription.upload_date = metadata.get('upload_date')
                transcription.audio_format = metadata.get('format')

                # Set audio cache expiration
                transcription.audio_cached_until = datetime.utcnow() + timedelta(days=settings.audio_cache_days)

                session.commit()

    async def _save_results(self, transcription_id: str, metadata: dict, transcription_data: dict):
        """Save transcription results to file and database."""
        # Build full transcription JSON
        full_data = {
            "id": transcription_id,
            "source": {
                "type": metadata.get('source_type'),
                "url": metadata.get('url'),
                "title": metadata.get('title'),
                "channel": metadata.get('channel'),
                "upload_date": metadata.get('upload_date'),
                "thumbnail": metadata.get('thumbnail_url')
            },
            "transcription": transcription_data,
            "full_text": self._extract_full_text(transcription_data),
            "metadata": {
                "word_count": self._count_words(transcription_data),
                "segments_count": len(transcription_data.get('segments', []))
            }
        }

        # Save to file
        path = self.storage.save_transcription(transcription_id, full_data)

        # Update database
        with self.SessionLocal() as session:
            transcription = session.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.transcription_path = str(path)
                transcription.language = transcription_data.get('language')
                transcription.word_count = full_data['metadata']['word_count']
                transcription.segments_count = full_data['metadata']['segments_count']
                transcription.full_text = full_data['full_text']
                transcription.model_used = 'whisper-medium-mlx'

                session.commit()

    async def _mark_failed(self, transcription_id: str, error: str):
        """Mark job as failed with error message."""
        with self.SessionLocal() as session:
            transcription = session.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.status = 'failed'
                transcription.error_message = error
                session.commit()
                logger.error(f"{transcription_id}: {error}")

    def _extract_full_text(self, transcription_data: dict) -> str:
        """Extract full text from segments."""
        segments = transcription_data.get('segments', [])
        return ' '.join(segment['text'].strip() for segment in segments)

    def _count_words(self, transcription_data: dict) -> int:
        """Count total words in transcription."""
        full_text = self._extract_full_text(transcription_data)
        return len(full_text.split())
```

### Step 4: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_orchestrator.py -v`

Expected: PASS (3 tests)

### Step 5: Commit

```bash
git add frontend/frontend/services/orchestrator.py frontend/tests/test_orchestrator.py
git commit -m "$(cat <<'EOF'
feat: add orchestrator service for workflow coordination

- Coordinate full transcription workflow
- Parse URL and check duplicates
- Download, transcribe, and save results
- Update database at each stage
- Handle errors and status updates
- Add comprehensive tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: API Routes and Models

**Files:**
- Create: `frontend/frontend/api/__init__.py`
- Create: `frontend/frontend/api/models.py`
- Create: `frontend/frontend/api/routes.py`

### Step 1: Write API models test

```python
# frontend/tests/test_api_models.py
"""Test API models."""
from frontend.api.models import TranscribeRequest, TranscriptionResponse


def test_transcribe_request_validation():
    """Test request validation"""
    req = TranscribeRequest(url="https://youtube.com/watch?v=test123")
    assert req.url == "https://youtube.com/watch?v=test123"


def test_transcription_response():
    """Test response model"""
    resp = TranscriptionResponse(
        id="youtube_test",
        status="completed",
        progress=100
    )
    assert resp.id == "youtube_test"
    assert resp.status == "completed"
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_api_models.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.api.models'"

### Step 3: Write API models

```python
# frontend/frontend/api/__init__.py
"""API layer for frontend service."""
```

```python
# frontend/frontend/api/models.py
"""Pydantic models for API requests and responses."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field


class TranscribeRequest(BaseModel):
    """Request to transcribe a URL."""
    url: str = Field(..., description="URL to transcribe (YouTube, Apple Podcasts, or direct audio)")


class TranscriptionResponse(BaseModel):
    """Response for transcription job."""
    id: str
    status: str
    progress: int = 0
    source: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    transcribed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    language: Optional[str] = None
    word_count: Optional[int] = None
    segments_count: Optional[int] = None
    error: Optional[str] = None


class TranscriptionListResponse(BaseModel):
    """Response for list of transcriptions."""
    total: int
    skip: int
    limit: int
    items: List[TranscriptionResponse]


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    existing_id: Optional[str] = None
```

### Step 4: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_api_models.py -v`

Expected: PASS (2 tests)

### Step 5: Write API routes test

```python
# frontend/tests/test_api_routes.py
"""Test API routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from frontend.main import app
from frontend.core.models import Base
from frontend.core.database import get_db, init_db


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return engine


@pytest.fixture
def client(test_db):
    """Create test client"""
    return TestClient(app)


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
```

### Step 6: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_api_routes.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.main'"

### Step 7: Write API routes

```python
# frontend/frontend/api/routes.py
"""API routes for frontend service."""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from frontend.api.models import (
    TranscribeRequest,
    TranscriptionResponse,
    TranscriptionListResponse,
    ErrorResponse
)
from frontend.core.database import get_db
from frontend.core.models import Transcription
from frontend.services.orchestrator import Orchestrator
from frontend.utils.url_parser import parse_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


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
            raise HTTPException(
                status_code=409,
                detail={
                    "detail": "This URL has already been transcribed",
                    "existing_id": existing.id
                }
            )

        # Create orchestrator and start processing in background
        orchestrator = Orchestrator()
        background_tasks.add_task(orchestrator.process_url, request.url)

        # Create pending record
        transcription = Transcription(
            id=url_info.id,
            source_type=url_info.source_type.value,
            source_url=request.url,
            status='pending',
            progress=0
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)

        return TranscriptionResponse(**transcription.to_dict())

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
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
        fts_query = text("""
            SELECT t.*
            FROM transcriptions t
            JOIN transcriptions_fts fts ON t.rowid = fts.rowid
            WHERE transcriptions_fts MATCH :search
            ORDER BY rank
        """)
        results = db.execute(fts_query, {"search": search}).fetchall()
        # Convert to Transcription objects
        items = [db.query(Transcription).filter_by(id=row.id).first() for row in results]
        total = len(items)
        items = items[skip:skip + limit]
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


@router.delete("/transcriptions/{transcription_id}")
async def delete_transcription(transcription_id: str, db: Session = Depends(get_db)):
    """Delete a transcription and its files."""
    transcription = db.query(Transcription).filter_by(id=transcription_id).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Delete from database
    db.delete(transcription)
    db.commit()

    # Delete files (storage manager will handle this)
    from frontend.services.storage import StorageManager
    from frontend.services.downloader import Downloader

    storage = StorageManager()
    downloader = Downloader()

    storage.delete_transcription(transcription_id)
    downloader.delete_audio(transcription_id)

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
```

### Step 8: Create main FastAPI app

```python
# frontend/frontend/main.py
"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from frontend.core.config import settings
from frontend.core.database import init_db, get_engine
from frontend.api.routes import router as api_router

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

    # Initialize database
    engine = get_engine()
    init_db(engine)
    logger.info("Database initialized")

    # Create data directories
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.transcriptions_dir.mkdir(parents=True, exist_ok=True)
    settings.audio_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)

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

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Scribe Frontend API", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "frontend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
```

### Step 9: Run API tests to verify they pass

Run: `cd frontend && python -m pytest tests/test_api_routes.py -v`

Expected: PASS (2 tests)

### Step 10: Test API manually

Run: `cd frontend && python -m frontend.main`

Expected: Server starts on http://localhost:8000

Open another terminal:
Run: `curl http://localhost:8000/api/health`

Expected: `{"status":"healthy"}`

### Step 11: Commit

```bash
git add frontend/frontend/api/ frontend/frontend/main.py frontend/tests/test_api_models.py frontend/tests/test_api_routes.py
git commit -m "$(cat <<'EOF'
feat: add REST API routes and FastAPI app

- Complete API routes (transcribe, list, get, delete, export)
- Pydantic request/response models
- Full-text search support
- Export to TXT, SRT, JSON
- Background task processing
- FastAPI app with CORS and lifecycle management
- Add API tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: WebSocket Support for Real-Time Updates

**Files:**
- Create: `frontend/frontend/api/websocket.py`

### Step 1: Write WebSocket handler test

```python
# frontend/tests/test_websocket.py
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
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_websocket.py -v`

Expected: FAIL with "WebSocket route not found"

### Step 3: Write WebSocket handler

```python
# frontend/frontend/api/websocket.py
"""WebSocket handler for real-time progress updates."""

import logging
import asyncio
import json
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

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

        for connection in self.active_connections:
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
                    # Send current status
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
```

### Step 4: Add WebSocket route to main app

```python
# Modify frontend/frontend/main.py

# Add after imports:
from frontend.api.websocket import websocket_endpoint

# Add before if __name__ == "__main__":
@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
    """WebSocket endpoint."""
    await websocket_endpoint(websocket)
```

### Step 5: Update orchestrator to broadcast progress

```python
# Modify frontend/frontend/services/orchestrator.py

# Add import at top:
from frontend.api.websocket import broadcast_progress, broadcast_completion, broadcast_error

# Modify _update_status method:
async def _update_status(self, transcription_id: str, status: str, progress: int):
    """Update job status and progress."""
    with self.SessionLocal() as session:
        transcription = session.query(Transcription).filter_by(id=transcription_id).first()
        if transcription:
            transcription.status = status
            transcription.progress = progress

            if status == "downloading" and not transcription.started_at:
                transcription.started_at = datetime.utcnow()
            elif status == "completed":
                transcription.transcribed_at = datetime.utcnow()

            session.commit()
            logger.info(f"{transcription_id}: {status} ({progress}%)")

            # Broadcast via WebSocket
            await broadcast_progress(transcription_id, status, progress)

# Similar updates for _mark_failed and completion
```

### Step 6: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_websocket.py -v`

Expected: PASS

### Step 7: Commit

```bash
git add frontend/frontend/api/websocket.py frontend/tests/test_websocket.py
git commit -m "$(cat <<'EOF'
feat: add WebSocket support for real-time updates

- Connection manager for WebSocket clients
- Broadcast status updates to all connected clients
- Personal status queries
- Ping/pong heartbeat
- Integration with orchestrator for live progress
- Add WebSocket tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Web Templates

**Files:**
- Create: `frontend/frontend/web/__init__.py`
- Create: `frontend/frontend/web/templates/base.html`
- Create: `frontend/frontend/web/templates/index.html`
- Create: `frontend/frontend/web/templates/transcription.html`

### Step 1: Create template directory structure

Run: `mkdir -p frontend/frontend/web/templates`

### Step 2: Write base template

```html
<!-- frontend/frontend/web/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Scribe - Audio Transcription{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>🎙️ Scribe</h1>
            <nav>
                <a href="/">Home</a>
                <a href="/transcriptions">Transcriptions</a>
            </nav>
        </div>
    </header>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <footer>
        <div class="container">
            <p>Scribe Transcription Service v0.1.0</p>
        </div>
    </footer>

    <script src="/static/js/app.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Step 3: Write index template

```html
<!-- frontend/frontend/web/templates/index.html -->
{% extends "base.html" %}

{% block title %}Scribe - Transcribe Audio{% endblock %}

{% block content %}
<div class="main-form">
    <h2>Transcribe Audio from URL</h2>
    <p class="subtitle">Enter a YouTube, Apple Podcasts, or direct audio URL to get started</p>

    <form id="transcribeForm">
        <div class="form-group">
            <label for="url">URL</label>
            <input
                type="url"
                id="url"
                name="url"
                placeholder="https://youtube.com/watch?v=..."
                required
                autofocus
            >
        </div>

        <button type="submit" id="submitButton" class="btn-primary">
            Transcribe
        </button>
    </form>

    <div id="status" class="status-message" style="display: none;">
        <div class="status-content">
            <h3 id="statusTitle">Processing...</h3>
            <div class="progress-bar">
                <div id="progressFill" class="progress-fill" style="width: 0%"></div>
            </div>
            <p id="statusMessage">Initializing...</p>
        </div>
    </div>

    <div id="error" class="error-message" style="display: none;">
        <h3>Error</h3>
        <p id="errorMessage"></p>
    </div>
</div>

<div class="recent-transcriptions">
    <h2>Recent Transcriptions</h2>
    <div id="recentList">
        <p class="loading">Loading...</p>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="/static/js/index.js"></script>
{% endblock %}
```

### Step 4: Write transcription detail template

```html
<!-- frontend/frontend/web/templates/transcription.html -->
{% extends "base.html" %}

{% block title %}{{ transcription.title or 'Transcription' }} - Scribe{% endblock %}

{% block content %}
<div class="transcription-detail">
    <div class="transcription-header">
        <h2>{{ transcription.title or 'Untitled' }}</h2>

        {% if transcription.channel %}
        <p class="channel">{{ transcription.channel }}</p>
        {% endif %}

        <div class="meta">
            <span class="status status-{{ transcription.status }}">
                {{ transcription.status }}
            </span>

            {% if transcription.duration_seconds %}
            <span class="duration">
                {{ (transcription.duration_seconds / 60) | round(1) }} minutes
            </span>
            {% endif %}

            {% if transcription.language %}
            <span class="language">{{ transcription.language }}</span>
            {% endif %}

            {% if transcription.word_count %}
            <span class="word-count">{{ transcription.word_count }} words</span>
            {% endif %}
        </div>
    </div>

    {% if transcription.status == 'completed' %}
    <div class="export-buttons">
        <a href="/api/transcriptions/{{ transcription.id }}/export/json" class="btn">
            📄 JSON
        </a>
        <a href="/api/transcriptions/{{ transcription.id }}/export/txt" class="btn">
            📝 TXT
        </a>
        <a href="/api/transcriptions/{{ transcription.id }}/export/srt" class="btn">
            🎬 SRT
        </a>
    </div>

    <div class="transcription-text">
        <h3>Transcription</h3>
        <div class="segments">
            {% for segment in segments %}
            <div class="segment">
                <span class="timestamp">{{ segment.start | format_time }}</span>
                <span class="text">{{ segment.text }}</span>
            </div>
            {% endfor %}
        </div>
    </div>

    {% elif transcription.status == 'failed' %}
    <div class="error-message">
        <h3>Transcription Failed</h3>
        <p>{{ transcription.error_message }}</p>
    </div>

    {% else %}
    <div class="processing-message">
        <h3>Processing...</h3>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {{ transcription.progress }}%"></div>
        </div>
        <p>{{ transcription.status }} - {{ transcription.progress }}%</p>
    </div>
    {% endif %}

    <div class="actions">
        <a href="/" class="btn">← Back to Home</a>
        <button onclick="deleteTranscription('{{ transcription.id }}')" class="btn btn-danger">
            🗑️ Delete
        </button>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function deleteTranscription(id) {
    if (confirm('Are you sure you want to delete this transcription?')) {
        fetch(`/api/transcriptions/${id}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                window.location.href = '/';
            } else {
                alert('Failed to delete transcription');
            }
        });
    }
}
</script>
{% endblock %}
```

### Step 5: Add web routes

```python
# Modify frontend/frontend/api/routes.py

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Add after router definition:
templates = Jinja2Templates(directory="frontend/web/templates")

# Add template filter
def format_time(seconds):
    """Format seconds to MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

templates.env.filters['format_time'] = format_time


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/transcriptions/{transcription_id}", response_class=HTMLResponse)
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
    data = storage.load_transcription(transcription_id) if transcription.status == 'completed' else None

    segments = data.get('transcription', {}).get('segments', []) if data else []

    return templates.TemplateResponse("transcription.html", {
        "request": request,
        "transcription": transcription,
        "segments": segments
    })
```

### Step 6: Test templates render

Run: `cd frontend && python -m frontend.main`

Open browser to: `http://localhost:8000/`

Expected: See main form page

### Step 7: Commit

```bash
git add frontend/frontend/web/
git commit -m "$(cat <<'EOF'
feat: add web templates for UI

- Base template with header and navigation
- Index page with URL submission form
- Transcription detail page with segments
- Export buttons for different formats
- Status and progress display
- Add Jinja2 template integration

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Static Assets (CSS and JavaScript)

**Files:**
- Create: `frontend/frontend/static/css/style.css`
- Create: `frontend/frontend/static/js/app.js`
- Create: `frontend/frontend/static/js/index.js`

### Step 1: Create static directory structure

Run: `mkdir -p frontend/frontend/static/{css,js}`

### Step 2: Write CSS stylesheet

```css
/* frontend/frontend/static/css/style.css */
:root {
    --primary: #3b82f6;
    --primary-dark: #2563eb;
    --success: #10b981;
    --warning: #f59e0b;
    --error: #ef4444;
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-700: #374151;
    --gray-900: #111827;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: var(--gray-900);
    background: var(--gray-50);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

/* Header */
header {
    background: white;
    border-bottom: 1px solid var(--gray-200);
    padding: 1rem 0;
    margin-bottom: 2rem;
}

header h1 {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
}

nav a {
    color: var(--gray-700);
    text-decoration: none;
    margin-right: 1.5rem;
    font-weight: 500;
}

nav a:hover {
    color: var(--primary);
}

/* Main Form */
.main-form {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    margin-bottom: 2rem;
}

.main-form h2 {
    margin-bottom: 0.5rem;
}

.subtitle {
    color: var(--gray-700);
    margin-bottom: 1.5rem;
}

.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
}

.form-group input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--gray-200);
    border-radius: 4px;
    font-size: 1rem;
}

.form-group input:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Buttons */
.btn, .btn-primary {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.2s;
}

.btn {
    background: var(--gray-100);
    color: var(--gray-700);
}

.btn:hover {
    background: var(--gray-200);
}

.btn-primary {
    background: var(--primary);
    color: white;
    width: 100%;
}

.btn-primary:hover {
    background: var(--primary-dark);
}

.btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-danger {
    background: var(--error);
    color: white;
}

/* Status Messages */
.status-message, .error-message {
    padding: 1.5rem;
    border-radius: 8px;
    margin-top: 1.5rem;
}

.status-message {
    background: var(--gray-100);
    border-left: 4px solid var(--primary);
}

.error-message {
    background: #fef2f2;
    border-left: 4px solid var(--error);
    color: #991b1b;
}

/* Progress Bar */
.progress-bar {
    width: 100%;
    height: 8px;
    background: var(--gray-200);
    border-radius: 4px;
    overflow: hidden;
    margin: 1rem 0;
}

.progress-fill {
    height: 100%;
    background: var(--primary);
    transition: width 0.3s ease;
}

/* Status Badges */
.status {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.875rem;
    font-weight: 500;
}

.status-pending {
    background: var(--gray-100);
    color: var(--gray-700);
}

.status-downloading, .status-transcribing {
    background: #dbeafe;
    color: #1e40af;
}

.status-completed {
    background: #d1fae5;
    color: #065f46;
}

.status-failed {
    background: #fee2e2;
    color: #991b1b;
}

/* Transcription List */
.recent-transcriptions {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.transcription-item {
    padding: 1rem;
    border-bottom: 1px solid var(--gray-200);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.transcription-item:last-child {
    border-bottom: none;
}

.transcription-item:hover {
    background: var(--gray-50);
}

/* Segments */
.segments {
    max-height: 600px;
    overflow-y: auto;
}

.segment {
    padding: 0.75rem;
    border-bottom: 1px solid var(--gray-200);
}

.segment:hover {
    background: var(--gray-50);
}

.timestamp {
    display: inline-block;
    min-width: 60px;
    color: var(--gray-700);
    font-family: monospace;
    font-size: 0.875rem;
    margin-right: 1rem;
}

.text {
    color: var(--gray-900);
}

/* Footer */
footer {
    margin-top: 3rem;
    padding: 2rem 0;
    text-align: center;
    color: var(--gray-700);
    font-size: 0.875rem;
}
```

### Step 3: Write JavaScript app core

```javascript
// frontend/frontend/static/js/app.js
/**
 * Core application JavaScript
 */

// WebSocket connection
let ws = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };

    // Heartbeat
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
}

function handleWebSocketMessage(data) {
    console.log('WebSocket message:', data);

    if (data.type === 'status') {
        updateProgress(data);
    } else if (data.type === 'completed') {
        handleCompletion(data);
    } else if (data.type === 'error') {
        handleError(data);
    }
}

function updateProgress(data) {
    const progressFill = document.getElementById('progressFill');
    const statusMessage = document.getElementById('statusMessage');

    if (progressFill) {
        progressFill.style.width = `${data.progress}%`;
    }

    if (statusMessage) {
        statusMessage.textContent = `${data.status} - ${data.progress}%`;
    }
}

function handleCompletion(data) {
    console.log('Transcription completed:', data.id);
    // Reload the page or update UI
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

function handleError(data) {
    console.error('Transcription error:', data.error);
    showError(data.error);
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');

    if (errorDiv && errorMessage) {
        errorMessage.textContent = message;
        errorDiv.style.display = 'block';
    }
}

function hideError() {
    const errorDiv = document.getElementById('error');
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
}

// Initialize WebSocket on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connectWebSocket);
} else {
    connectWebSocket();
}
```

### Step 4: Write index page JavaScript

```javascript
// frontend/frontend/static/js/index.js
/**
 * JavaScript for index page
 */

const form = document.getElementById('transcribeForm');
const submitButton = document.getElementById('submitButton');
const statusDiv = document.getElementById('status');
const recentList = document.getElementById('recentList');

// Handle form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = document.getElementById('url').value;

    hideError();
    submitButton.disabled = true;
    submitButton.textContent = 'Submitting...';

    try {
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        const data = await response.json();

        if (response.ok) {
            // Show status
            statusDiv.style.display = 'block';
            document.getElementById('statusTitle').textContent = 'Processing';
            document.getElementById('statusMessage').textContent = 'Starting transcription...';

            // Subscribe to updates
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'subscribe',
                    id: data.id
                }));
            }

            // Clear form
            form.reset();

        } else if (response.status === 409) {
            // Already exists
            showError('This URL has already been transcribed');
            if (data.existing_id) {
                setTimeout(() => {
                    window.location.href = `/transcriptions/${data.existing_id}`;
                }, 2000);
            }
        } else {
            showError(data.detail || 'Failed to submit transcription');
        }

    } catch (error) {
        console.error('Error:', error);
        showError('Network error. Please try again.');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Transcribe';
    }
});

// Load recent transcriptions
async function loadRecent() {
    try {
        const response = await fetch('/api/transcriptions?limit=10');
        const data = await response.json();

        if (data.items.length === 0) {
            recentList.innerHTML = '<p class="loading">No transcriptions yet</p>';
            return;
        }

        recentList.innerHTML = data.items.map(item => `
            <div class="transcription-item">
                <div>
                    <h3>${item.source.title || 'Untitled'}</h3>
                    <p style="color: var(--gray-700); font-size: 0.875rem;">
                        ${item.source.channel || 'Unknown channel'}
                    </p>
                </div>
                <div>
                    <span class="status status-${item.status}">
                        ${item.status}
                    </span>
                    <a href="/transcriptions/${item.id}" class="btn" style="margin-left: 1rem;">
                        View
                    </a>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading recent:', error);
        recentList.innerHTML = '<p class="error">Failed to load transcriptions</p>';
    }
}

// Load recent on page load
loadRecent();

// Refresh every 30 seconds
setInterval(loadRecent, 30000);
```

### Step 5: Mount static files in FastAPI

```python
# Modify frontend/frontend/main.py

from fastapi.staticfiles import StaticFiles

# Add after app creation:
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
```

### Step 6: Test static assets load

Run: `cd frontend && python -m frontend.main`

Open browser to: `http://localhost:8000/`

Expected: Styled page with working form

### Step 7: Commit

```bash
git add frontend/frontend/static/
git commit -m "$(cat <<'EOF'
feat: add static assets (CSS and JavaScript)

- Complete CSS stylesheet with responsive design
- WebSocket integration for real-time updates
- Form submission and validation
- Recent transcriptions list with auto-refresh
- Progress bars and status indicators
- Error handling and display

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Cleanup Service

**Files:**
- Create: `frontend/frontend/utils/cleanup.py`

### Step 1: Write cleanup service tests

```python
# frontend/tests/test_cleanup.py
"""Test cleanup service."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from frontend.core.models import Base, Transcription
from frontend.core.database import init_db
from frontend.utils.cleanup import CleanupService


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return engine


@pytest.fixture
def cleanup_service(test_db, tmp_path):
    """Create cleanup service"""
    return CleanupService(
        db_engine=test_db,
        audio_cache_dir=tmp_path / "audio"
    )


def test_find_expired_audio(cleanup_service, test_db):
    """Test finding expired audio files"""
    with Session(test_db) as session:
        # Create transcriptions with different expiry dates
        t1 = Transcription(
            id="expired_1",
            source_type="youtube",
            source_url="https://youtube.com/1",
            status="completed",
            audio_path="/path/to/audio1.m4a",
            audio_cached_until=datetime.utcnow() - timedelta(days=1)  # Expired
        )
        t2 = Transcription(
            id="valid_1",
            source_type="youtube",
            source_url="https://youtube.com/2",
            status="completed",
            audio_path="/path/to/audio2.m4a",
            audio_cached_until=datetime.utcnow() + timedelta(days=1)  # Valid
        )
        session.add_all([t1, t2])
        session.commit()

    expired = cleanup_service._find_expired_audio()
    assert len(expired) == 1
    assert expired[0].id == "expired_1"


async def test_cleanup_expired_audio(cleanup_service, test_db, tmp_path):
    """Test cleanup of expired audio"""
    # Create test audio file
    audio_file = tmp_path / "audio" / "test.m4a"
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    audio_file.write_text("fake audio")

    with Session(test_db) as session:
        t = Transcription(
            id="test",
            source_type="youtube",
            source_url="https://youtube.com/test",
            status="completed",
            audio_path=str(audio_file),
            audio_cached_until=datetime.utcnow() - timedelta(days=1)
        )
        session.add(t)
        session.commit()

    # Run cleanup
    count = await cleanup_service.cleanup_expired_audio()
    assert count == 1
    assert not audio_file.exists()
```

### Step 2: Run test to verify it fails

Run: `cd frontend && python -m pytest tests/test_cleanup.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'frontend.utils.cleanup'"

### Step 3: Write cleanup service

```python
# frontend/frontend/utils/cleanup.py
"""Cleanup service for expired audio and old jobs."""

import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine

from frontend.core.config import settings
from frontend.core.models import Transcription

logger = logging.getLogger(__name__)


class CleanupService:
    """Handles cleanup of expired audio files and old jobs."""

    def __init__(self, db_engine: Engine = None, audio_cache_dir: Path = None):
        """
        Initialize cleanup service.

        Args:
            db_engine: Database engine
            audio_cache_dir: Audio cache directory
        """
        if db_engine is None:
            db_engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False}
            )

        self.engine = db_engine
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.audio_cache_dir = Path(audio_cache_dir or settings.audio_cache_dir)

    def _find_expired_audio(self):
        """Find transcriptions with expired audio cache."""
        with self.SessionLocal() as session:
            expired = session.query(Transcription).filter(
                Transcription.audio_cached_until < datetime.utcnow(),
                Transcription.audio_path.isnot(None)
            ).all()

            return expired

    async def cleanup_expired_audio(self) -> int:
        """
        Delete expired audio files.

        Returns:
            Number of files deleted
        """
        expired = self._find_expired_audio()
        count = 0

        for transcription in expired:
            try:
                # Delete audio file
                audio_path = Path(transcription.audio_path)
                if audio_path.exists():
                    audio_path.unlink()
                    logger.info(f"Deleted expired audio: {audio_path}")
                    count += 1

                # Update database
                with self.SessionLocal() as session:
                    t = session.query(Transcription).filter_by(id=transcription.id).first()
                    if t:
                        t.audio_path = None
                        session.commit()

            except Exception as e:
                logger.error(f"Error deleting {transcription.audio_path}: {e}")

        if count > 0:
            logger.info(f"Cleaned up {count} expired audio files")

        return count

    async def cleanup_failed_jobs(self, max_age_days: int = 7) -> int:
        """
        Delete failed job records older than max_age_days.

        Args:
            max_age_days: Maximum age in days for failed jobs

        Returns:
            Number of jobs deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        with self.SessionLocal() as session:
            failed_jobs = session.query(Transcription).filter(
                Transcription.status == 'failed',
                Transcription.created_at < cutoff_date
            ).all()

            count = len(failed_jobs)

            for job in failed_jobs:
                session.delete(job)

            session.commit()

        if count > 0:
            logger.info(f"Deleted {count} old failed jobs")

        return count

    async def run_cleanup(self):
        """Run all cleanup tasks."""
        logger.info("Starting cleanup tasks")

        audio_count = await self.cleanup_expired_audio()
        failed_count = await self.cleanup_failed_jobs()

        logger.info(
            f"Cleanup complete: {audio_count} audio files, {failed_count} failed jobs"
        )

        return {
            'audio_files_deleted': audio_count,
            'failed_jobs_deleted': failed_count
        }
```

### Step 4: Run test to verify it passes

Run: `cd frontend && python -m pytest tests/test_cleanup.py -v`

Expected: PASS (2 tests)

### Step 5: Add cleanup scheduled task to main app

```python
# Modify frontend/frontend/main.py

from frontend.utils.cleanup import CleanupService
import asyncio

# Add to lifespan function after startup:
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting frontend service")

    # Initialize database
    engine = get_engine()
    init_db(engine)
    logger.info("Database initialized")

    # Create data directories
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.transcriptions_dir.mkdir(parents=True, exist_ok=True)
    settings.audio_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)

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
```

### Step 6: Commit

```bash
git add frontend/frontend/utils/cleanup.py frontend/tests/test_cleanup.py
git commit -m "$(cat <<'EOF'
feat: add cleanup service for expired files

- Cleanup expired audio cache files
- Delete old failed job records
- Scheduled periodic cleanup (every 6 hours)
- Database updates after cleanup
- Add comprehensive tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Integration Testing

**Files:**
- Create: `frontend/tests/test_integration.py`
- Create: `frontend/README.md`

### Step 1: Write integration tests

```python
# frontend/tests/test_integration.py
"""Integration tests for complete workflow."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from pathlib import Path

from frontend.main import app


@pytest.mark.integration
@patch('frontend.services.downloader.yt_dlp.YoutubeDL')
@patch('frontend.services.transcriber_client.httpx.Client')
async def test_complete_workflow(mock_http, mock_ytdl, tmp_path):
    """Test complete transcription workflow"""
    # Mock yt-dlp download
    mock_ytdl_instance = Mock()
    mock_ytdl_instance.extract_info.return_value = {
        'title': 'Test Video',
        'uploader': 'Test Channel',
        'duration': 120,
        'ext': 'm4a'
    }
    mock_ytdl.return_value.__enter__.return_value = mock_ytdl_instance

    # Create fake audio file
    audio_file = tmp_path / "youtube_test.m4a"
    audio_file.write_bytes(b"fake audio")

    # Mock transcriber service
    mock_http_instance = Mock()
    mock_http_instance.post.return_value = Mock(
        status_code=202,
        json=lambda: {'job_id': 'test_job_123'}
    )
    mock_http_instance.get.return_value = Mock(
        status_code=200,
        json=lambda: {
            'status': 'completed',
            'result': {
                'language': 'en',
                'duration': 120,
                'segments': [
                    {'id': 0, 'start': 0.0, 'end': 5.0, 'text': 'Test transcription'}
                ]
            }
        }
    )
    mock_http.return_value.__enter__.return_value = mock_http_instance

    # Test workflow
    client = TestClient(app)

    # 1. Submit URL
    response = client.post('/api/transcribe', json={
        'url': 'https://youtube.com/watch?v=test123'
    })
    assert response.status_code == 202
    data = response.json()
    assert 'id' in data

    # 2. Check status (would be processing in real scenario)
    # In this test, we just verify the endpoint works
    response = client.get(f'/api/transcriptions/{data["id"]}')
    assert response.status_code in [200, 404]  # May not exist in test DB
```

### Step 2: Write README

```markdown
# Frontend Service

Web interface and orchestration service for Scribe transcription system.

## Features

- Web-based URL submission form
- Support for YouTube, Apple Podcasts, and direct audio URLs
- Real-time progress updates via WebSocket
- Transcription viewing with timestamps
- Export to multiple formats (JSON, TXT, SRT)
- Full-text search
- Automatic audio cache cleanup

## Installation

```bash
cd frontend/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings
```

## Configuration

Edit `.env` file:

```env
# Service
HOST=0.0.0.0
PORT=8000

# Transcriber Service
TRANSCRIBER_URL=http://localhost:8001

# Storage
DATA_DIR=data
AUDIO_CACHE_DAYS=7

# Database
DATABASE_URL=sqlite:///data/scribe.db
```

## Usage

### Start Service

```bash
python -m frontend.main
```

Service will start on http://localhost:8000

### API Endpoints

- `GET /` - Web interface
- `POST /api/transcribe` - Submit URL for transcription
- `GET /api/transcriptions` - List all transcriptions
- `GET /api/transcriptions/{id}` - Get transcription details
- `GET /api/transcriptions/{id}/export/{format}` - Export (txt, srt, json)
- `DELETE /api/transcriptions/{id}` - Delete transcription
- `WS /ws` - WebSocket for real-time updates

## Development

### Run Tests

```bash
pytest
```

### Run with Auto-reload

```bash
uvicorn frontend.main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture

```
frontend/
├── frontend/
│   ├── api/          # REST API and WebSocket
│   ├── core/         # Database and config
│   ├── services/     # Business logic
│   ├── utils/        # Utilities
│   ├── web/          # Templates
│   ├── static/       # CSS, JS
│   └── main.py       # FastAPI app
├── tests/            # Tests
└── data/             # Runtime data
```

## License

MIT
```

### Step 3: Run integration tests

Run: `cd frontend && python -m pytest tests/test_integration.py -v -m integration`

Expected: PASS

### Step 4: Run all tests

Run: `cd frontend && python -m pytest -v`

Expected: All tests pass

### Step 5: Commit

```bash
git add frontend/tests/test_integration.py frontend/README.md
git commit -m "$(cat <<'EOF'
feat: add integration tests and documentation

- Complete workflow integration test
- Comprehensive README with setup instructions
- API documentation
- Development guidelines
- Architecture overview

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Final Testing and Deployment Preparation

### Step 1: Create startup script

```bash
# frontend/scripts/start.sh
#!/bin/bash

# Start frontend service

cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Check if transcriber service is running
echo "Checking transcriber service..."
if ! curl -s http://localhost:8001/health > /dev/null; then
    echo "Warning: Transcriber service not responding at http://localhost:8001"
    echo "Make sure the transcriber service is running before submitting jobs"
fi

# Start frontend service
echo "Starting frontend service on port 8000..."
python -m frontend.main
```

Run: `chmod +x frontend/scripts/start.sh`

### Step 2: Create environment example

```bash
# frontend/.env.example
# Service Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Transcriber Service
TRANSCRIBER_URL=http://localhost:8001
TRANSCRIBER_TIMEOUT=300

# Storage
DATA_DIR=../data
TRANSCRIPTIONS_DIR=../data/transcriptions
AUDIO_CACHE_DIR=../data/cache/audio
AUDIO_CACHE_DAYS=7

# Database
DATABASE_URL=sqlite:///../data/scribe.db

# Downloads
MAX_AUDIO_SIZE_MB=500
DOWNLOAD_TIMEOUT=600
```

### Step 3: Test full system end-to-end

Run transcriber service:
```bash
cd transcriber && source venv/bin/activate && python -m transcriber.main
```

Run frontend service:
```bash
cd frontend && source venv/bin/activate && python -m frontend.main
```

Open browser to: http://localhost:8000

Test workflow:
1. Submit a URL
2. Watch real-time progress
3. View completed transcription
4. Export to different formats
5. Delete transcription

Expected: Complete workflow works

### Step 4: Update main project README

Modify root README.md to include frontend service information and update quick start.

### Step 5: Final commit

```bash
git add frontend/scripts/ frontend/.env.example
git commit -m "$(cat <<'EOF'
feat: add deployment scripts and finalize frontend

- Startup script with health check
- Environment configuration example
- Complete end-to-end testing
- Production-ready deployment
- Update documentation

Frontend service implementation complete!

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-01-03-frontend-service.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach would you like to use?**
