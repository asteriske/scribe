# HTML Email Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Send attractive HTML emails with proper rendering of LLM-generated summaries, with plain text fallback.

**Architecture:** Add `system_prompt_suffix` parameter to frontend API so emailer can request HTML-formatted summaries. Emailer builds multipart emails (HTML + plain text) using html2text for the fallback.

**Tech Stack:** Python, FastAPI, aiosmtplib, html2text, Pydantic

---

## Task 1: Add system_prompt_suffix to Frontend API Models

**Files:**
- Modify: `frontend/frontend/api/models.py:52-58`
- Test: `frontend/tests/test_api.py`

**Step 1: Write the failing test**

Add to `frontend/tests/test_api.py`:

```python
def test_summary_request_accepts_suffix():
    """Test that SummaryRequest accepts system_prompt_suffix."""
    from frontend.api.models import SummaryRequest

    request = SummaryRequest(
        transcription_id="test123",
        system_prompt_suffix="Format as HTML"
    )
    assert request.system_prompt_suffix == "Format as HTML"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/frontend && python -m pytest tests/test_api.py::test_summary_request_accepts_suffix -v`
Expected: FAIL with ValidationError or AttributeError

**Step 3: Write minimal implementation**

In `frontend/frontend/api/models.py`, add to `SummaryRequest` class:

```python
class SummaryRequest(BaseModel):
    """Request to generate a summary."""
    transcription_id: str = Field(..., description="ID of the transcription to summarize")
    api_endpoint: Optional[str] = Field(None, description="Override API endpoint")
    model: Optional[str] = Field(None, description="Override model name")
    api_key: Optional[str] = Field(None, description="Override API key")
    system_prompt: Optional[str] = Field(None, description="Override system prompt")
    system_prompt_suffix: Optional[str] = Field(None, description="Append to system prompt")
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/frontend && python -m pytest tests/test_api.py::test_summary_request_accepts_suffix -v`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/frontend/api/models.py frontend/tests/test_api.py
git commit -m "feat(frontend): add system_prompt_suffix field to SummaryRequest"
```

---

## Task 2: Handle system_prompt_suffix in Summarizer Service

**Files:**
- Modify: `frontend/frontend/services/summarizer.py:118-190`
- Test: `frontend/tests/test_summarizer.py`

**Step 1: Write the failing test**

Add to `frontend/tests/test_summarizer.py`:

```python
def test_generate_summary_appends_suffix(mock_db, mock_transcription):
    """Test that system_prompt_suffix is appended to the resolved prompt."""
    from unittest.mock import patch, MagicMock
    from frontend.services.summarizer import SummarizerService

    with patch.object(SummarizerService, '_call_llm_api') as mock_llm:
        mock_llm.return_value = ("Summary text", {"prompt_tokens": 100}, None)

        service = SummarizerService()
        result = service.generate_summary(
            db=mock_db,
            transcription_id=mock_transcription.id,
            system_prompt_suffix="Format using HTML elements."
        )

        # Verify the suffix was appended to the prompt
        call_args = mock_llm.call_args
        system_prompt_used = call_args[0][3]  # 4th positional arg is system_prompt
        assert "Format using HTML elements." in system_prompt_used
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/frontend && python -m pytest tests/test_summarizer.py::test_generate_summary_appends_suffix -v`
Expected: FAIL - TypeError (unexpected keyword argument 'system_prompt_suffix')

**Step 3: Write minimal implementation**

In `frontend/frontend/services/summarizer.py`, modify `generate_summary` method:

```python
def generate_summary(
    self,
    db: Session,
    transcription_id: str,
    api_endpoint: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    system_prompt: Optional[str] = None,
    system_prompt_suffix: Optional[str] = None,
) -> SummaryResult:
```

And after resolving the prompt (around line 167):

```python
final_prompt = system_prompt or resolved.system_prompt

# Append suffix if provided
if system_prompt_suffix:
    final_prompt = f"{final_prompt}\n\n{system_prompt_suffix}"
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/frontend && python -m pytest tests/test_summarizer.py::test_generate_summary_appends_suffix -v`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/frontend/services/summarizer.py frontend/tests/test_summarizer.py
git commit -m "feat(frontend): support system_prompt_suffix in summarizer"
```

---

## Task 3: Pass system_prompt_suffix Through API Route

**Files:**
- Modify: `frontend/frontend/api/routes.py:377-390`
- Test: Already covered by integration

