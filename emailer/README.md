# Emailer Service

Email-based job submission for Scribe transcription system.

## Overview

Monitors an IMAP folder for emails containing transcribable URLs, processes them through the frontend API, and sends results via email. This enables email-based workflow where users can forward links to a dedicated email address and receive transcriptions back automatically.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Email Client  │────▶│  IMAP Server    │────▶│ Emailer Service │
│                 │     │  (ToScribe)     │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         │ HTTP API
                                                         ▼
                                                ┌─────────────────┐
                                                │ Frontend Service│
                                                │ (Transcription) │
                                                └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Results Email  │◀────│  SMTP Server    │◀────│ Emailer Service │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Setup

1. Create virtual environment:
   ```bash
   cd emailer/
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   cp .secrets.example .secrets
   # Edit .env and .secrets with your settings
   ```

3. Create IMAP folders on your mail server:
   - `ToScribe` - Inbox for transcription requests
   - `ScribeDone` - Completed requests (moved here after processing)
   - `ScribeError` - Failed requests

4. Run the service:
   ```bash
   python -m emailer.main
   ```

## Configuration

### Environment Variables (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `IMAP_HOST` | IMAP server hostname | Required |
| `IMAP_PORT` | IMAP server port | `993` |
| `IMAP_USER` | IMAP username/email | Required |
| `IMAP_USE_SSL` | Use SSL for IMAP | `true` |
| `SMTP_HOST` | SMTP server hostname | Required |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username/email | Required |
| `SMTP_USE_TLS` | Use STARTTLS for SMTP | `true` |
| `IMAP_FOLDER_INBOX` | Folder to monitor | `ToScribe` |
| `IMAP_FOLDER_DONE` | Folder for completed | `ScribeDone` |
| `IMAP_FOLDER_ERROR` | Folder for errors | `ScribeError` |
| `POLL_INTERVAL_SECONDS` | Check interval | `300` |
| `MAX_CONCURRENT_JOBS` | Parallel processing limit | `3` |
| `RESULT_EMAIL_ADDRESS` | Where to send results | Required |
| `FROM_EMAIL_ADDRESS` | Sender address | Required |
| `FRONTEND_URL` | Frontend API URL | `http://localhost:8000` |

### Secrets (.secrets)

| Variable | Description |
|----------|-------------|
| `IMAP_PASSWORD` | IMAP account password |
| `SMTP_PASSWORD` | SMTP account password |

## Usage

1. Forward or send an email containing transcribable URLs to your configured email address
2. The emailer service will:
   - Detect the email in the ToScribe folder
   - Extract YouTube, Apple Podcasts, or direct audio URLs
   - Submit each URL to the frontend for transcription
   - Wait for transcription to complete
   - Generate a summary
   - Email results to `RESULT_EMAIL_ADDRESS`
   - Move the original email to ScribeDone or ScribeError

### Supported URL Types

- YouTube: `youtube.com/watch?v=...`, `youtu.be/...`
- Apple Podcasts: `podcasts.apple.com/...`
- Podcast Addict: `podcastaddict.com/.../episode/...`
- Direct audio: `.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg`, `.aac`

## Testing

```bash
cd emailer/
source venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

## Troubleshooting

**Service won't connect to IMAP:**
- Verify IMAP credentials and server settings
- Check if app-specific passwords are required (Gmail, etc.)
- Ensure the IMAP folders exist on the server

**Emails not being processed:**
- Check that emails are in the correct folder (ToScribe)
- Verify emails contain supported URL types
- Check service logs for errors

**Results not being sent:**
- Verify SMTP credentials and server settings
- Check `RESULT_EMAIL_ADDRESS` is correct
- Look for SMTP errors in logs
