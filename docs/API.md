# API Specifications

## Overview

Scribe consists of two API surfaces:

1. **Frontend API** - Public-facing web interface and REST API
2. **Transcriber API** - Internal service-to-service API

---

## Frontend API (Port 8000)

### Web Interface Routes

#### `GET /`

Serve the main web interface with URL submission form.

**Response:** HTML page

**Template:** `templates/index.html`

---

#### `GET /transcriptions/{id}`

View a single transcription detail page.

**Parameters:**
- `id` (path) - Transcription ID (e.g., `youtube_abc123`)

**Response:** HTML page with transcription details

**Template:** `templates/transcription.html`

---

### REST API Routes

#### `POST /api/transcribe`

Submit a new URL for transcription.

**Request Body:**
```json
{
  "url": "https://youtube.com/watch?v=abc123"
}
```

**Response (202 Accepted):**
```json
{
  "id": "youtube_abc123",
  "status": "pending",
  "message": "Job created successfully",
  "created_at": "2026-01-02T10:30:00Z"
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Invalid URL format"
}
```

**Response (409 Conflict):**
```json
{
  "detail": "This URL has already been transcribed",
  "existing_id": "youtube_abc123"
}
```

**Supported URL formats:**
- YouTube: `https://youtube.com/watch?v=VIDEO_ID`
- YouTube short: `https://youtu.be/VIDEO_ID`
- Apple Podcasts: `https://podcasts.apple.com/...`
- Direct audio: `https://example.com/audio.mp3`

---

#### `GET /api/transcriptions`

List all transcriptions with pagination.

**Query Parameters:**
- `skip` (int, optional) - Number of records to skip (default: 0)
- `limit` (int, optional) - Number of records to return (default: 50, max: 100)
- `status` (string, optional) - Filter by status: `pending`, `downloading`, `transcribing`, `completed`, `failed`
- `search` (string, optional) - Full-text search query

**Response (200 OK):**
```json
{
  "total": 150,
  "skip": 0,
  "limit": 50,
  "items": [
    {
      "id": "youtube_abc123",
      "title": "Video Title",
      "status": "completed",
      "source_type": "youtube",
      "source_url": "https://youtube.com/watch?v=abc123",
      "duration_seconds": 212,
      "transcribed_at": "2026-01-02T10:30:00Z",
      "created_at": "2026-01-02T10:25:00Z"
    },
    ...
  ]
}
```

---

#### `GET /api/transcriptions/{id}`

Get details of a specific transcription.

**Parameters:**
- `id` (path) - Transcription ID

**Response (200 OK):**
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
  "status": "completed",
  "created_at": "2026-01-02T10:25:00Z",
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
    ],
    "full_text": "Welcome to this video...",
    "word_count": 485,
    "segments_count": 42
  },
  "files": {
    "json": "/api/transcriptions/youtube_abc123/export/json",
    "txt": "/api/transcriptions/youtube_abc123/export/txt",
    "srt": "/api/transcriptions/youtube_abc123/export/srt"
  }
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Transcription not found"
}
```

---

#### `GET /api/transcriptions/{id}/export/{format}`

Download transcription in specified format.

**Parameters:**
- `id` (path) - Transcription ID
- `format` (path) - Export format: `json`, `txt`, `srt`

**Response (200 OK):**
- `Content-Type`: Depends on format
  - `json`: `application/json`
  - `txt`: `text/plain`
  - `srt`: `text/srt`
- `Content-Disposition`: `attachment; filename="youtube_abc123.{format}"`

**Example TXT format:**
```
Title: Video Title
URL: https://youtube.com/watch?v=abc123
Duration: 212.5s
Transcribed: 2026-01-02 10:30:00

Welcome to this video. In today's tutorial...
```

**Example SRT format:**
```
1
00:00:00,000 --> 00:00:03,500
Welcome to this video

2
00:00:03,500 --> 00:00:06,800
In today's tutorial we'll learn...
```

---

#### `DELETE /api/transcriptions/{id}`

Delete a transcription and its associated files.

**Parameters:**
- `id` (path) - Transcription ID

**Response (204 No Content)**

**Response (404 Not Found):**
```json
{
  "detail": "Transcription not found"
}
```

---

#### `GET /api/search`

Full-text search across all transcriptions.

**Query Parameters:**
- `q` (string, required) - Search query
- `limit` (int, optional) - Number of results (default: 20, max: 100)

**Response (200 OK):**
```json
{
  "query": "machine learning",
  "total": 15,
  "results": [
    {
      "id": "youtube_abc123",
      "title": "Introduction to Machine Learning",
      "snippet": "...concepts of machine learning and how...",
      "relevance_score": 0.95
    },
    ...
  ]
}
```

---

### WebSocket Routes

#### `WS /ws/progress/{id}`

Real-time progress updates for a transcription job.

**Parameters:**
- `id` (path) - Transcription ID

**Messages from server:**

```json
// Status update
{
  "type": "status",
  "status": "downloading",
  "progress": 45,
  "message": "Downloading audio..."
}

// Progress update
{
  "type": "progress",
  "status": "transcribing",
  "progress": 67,
  "estimated_seconds_remaining": 45
}