**Step 1: Verify current behavior**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/frontend && python -m pytest tests/test_api.py -v -k summary`
Expected: All summary tests pass

**Step 2: Update the route**

In `frontend/frontend/api/routes.py`, update the `create_summary` function:

```python
result = summarizer.generate_summary(
    db=db,
    transcription_id=request.transcription_id,
    api_endpoint=request.api_endpoint,
    model=request.model,
    api_key=request.api_key,
    system_prompt=request.system_prompt,
    system_prompt_suffix=request.system_prompt_suffix,
)
```

**Step 3: Verify tests still pass**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/frontend && python -m pytest tests/test_api.py -v -k summary`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/frontend/api/routes.py
git commit -m "feat(frontend): pass system_prompt_suffix through API route"
```

---

## Task 4: Add html2text Dependency to Emailer

**Files:**
- Modify: `emailer/requirements.txt`

**Step 1: Add dependency**

Add to `emailer/requirements.txt`:

```
html2text>=2024.2.26
```

**Step 2: Install dependency**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && pip install -r requirements.txt`
Expected: Successfully installed html2text

**Step 3: Verify import works**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -c "import html2text; print('OK')"`
Expected: OK

**Step 4: Commit**

```bash
git add emailer/requirements.txt
git commit -m "feat(emailer): add html2text dependency"
```

---

## Task 5: Update FrontendClient to Pass system_prompt_suffix

**Files:**
- Modify: `emailer/emailer/frontend_client.py:170-194`
- Test: `emailer/tests/test_frontend_client.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_frontend_client.py`:

```python
@pytest.mark.asyncio
async def test_generate_summary_with_suffix(self):
    """Test that generate_summary passes system_prompt_suffix."""
    with patch("emailer.frontend_client.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {"summary_text": "HTML summary"},
            )
        )

        client = FrontendClient(base_url="http://localhost:8000")
        result = await client.generate_summary(
            "test123",
            system_prompt_suffix="Format as HTML"
        )

        assert result == "HTML summary"
        mock_instance.post.assert_called_once()
        call_args = mock_instance.post.call_args
        assert call_args[1]["json"]["system_prompt_suffix"] == "Format as HTML"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_frontend_client.py::TestFrontendClient::test_generate_summary_with_suffix -v`
Expected: FAIL - TypeError (unexpected keyword argument)

**Step 3: Write minimal implementation**

In `emailer/emailer/frontend_client.py`, update `generate_summary`:

```python
async def generate_summary(
    self,
    transcription_id: str,
    system_prompt_suffix: str | None = None,
) -> str:
    """
    Generate a summary for a transcription.

    Args:
        transcription_id: ID of the transcription
        system_prompt_suffix: Optional suffix to append to system prompt

    Returns:
        Summary text

    Raises:
        httpx.HTTPStatusError: If the request fails
    """
    logger.debug(f"POST /api/summaries starting for {transcription_id}")
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=360.0) as client:
        payload = {"transcription_id": transcription_id}
        if system_prompt_suffix:
            payload["system_prompt_suffix"] = system_prompt_suffix

        response = await client.post(
            f"{self.base_url}/api/summaries",
            json=payload,
        )
        elapsed = time.monotonic() - start
        response.raise_for_status()
        data = response.json()
        logger.info(f"Generated summary for {transcription_id} ({elapsed:.2f}s)")
        return data["summary_text"]
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_frontend_client.py::TestFrontendClient::test_generate_summary_with_suffix -v`
Expected: PASS

**Step 5: Commit**

```bash
git add emailer/emailer/frontend_client.py emailer/tests/test_frontend_client.py
git commit -m "feat(emailer): support system_prompt_suffix in frontend client"
```

---

## Task 6: Add HTML_SUMMARY_SUFFIX Constant and Update JobProcessor

**Files:**
- Modify: `emailer/emailer/frontend_client.py` (add constant)
- Modify: `emailer/emailer/job_processor.py:46-59, 96-102`
- Test: `emailer/tests/test_job_processor.py`

**Step 1: Add the constant**

At the top of `emailer/emailer/frontend_client.py` after imports:

```python
HTML_SUMMARY_SUFFIX = """Format your response using valid HTML elements (headings, paragraphs, lists, tables, etc.). Do not include <html>, <head>, or <body> tags - only the inner content."""
```

**Step 2: Write the failing test**

Add to `emailer/tests/test_job_processor.py`:

```python
@pytest.mark.asyncio
async def test_process_url_requests_html_summary():
    """Test that process_url requests HTML-formatted summary."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from emailer.job_processor import JobProcessor
    from emailer.frontend_client import FrontendClient, HTML_SUMMARY_SUFFIX

    mock_frontend = AsyncMock(spec=FrontendClient)
    mock_frontend.submit_url = AsyncMock(return_value="test-id")
    mock_frontend.wait_for_completion = AsyncMock(return_value=MagicMock(
        status="completed",
        title="Test",
        duration_seconds=60,
    ))
    mock_frontend.get_transcript_text = AsyncMock(return_value="Transcript text")
    mock_frontend.generate_summary = AsyncMock(return_value="<p>Summary</p>")

    processor = JobProcessor(frontend_client=mock_frontend)
    result = await processor.process_url("https://example.com/audio.mp3")

    # Verify generate_summary was called with HTML suffix
    mock_frontend.generate_summary.assert_called_once_with(
        "test-id",
        system_prompt_suffix=HTML_SUMMARY_SUFFIX,
    )
```

**Step 3: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_job_processor.py::test_process_url_requests_html_summary -v`
Expected: FAIL - AssertionError (called without suffix)

**Step 4: Write minimal implementation**

In `emailer/emailer/job_processor.py`, add import and update calls:

```python
from emailer.frontend_client import FrontendClient, HTML_SUMMARY_SUFFIX
```

Update `_process_existing` method:

```python
summary = await self.frontend.generate_summary(
    transcription_id,
    system_prompt_suffix=HTML_SUMMARY_SUFFIX,
)
```

Update `process_url` method:

```python
summary = await self.frontend.generate_summary(
    transcription_id,
    system_prompt_suffix=HTML_SUMMARY_SUFFIX,
)
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_job_processor.py::test_process_url_requests_html_summary -v`
Expected: PASS

**Step 6: Commit**

```bash
git add emailer/emailer/frontend_client.py emailer/emailer/job_processor.py emailer/tests/test_job_processor.py
git commit -m "feat(emailer): request HTML-formatted summaries from frontend"
```

---

## Task 7: Update result_formatter to Generate HTML and Plain Text

**Files:**
- Modify: `emailer/emailer/result_formatter.py`
- Test: `emailer/tests/test_result_formatter.py`

**Step 1: Write the failing test**

Replace/update tests in `emailer/tests/test_result_formatter.py`:

```python
def test_format_success_email_returns_three_values():
    """Test that format_success_email returns subject, html_body, text_body."""
    from emailer.result_formatter import format_success_email

    result = format_success_email(
        url="https://example.com/video",
        title="Test Video",
        duration_seconds=120,
        summary="<p>This is an <strong>HTML</strong> summary.</p>",
        transcript="This is the transcript.",
    )

    assert len(result) == 3
    subject, html_body, text_body = result

    # Check subject
    assert "[Scribe]" in subject
    assert "Test Video" in subject

    # Check HTML body
    assert "<!DOCTYPE html>" in html_body
    assert "<p>This is an <strong>HTML</strong> summary.</p>" in html_body
    assert "https://example.com/video" in html_body

    # Check plain text body
    assert "--- SUMMARY ---" in text_body
    assert "--- TRANSCRIPT ---" in text_body
    assert "This is the transcript." in text_body


def test_format_success_email_html_escapes_transcript():
    """Test that transcript is HTML-escaped in HTML body."""
    from emailer.result_formatter import format_success_email

    _, html_body, _ = format_success_email(
        url="https://example.com",
        title="Test",
        duration_seconds=60,
        summary="<p>Summary</p>",
        transcript="Text with <script>alert('xss')</script> tags",
    )

    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_result_formatter.py -v`
Expected: FAIL - wrong number of values to unpack

**Step 3: Write minimal implementation**

Replace `emailer/emailer/result_formatter.py`:

```python
"""Format emails for transcription results and errors."""

import html
from datetime import datetime, timezone
from typing import Tuple

import html2text


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}:{secs:02d}"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{mins:02d}:{secs:02d}"


def _html_to_plain_text(html_content: str) -> str:
    """Convert HTML to readable plain text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0  # Don't wrap lines
    return h.handle(html_content).strip()


