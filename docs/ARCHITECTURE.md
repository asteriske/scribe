# Architecture Overview

## System Design

Scribe is a distributed transcription system designed to separate compute-intensive transcription from orchestration and user interaction. This allows the MLX-accelerated transcription to run on Apple Silicon while the frontend can run on any platform.

## Components

### 1. Transcriber Service (macOS/MLX)

**Purpose:** Execute audio transcription using MLX-optimized Whisper models

**Location:** Runs on macOS machine with Apple Silicon (M1/M2/M3)

**Responsibilities:**
- Load and manage Whisper models in memory
- Accept transcription jobs via HTTP API
- Process audio files through MLX Whisper
- Return structured transcription results
- Manage job queue for sequential processing

**Technology:**
- FastAPI (HTTP server)
- mlx-whisper (Apple Silicon optimized Whisper)
- Background job queue

**Port:** 8001 (configurable)

**State:** Stateless (jobs are ephemeral, results returned to caller)

---

### 2. Frontend Service (Any Platform)

**Purpose:** User interface, job orchestration, and data persistence

**Location:** Runs on any platform (Intel/ARM/cloud)

**Responsibilities:**
- Serve web interface for URL submission
- Download audio from various sources (YouTube, podcasts, direct URLs)
- Manage local audio cache
- Submit jobs to transcriber service
- Poll for job completion
- Persist transcription results to database and filesystem
- Provide API for viewing and exporting transcriptions
- Schedule cleanup of cached audio files
- Serve WebSocket connections for real-time progress

**Technology:**
- FastAPI (HTTP server + WebSocket)
- SQLAlchemy (ORM)
- yt-dlp (media downloads)
- Jinja2 (HTML templates)
- SQLite (database)

**Port:** 8000 (configurable)

**State:** Stateful (maintains database, file storage, and job status)

---

## Data Flow

### Complete Workflow

```
1. User Submission
   │
   ├─ User enters URL in web form
   ├─ Frontend validates URL format
   ├─ Frontend creates database entry (status: 'pending')
   └─ Frontend returns job ID to user
   │
2. Audio Download
   │
   ├─ Frontend initiates background task
   ├─ yt-dlp downloads audio (best quality, audio-only)
   ├─ Audio saved to cache/audio/{id}.{ext}
   ├─ Metadata extracted (title, duration, channel)
   ├─ Database updated (status: 'downloading' → 'downloaded')
   └─ WebSocket update sent to user
   │
3. Transcription
   │
   ├─ Frontend uploads audio to transcriber
   ├─ Transcriber queues job (returns job_id)
   ├─ Transcriber processes audio through Whisper
   ├─ Database updated (status: 'transcribing')
   ├─ Frontend polls transcriber for progress
   └─ WebSocket updates sent to user
   │
4. Storage
   │
   ├─ Transcriber returns completed JSON result
   ├─ Frontend saves to data/transcriptions/YYYY/MM/{id}.json
   ├─ Frontend updates database with full metadata
   ├─ Database updated (status: 'completed')
   ├─ Full-text search index updated
   └─ WebSocket completion notification sent
   │
5. Cleanup
   │
   ├─ Audio file scheduled for deletion (7 days)
   ├─ Background task monitors cleanup queue
   └─ Files deleted after retention period
```

### Error Handling Flow

```
Error occurs at any stage:
   │
   ├─ Exception caught by frontend
   ├─ Database updated (status: 'failed', error_message: '...')
   ├─ Error logged to logs/frontend.log
   ├─ WebSocket error notification sent
   └─ User sees error in UI
```

---

## Communication Protocol

### Frontend → Transcriber

**Protocol:** HTTP/REST

**Authentication:** None (trusted network)

**Timeout:** 300 seconds (configurable)

**Retry Logic:**
- Network errors: 3 retries with exponential backoff
- HTTP 5xx: 3 retries
- HTTP 4xx: No retry (client error)

**Request Flow:**
```
1. POST /transcribe (submit job)
   - Upload audio file
   - Receive job_id

2. GET /jobs/{job_id} (poll status)
   - Poll every 2 seconds
   - Continue until status = 'completed' or 'failed'

3. Retrieve result from response
```

---

## Storage Architecture

### Database (SQLite)

**Location:** `data/scribe.db`

**Purpose:**
- Job metadata and status tracking
- Searchable transcription index
- Audio cache management
- Query interface for frontend

**Access Pattern:**
- Frontend: Read/Write
- Transcriber: None (stateless)

### File Storage

**Transcriptions:**
```
data/transcriptions/
├── 2026/
│   ├── 01/
│   │   ├── youtube_abc123.json
│   │   ├── youtube_def456.json
│   │   └── ...
│   └── 02/
└── 2025/
```

**Audio Cache:**
```
data/cache/audio/
├── youtube_abc123.m4a
├── youtube_def456.m4a
└── ... (auto-deleted after 7 days)
```

**Logs:**
```
data/logs/
├── frontend.log
└── transcriber.log
```

---

## Scalability Considerations

### Current Design (Single User)

- **Transcriber:** Processes one job at a time (GPU memory constraint)
- **Frontend:** Can handle multiple concurrent web requests
- **Database:** SQLite sufficient for 1000s of transcriptions
- **Storage:** Local filesystem

