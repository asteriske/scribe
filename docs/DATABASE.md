# Database Schema

## Overview

Scribe uses SQLite for data persistence. The database stores metadata about transcription jobs, while the actual transcription content is stored as JSON files on the filesystem.

**Database Location:** `data/scribe.db`

**ORM:** SQLAlchemy

---

## Schema

### Table: `transcriptions`

Primary table for transcription job metadata.

```sql
CREATE TABLE transcriptions (
    -- Primary Key
    id TEXT PRIMARY KEY,                    -- e.g., 'youtube_abc123', 'podcast_xyz789'

    -- Source Information
    source_type TEXT NOT NULL,              -- 'youtube', 'apple_podcasts', 'direct_audio'
    source_url TEXT NOT NULL UNIQUE,        -- Original URL submitted
    title TEXT,                             -- Video/podcast title
    channel TEXT,                           -- Channel/creator name
    thumbnail_url TEXT,                     -- Thumbnail image URL
    upload_date TEXT,                       -- Original upload date (ISO 8601)

    -- Media Information
    duration_seconds INTEGER,               -- Audio duration in seconds
    file_size_bytes INTEGER,                -- Audio file size
    audio_format TEXT,                      -- 'm4a', 'mp3', 'wav', etc.

    -- File Paths
    audio_path TEXT,                        -- Path to cached audio file
    transcription_path TEXT,                -- Path to JSON transcription file

    -- Job Status
    status TEXT NOT NULL,                   -- 'pending', 'downloading', 'transcribing',
                                            -- 'completed', 'failed'
    progress INTEGER DEFAULT 0,             -- Progress percentage (0-100)

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,                   -- When processing started
    transcribed_at TIMESTAMP,               -- When transcription completed
    audio_cached_until TIMESTAMP,           -- When audio file should be deleted

    -- Transcription Metadata
    model_used TEXT,                        -- 'whisper-medium-mlx'
    language TEXT,                          -- 'en', 'es', 'fr', etc.
    word_count INTEGER,                     -- Total words in transcription
    segments_count INTEGER,                 -- Number of segments

    -- Error Handling
    error_message TEXT,                     -- Error details if failed
    retry_count INTEGER DEFAULT 0,          -- Number of retries attempted

    -- Search
    full_text TEXT                          -- Cached full text for searching
);
```

**Indexes:**

```sql
CREATE INDEX idx_status ON transcriptions(status);
CREATE INDEX idx_created_at ON transcriptions(created_at DESC);
CREATE INDEX idx_transcribed_at ON transcriptions(transcribed_at DESC);
CREATE INDEX idx_cached_until ON transcriptions(audio_cached_until);
CREATE INDEX idx_source_type ON transcriptions(source_type);
CREATE UNIQUE INDEX idx_source_url ON transcriptions(source_url);
```

---

### Virtual Table: `transcriptions_fts`

Full-text search index using SQLite FTS5.

```sql
CREATE VIRTUAL TABLE transcriptions_fts USING fts5(
    id UNINDEXED,           -- Link to transcriptions.id
    title,                  -- Searchable title
    channel,                -- Searchable channel name
    content,                -- Full transcription text
    content='transcriptions',
    content_rowid='rowid'
);
```

**Triggers to keep FTS in sync:**

```sql
-- Insert trigger
CREATE TRIGGER transcriptions_ai AFTER INSERT ON transcriptions BEGIN
  INSERT INTO transcriptions_fts(rowid, id, title, channel, content)
  VALUES (new.rowid, new.id, new.title, new.channel, new.full_text);
END;

-- Update trigger
CREATE TRIGGER transcriptions_au AFTER UPDATE ON transcriptions BEGIN
  UPDATE transcriptions_fts
  SET title = new.title,
      channel = new.channel,
      content = new.full_text
  WHERE rowid = new.rowid;
END;

-- Delete trigger
CREATE TRIGGER transcriptions_ad AFTER DELETE ON transcriptions BEGIN
  DELETE FROM transcriptions_fts WHERE rowid = old.rowid;
END;
```

---

## Data Models (SQLAlchemy)

### Python Model Definition

```python
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta

Base = declarative_base()

class Transcription(Base):
    __tablename__ = 'transcriptions'

    # Primary Key
    id = Column(String, primary_key=True)

    # Source Information
    source_type = Column(String, nullable=False)
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
        """Convert to dictionary for API responses"""
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
            'error': self.error_message
        }
```

---

## Status Lifecycle

```
pending
   │
   ├─→ downloading (progress 0-99)
   │      │
   │      ├─→ transcribing (progress 0-99)
   │      │      │
   │      │      └─→ completed (progress 100)
   │      │
   │      └─→ failed (with error_message)
   │
   └─→ failed (download failed, with error_message)
```

**Status Values:**

- `pending` - Job created, not started
- `downloading` - Audio being downloaded
- `transcribing` - Being processed by transcriber service
- `completed` - Successfully completed
- `failed` - Error occurred (see error_message)

---

## ID Generation

IDs are generated from the source URL to enable idempotency:

```python
def generate_id(source_url: str) -> str:
    """
    Generate deterministic ID from URL

    Examples:
    - youtube.com/watch?v=abc123 → 'youtube_abc123'
    - youtu.be/abc123 → 'youtube_abc123'
    - podcasts.apple.com/.../id123 → 'apple_podcasts_123'
    - example.com/audio.mp3 → 'direct_audio_<hash>'
    """
    if 'youtube.com' in source_url or 'youtu.be' in source_url:
        video_id = extract_youtube_id(source_url)
        return f'youtube_{video_id}'
    elif 'podcasts.apple.com' in source_url:
        podcast_id = extract_apple_podcast_id(source_url)
        return f'apple_podcasts_{podcast_id}'
    else:
        # For direct URLs, use hash
        url_hash = hashlib.md5(source_url.encode()).hexdigest()[:12]
        return f'direct_audio_{url_hash}'
```

