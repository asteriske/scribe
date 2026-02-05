# Show Notes Context Feature Design

## Overview

Enrich podcast summarization by fetching and using creator-provided show notes as context for the LLM.

## Problem

When summarizing podcast transcripts, the LLM lacks the creator's own framing of what's important. Show notes often contain the "thesis" of an episode - topics, questions, guest info, and timestamps that indicate what the creator considers essential.

## Solution

Fetch show notes from the source URL at submission time and inject them into the summarization prompt, allowing the LLM to use relevant context when generating summaries.

## Design

### Storage

Add a new optional field to job storage:

- **Field name:** `source_context`
- **Type:** Text (nullable)
- **Contents:** Raw text extracted from the source URL's page - show notes, description, timestamps, topic lists, guest info
- **Platform-agnostic:** The field works for any source, populated by platform-specific scrapers

### Apple Podcasts Scraper

Implemented for URLs matching `podcasts.apple.com`:

**Extraction targets:**
- Episode title and description
- Show notes / detailed description text
- Timestamps with labels (if present)
- Guest names and listed topics

**Retry logic:**
- Up to 3 attempts for transient errors (timeouts, 5xx responses)
- Give up quickly to avoid hindering the submission flow

**Failure handling:**
- Network errors, parsing failures, or empty results: log and continue
- Set `source_context` to null, proceed with normal processing
- No user-facing error

### LLM Prompt Integration

When `source_context` exists, prepend to the summarization prompt:

```
The creator provided the following show notes for this episode:

---
{source_context}
---

If any of this context is relevant to the summarization task below,
use it to guide what you extract. Ignore any show notes content
that isn't relevant to the specific request.
```

When no context exists, the prompt remains unchanged.

### Email Output Format

Updated structure with three labeled sections:

1. **Summary** - LLM-generated summary
2. **Creator's Notes** - Fetched show notes (omit section if none available)
3. **Transcript** - Full transcript

## Scope

### In Scope

1. Add `source_context` field to job storage
2. Apple Podcasts URL detection
3. Page fetcher with retry logic
4. HTML parser to extract show notes content
5. Conditional prompt injection in summarization step
6. Updated email output format

### Out of Scope

- Scrapers for other platforms (Spotify, YouTube, RSS)
- Structured parsing of show notes into separate fields

## Testing

- Unit test the Apple Podcasts scraper with sample HTML
- Integration test the prompt injection with/without context
- Manual test with real Apple Podcasts URLs
