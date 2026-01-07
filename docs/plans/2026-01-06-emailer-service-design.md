# Emailer Service Design

## Overview

A standalone Python module that monitors an IMAP folder for emails containing transcribable URLs, processes them through the existing frontend/transcriber pipeline, and sends results via email.

## Architecture

```
scribe/
├── emailer/                    # New email processing service
│   ├── emailer/
│   │   ├── __init__.py
│   │   ├── main.py             # Entry point, async main loop
│   │   ├── config.py           # Settings from env vars
│   │   ├── imap_client.py      # IMAP operations (fetch, move)
│   │   ├── smtp_client.py      # SMTP operations (send results/errors)
│   │   ├── url_extractor.py    # Parse emails, extract transcribable URLs
│   │   ├── job_processor.py    # Orchestrate transcription + summarization
│   │   └── result_formatter.py # Format summary + transcript for email
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   ├── .secrets.example
│   └── README.md
├── frontend/
├── transcriber/
└── ...
```

### Communication Flow

```
┌─────────────┐     IMAP      ┌─────────────┐
│  Email      │ ◄──────────── │  Emailer    │
│  Server     │ ──────────────►  Service    │
└─────────────┘     SMTP      └──────┬──────┘
                                     │ REST
                              ┌──────▼──────┐
                              │  Frontend   │
                              │  Service    │
                              └──────┬──────┘
                                     │ REST
                              ┌──────▼──────┐
                              │ Transcriber │
                              │  Service    │
                              └─────────────┘
```

The emailer calls the frontend's existing REST API to submit transcription jobs and retrieve results (including summaries). It does not communicate directly with the transcriber.

## Configuration

### Environment Variables (`.env`)

```
# IMAP Settings
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USER=scribe@example.com
IMAP_USE_SSL=true

# SMTP Settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=scribe@example.com
SMTP_USE_TLS=true

# Folder Names
IMAP_FOLDER_INBOX=ToScribe
IMAP_FOLDER_DONE=ScribeDone
IMAP_FOLDER_ERROR=ScribeError

# Processing
POLL_INTERVAL_SECONDS=300
MAX_CONCURRENT_JOBS=3

# Destinations
RESULT_EMAIL_ADDRESS=results@example.com
FROM_EMAIL_ADDRESS=scribe@example.com

# Frontend Service
FRONTEND_URL=http://localhost:8000
```

### Secrets (`.secrets`)

Passwords stored separately from config:

```
IMAP_PASSWORD=your_imap_password
SMTP_PASSWORD=your_smtp_password
```

These are expected to be injected via secrets management (Docker secrets, systemd credentials, or a `.secrets` file not in version control).

### Validation

On startup, the service validates all required settings are present and fails fast with clear error messages if not.

## Processing Logic

### Main Loop

```python
async def main():
    config = load_config()
    semaphore = asyncio.Semaphore(config.max_concurrent_jobs)

    while True:
        emails = await fetch_emails_from_folder(config.inbox_folder)

        for email in emails:
            asyncio.create_task(process_email(email, semaphore))

        await asyncio.sleep(config.poll_interval)
```

### Email Processing Flow

For each email:

1. Extract all transcribable URLs from body
2. If no URLs found → move to ScribeError, notify sender
3. For each URL (concurrently, respecting semaphore):
   - POST to frontend `/api/transcriptions` with URL
   - Poll for completion
   - On success: fetch summary + transcript, send result email to configured address
   - On failure: send error email to original sender
4. After all URLs processed:
   - If all failed → move email to ScribeError
   - Otherwise → move email to ScribeDone

### URL Extraction

- Parse both plain text and HTML parts of email
- Regex pattern matching for known transcribable domains (youtube.com, youtu.be, podcasts.apple.com, etc.)
- Configurable list of supported URL patterns for future expansion
- Deduplicate URLs found in both text and HTML parts

### In-Progress Tracking

IMAP `\Seen` flag prevents duplicate processing:

```python
# 1. Fetch only unseen emails from ToScribe
await imap.select('ToScribe')
_, message_ids = await imap.search('UNSEEN')

# 2. For each email, immediately mark as seen before processing
for msg_id in message_ids:
    await imap.store(msg_id, '+FLAGS', '\\Seen')
    asyncio.create_task(process_email(msg_id, ...))
```

If the service crashes mid-processing, the email remains in ToScribe but flagged as seen and won't be retried. This is an acceptable trade-off for simplicity.

## Email Formats

### Result Email (Success)

```
To: results@example.com
From: scribe@example.com
Subject: [Scribe] {video_title}

Source: {url}
Duration: {duration}
Transcribed: {timestamp}

--- SUMMARY ---

{summary_text}

--- TRANSCRIPT ---

{full_transcript_text}
```

### Error Email (to Original Sender)

```
To: {original_sender}
From: scribe@example.com
Subject: [Scribe Error] Failed to process URL

The following URL could not be transcribed:

{url}

Error: {error_message}

---
Original request received: {timestamp}
```

### No URLs Found Email (to Original Sender)

```
To: {original_sender}
From: scribe@example.com
Subject: [Scribe Error] No transcribable URLs found

Your email did not contain any transcribable URLs.

Supported sources:
- YouTube (youtube.com, youtu.be)
- Apple Podcasts (podcasts.apple.com)
- Direct audio URLs (.mp3, .m4a, .wav)

---
Original request received: {timestamp}
```

All emails are plain text for maximum compatibility.

## Error Handling & Resilience

### Transient Failures (Retry)

- IMAP/SMTP connection errors: retry with exponential backoff (3 attempts, 5s/15s/45s)
- Frontend API unavailable: retry with backoff, leave email in ToScribe folder
- Network timeouts: retry with backoff

### Permanent Failures (No Retry)

- URL not supported/invalid: send error email, count as failed
- Transcription failed (audio unavailable, etc.): send error email, count as failed
- Email parsing error: move to ScribeError, send error notification

### Service Resilience

- Graceful shutdown on SIGTERM/SIGINT: finish in-progress jobs before exiting
- Startup validation: verify IMAP/SMTP connectivity, verify frontend reachable
- Each email processed independently: one failure doesn't block others
- Logging: structured logs for all operations

## Testing Strategy

### Unit Tests

- `url_extractor.py`: URL extraction from plain text, HTML, mixed content, edge cases
- `result_formatter.py`: Email body formatting
- `config.py`: Validation, defaults, missing required values

### Integration Tests (with Mocks)

- Mock IMAP server: email fetching, flag setting, folder moves
- Mock SMTP server: result/error email sending
- Mock frontend API: job submission, polling, result retrieval
- Full flow test: email in → job processed → result sent → email moved

### Test Utilities

- Factory functions for creating test emails
- Fixtures for common scenarios (single URL, multiple URLs, no URLs, HTML-only)

## Dependencies

```
aioimaplib>=1.0.0      # Async IMAP client
aiosmtplib>=3.0.0      # Async SMTP client
httpx>=0.26.0          # Async HTTP client (for frontend API)
pydantic>=2.0.0        # Config validation
pydantic-settings>=2.0.0
python-dotenv>=1.0.0   # Environment loading
beautifulsoup4>=4.12.0 # HTML parsing for URL extraction
pytest>=8.0.0          # Testing
pytest-asyncio>=0.23.0 # Async test support
```
