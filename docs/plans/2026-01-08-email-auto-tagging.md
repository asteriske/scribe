# Email Auto-Tagging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically tag email-submitted transcriptions based on subject line keywords to enable tag-based summarization settings.

**Architecture:** The emailer fetches available tags from the frontend API, matches words in the email subject against tag names (case-insensitive), and submits jobs with the resolved tag. Falls back to a configurable default tag when no match is found.

**Tech Stack:** Python, pydantic-settings, httpx, FastAPI

---

## Task 1: Add default_tag config to emailer

**Files:**
- Modify: `emailer/emailer/config.py:6-48`
- Test: `emailer/tests/test_config.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_config.py`:

```python
def test_default_tag_config():
    """Test that default_tag can be configured."""
    import os
    os.environ["DEFAULT_TAG"] = "inbox"
    os.environ["IMAP_HOST"] = "imap.test.com"
    os.environ["IMAP_USER"] = "test"
    os.environ["IMAP_PASSWORD"] = "test"
    os.environ["SMTP_HOST"] = "smtp.test.com"
    os.environ["SMTP_USER"] = "test"
    os.environ["SMTP_PASSWORD"] = "test"
    os.environ["RESULT_EMAIL_ADDRESS"] = "results@test.com"
    os.environ["FROM_EMAIL_ADDRESS"] = "scribe@test.com"

    from emailer.config import Settings
    settings = Settings()
    assert settings.default_tag == "inbox"

    # Cleanup
    del os.environ["DEFAULT_TAG"]
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && python -m pytest tests/test_config.py::test_default_tag_config -v`
Expected: FAIL with "Settings object has no field 'default_tag'"

**Step 3: Write minimal implementation**

In `emailer/emailer/config.py`, add to the `Settings` class after line 43 (after `frontend_url`):

```python
    # Tagging
    default_tag: str = "email"
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && python -m pytest tests/test_config.py::test_default_tag_config -v`
Expected: PASS

**Step 5: Commit**

```bash
git add emailer/emailer/config.py emailer/tests/test_config.py
git commit -m "feat(emailer): add default_tag config option"
```

---

## Task 2: Add get_tags method to FrontendClient

**Files:**
- Modify: `emailer/emailer/frontend_client.py:24-168`
- Test: `emailer/tests/test_frontend_client.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_frontend_client.py`:

```python
@pytest.mark.asyncio
async def test_get_tags(mock_response):
    """Test fetching tags from frontend."""
    client = FrontendClient(base_url="http://localhost:8000")

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response({"tags": ["podcast", "interview", "meeting"]})

        tags = await client.get_tags()

        assert tags == {"podcast", "interview", "meeting"}
        mock_get.assert_called_once_with("http://localhost:8000/api/tags")
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && python -m pytest tests/test_frontend_client.py::test_get_tags -v`
Expected: FAIL with "FrontendClient has no method 'get_tags'"

**Step 3: Write minimal implementation**

Add to `emailer/emailer/frontend_client.py` after `submit_url` method (after line 52):

```python
    async def get_tags(self) -> set[str]:
        """
        Fetch available tags from frontend.

        Returns:
            Set of tag names

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return set(data.get("tags", []))
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && python -m pytest tests/test_frontend_client.py::test_get_tags -v`
Expected: PASS

**Step 5: Commit**

```bash
git add emailer/emailer/frontend_client.py emailer/tests/test_frontend_client.py
git commit -m "feat(emailer): add get_tags method to FrontendClient"
```

---

## Task 3: Add tag parameter to submit_url

**Files:**
- Modify: `emailer/emailer/frontend_client.py:31-52`
- Test: `emailer/tests/test_frontend_client.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_frontend_client.py`:

```python
@pytest.mark.asyncio
async def test_submit_url_with_tag(mock_response):
    """Test submitting URL with a tag."""
    client = FrontendClient(base_url="http://localhost:8000")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response({"id": "test-123"})

        result = await client.submit_url("https://example.com/audio.mp3", tag="podcast")

        assert result == "test-123"
        mock_post.assert_called_once_with(
            "http://localhost:8000/api/transcribe",
            json={"url": "https://example.com/audio.mp3", "tags": ["podcast"]},
        )
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && python -m pytest tests/test_frontend_client.py::test_submit_url_with_tag -v`
Expected: FAIL with "submit_url() got unexpected keyword argument 'tag'"

**Step 3: Write minimal implementation**

Update `submit_url` in `emailer/emailer/frontend_client.py`:

```python
    async def submit_url(self, url: str, tag: str | None = None) -> str:
        """
        Submit a URL for transcription.

        Args:
            url: URL to transcribe
            tag: Optional tag to apply to the transcription

        Returns:
            Transcription ID

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {"url": url}
            if tag:
                payload["tags"] = [tag]
            response = await client.post(
                f"{self.base_url}/api/transcribe",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Submitted URL for transcription: {url} -> {data['id']}")
            return data["id"]
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && python -m pytest tests/test_frontend_client.py::test_submit_url_with_tag -v`
Expected: PASS

