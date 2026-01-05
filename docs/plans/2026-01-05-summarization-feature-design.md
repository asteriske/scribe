# Transcription Summarization Feature

**Date:** 2026-01-05
**Status:** Design - Pending Implementation

## Overview

Add a summarization feature to the Scribe transcription system that allows users to generate AI-powered summaries of transcribed text using external LLM APIs. The feature supports tag-based configuration presets and maintains a history of generated summaries.

## Goals

- Generate summaries via external API calls (no local models)
- Support OpenAI-compatible APIs (OpenAI, Ollama, etc.)
- Configure different summarization styles per tag (e.g., "supersummarize" vs "highlevel")
- Store summarization configurations in version control
- Store generated summaries in database with full metadata
- Provide download options for summaries

## Non-Goals

- Local LLM integration (use external APIs only)
- Real-time streaming of summary generation
- Automatic summarization on transcription completion
- Multi-transcription batch summarization

## Architecture

### Navigation & Pages

**New Pages:**
- `/summarize` - Summarization interface
- `/settings/tags` - Tag configuration management

**Navigation Bar:**
Add to `base.html` with links: Home, Summarize, Settings

### Database Schema

**New `Summary` Table:**

```python
class Summary(Base):
    __tablename__ = 'summaries'

    # Identity
    id = Column(String, primary_key=True)  # e.g., 'sum_abc123'
    transcription_id = Column(String, ForeignKey('transcriptions.id'), nullable=False)

    # Configuration used for this summary
    api_endpoint = Column(String, nullable=False)
    model = Column(String, nullable=False)
    api_key_used = Column(Boolean, default=False)  # Don't store the actual key
    system_prompt = Column(Text, nullable=False)
    tags_at_time = Column(Text, nullable=False, default='[]')  # JSON array
    config_source = Column(String)  # e.g., "tag:supersummarize" or "system_default"

    # Result
    summary_text = Column(Text, nullable=False)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    generation_time_ms = Column(Integer)  # How long the API call took

    # Token usage (if API returns it)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
```

**Indexes:**
- `idx_summary_transcription_id` on `transcription_id`
- `idx_summary_created_at` on `created_at DESC`

### Configuration Files

**Tag Configurations (`frontend/config/tag_configs.json`)** - Version controlled:

```json
{
  "default": {
    "api_endpoint": "http://localhost:11434/v1",
    "model": "llama2",
    "api_key_ref": null,
    "system_prompt": "Provide a concise summary of the following transcription:"
  },
  "tags": {
    "supersummarize": {
      "api_endpoint": "https://api.openai.com/v1",
      "model": "gpt-4",
      "api_key_ref": "openai",
      "system_prompt": "Provide a detailed, nuanced summary with key insights from the following transcription. Include main themes, important details, and notable quotes."
    },
    "highlevel": {
      "api_endpoint": "http://localhost:11434/v1",
      "model": "llama2",
      "api_key_ref": null,
      "system_prompt": "Provide a brief high-level overview of the following transcription in 2-3 sentences."
    }
  }
}
```

**API Secrets (`frontend/config/secrets.json`)** - Gitignored:

```json
{
  "openai": "sk-...",
  "anthropic": "sk-ant-..."
}
```

### Configuration Resolution Logic

When a transcription is selected for summarization:

1. **Get transcription tags** from database (JSON array)
2. **Read tag_configs.json**
3. **Resolve configuration:**
   - Iterate through transcription tags in order
   - If tag exists in `tag_configs.json["tags"]`, use that config
   - Set `config_source = "tag:{tag_name}"`
   - Stop at first match
4. **Fallback to default:**
   - If no tag matches, use `tag_configs.json["default"]`
   - Set `config_source = "system_default"`
5. **Resolve API key:**
   - If `api_key_ref` is set (e.g., "openai"):
     - Check environment variable `{API_KEY_REF}_API_KEY` (uppercase)
     - If not found, check `secrets.json[api_key_ref]`
     - If not found, use empty string
   - If `api_key_ref` is null, use empty string

### API Endpoints

**Summarization:**
- `GET /api/summaries?transcription_id={id}` - List all summaries for a transcription
- `GET /api/summaries/{summary_id}` - Get a specific summary by ID
- `POST /api/summaries` - Generate and save a new summary
  - Request body: `{"transcription_id": "...", "api_endpoint": "...", "model": "...", "api_key_ref": "...", "system_prompt": "..."}`
  - Returns: Summary object with generated text
- `GET /api/summaries/{summary_id}/export/{format}` - Download summary (txt, json)
- `DELETE /api/summaries/{summary_id}` - Delete a summary

**Tag Configuration:**
- `GET /api/config/tags` - Get all tag configs (reads from file)
- `POST /api/config/tags` - Create new tag config (writes to file)
  - Request body: `{"tag_name": "...", "api_endpoint": "...", "model": "...", "api_key_ref": "...", "system_prompt": "..."}`
- `PUT /api/config/tags/{tag_name}` - Update tag config
- `DELETE /api/config/tags/{tag_name}` - Delete tag config
- `GET /api/config/tags/default` - Get default config
- `PUT /api/config/tags/default` - Update default config

**Secrets Management:**
- `GET /api/config/secrets` - List secret key names only (not values)
- `POST /api/config/secrets` - Add/update a secret
  - Request body: `{"key_name": "openai", "key_value": "sk-..."}`