def format_success_email(
    url: str,
    title: str,
    duration_seconds: int,
    summary: str,
    transcript: str,
) -> Tuple[str, str, str]:
    """
    Format a success email with summary and transcript.

    Args:
        url: Source URL
        title: Content title
        duration_seconds: Duration in seconds
        summary: Generated summary (HTML from LLM)
        transcript: Full transcript text

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    # Truncate title for subject if too long
    max_title_len = 100
    display_title = title[:max_title_len] + "..." if len(title) > max_title_len else title
    subject = f"[Scribe] {display_title}"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    duration = _format_duration(duration_seconds)

    # Escape transcript for HTML (prevent XSS)
    escaped_transcript = html.escape(transcript)
    # Convert newlines to <br> for HTML display
    html_transcript = escaped_transcript.replace("\n", "<br>\n")

    # HTML version
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .metadata {{ color: #666; font-size: 14px; border-bottom: 1px solid #eee; padding-bottom: 16px; margin-bottom: 24px; }}
        .metadata a {{ color: #0066cc; }}
        .section-title {{ font-size: 14px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin: 32px 0 16px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .transcript {{ font-size: 14px; color: #444; }}
    </style>
</head>
<body>
    <div class="metadata">
        <div><strong>Source:</strong> <a href="{html.escape(url)}">{html.escape(url)}</a></div>
        <div><strong>Duration:</strong> {duration}</div>
        <div><strong>Transcribed:</strong> {timestamp}</div>
    </div>

    <div class="section-title">Summary</div>
    {summary}

    <div class="section-title">Transcript</div>
    <div class="transcript">{html_transcript}</div>
</body>
</html>"""

    # Plain text version
    plain_summary = _html_to_plain_text(summary)

    text_body = f"""Source: {url}
Duration: {duration}
Transcribed: {timestamp}

--- SUMMARY ---

{plain_summary}

--- TRANSCRIPT ---

{transcript}
"""

    return subject, html_body, text_body