**Step 5: Commit**

```bash
git add emailer/emailer/frontend_client.py emailer/tests/test_frontend_client.py
git commit -m "feat(emailer): add tag parameter to submit_url"
```

---

## Task 4: Add tag parameter to JobProcessor.process_url

**Files:**
- Modify: `emailer/emailer/job_processor.py:60-132`
- Test: `emailer/tests/test_job_processor.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_job_processor.py`:

```python
@pytest.mark.asyncio
async def test_process_url_with_tag():
    """Test that tag is passed to submit_url."""
    mock_client = AsyncMock()
    mock_client.submit_url = AsyncMock(return_value="test-123")
    mock_client.wait_for_completion = AsyncMock(return_value=MagicMock(
        status="completed",
        title="Test",
        duration_seconds=100,
        error=None,
    ))
    mock_client.get_transcript_text = AsyncMock(return_value="Transcript text")
    mock_client.generate_summary = AsyncMock(return_value="Summary text")

    processor = JobProcessor(frontend_client=mock_client)
    result = await processor.process_url("https://example.com/audio.mp3", tag="podcast")

    mock_client.submit_url.assert_called_once_with("https://example.com/audio.mp3", tag="podcast")
    assert result.success is True
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && python -m pytest tests/test_job_processor.py::test_process_url_with_tag -v`
Expected: FAIL with "process_url() got unexpected keyword argument 'tag'"

**Step 3: Write minimal implementation**

Update `process_url` signature in `emailer/emailer/job_processor.py`:

```python
    async def process_url(self, url: str, tag: str | None = None) -> JobResult:
        """
        Process a single URL through transcription and summarization.

        Args:
            url: URL to process
            tag: Optional tag to apply to the transcription

        Returns:
            JobResult with success status and data or error
        """
        try:
            # Submit for transcription
            logger.info(f"Submitting URL: {url}")
            transcription_id = await self.frontend.submit_url(url, tag=tag)
```

(Rest of the method stays the same)

**Step 4: Run test to verify it passes**

Run: `cd emailer && python -m pytest tests/test_job_processor.py::test_process_url_with_tag -v`
Expected: PASS

**Step 5: Commit**

```bash
git add emailer/emailer/job_processor.py emailer/tests/test_job_processor.py
git commit -m "feat(emailer): add tag parameter to process_url"
```

---

## Task 5: Add resolve_tag function

**Files:**
- Create: `emailer/emailer/tag_resolver.py`
- Create: `emailer/tests/test_tag_resolver.py`

**Step 1: Write the failing test**

Create `emailer/tests/test_tag_resolver.py`:

```python
"""Tests for tag resolution from email subject."""

import pytest
from emailer.tag_resolver import resolve_tag


class TestResolveTag:
    """Tests for resolve_tag function."""

    def test_matches_tag_in_subject(self):
        """Test matching a word in subject to a tag."""
        result = resolve_tag(
            subject="New podcast episode",
            available_tags={"podcast", "interview", "meeting"},
            default="email",
        )
        assert result == "podcast"

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        result = resolve_tag(
            subject="PODCAST Episode",
            available_tags={"podcast", "interview"},
            default="email",
        )
        assert result == "podcast"

    def test_returns_default_when_no_match(self):
        """Test fallback to default when no match."""
        result = resolve_tag(
            subject="Random subject line",
            available_tags={"podcast", "interview"},
            default="inbox",
        )
        assert result == "inbox"

    def test_empty_subject_returns_default(self):
        """Test empty subject returns default."""
        result = resolve_tag(
            subject="",
            available_tags={"podcast", "interview"},
            default="email",
        )
        assert result == "email"

    def test_none_subject_returns_default(self):
        """Test None subject returns default."""
        result = resolve_tag(
            subject=None,
            available_tags={"podcast", "interview"},
            default="email",
        )
        assert result == "email"

    def test_empty_tags_returns_default(self):
        """Test empty available tags returns default."""
        result = resolve_tag(
            subject="podcast episode",
            available_tags=set(),
            default="email",
        )
        assert result == "email"
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && python -m pytest tests/test_tag_resolver.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'emailer.tag_resolver'"

**Step 3: Write minimal implementation**

Create `emailer/emailer/tag_resolver.py`:

```python
"""Resolve tags from email subject lines."""