- `DELETE /api/config/secrets/{key_name}` - Delete a secret

**Web Routes:**
- `GET /summarize` - Summarize page
- `GET /settings/tags` - Tag configuration settings page

## User Interface

### Summarize Page (`/summarize`)

**Layout Sections:**

**1. Transcription Selector**
- Heading: "Select a Transcription to Summarize"
- Display recent transcriptions in a list (similar to homepage)
- Each item: radio button, title, date, tags (chips), word count
- Show 20 most recent with pagination/load more
- Support URL parameter `?transcription_id=xyz` to pre-select
- Auto-populate config when selection changes

**2. Configuration Form**
- Visible after transcription selected
- Heading: "Summary Configuration"
- Info banner: "Using tag: supersummarize" or "Using default config"
- Editable fields:
  - API Endpoint (text input)
  - Model (text input)
  - API Key (password input, shows "Using saved key: openai" if ref exists)
  - System Prompt (textarea, expandable)
- Token counter showing estimated tokens for the transcription text
- "Generate Summary" button

**3. Results Section**
- Visible after summary generated
- Heading: "Generated Summary"
- Summary text in readonly textarea or formatted div
- Metadata: timestamp, generation time, tokens used
- Actions:
  - Download as TXT
  - Download as JSON
  - "View All Summaries for This Transcription" link

**User Flow:**
1. User selects transcription → Config auto-populates
2. User reviews/edits config → Clicks "Generate"
3. Loading spinner during API call
4. Summary appears → Download or view history

### Settings Page (`/settings/tags`)

**Layout Sections:**

**1. Tag Configurations**
- Heading: "Tag Summarization Configurations"
- Table/list view with columns:
  - Tag Name
  - Model
  - Endpoint (truncated if long)
  - API Key (shows ref name or "none")
  - Actions: Edit, Delete
- "Add New Tag Configuration" button

**2. Default Configuration**
- Heading: "Default Configuration"
- Current default shown in card/panel
- "Edit Default" button
- Info: Used when transcriptions have no matching tag configs

**3. API Keys Management**
- Heading: "API Key Management"
- List showing only key names (not values):
  - Key name (e.g., "openai")
  - Actions: Edit, Delete
- "Add API Key" button

**Modals:**
- Add/Edit Tag Config: tag name, endpoint, model, api_key_ref (dropdown), system prompt
- Edit Default Config: same fields minus tag name
- Add/Edit API Key: key name, key value (password input)

**File Operations:**
All changes write immediately to `tag_configs.json` and `secrets.json` via API. Show success/error toast messages.

## External API Integration

**Format:** OpenAI-compatible API
**Why:** Ollama supports this format, covers both OpenAI and Ollama requirements, compatible with many providers

**Request Format:**
```json
POST {api_endpoint}/chat/completions
Headers:
  Authorization: Bearer {api_key}
  Content-Type: application/json

Body:
{
  "model": "{model}",
  "messages": [
    {
      "role": "system",
      "content": "{system_prompt}"
    },
    {
      "role": "user",
      "content": "{transcription_full_text}"
    }
  ]
}
```

**Response Handling:**
- Extract `choices[0].message.content` as summary text
- Extract `usage.prompt_tokens` and `usage.completion_tokens` if available
- Measure API call duration for `generation_time_ms`

## Error Handling

**API Call Failures:**
- Display error in dismissible alert banner
- Keep form populated for retry
- No database record created for failures

**Missing Configurations:**
- Create `tag_configs.json` with defaults if missing
- Create empty `secrets.json` if missing
- Use empty string for API key if ref doesn't exist

**File Write Failures:**
- Show error modal on settings page
- Don't update UI if write fails
- Validate JSON before writing

**Missing Transcriptions:**
- Show "Transcription not found" if URL param invalid
- Display full transcription selector

**Deleted Transcriptions:**
- Summaries remain if transcription deleted (orphaned but accessible)
- Consider cascade delete in future

**Long API Responses:**
- Show loading spinner during call
- Implement 60-second timeout

**Large Transcriptions:**
- Token counter warns if approaching model limits (~128k for GPT-4)
- Consider truncation or warning before API call

## Service Modules

**New Services:**

`frontend/services/config_manager.py`
- Read/write `tag_configs.json`
- Read/write `secrets.json`
- Resolve configuration for a transcription
- Resolve API keys (env vars → secrets file)

`frontend/services/summarizer.py`
- Call external API with OpenAI-compatible format
- Handle request/response formatting
- Measure timing and extract metadata
- Store result in database

## Migration

**Database Migration:**
- Create `summaries` table with indexes
- No changes to existing tables

**Configuration Files:**
- Create `frontend/config/` directory
- Add `frontend/config/tag_configs.json` with default config
- Add `frontend/config/secrets.json` to `.gitignore`
- Create `frontend/config/.gitignore` to ignore `secrets.json`

## Future Enhancements

- Streaming response support for long summaries
- Batch summarization of multiple transcriptions
- Summary comparison view (compare multiple summaries of same transcription)
- Additional export formats (Markdown, PDF)
- Summary templates/presets beyond tags
- Integration with transcription detail page (quick summarize button)

## Open Questions

None - design validated.
