# Episode Sources Design

## Overview

A new pipeline in the emailer service that monitors an IMAP folder for podcast-related emails (newsletters, announcements, recommendations). It captures the email content as a source document, extracts an Apple Podcasts or YouTube URL, and triggers the existing transcription/summarization pipeline. The stored email content is linked to the resulting transcription via foreign key for later use in evals.

## Architecture

### Pipeline Flow

1. Emailer polls the `EpisodeSources` IMAP folder alongside the existing `ToScribe` folder
2. For each unseen email:
   a. Extract the plain text body (convert HTML to plain text if no text/plain part)
   b. Search for Apple Podcasts or YouTube URLs
   c. If no matching URL found: move to `EpisodeSourcesError`, notify sender
   d. If a matching URL is found (first match wins):
      - Submit URL to frontend with tag `"digest"`
      - Wait for transcription/summarization to complete
      - POST episode source record to new frontend API endpoint
      - Send result email to configured return address (default: `scribe_newsletters@patrickmccarthy.cc`)
      - Move email to `EpisodeSourcesDone`

### URL Matching

Only Apple Podcasts and YouTube URLs are accepted (subset of existing `url_extractor`):
- `podcasts.apple.com/`
- `youtube.com/watch`, `youtube.com/live/`, `youtu.be/`

The first matching URL is selected. The result email includes the original email subject and matched URL so the recipient can verify the pairing.

## Database Schema

New table in `scribe.db`:

```sql
CREATE TABLE episode_sources (
    id               VARCHAR PRIMARY KEY,
    transcription_id VARCHAR NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    email_subject    VARCHAR,
    email_from       VARCHAR,
    source_text      TEXT NOT NULL,
    matched_url      VARCHAR NOT NULL,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_episode_sources_transcription_id ON episode_sources(transcription_id);
```

- ID prefix `es_` follows the existing `sum_` convention from the summaries table
- Foreign key cascade: deleting a transcription removes associated episode source records
- `matched_url` stored for traceability of which URL was selected from the email

### SQLAlchemy Model

New `EpisodeSource` model in `models.py` with relationship to `Transcription`. Follows the same pattern as the existing `Summary` model.

### Migration

New function `create_episode_sources_table_if_missing(engine)` added to `migrations.py` and called from `run_migrations()`.

## Frontend API

### POST /api/episode-sources

Creates an episode source record.

**Request:**
```json
{
    "transcription_id": "abc123",
    "email_subject": "New episode: The Art of ...",
    "email_from": "newsletter@example.com",
    "source_text": "This week we discuss...",
    "matched_url": "https://podcasts.apple.com/..."
}
```

**Response:** `201 Created` with the new record.

No GET endpoint initially; the database is queried directly for evals.

## Emailer Changes

### Configuration

New settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `IMAP_FOLDER_EPISODE_SOURCES` | `"EpisodeSources"` | Inbox folder for podcast emails |
| `IMAP_FOLDER_EPISODE_SOURCES_DONE` | `"EpisodeSourcesDone"` | Folder for successfully processed emails |
| `IMAP_FOLDER_EPISODE_SOURCES_ERROR` | `"EpisodeSourcesError"` | Folder for emails with no matching URL |
| `EPISODE_SOURCES_RETURN_ADDRESS` | `"scribe_newsletters@patrickmccarthy.cc"` | Destination for result emails |

### New Module: episode_source_processor.py

Responsibilities:
- Extract plain text from email (reuses existing HTML-to-text conversion)
- Filter URLs to Apple Podcasts + YouTube only
- Select first matching URL
- Submit URL to frontend with tag `"digest"`
- POST episode source record to frontend API
- Send result to configured return address

### Polling Loop

The existing poll cycle in `main.py` is extended to check the `EpisodeSources` folder alongside `ToScribe`. Both pipelines share the concurrency semaphore.

## Result Email

### Success

- **To:** Configured return address (`EPISODE_SOURCES_RETURN_ADDRESS`)
- **Subject:** `"Scribe: {original email subject}"`
- **Body:** Verification line with matched URL, followed by standard transcription result (summary, transcript, show notes)

### Error (no matching URL)

- **To:** Original sender
- **Subject/Body:** Same "no supported URLs found" format as existing pipeline, noting that only Apple Podcasts and YouTube URLs are supported in this pipeline

## IMAP Setup

Three new folders must be created on the mail server:
- `EpisodeSources`
- `EpisodeSourcesDone`
- `EpisodeSourcesError`

## Summary of Changes

| Component | Changes |
|-----------|---------|
| **Frontend model** | New `EpisodeSource` SQLAlchemy model |
| **Frontend migration** | New `create_episode_sources_table_if_missing()` |
| **Frontend API** | New `POST /api/episode-sources` endpoint |
| **Emailer config** | 4 new settings |
| **Emailer processor** | New `episode_source_processor.py` module |
| **Emailer main** | Second folder check in poll loop |
| **Emailer frontend_client** | New method to POST episode source records |
| **IMAP server** | 3 new folders |