// Completion
{
  "type": "complete",
  "status": "completed",
  "transcription_id": "youtube_abc123"
}

// Error
{
  "type": "error",
  "status": "failed",
  "error": "Failed to download audio: Video not available"
}
```

**Connection lifecycle:**
1. Client connects with transcription ID
2. Server sends current status immediately
3. Server sends updates as job progresses
4. Server closes connection when job completes or fails
5. Client can reconnect if connection drops

---

### Health & Status

#### `GET /health`

Service health check.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "database": "connected",
  "transcriber": {
    "status": "connected",
    "url": "http://192.168.1.10:8001"
  },
  "disk_space": {
    "total_gb": 500,
    "available_gb": 350,
    "usage_percent": 30
  }
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "database": "connected",
  "transcriber": {
    "status": "unreachable",
    "url": "http://192.168.1.10:8001",
    "error": "Connection timeout"
  }
}
```

---

## Transcriber API (Port 8001)

Internal service-to-service API for audio transcription.

### Endpoints

#### `POST /transcribe`

Submit audio for transcription.

**Request (multipart/form-data):**
```
file: audio.m4a (binary)
model: "medium" (optional, default from config)
language: "en" (optional, auto-detect if not specified)
task: "transcribe" (optional, "transcribe" or "translate")
```

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_duration_seconds": 30,
  "queue_position": 0
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Invalid audio format. Supported: mp3, m4a, wav, flac, ogg"
}
```

**Response (413 Payload Too Large):**
```json
{
  "detail": "Audio file too large. Maximum size: 500MB"
}
```

**Response (503 Service Unavailable):**
```json
{
  "detail": "Job queue is full. Try again later."
}
```

---

#### `GET /jobs/{job_id}`

Get status and result of a transcription job.

**Parameters:**
- `job_id` (path) - UUID of the job

**Response (200 OK) - Queued:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "queue_position": 2,
  "created_at": "2026-01-02T10:30:00Z"
}
```

**Response (200 OK) - Processing:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "started_at": "2026-01-02T10:30:05Z"
}
```

**Response (200 OK) - Completed:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2026-01-02T10:30:00Z",
  "started_at": "2026-01-02T10:30:05Z",
  "completed_at": "2026-01-02T10:31:30Z",
  "result": {
    "language": "en",
    "duration": 212.5,
    "segments": [
      {
        "id": 0,
        "start": 0.0,
        "end": 3.5,
        "text": "Welcome to this video",
        "tokens": [1, 2, 3, ...],
        "temperature": 0.0,
        "avg_logprob": -0.3,
        "compression_ratio": 1.5,
        "no_speech_prob": 0.01
      },
      ...
    ],
    "text": "Welcome to this video. In today's tutorial..."
  }
}
```

**Response (200 OK) - Failed:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": "Audio decoding failed",
  "created_at": "2026-01-02T10:30:00Z",
  "failed_at": "2026-01-02T10:30:10Z"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Job not found"
}
```

**Note:** Jobs are kept in memory for 1 hour after completion, then deleted.

---

#### `GET /health`

Service health check.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "model": {
    "name": "medium",
    "loaded": true,
    "device": "mlx"
  },
  "queue": {
    "size": 2,
    "max_size": 10,
    "current_job": "550e8400-e29b-41d4-a716-446655440000"
  },
  "memory": {
    "used_mb": 2048,
    "available_mb": 14336
  }
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "model": {
    "name": "medium",
    "loaded": false,
    "error": "Model loading failed"
  }
}
```

---

#### `GET /models`

List available Whisper models.

**Response (200 OK):**
```json
{
  "current": "medium",
  "available": [
    {
      "name": "tiny",
      "size_mb": 75,
      "downloaded": true
    },
    {
      "name": "base",
      "size_mb": 142,
      "downloaded": true
    },
    {
      "name": "small",
      "size_mb": 466,
      "downloaded": false
    },
    {
      "name": "medium",
      "size_mb": 1462,
      "downloaded": true
    },
    {
      "name": "large-v3",
      "size_mb": 2938,
      "downloaded": false
    }
  ]
}
```

---

## Error Responses

All APIs use standard HTTP status codes and return errors in this format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2026-01-02T10:30:00Z"
}
```

### Common Status Codes

- `200 OK` - Success
- `202 Accepted` - Job accepted for processing
- `204 No Content` - Success with no response body
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate)
- `413 Payload Too Large` - File too large
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

---

## Rate Limiting

**Current:** None (trusted network)

**Future considerations:**
- Per-IP rate limiting
- Per-user quotas
- Queue size limits

---

## CORS

**Current:** Disabled (same-origin only)

**Future:** Configurable allowed origins for external clients

---

## API Versioning

**Current:** v1 (implicit, no version in URL)

**Future:** Version prefix in URL path (e.g., `/api/v1/transcriptions`)

---

## OpenAPI Documentation

Both services provide auto-generated OpenAPI documentation:

- **Frontend API:** `http://localhost:8000/docs`
- **Transcriber API:** `http://localhost:8001/docs`

Interactive API testing available via Swagger UI at these endpoints.