---

## File System Structure

While metadata is in SQLite, the actual transcription content is stored as JSON files:

```
data/
├── scribe.db                                # SQLite database
├── transcriptions/
│   └── 2026/
│       └── 01/
│           ├── youtube_abc123.json         # Transcription JSON
│           ├── youtube_def456.json
│           └── apple_podcasts_xyz.json
└── cache/
    └── audio/
        ├── youtube_abc123.m4a              # Cached audio (temp)
        └── youtube_def456.m4a
```

**Why separate storage?**

- JSON files can be large (100KB - 10MB for long videos)
- SQLite has size limits and performance degrades with large BLOBs
- Files are easier to backup, process, and export
- Database stays small and fast for queries

---

## Transcription JSON Format

Each `{id}.json` file contains:

```json
{
  "id": "youtube_abc123",
  "source": {
    "type": "youtube",
    "url": "https://youtube.com/watch?v=abc123",
    "title": "Video Title",
    "channel": "Channel Name",
    "upload_date": "2024-01-15",
    "thumbnail": "https://i.ytimg.com/..."
  },
  "transcription": {
    "model": "whisper-medium-mlx",
    "language": "en",
    "duration": 212.5,
    "transcribed_at": "2026-01-02T10:30:00Z",
    "segments": [
      {
        "id": 0,
        "start": 0.0,
        "end": 3.5,
        "text": "Welcome to this video"
      },
      ...
    ]
  },
  "full_text": "Welcome to this video. In today's tutorial...",
  "metadata": {
    "word_count": 485,
    "segments_count": 42,
    "average_words_per_segment": 11.5
  }
}
```

This JSON is:
1. Saved to filesystem at `transcription_path`
2. Full text extracted and stored in `full_text` column for FTS
3. Metadata (word_count, segments_count) stored in database columns

---

## Common Queries

### List recent transcriptions

```python
from sqlalchemy.orm import Session

def get_recent_transcriptions(db: Session, limit: int = 50):
    return db.query(Transcription)\
        .filter(Transcription.status == 'completed')\
        .order_by(Transcription.transcribed_at.desc())\
        .limit(limit)\
        .all()
```

### Search transcriptions

```python
def search_transcriptions(db: Session, query: str, limit: int = 20):
    """Full-text search using FTS5"""
    sql = """
        SELECT t.*
        FROM transcriptions t
        JOIN transcriptions_fts fts ON t.rowid = fts.rowid
        WHERE transcriptions_fts MATCH :query
        ORDER BY rank
        LIMIT :limit
    """
    return db.execute(sql, {'query': query, 'limit': limit}).fetchall()
```

### Find jobs to cleanup

```python
def get_expired_audio(db: Session):
    """Find audio files that should be deleted"""
    return db.query(Transcription)\
        .filter(
            Transcription.audio_cached_until < datetime.utcnow(),
            Transcription.audio_path.isnot(None)
        )\
        .all()
```

### Check for duplicate URL

```python
def find_by_url(db: Session, url: str):
    """Check if URL has already been transcribed"""
    return db.query(Transcription)\
        .filter(Transcription.source_url == url)\
        .first()
```

---

## Database Migrations

**Current:** Manual schema creation on first run

**Future:** Alembic for migrations

**Initial setup:**

```python
from sqlalchemy import create_engine
from models import Base

engine = create_engine('sqlite:///data/scribe.db')
Base.metadata.create_all(engine)

# Create FTS table and triggers
with engine.connect() as conn:
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS transcriptions_fts
        USING fts5(id UNINDEXED, title, channel, content);
    """)
    # Create triggers...
```

---

## Backup & Recovery

### Backup

```bash
# Simple file copy (SQLite is single file)
cp data/scribe.db data/backups/scribe_$(date +%Y%m%d).db

# Or use SQLite backup command
sqlite3 data/scribe.db ".backup data/backups/scribe_backup.db"
```

### Recovery

```bash
# Restore from backup
cp data/backups/scribe_backup.db data/scribe.db

# Verify integrity
sqlite3 data/scribe.db "PRAGMA integrity_check;"

# Rebuild FTS index if needed
sqlite3 data/scribe.db "INSERT INTO transcriptions_fts(transcriptions_fts) VALUES('rebuild');"
```

---

## Performance Considerations

### Query Optimization

- All common query patterns have indexes
- FTS5 provides fast full-text search
- Status-based filtering is indexed
- Time-based queries use indexed timestamps

### Vacuum

```bash
# Periodic database optimization
sqlite3 data/scribe.db "VACUUM;"
```

### Connection Pooling

SQLAlchemy provides connection pooling by default:

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'sqlite:///data/scribe.db',
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10
)
```

---

## Constraints & Validation

### Application-Level Validation

- URL format validation before insert
- Status transitions enforced by business logic
- Progress must be 0-100
- Timestamps must be logical (started_at > created_at)

### Database-Level Constraints

- `id` is PRIMARY KEY (must be unique)
- `source_url` has UNIQUE constraint (prevents duplicates)
- `status` and `source_type` should be validated by application (SQLite doesn't support ENUMs)

---

## Future Schema Extensions

Potential additions for future features:

```sql
-- User management table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link transcriptions to users
ALTER TABLE transcriptions ADD COLUMN user_id INTEGER REFERENCES users(id);

-- Tags/categories
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE transcription_tags (
    transcription_id TEXT REFERENCES transcriptions(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (transcription_id, tag_id)
);

-- Analytics
CREATE TABLE transcription_analytics (
    transcription_id TEXT REFERENCES transcriptions(id),
    view_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    PRIMARY KEY (transcription_id)
);
```