def format_error_email(
    url: str,
    error_message: str,
) -> Tuple[str, str]:
    """
    Format an error notification email.

    Args:
        url: URL that failed
        error_message: Error description

    Returns:
        Tuple of (subject, body)
    """
    subject = "[Scribe Error] Failed to process URL"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""The following URL could not be transcribed:

{url}

Error: {error_message}

---
Original request received: {timestamp}
"""

    return subject, body


def format_no_urls_email() -> Tuple[str, str]:
    """
    Format an email for when no transcribable URLs were found.

    Returns:
        Tuple of (subject, body)
    """
    subject = "[Scribe Error] No transcribable URLs found"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""Your email did not contain any transcribable URLs.

Supported sources:
- YouTube (youtube.com, youtu.be)
- Apple Podcasts (podcasts.apple.com)
- Direct audio URLs (.mp3, .m4a, .wav)

---
Original request received: {timestamp}
"""

    return subject, body
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_result_formatter.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add emailer/emailer/result_formatter.py emailer/tests/test_result_formatter.py
git commit -m "feat(emailer): generate HTML and plain text email bodies"
```

---

## Task 8: Update SmtpClient to Support Multipart Emails

**Files:**
- Modify: `emailer/emailer/smtp_client.py`
- Modify: `emailer/tests/test_smtp_client.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_smtp_client.py`:

```python
@pytest.mark.asyncio
async def test_send_email_with_html_body(self):
    """Test sending email with HTML alternative."""
    with patch("emailer.smtp_client.SMTP") as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value = mock_instance
        mock_instance.connect = AsyncMock()
        mock_instance.login = AsyncMock()
        mock_instance.send_message = AsyncMock()
        mock_instance.quit = AsyncMock()

        client = SmtpClient(
            host="smtp.test.com",
            port=587,
            user="test@test.com",
            password="testpass",
            use_tls=True,
        )

        await client.send_email(
            from_addr="from@test.com",
            to_addr="to@test.com",
            subject="Test Subject",
            body="Plain text body",
            html_body="<p>HTML body</p>",
        )

        mock_instance.send_message.assert_called_once()
        call_args = mock_instance.send_message.call_args
        msg = call_args[0][0]

        # Check it's a multipart message
        assert msg.is_multipart()

        # Get parts
        parts = list(msg.iter_parts())
        content_types = [part.get_content_type() for part in parts]
        assert "text/plain" in content_types
        assert "text/html" in content_types
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_smtp_client.py::TestSmtpClient::test_send_email_with_html_body -v`
Expected: FAIL - TypeError (unexpected keyword argument 'html_body')

**Step 3: Write minimal implementation**

Update `emailer/emailer/smtp_client.py`:

```python
async def send_email(
    self,
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> None:
    """
    Send an email.

    Args:
        from_addr: Sender email address
        to_addr: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        html_body: Optional HTML body (creates multipart email)
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    # Set plain text as base content
    msg.set_content(body)

    # Add HTML alternative if provided
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    # Port 587 uses STARTTLS (start_tls=True), port 465 uses implicit TLS (use_tls=True)
    use_implicit_tls = self.port == 465
    smtp = SMTP(
        hostname=self.host,
        port=self.port,
        use_tls=use_implicit_tls,
        start_tls=self.use_tls and not use_implicit_tls,
    )

    try:
        logger.debug(f"Connecting to SMTP server {self.host}:{self.port}")
        await smtp.connect()
        logger.debug("SMTP connected, logging in...")
        await smtp.login(self.user, self.password)
        await smtp.send_message(msg)

        logger.info(f"Sent email to {to_addr}: {subject}")

    finally:
        await smtp.quit()
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_smtp_client.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add emailer/emailer/smtp_client.py emailer/tests/test_smtp_client.py
git commit -m "feat(emailer): support HTML alternative in emails"
```

---

## Task 9: Update main.py to Wire Everything Together

**Files:**
- Modify: `emailer/emailer/main.py:205-241`
- Test: `emailer/tests/test_main.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_main.py`:

```python
@pytest.mark.asyncio
async def test_send_result_email_uses_html():
    """Test that successful result emails include HTML body."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from emailer.main import EmailerService
    from emailer.job_processor import JobResult
    from emailer.imap_client import EmailMessage

    with patch("emailer.main.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            from_email_address="scribe@test.com",
        )

        service = EmailerService(mock_settings.return_value)
        service.smtp = AsyncMock()

        email = EmailMessage(
            msg_num=1,
            sender="user@test.com",
            subject="Test",
            body_text="",
            body_html="",
        )

        result = JobResult(
            url="https://example.com/video",
            success=True,
            title="Test Video",
            summary="<p>HTML summary</p>",
            transcript="Transcript text",
            duration_seconds=120,
        )

        await service._send_result_email(email, result, tag_config=None)

        service.smtp.send_email.assert_called_once()
        call_kwargs = service.smtp.send_email.call_args[1]

        # Verify html_body was passed
        assert "html_body" in call_kwargs
        assert "<!DOCTYPE html>" in call_kwargs["html_body"]
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_main.py::test_send_result_email_uses_html -v`
Expected: FAIL - html_body not in call

**Step 3: Write minimal implementation**

Update `emailer/emailer/main.py`, specifically `_send_result_email`:

```python
async def _send_result_email(
    self, email: EmailMessage, result: JobResult, tag_config: dict | None = None
) -> None:
    """Send result or error email based on job result."""
    if result.success:
        subject, html_body, text_body = format_success_email(
            url=result.url,
            title=result.title or "Untitled",
            duration_seconds=result.duration_seconds or 0,
            summary=result.summary or "",
            transcript=result.transcript or "",
        )
        # Use tag's destination_emails if set, otherwise reply to sender
        destination_emails = tag_config.get("destination_emails", []) if tag_config else []
        if destination_emails:
            recipients = destination_emails
        else:
            recipients = [email.sender]

        for to_addr in recipients:
            await self.smtp.send_email(
                from_addr=self.settings.from_email_address,
                to_addr=to_addr,
                subject=subject,
                body=text_body,
                html_body=html_body,
            )
    else:
        subject, body = format_error_email(
            url=result.url,
            error_message=result.error or "Unknown error",
        )
        await self.smtp.send_email(
            from_addr=self.settings.from_email_address,
            to_addr=email.sender,
            subject=subject,
            body=body,
        )
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/test_main.py::test_send_result_email_uses_html -v`
Expected: PASS

**Step 5: Run all emailer tests**

Run: `cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add emailer/emailer/main.py emailer/tests/test_main.py
git commit -m "feat(emailer): send HTML emails for successful transcriptions"
```

---

## Task 10: Final Integration Test and Cleanup

**Step 1: Run all tests**

Run frontend tests:
```bash
cd /Users/patrick/git/scribe/.worktrees/html-emails/frontend && python -m pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/test_orchestrator.py
```
Expected: All PASS (ignoring known SQLite issues)

Run emailer tests:
```bash
cd /Users/patrick/git/scribe/.worktrees/html-emails/emailer && python -m pytest tests/ -v
```
Expected: All PASS

**Step 2: Create final commit with any remaining fixes**

If any tests fail, fix them and commit.

**Step 3: Summary commit message for PR**

The feature is complete. Ready for code review and PR creation.
