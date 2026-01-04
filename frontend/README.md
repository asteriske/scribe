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
