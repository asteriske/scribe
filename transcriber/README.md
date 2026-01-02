# Scribe Transcriber Service

MLX-powered audio transcription service using Whisper models.

## Requirements

- macOS with Apple Silicon (M1/M2/M3)
- Python 3.10+
- ~2GB disk space for Whisper medium model

## Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Start the service
python -m transcriber.main
```

Or use the launch script:

```bash
./scripts/start.sh
```

The service will start on `http://localhost:8001`

## API Documentation

Once running, visit:
- OpenAPI docs: `http://localhost:8001/docs`
- Alternative docs: `http://localhost:8001/redoc`

## Configuration

Edit `.env` to configure:

- `WHISPER_MODEL` - Model size (tiny, base, small, medium, large-v3)
- `PORT` - Service port (default: 8001)
- `MAX_CONCURRENT_JOBS` - Number of concurrent jobs (default: 1)

See `.env.example` for all options.

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# With coverage
pytest --cov=transcriber
```

## Usage Example

```bash
# Submit audio file for transcription
curl -X POST http://localhost:8001/transcribe \
  -F "file=@audio.mp3" \
  -F "language=en"

# Response: {"job_id": "...", "status": "queued", ...}

# Check job status
curl http://localhost:8001/jobs/{job_id}

# Health check
curl http://localhost:8001/health
```

## Development

```bash
# Format code
black transcriber/ tests/

# Run linter
flake8 transcriber/ tests/

# Type checking
mypy transcriber/
```

## Architecture

- **FastAPI** - HTTP server
- **MLX Whisper** - Transcription engine
- **Async queue** - Job management

See `../docs/ARCHITECTURE.md` for details.