def resolve_tag(
    subject: str | None,
    available_tags: set[str],
    default: str,
) -> str:
    """
    Match words in email subject against available tags.

    Args:
        subject: Email subject line (may be None or empty)
        available_tags: Set of available tag names (lowercase)
        default: Default tag to use when no match found

    Returns:
        Matched tag name or default
    """
    if not subject:
        return default

    words = subject.lower().split()
    for word in words:
        if word in available_tags:
            return word

    return default
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && python -m pytest tests/test_tag_resolver.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add emailer/emailer/tag_resolver.py emailer/tests/test_tag_resolver.py
git commit -m "feat(emailer): add resolve_tag function"
```

---

## Task 6: Integrate tag resolution in EmailerService

**Files:**
- Modify: `emailer/emailer/main.py:110-134`
- Test: `emailer/tests/test_main.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_main.py`:

```python
@pytest.mark.asyncio
async def test_process_email_resolves_tag_from_subject(mock_settings, mock_email):
    """Test that tag is resolved from email subject."""
    mock_settings.default_tag = "email"
    mock_email.subject = "New podcast episode"
    mock_email.body_text = "https://example.com/audio.mp3"

    service = EmailerService(mock_settings)

    # Mock the frontend client methods
    service.processor.frontend.get_tags = AsyncMock(return_value={"podcast", "interview"})
    service.processor.frontend.submit_url = AsyncMock(return_value="test-123")
    service.processor.frontend.wait_for_completion = AsyncMock(return_value=MagicMock(
        status="completed", title="Test", duration_seconds=100, error=None
    ))
    service.processor.frontend.get_transcript_text = AsyncMock(return_value="Text")
    service.processor.frontend.generate_summary = AsyncMock(return_value="Summary")

    # Mock SMTP and IMAP
    service.smtp.send_email = AsyncMock()
    service.imap.move_to_folder = AsyncMock()

    await service._process_email(mock_email)

    # Verify submit_url was called with resolved tag
    service.processor.frontend.submit_url.assert_called_once_with(
        "https://example.com/audio.mp3", tag="podcast"
    )
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && python -m pytest tests/test_main.py::test_process_email_resolves_tag_from_subject -v`
Expected: FAIL (tag not being passed)

**Step 3: Write minimal implementation**

Update `emailer/emailer/main.py`:

Add import at top:
```python
from emailer.tag_resolver import resolve_tag
```

Update `_process_email` method to fetch tags and resolve:

```python
    async def _process_email(self, email: EmailMessage) -> None:
        """Process a single email."""
        logger.info(f"Processing email {email.msg_num} from {email.sender}")

        # Extract URLs from both text and HTML
        urls = []
        if email.body_text:
            urls.extend(extract_urls(email.body_text, is_html=False))
        if email.body_html:
            urls.extend(extract_urls(email.body_html, is_html=True))

        # Deduplicate
        urls = list(dict.fromkeys(urls))

        if not urls:
            # No transcribable URLs found
            await self._handle_no_urls(email)
            return

        # Resolve tag from subject
        try:
            available_tags = await self.processor.frontend.get_tags()
        except Exception as e:
            logger.warning(f"Failed to fetch tags, using default: {e}")
            available_tags = set()

        tag = resolve_tag(
            subject=email.subject,
            available_tags=available_tags,
            default=self.settings.default_tag,
        )
        logger.info(f"Resolved tag '{tag}' from subject: {email.subject}")

        # Process each URL
        results = []
        for url in urls:
            result = await self.processor.process_url(url, tag=tag)
            results.append(result)
            await self._send_result_email(email, result)

        # Determine final folder and move
        any_success = any(r.success for r in results)
        target_folder = (
            self.settings.imap_folder_done if any_success
            else self.settings.imap_folder_error
        )
        try:
            await self.imap.move_to_folder(email.msg_num, target_folder)
        except Exception as e:
            logger.error(
                f"Failed to move email {email.msg_num} to {target_folder}: {e}"
            )
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && python -m pytest tests/test_main.py::test_process_email_resolves_tag_from_subject -v`
Expected: PASS

**Step 5: Commit**

```bash
git add emailer/emailer/main.py emailer/tests/test_main.py
git commit -m "feat(emailer): integrate tag resolution in email processing"
```

---

## Task 7: Run full test suite and verify

**Step 1: Run all emailer tests**

Run: `cd emailer && python -m pytest tests/ -v`
Expected: All new tests pass (existing failures are pre-existing)

**Step 2: Run frontend tests**

Run: `cd frontend && python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All tests pass (integration tests excluded due to DB path issues)

**Step 3: Final commit if any cleanup needed**

If tests reveal issues, fix and commit with appropriate message.

---

## Summary

Changes made:
1. `emailer/emailer/config.py` - Added `default_tag` config option
2. `emailer/emailer/frontend_client.py` - Added `get_tags()` method, updated `submit_url()` with optional `tag` parameter
3. `emailer/emailer/job_processor.py` - Updated `process_url()` with optional `tag` parameter
4. `emailer/emailer/tag_resolver.py` - New module with `resolve_tag()` function
5. `emailer/emailer/main.py` - Integrated tag resolution in `_process_email()`

Test files:
- `emailer/tests/test_config.py` - Test for default_tag config
- `emailer/tests/test_frontend_client.py` - Tests for get_tags and submit_url with tag
- `emailer/tests/test_job_processor.py` - Test for process_url with tag
- `emailer/tests/test_tag_resolver.py` - Tests for resolve_tag function
- `emailer/tests/test_main.py` - Test for tag resolution integration
