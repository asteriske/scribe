# HTML Email Formatting Design

## Overview

Send attractive HTML emails with proper rendering of summaries (tables, bold, lists), with plain text fallback for clients that don't support HTML.

## Problem

Currently, the emailer sends plain text emails containing markdown formatting from the LLM-generated summary. This results in raw markdown syntax (tables, `**bold**`, etc.) appearing as ugly text instead of rendering properly.

## Solution

1. Have the LLM produce HTML instead of markdown by appending an instruction to the system prompt
2. Build HTML emails with minimal, clean styling
3. Include a plain text fallback using `html2text` to convert the HTML summary

## Data Flow

```
1. Emailer requests summary from frontend API
   - Passes: transcription_id, system_prompt_suffix="Format with HTML..."

2. Frontend summarizer
   - Resolves base system_prompt from tag config or default
   - Appends the suffix
   - Calls LLM → receives HTML-formatted summary

3. Emailer receives HTML summary
   - result_formatter.py builds full HTML email:
     • HTML header (source, duration, timestamp)
     • HTML summary (from LLM, as-is)
     • HTML transcript (wrapped in paragraphs)
   - Also builds plain text version using html2text

4. smtp_client.py sends multipart email (HTML + plain text)
```

## Implementation Details

### Frontend API Changes

**`frontend/frontend/api/models.py`** - Add field to SummaryRequest:

```python
class SummaryRequest(BaseModel):
    transcription_id: str
    api_endpoint: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    system_prompt: Optional[str] = None
    system_prompt_suffix: Optional[str] = None  # NEW
```

**`frontend/frontend/services/summarizer.py`** - Append suffix to resolved prompt:

```python
def generate_summary(
    self,
    db: Session,
    transcription_id: str,
    ...
    system_prompt: Optional[str] = None,
    system_prompt_suffix: Optional[str] = None,  # NEW
) -> SummaryResult:
    ...
    # Resolve base prompt
    final_prompt = system_prompt or resolved.system_prompt

    # Append suffix if provided
    if system_prompt_suffix:
        final_prompt = f"{final_prompt}\n\n{system_prompt_suffix}"
```

**`frontend/frontend/api/routes.py`** - Pass suffix through:

```python
result = summarizer.generate_summary(
    ...
    system_prompt=request.system_prompt,
    system_prompt_suffix=request.system_prompt_suffix,
)
```

### Emailer Client Changes

**`emailer/emailer/frontend_client.py`** - Add suffix constant and parameter:

```python
HTML_SUMMARY_SUFFIX = """Format your response using valid HTML elements (headings, paragraphs, lists, tables, etc.). Do not include <html>, <head>, or <body> tags - only the inner content."""

async def generate_summary(
    self,
    transcription_id: str,
    system_prompt_suffix: str | None = None,
) -> str:
    ...
    async with httpx.AsyncClient(timeout=360.0) as client:
        response = await client.post(
            f"{self.base_url}/api/summaries",
            json={
                "transcription_id": transcription_id,
                "system_prompt_suffix": system_prompt_suffix,
            },
        )
```

**`emailer/emailer/job_processor.py`** - Pass the suffix when calling:

```python
from emailer.frontend_client import HTML_SUMMARY_SUFFIX

summary = await self.frontend.generate_summary(
    transcription_id,
    system_prompt_suffix=HTML_SUMMARY_SUFFIX,
)
```

### HTML Email Generation

**`emailer/emailer/result_formatter.py`** - Generate both HTML and plain text:

```python
import html2text

def format_success_email(
    url: str,
    title: str,
    duration_seconds: int,
    summary: str,  # Now HTML from LLM
    transcript: str,
) -> Tuple[str, str, str]:  # Returns (subject, html_body, text_body)

    # HTML version
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .metadata {{ color: #666; font-size: 14px; border-bottom: 1px solid #eee; padding-bottom: 16px; margin-bottom: 24px; }}
        .section-title {{ font-size: 14px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin: 32px 0 16px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="metadata">
        <div><strong>Source:</strong> <a href="{url}">{url}</a></div>
        <div><strong>Duration:</strong> {duration}</div>
        <div><strong>Transcribed:</strong> {timestamp}</div>
    </div>

    <div class="section-title">Summary</div>
    {summary}

    <div class="section-title">Transcript</div>
    <p>{escaped_transcript_with_line_breaks}</p>
</body>
</html>"""

    # Plain text version
    h = html2text.HTML2Text()
    h.ignore_links = False
    plain_summary = h.handle(summary)

    text_body = f"""Source: {url}
Duration: {duration}
Transcribed: {timestamp}

--- SUMMARY ---

{plain_summary}

--- TRANSCRIPT ---

{transcript}"""

    return subject, html_body, text_body
```

### Multipart Email Sending

**`emailer/emailer/smtp_client.py`** - Support HTML + plain text:

```python
from email.message import EmailMessage

async def send_email(
    self,
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    # Set plain text as the base content
    msg.set_content(body)

    # Add HTML alternative if provided
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    # ... rest of sending logic unchanged
```

**`emailer/emailer/main.py`** - Pass both bodies:

```python
async def _send_result_email(self, email, result, tag_config):
    if result.success:
        subject, html_body, text_body = format_success_email(...)

        for to_addr in recipients:
            await self.smtp.send_email(
                from_addr=self.settings.from_email_address,
                to_addr=to_addr,
                subject=subject,
                body=text_body,
                html_body=html_body,
            )
```

Error emails (`format_error_email`, `format_no_urls_email`) remain plain text since they're simple messages.

## Dependencies

Add `html2text` to `emailer/pyproject.toml`:

```toml
dependencies = [
    ...
    "html2text>=2024.2.26",
]
```

## Files Changed

| File | Change |
|------|--------|
| `frontend/frontend/api/models.py` | Add `system_prompt_suffix` field |
| `frontend/frontend/services/summarizer.py` | Append suffix to resolved prompt |
| `frontend/frontend/api/routes.py` | Pass suffix to summarizer |
| `emailer/emailer/frontend_client.py` | Add suffix constant, pass to API |
| `emailer/emailer/job_processor.py` | Pass suffix when requesting summary |
| `emailer/emailer/result_formatter.py` | Return HTML + plain text tuple |
| `emailer/emailer/smtp_client.py` | Support multipart emails |
| `emailer/emailer/main.py` | Wire up the new signatures |
| `emailer/pyproject.toml` | Add html2text dependency |

## Testing

- Update `test_result_formatter.py` for new return signature (3-tuple instead of 2-tuple)
- Update `test_smtp_client.py` for optional html_body parameter
- Manual test: send a test email and verify HTML renders correctly in email client

## Design Decisions

1. **HTML instruction appended in emailer** - The emailer controls what format it needs; the summarizer stays format-agnostic
2. **Minimal CSS styling** - Works reliably across email clients; uses system fonts and light borders
3. **html2text for plain text fallback** - Preserves structure (tables become ASCII, lists remain readable)
4. **Error emails stay plain text** - They're simple messages that don't need formatting
