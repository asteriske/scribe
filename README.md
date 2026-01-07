# Scribe - Audio Transcription Service

A distributed transcription system for YouTube videos and podcasts, leveraging MLX-accelerated Whisper models on Apple Silicon.

## Overview

Scribe consists of three independent services:

1. **Transcriber Service** - MLX-powered transcription engine (runs on macOS with Apple Silicon)
2. **Frontend Service** - Web interface and job orchestration (runs anywhere, including Intel-based systems)
3. **Emailer Service** - Email-based job submission (monitors IMAP folder, sends results via SMTP)

## Features

- Web-based interface for submitting URLs
- Email-based job submission (forward URLs to get transcriptions back)
- Support for YouTube videos, Apple Podcasts, and direct audio URLs
- MLX-accelerated Whisper transcription on Apple Silicon
- SQLite database for metadata and job tracking
- Automatic audio caching with configurable retention (7 days default)
- Export transcriptions in multiple formats (JSON, TXT, SRT)
- Real-time progress updates via WebSocket
- Full-text search capabilities

## Architecture

```
┌─────────────────────────────────────┐
│  Intel Task Orchestrator            │
│  ┌───────────────────────────────┐  │
│  │  Frontend Service (FastAPI)   │  │
│  │  - Web UI (form)              │  │
│  │  - Job orchestration          │  │
│  │  - yt-dlp downloads           │  │
│  │  - SQLite database            │  │
│  │  - Storage management         │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
           │
           │ HTTP API
           ▼
┌─────────────────────────────────────┐
│  macOS Machine (MLX)                │
│  ┌───────────────────────────────┐  │
│  │  Transcriber Service          │  │
│  │  - MLX Whisper model          │  │
│  │  - Transcription engine       │  │
│  │  - Job queue                  │  │
│  │  - HTTP API                   │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Emailer Service (Optional)         │
│  ┌───────────────────────────────┐  │
│  │  - IMAP folder monitoring     │  │
│  │  - URL extraction from emails │  │
│  │  - Frontend API integration   │  │
│  │  - SMTP result delivery       │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Project Structure

```
scribe/
├── transcriber/          # MLX transcription service (macOS)
├── frontend/             # Web UI and orchestrator (any platform)
├── emailer/              # Email-based job submission (optional)
├── data/                 # Shared data directory
│   ├── transcriptions/  # JSON outputs
│   ├── cache/audio/     # Temporary audio files
│   └── scribe.db        # SQLite database
└── docs/                # Documentation
```

## Quick Start

### Prerequisites

**Transcriber Service (macOS with Apple Silicon):**
- Python 3.10+
- macOS with Apple Silicon (M1/M2/M3)
- ~2GB free disk space for Whisper medium model

**Frontend Service (any platform):**
- Python 3.10+
- yt-dlp
- SQLite

### Installation

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions.

**Quick setup:**

```bash
# 1. Start transcriber service (on macOS machine)
cd transcriber/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m transcriber.main

# 2. Start frontend service (on orchestrator machine)
cd frontend/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m frontend.main

# 3. Open browser to http://localhost:8000
```

## Usage

1. Open the web interface at `http://localhost:8000`
2. Paste a YouTube URL, Apple Podcasts link, or direct audio URL
3. Click "Transcribe"
4. Monitor progress in real-time
5. View or download the transcription when complete

## Configuration

Both services are configured via environment variables. See:
- `transcriber/.env.example` - Transcriber configuration
- `frontend/.env.example` - Frontend configuration

Key settings:
- `TRANSCRIBER_URL` - URL of the transcriber service
- `WHISPER_MODEL` - Model size (tiny, base, small, medium, large-v3)
- `AUDIO_CACHE_DAYS` - How long to keep audio files (default: 7)
- `DATA_DIR` - Path to shared data directory

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Specifications](docs/API.md)
- [Database Schema](docs/DATABASE.md)
- [Setup & Deployment](docs/SETUP.md)

## Technical Stack

**Transcriber:**
- FastAPI (HTTP server)
- mlx-whisper (Whisper implementation for Apple Silicon)
- Python 3.10+

**Frontend:**
- FastAPI (web server + API)
- SQLAlchemy (ORM)
- yt-dlp (media downloader)
- Jinja2 (templates)
- WebSockets (real-time updates)

**Emailer:**
- aioimaplib (async IMAP client)
- aiosmtplib (async SMTP client)
- httpx (async HTTP client)
- pydantic-settings (configuration)
- BeautifulSoup4 (HTML parsing)

## Design Decisions

- **No authentication**: Designed for trusted network environments
- **Whisper medium model**: Balance of quality and speed
- **7-day audio cache**: Allows re-processing without re-download
- **SQLite database**: Simple, serverless, sufficient for single-user scenarios
- **JSON with timestamps**: Primary format for future processing flexibility

## Future Enhancements

- Full-text search across all transcriptions
- RAG integration for question-answering
- Batch processing of playlists
- Multiple model support
- Speaker diarization
- Summary generation
- Export to additional formats

## License

MIT

## Contributing

This is a personal project. Contributions welcome via issues and pull requests.
