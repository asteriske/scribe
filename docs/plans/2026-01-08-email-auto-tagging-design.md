# Email Auto-Tagging Feature Design

## Overview

When transcriptions are submitted via the emailer service, automatically assign a tag based on keywords in the email subject. This enables tag-based summarization settings to apply to email-submitted jobs.

## Behavior

1. Email arrives with a URL in the body
2. Emailer parses the subject line into lowercase words
3. Emailer fetches the current tag list from the frontend API
4. If any word in the subject matches an existing tag name (case-insensitive), use that tag
5. If no match or subject is blank, use the configured default tag
6. Submit the job to the frontend with the resolved tag

### Matching Rules

- All matching is case-insensitive (tags are lowercase)
- Subject is split on whitespace into individual words
- First matching word wins (order is arbitrary if multiple match)
- No mapping configuration needed - direct word-to-tag matching only

## Configuration

**Emailer config** (`config.yaml`):

```yaml
tagging:
  default_tag: "email"  # fallback when no subject match
```

## API Changes

### Frontend: `GET /api/tags`

Returns the list of available tag names.

**Response**:
```json
["email", "podcast", "interview", "meeting"]
```

If this endpoint already exists, no change needed.

### Frontend: Job Submission

Ensure `POST /api/transcriptions` (or equivalent) accepts an optional `tag` parameter:

```json
{
  "url": "https://example.com/audio.mp3",
  "tag": "podcast"
}
```

## Implementation

### Emailer Changes

**Config** (`emailer/emailer/config.py`):
- Add `default_tag: str` field to configuration

**Tag Resolution** (new function):
```python
def resolve_tag(subject: str, available_tags: set[str], default: str) -> str:
    """Match subject words against available tags, return first match or default."""
    words = subject.lower().split()
    for word in words:
        if word in available_tags:
            return word
    return default
```

**Email Processing**:
1. Fetch tags fresh from frontend API on each email
2. Call `resolve_tag()` with subject, tags, and configured default
3. Include resolved tag in job submission payload

**Error Handling**:
- If tag fetch fails: log warning, use default tag
- If default tag doesn't exist in frontend: job created without tag

### Frontend Changes

**Tags Endpoint** (if not existing):
- Add `GET /api/tags` route returning list of tag names from database

**Job Submission**:
- Ensure tag parameter is accepted and applied to new transcriptions

## Files to Modify

**Emailer**:
- `emailer/emailer/config.py` - add default_tag config
- `emailer/emailer/client.py` - add tag fetching method
- `emailer/emailer/processor.py` - resolve and submit tag

**Frontend**:
- `frontend/frontend/api/routes.py` - add tags endpoint (if needed)
- `frontend/frontend/api/routes.py` - ensure job submission accepts tag
