# Development Guide

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Testing](#testing)
5. [Code Style](#code-style)
6. [Adding Features](#adding-features)
7. [Debugging](#debugging)

---

## Development Setup

### Initial Setup

```bash
# Clone repository
git clone <repo-url> scribe
cd scribe

# Set up pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install

# Set up both services
cd transcriber && python -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt
cd ../frontend && python -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt
```

### Development Dependencies

**transcriber/requirements-dev.txt:**
```txt
# Production dependencies
-r requirements.txt

# Development dependencies
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
ipython>=8.14.0
```

**frontend/requirements-dev.txt:**
```txt
# Production dependencies
-r requirements.txt

# Development dependencies
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.24.0  # For testing FastAPI
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
ipython>=8.14.0
alembic>=1.11.0  # For future database migrations
```

---

## Project Structure

```
scribe/
├── README.md
├── .gitignore
├── .pre-commit-config.yaml
│
├── transcriber/                 # Transcription service
│   ├── README.md
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── setup.py
│   ├── pytest.ini
│   ├── .env.example
│   │
│   ├── transcriber/            # Main package
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app entry
│   │   │
│   │   ├── api/               # API layer
│   │   │   ├── __init__.py
│   │   │   ├── routes.py      # Endpoints
│   │   │   └── models.py      # Pydantic schemas
│   │   │
│   │   ├── core/              # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── config.py      # Configuration
│   │   │   ├── whisper.py     # Whisper wrapper
│   │   │   └── queue.py       # Job queue
│   │   │
│   │   └── utils/             # Utilities
│   │       ├── __init__.py
│   │       └── audio.py
│   │
│   ├── scripts/               # Helper scripts
│   │   ├── start.sh
│   │   └── download_models.py
│   │
│   └── tests/                 # Tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_api.py
│       └── test_whisper.py
│
├── frontend/                   # Frontend service
│   ├── README.md
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── setup.py
│   ├── pytest.ini
│   ├── .env.example
│   │
│   ├── frontend/              # Main package
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app entry
│   │   │
│   │   ├── api/              # API layer
│   │   │   ├── __init__.py
│   │   │   ├── routes.py     # Endpoints
│   │   │   ├── models.py     # Pydantic schemas
│   │   │   └── websocket.py  # WebSocket handlers
│   │   │
│   │   ├── web/              # Web interface
│   │   │   ├── __init__.py
│   │   │   └── templates/
│   │   │       ├── base.html
│   │   │       ├── index.html
│   │   │       └── transcription.html
│   │   │
│   │   ├── core/             # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── config.py     # Configuration
│   │   │   ├── database.py   # Database setup
│   │   │   └── models.py     # SQLAlchemy models
│   │   │
│   │   ├── services/         # Business services
│   │   │   ├── __init__.py
│   │   │   ├── downloader.py
│   │   │   ├── transcriber_client.py
│   │   │   ├── storage.py
│   │   │   └── orchestrator.py
│   │   │
│   │   └── utils/            # Utilities
│   │       ├── __init__.py
│   │       ├── cleanup.py
│   │       └── url_parser.py
│   │
│   ├── static/               # Static assets
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js
│   │
│   ├── scripts/              # Helper scripts
│   │   └── start.sh
│   │
│   └── tests/                # Tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_api.py
│       ├── test_downloader.py
│       ├── test_orchestrator.py
│       └── test_storage.py
│
├── data/                      # Data directory (gitignored)
│   ├── transcriptions/
│   ├── cache/
│   ├── logs/
│   └── scribe.db
│
└── docs/                      # Documentation
    ├── ARCHITECTURE.md
    ├── API.md
    ├── DATABASE.md
    ├── SETUP.md
    └── DEVELOPMENT.md
```

---

## Development Workflow

### Running in Development Mode

**Option 1: Manual (Two Terminals)**

```bash
# Terminal 1 - Transcriber
cd transcriber/
source venv/bin/activate
export LOG_LEVEL=DEBUG
python -m transcriber.main --reload

# Terminal 2 - Frontend
cd frontend/
source venv/bin/activate
export LOG_LEVEL=DEBUG
python -m frontend.main --reload
```

**Option 2: Using Scripts**

```bash
# Create dev launch script
cat > dev.sh << 'EOF'
#!/bin/bash
trap 'kill 0' EXIT  # Kill all processes on exit

cd transcriber && source venv/bin/activate && LOG_LEVEL=DEBUG python -m transcriber.main --reload &
cd frontend && source venv/bin/activate && LOG_LEVEL=DEBUG python -m frontend.main --reload &

wait
EOF

chmod +x dev.sh
./dev.sh
```

**Option 3: Using docker-compose (Frontend only)**

```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "8000:8000"
    volumes:
      - ./frontend:/app
      - ./data:/app/data
    environment:
      - TRANSCRIBER_URL=http://host.docker.internal:8001
      - LOG_LEVEL=DEBUG
```

---

### Code Formatting

```bash
# Format code with black
cd transcriber/
black transcriber/ tests/

cd ../frontend/
black frontend/ tests/

# Check code style
flake8 transcriber/ tests/
flake8 frontend/ tests/

# Type checking
mypy transcriber/
mypy frontend/
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/add-podcast-support

# Make changes
# ... edit files ...

# Format and lint
black .
flake8 .

# Run tests
pytest

# Commit
git add .
git commit -m "Add podcast RSS feed support"

# Push
git push origin feature/add-podcast-support

# Create pull request on GitHub
```

---

## Testing

### Running Tests

```bash
# Run all tests
cd transcriber/
pytest

cd ../frontend/
pytest

# Run with coverage
pytest --cov=transcriber --cov-report=html
pytest --cov=frontend --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::test_health_endpoint

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x
```

### Writing Tests

**Test structure (transcriber/tests/test_api.py):**

```python
import pytest
from fastapi.testclient import TestClient
from transcriber.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check returns 200"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]

@pytest.mark.asyncio
async def test_transcribe_endpoint():
    """Test transcription submission"""
    with open("tests/fixtures/test_audio.mp3", "rb") as f:
        files = {"file": ("test.mp3", f, "audio/mpeg")}
        response = client.post("/transcribe", files=files)

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
```

**Fixtures (tests/conftest.py):**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from frontend.core.database import Base
from frontend.core.models import Transcription

@pytest.fixture(scope="function")
def test_db():
    """Create a test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def sample_transcription(test_db):
    """Create a sample transcription for testing"""
    trans = Transcription(
        id="test_123",
        source_url="https://youtube.com/watch?v=test123",
        source_type="youtube",
        status="completed"
    )
    test_db.add(trans)
    test_db.commit()
    return trans
```

### Integration Tests

```python
# tests/test_integration.py
import pytest
from httpx import AsyncClient
from frontend.main import app as frontend_app
from transcriber.main import app as transcriber_app

@pytest.mark.asyncio
async def test_end_to_end_transcription():
    """Test full workflow from URL to transcription"""
    # This test requires both services running
    async with AsyncClient(app=frontend_app, base_url="http://test") as client:
        # Submit URL
        response = await client.post(
            "/api/transcribe",
            json={"url": "https://example.com/test.mp3"}
        )
        assert response.status_code == 202
        job_id = response.json()["id"]

        # Poll for completion (with timeout)
        import asyncio
        for _ in range(30):  # 30 seconds max
            response = await client.get(f"/api/transcriptions/{job_id}")
            status = response.json()["status"]
            if status in ["completed", "failed"]:
                break
            await asyncio.sleep(1)

        assert status == "completed"
```

---

## Code Style

### Python Style Guide

Follow [PEP 8](https://pep8.org/) with these additions:

- **Line length**: 100 characters (not 79)
- **Quotes**: Double quotes for strings
- **Imports**: Sort with `isort`
- **Docstrings**: Google style

```python
def function_name(param1: str, param2: int) -> dict:
    """Short description of function.

    Longer description if needed, explaining what the function
    does in more detail.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Dictionary containing the result

    Raises:
        ValueError: If param2 is negative
    """
    if param2 < 0:
        raise ValueError("param2 must be positive")

    return {"result": param1 * param2}
```

### Type Hints

Use type hints everywhere:

```python
from typing import Optional, List, Dict
from pydantic import BaseModel

class TranscriptionRequest(BaseModel):
    url: str
    model: Optional[str] = "medium"

def process_transcription(
    job_id: str,
    audio_path: str,
    model: str = "medium"
) -> Dict[str, any]:
    # Implementation
    pass
```

### Error Handling

```python
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def risky_operation():
    try:
        # Attempt operation
        result = perform_task()
    except SpecificException as e:
        logger.error(f"Task failed: {e}")
        raise HTTPException(status_code=500, detail="Task failed")
    except Exception as e:
        logger.exception("Unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")
    else:
        return result
```

---

## Adding Features

### Adding a New Download Source

1. **Update URL parser** (`frontend/utils/url_parser.py`):

```python
def parse_url(url: str) -> dict:
    """Parse URL and extract source type and ID"""
    if "spotify.com" in url:
        return {
            "type": "spotify",
            "id": extract_spotify_id(url),
            "url": url
        }
    # ... existing parsers
```

2. **Add downloader** (`frontend/services/downloader.py`):

```python
async def download_spotify(url: str, output_path: str) -> dict:
    """Download audio from Spotify"""
    # Implementation
    pass
```

3. **Update configuration** (`.env.example`):

```bash
SUPPORTED_SOURCES=youtube,apple_podcasts,direct_audio,spotify
```

4. **Add tests** (`tests/test_downloader.py`):

```python
def test_spotify_download():
    result = download_spotify("https://open.spotify.com/episode/...")
    assert result["status"] == "success"
```

---

### Adding a New Export Format

1. **Add export function** (`frontend/services/storage.py`):

```python
def export_to_vtt(transcription: dict) -> str:
    """Export transcription as WebVTT subtitle format"""
    vtt = "WEBVTT\n\n"
    for seg in transcription["segments"]:
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        vtt += f"{start} --> {end}\n{seg['text']}\n\n"
    return vtt
```

2. **Add API endpoint** (`frontend/api/routes.py`):

```python
@app.get("/api/transcriptions/{id}/export/vtt")
async def export_vtt(id: str):
    # Load transcription
    # Export to VTT
    # Return file
```

3. **Update UI** (`templates/transcription.html`):

```html
<a href="/api/transcriptions/{{id}}/export/vtt">Download VTT</a>
```

---

## Debugging

### Debug Mode

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Or in .env
LOG_LEVEL=DEBUG
```

### Using Python Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()

# Remote debugging with debugpy
import debugpy
debugpy.listen(5678)
print("Waiting for debugger...")
debugpy.wait_for_client()
```

### Debugging FastAPI

```python
# Enable FastAPI debug mode
from fastapi import FastAPI

app = FastAPI(debug=True)

# See detailed error traces in responses
```

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use logging
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Exception with traceback")
```

### Testing API Endpoints

```bash
# Using curl
curl -X POST http://localhost:8000/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{"url":"https://youtube.com/watch?v=test"}'

# Using httpie (better formatting)
pip install httpie
http POST localhost:8000/api/transcribe url="https://youtube.com/watch?v=test"

# Interactive API docs
open http://localhost:8000/docs
open http://localhost:8001/docs
```

---

## Common Development Tasks

### Reset Database

```bash
# Backup first
cp data/scribe.db data/scribe.db.backup

# Delete database
rm data/scribe.db

# Restart frontend (will recreate)
python -m frontend.main
```

### Clear Cache

```bash
# Clear audio cache
rm -rf data/cache/audio/*

# Clear Whisper model cache
rm -rf ~/.cache/whisper
```

### Generate Migration

```bash
# Using Alembic (future)
cd frontend/
alembic revision --autogenerate -m "Add new column"
alembic upgrade head
```

### Profile Performance

```python
# Add timing decorator
import time
from functools import wraps

def timing(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        print(f"{f.__name__} took {end-start:.2f}s")
        return result
    return wrap

@timing
def slow_function():
    # ...
```

---

## Documentation

### Update API Docs

FastAPI auto-generates OpenAPI docs from docstrings:

```python
@app.post("/transcribe", response_model=TranscriptionResponse)
async def create_transcription(request: TranscriptionRequest):
    """
    Create a new transcription job

    Submit a URL for transcription. Supported sources:
    - YouTube videos
    - Apple Podcasts
    - Direct audio URLs (.mp3, .m4a)

    Returns a job ID for tracking progress.
    """
    # Implementation
```

### Update Documentation Files

When making significant changes, update relevant docs:
- `README.md` - Overview and quick start
- `docs/ARCHITECTURE.md` - System design
- `docs/API.md` - API changes
- `docs/DATABASE.md` - Schema changes
- `docs/SETUP.md` - Configuration
- `docs/DEVELOPMENT.md` - Development workflow

---

## Release Process

1. **Update version**
   - Update `transcriber/setup.py`
   - Update `frontend/setup.py`

2. **Update CHANGELOG.md**
   - Document new features
   - Document bug fixes
   - Document breaking changes

3. **Run full test suite**
   ```bash
   pytest transcriber/ frontend/
   ```

4. **Tag release**
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

5. **Create GitHub release**
   - Add release notes
   - Attach binaries if applicable

---

## Tips & Best Practices

### Performance

- Use async/await for I/O operations
- Cache frequently accessed data
- Use database indexes
- Profile before optimizing

### Security

- Validate all user input
- Sanitize URLs before downloading
- Use parameterized SQL queries
- Keep dependencies updated

### Code Quality

- Write tests first (TDD)
- Keep functions small and focused
- Use meaningful variable names
- Comment complex logic only
- Refactor regularly

### Git

- Commit early and often
- Write descriptive commit messages
- Keep commits atomic
- Rebase before merge (if team agrees)