### Future Scaling Options

**Horizontal Scaling:**
- Multiple transcriber instances with load balancer
- Job queue (Redis/RabbitMQ) instead of direct HTTP
- PostgreSQL instead of SQLite
- S3/Object storage instead of local files

**Vertical Scaling:**
- Larger Whisper models for better quality
- Batch processing multiple segments in parallel
- GPU memory optimization for concurrent jobs

---

## Security Model

**Current:** Trusted network only, no authentication

**Assumptions:**
- Services run on private network
- Network access controlled by firewall/VPN
- Single user or small trusted team

**Future Considerations:**
- API key authentication between services
- User login for frontend
- Rate limiting
- Input sanitization (already required for URLs)

---

## Network Architecture

### Local Network Deployment

```
┌──────────────────────────────────────┐
│  Local Network (192.168.1.0/24)     │
│                                       │
│  ┌─────────────────────────────┐    │
│  │  macOS Machine              │    │
│  │  IP: 192.168.1.10:8001      │    │
│  │  [Transcriber Service]      │    │
│  └─────────────────────────────┘    │
│              ▲                        │
│              │ HTTP                  │
│              │                        │
│  ┌─────────────────────────────┐    │
│  │  Intel Server               │    │
│  │  IP: 192.168.1.20:8000      │    │
│  │  [Frontend Service]         │    │
│  └─────────────────────────────┘    │
│              ▲                        │
│              │ HTTP/WS               │
│              │                        │
│  ┌─────────────────────────────┐    │
│  │  User Browser               │    │
│  └─────────────────────────────┘    │
│                                       │
└──────────────────────────────────────┘
```

### Same Machine Deployment

```
┌──────────────────────────────────────┐
│  macOS Machine (localhost)           │
│                                       │
│  ┌─────────────────────────────┐    │
│  │  Transcriber :8001          │    │
│  └─────────────────────────────┘    │
│              ▲                        │
│              │                        │
│  ┌─────────────────────────────┐    │
│  │  Frontend :8000             │    │
│  └─────────────────────────────┘    │
│              ▲                        │
│              │                        │
│  ┌─────────────────────────────┐    │
│  │  Browser :8000              │    │
│  └─────────────────────────────┘    │
└──────────────────────────────────────┘
```

---

## Configuration Management

Both services use environment variables loaded from `.env` files:

**Transcriber:**
- Service configuration (host, port, workers)
- Model configuration (model size, cache location)
- Queue settings (max concurrent jobs, queue size)
- Logging configuration

**Frontend:**
- Service configuration (host, port)
- Transcriber connection (URL, timeout, polling)
- Storage configuration (data directory, cache retention)
- Database configuration (SQLite path)
- Download configuration (yt-dlp settings)
- Logging configuration

See [SETUP.md](SETUP.md) for detailed configuration options.

---

## Monitoring & Observability

### Logs

**Frontend Logs:**
- Job submissions
- Download progress
- Transcriber communication
- Database operations
- Errors and exceptions

**Transcriber Logs:**
- Job queue status
- Model loading
- Transcription progress
- Memory usage
- Errors and exceptions

### Health Checks

**Transcriber:**
```
GET /health
Returns:
- Service status
- Model loaded (yes/no)
- Queue size
- Current job status
```

**Frontend:**
```
GET /health
Returns:
- Service status
- Database connectivity
- Transcriber connectivity
- Disk space available
```

### Metrics (Future)

- Jobs per day
- Average transcription time
- Success/failure rates
- Storage usage trends
- Queue wait times

---

## Failure Modes & Recovery

### Transcriber Crashes

**Impact:** Current job fails, queued jobs lost

**Recovery:**
1. Frontend receives connection error
2. Job marked as failed in database
3. User notified via UI
4. Audio file remains in cache for retry
5. Restart transcriber service
6. User can resubmit job

### Frontend Crashes

**Impact:** In-progress downloads/uploads may fail

**Recovery:**
1. Database persists all completed work
2. On restart, check for jobs in 'downloading' or 'transcribing' status
3. Retry or mark as failed
4. WebSocket clients reconnect automatically

### Network Partition

**Impact:** Frontend cannot reach transcriber

**Recovery:**
1. Frontend retries with exponential backoff
2. After max retries, job marked as failed
3. User can retry when network restored

### Disk Full

**Impact:** Cannot save audio or transcriptions

**Recovery:**
1. Frontend checks disk space before operations
2. Cleanup old audio files early if approaching limit
3. Fail gracefully with clear error message

---

## Technology Choices Rationale

**FastAPI:**
- Modern async Python framework
- Built-in OpenAPI docs
- WebSocket support
- Easy to develop and test

**MLX Whisper:**
- Optimized for Apple Silicon
- Significantly faster than CPU/CUDA on M-series chips
- Active development by Apple
- Similar accuracy to official Whisper

**SQLite:**
- Serverless (no separate DB process)
- Sufficient for single-user scenarios
- Full-text search via FTS5
- Easy backup (single file)

**yt-dlp:**
- Most comprehensive media downloader
- Supports 1000+ sites
- Active maintenance
- Powerful extraction options

**WebSockets:**
- Real-time progress updates
- Lower latency than polling
- Better user experience
- Native browser support
