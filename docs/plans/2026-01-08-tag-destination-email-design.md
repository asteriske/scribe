# Tag Destination Email Feature Design

## Overview

Allow tag definitions to include an optional destination email address. When a transcription result is sent via the emailer, it routes to the tag's destination email if configured, otherwise falls back to the emailer's default `result_email_address`.

## Configuration Format

The `tag_configs.json` gains an optional `destination_email` field per tag:

```json
{
  "default": {
    "api_endpoint": "http://10.100.2.50:1234/v1",
    "model": "openai/gpt-oss-20b",
    "system_prompt": "Provide a concise summary..."
  },
  "tags": {
    "kindle": {
      "api_endpoint": "http://10.100.2.50:11434/v1",
      "model": "openai/gpt-oss-20b",
      "system_prompt": "Summarize the following podcast...",
      "destination_email": "kindle@example.com"
    },
    "supersummarize": {
      "api_endpoint": "https://api.openai.com/v1",
      "model": "gpt-4",
      "system_prompt": "Provide a detailed summary..."
    }
  }
}
```

Tags without `destination_email` (like `supersummarize`) use the emailer's default `result_email_address`.

## API Changes

### New Endpoint: `GET /api/tags/{name}`

Returns the full tag configuration.

**Request:**
```
GET /api/tags/kindle
```

**Response (tag with destination):**
```json
{
  "name": "kindle",
  "api_endpoint": "http://10.100.2.50:11434/v1",
  "model": "openai/gpt-oss-20b",
  "system_prompt": "Summarize the following podcast...",
  "destination_email": "kindle@example.com"
}
```

**Response (tag without destination):**
```json
{
  "name": "supersummarize",
  "api_endpoint": "https://api.openai.com/v1",
  "model": "gpt-4",
  "system_prompt": "Provide a detailed summary...",
  "destination_email": null
}
```

**Response (unknown tag):** 404

The existing `GET /api/tags` endpoint remains unchanged (returns list of tag names).

## Emailer Flow

When processing an email:

1. Parse subject line, resolve tag name (existing logic)
2. Call `GET /api/tags/{resolved_tag}` to fetch tag config
3. Extract `destination_email` from response
4. If `destination_email` is `null`, use emailer's `result_email_address` from config
5. Send result to the resolved destination

### Error Handling

- If tag config fetch fails (network error, 404): log warning, use default `result_email_address`
- Emailer never fails to send just because tag lookup failed

## Files to Modify

### Frontend

- `frontend/frontend/api/routes.py` - Add `GET /api/tags/{name}` endpoint
- `frontend/frontend/config/tag_configs.json` - Add `destination_email` to desired tags

### Emailer

- `emailer/emailer/frontend_client.py` - Add `get_tag_config(tag_name)` method
- `emailer/emailer/job_processor.py` - Fetch tag config, resolve destination email before sending

### Tests

- `frontend/tests/` - Test new endpoint (returns config, returns null for missing field, 404 for unknown tag)
- `emailer/tests/` - Test destination resolution logic (uses tag email when present, falls back to default)
