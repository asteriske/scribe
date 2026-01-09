# Tag Destination Email Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow tags to specify a destination email address, routing transcription results to different recipients based on tag.

**Architecture:** Add optional `destination_email` field to tag configs in `tag_configs.json`. New frontend endpoint `GET /api/tags/{name}` returns full tag config. Emailer fetches tag config after resolving tag name, uses `destination_email` if set, otherwise falls back to its configured default.

**Tech Stack:** FastAPI, httpx, pytest, pydantic

---

## Task 1: Frontend - Add GET /api/tags/{name} endpoint

**Files:**
- Modify: `frontend/frontend/api/routes.py:440-570` (tag config section)
- Test: `frontend/tests/test_api_routes.py`

### Step 1: Write failing tests for the new endpoint

Add to `frontend/tests/test_api_routes.py`:

```python
def test_get_tag_config_returns_config(client, monkeypatch):
    """Test GET /api/tags/{name} returns tag configuration."""
    from frontend.services.config_manager import ConfigManager

    mock_config = {
        "api_endpoint": "http://test.com/v1",
        "model": "test-model",
        "api_key_ref": "test",
        "system_prompt": "Test prompt",
        "destination_email": "test@example.com"
    }

    monkeypatch.setattr(
        ConfigManager, 'get_tag_config',
        lambda self, name: mock_config
    )

    response = client.get("/api/tags/testag")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "testag"
    assert data["api_endpoint"] == "http://test.com/v1"
    assert data["model"] == "test-model"
    assert data["destination_email"] == "test@example.com"


def test_get_tag_config_returns_null_destination_email(client, monkeypatch):
    """Test GET /api/tags/{name} returns null for missing destination_email."""
    from frontend.services.config_manager import ConfigManager

    mock_config = {
        "api_endpoint": "http://test.com/v1",
        "model": "test-model",
        "api_key_ref": None,
        "system_prompt": "Test prompt"
        # No destination_email
    }

    monkeypatch.setattr(
        ConfigManager, 'get_tag_config',
        lambda self, name: mock_config
    )

    response = client.get("/api/tags/notag")
    assert response.status_code == 200
    data = response.json()
    assert data["destination_email"] is None


def test_get_tag_config_not_found(client, monkeypatch):
    """Test GET /api/tags/{name} returns 404 for unknown tag."""
    from frontend.services.config_manager import ConfigManager

    monkeypatch.setattr(
        ConfigManager, 'get_tag_config',
        lambda self, name: None
    )

    response = client.get("/api/tags/nonexistent")
    assert response.status_code == 404
```

### Step 2: Run tests to verify they fail

```bash
cd /Users/patrick/git/scribe/.worktrees/tag-destination-email/frontend
source venv/bin/activate
pytest tests/test_api_routes.py::test_get_tag_config_returns_config tests/test_api_routes.py::test_get_tag_config_returns_null_destination_email tests/test_api_routes.py::test_get_tag_config_not_found -v
```

Expected: FAIL with 404 (endpoint doesn't exist)

### Step 3: Add response model to api/models.py

Add to `frontend/frontend/api/models.py` (find the TagConfigResponse class and update or add a new one):

```python
class TagConfigDetailResponse(BaseModel):
    """Response for single tag config lookup."""
    name: str
    api_endpoint: str
    model: str
    api_key_ref: Optional[str] = None
    system_prompt: str
    destination_email: Optional[str] = None
```

### Step 4: Add the endpoint to routes.py

Add after the existing `/api/config/tags/{tag_name}` PUT endpoint (around line 558), in the Tag Configuration API section:

```python
@router.get(
    "/tags/{tag_name}",
    response_model=TagConfigDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Tag config not found"}
    }
)
async def get_tag_config(tag_name: str):
    """Get configuration for a specific tag."""
    config_manager = ConfigManager()
    config = config_manager.get_tag_config(tag_name)

    if not config:
        raise HTTPException(status_code=404, detail=f"Tag config '{tag_name}' not found")

    return TagConfigDetailResponse(
        name=tag_name,
        api_endpoint=config["api_endpoint"],
        model=config["model"],
        api_key_ref=config.get("api_key_ref"),
        system_prompt=config["system_prompt"],
        destination_email=config.get("destination_email")
    )
```

Add the import at the top of routes.py:
```python
from frontend.api.models import (
    # ... existing imports ...
    TagConfigDetailResponse,
)
```

### Step 5: Run tests to verify they pass

```bash
pytest tests/test_api_routes.py::test_get_tag_config_returns_config tests/test_api_routes.py::test_get_tag_config_returns_null_destination_email tests/test_api_routes.py::test_get_tag_config_not_found -v
```

Expected: PASS

### Step 6: Run full test suite

```bash
pytest -v
```

Expected: All tests pass

### Step 7: Commit

```bash
git add frontend/frontend/api/routes.py frontend/frontend/api/models.py frontend/tests/test_api_routes.py
git commit -m "feat(frontend): add GET /api/tags/{name} endpoint

Returns full tag configuration including optional destination_email field.
Returns 404 if tag config doesn't exist."
```

---

## Task 2: Emailer - Add get_tag_config method to FrontendClient

**Files:**
- Modify: `emailer/emailer/frontend_client.py`
- Test: `emailer/tests/test_frontend_client.py`

### Step 1: Write failing tests

Add to `emailer/tests/test_frontend_client.py`:

```python
@pytest.mark.asyncio
async def test_get_tag_config_returns_config():
    """Test that get_tag_config returns tag configuration."""
    with patch("emailer.frontend_client.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.get = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {
                    "name": "kindle",
                    "api_endpoint": "http://test.com/v1",
                    "model": "test-model",
                    "api_key_ref": None,
                    "system_prompt": "Test",
                    "destination_email": "kindle@example.com"
                },
            )
        )

        client = FrontendClient(base_url="http://localhost:8000")
        result = await client.get_tag_config("kindle")

        assert result is not None
        assert result["name"] == "kindle"
        assert result["destination_email"] == "kindle@example.com"


@pytest.mark.asyncio
async def test_get_tag_config_returns_none_on_404():
    """Test that get_tag_config returns None for unknown tag."""
    with patch("emailer.frontend_client.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_response = MagicMock(status_code=404)
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )
        )
        mock_instance.get = AsyncMock(return_value=mock_response)

        client = FrontendClient(base_url="http://localhost:8000")
        result = await client.get_tag_config("nonexistent")

        assert result is None
```

### Step 2: Run tests to verify they fail

```bash
cd /Users/patrick/git/scribe/.worktrees/tag-destination-email/emailer
source venv/bin/activate
pytest tests/test_frontend_client.py::test_get_tag_config_returns_config tests/test_frontend_client.py::test_get_tag_config_returns_none_on_404 -v
```

Expected: FAIL with "AttributeError: 'FrontendClient' object has no attribute 'get_tag_config'"

### Step 3: Implement get_tag_config method

Add to `emailer/emailer/frontend_client.py` after the `get_tags` method:

```python
async def get_tag_config(self, tag_name: str) -> dict | None:
    """
    Fetch configuration for a specific tag.

    Args:
        tag_name: Name of the tag to fetch config for

    Returns:
        Tag configuration dict or None if tag not found
    """
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        try:
            response = await client.get(f"{self.base_url}/api/tags/{tag_name}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
```

### Step 4: Run tests to verify they pass

```bash
pytest tests/test_frontend_client.py::test_get_tag_config_returns_config tests/test_frontend_client.py::test_get_tag_config_returns_none_on_404 -v
```

Expected: PASS

### Step 5: Run full emailer test suite

```bash
pytest -v
```

Expected: 48 passed, 2 failed (pre-existing failures in test_smtp_client.py)

### Step 6: Commit

```bash
git add emailer/emailer/frontend_client.py emailer/tests/test_frontend_client.py
git commit -m "feat(emailer): add get_tag_config method to FrontendClient

Fetches full tag configuration from frontend API.
Returns None if tag config not found (404)."
```

---

## Task 3: Emailer - Use destination_email when sending results

**Files:**
- Modify: `emailer/emailer/main.py:184-208` (_send_result_email method)
- Test: `emailer/tests/test_main.py` (new file)

### Step 1: Write failing test

Create `emailer/tests/test_main.py`:

```python
"""Tests for emailer main service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from emailer.main import EmailerService
from emailer.config import Settings
from emailer.job_processor import JobResult


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    return Settings(
        imap_host="imap.test.com",
        imap_user="test@test.com",
        imap_password="password",
        smtp_host="smtp.test.com",
        smtp_user="test@test.com",
        smtp_password="password",
        result_email_address="default@example.com",
        from_email_address="scribe@example.com",
        frontend_url="http://localhost:8000",
        default_tag="email",
    )


class TestSendResultEmail:
    """Tests for _send_result_email destination resolution."""

    @pytest.mark.asyncio
    async def test_uses_tag_destination_email_when_set(self, mock_settings):
        """Test that tag's destination_email is used when available."""
        service = EmailerService(mock_settings)
        service.smtp = AsyncMock()
        service.resolved_destination = None  # Track what destination was used

        # Mock the tag config with destination_email
        service._tag_config = {
            "name": "kindle",
            "destination_email": "kindle@example.com"
        }

        mock_email = MagicMock(sender="user@test.com", subject="Test")
        result = JobResult(
            url="https://youtube.com/test",
            success=True,
            title="Test Video",
            summary="Test summary",
            transcript="Test transcript",
            duration_seconds=120,
        )

        await service._send_result_email(mock_email, result)

        # Verify email was sent to tag's destination
        service.smtp.send_email.assert_called_once()
        call_kwargs = service.smtp.send_email.call_args
        assert call_kwargs.kwargs["to_addr"] == "kindle@example.com"

    @pytest.mark.asyncio
    async def test_uses_default_when_tag_destination_not_set(self, mock_settings):
        """Test fallback to default when tag has no destination_email."""
        service = EmailerService(mock_settings)
        service.smtp = AsyncMock()

        # Mock tag config without destination_email
        service._tag_config = {
            "name": "podcast",
            "destination_email": None
        }

        mock_email = MagicMock(sender="user@test.com", subject="Test")
        result = JobResult(
            url="https://youtube.com/test",
            success=True,
            title="Test Video",
            summary="Test summary",
            transcript="Test transcript",
            duration_seconds=120,
        )

        await service._send_result_email(mock_email, result)

        # Verify email was sent to default destination
        service.smtp.send_email.assert_called_once()
        call_kwargs = service.smtp.send_email.call_args
        assert call_kwargs.kwargs["to_addr"] == "default@example.com"

    @pytest.mark.asyncio
    async def test_uses_default_when_no_tag_config(self, mock_settings):
        """Test fallback to default when no tag config available."""
        service = EmailerService(mock_settings)
        service.smtp = AsyncMock()

        # No tag config
        service._tag_config = None

        mock_email = MagicMock(sender="user@test.com", subject="Test")
        result = JobResult(
            url="https://youtube.com/test",
            success=True,
            title="Test Video",
            summary="Test summary",
            transcript="Test transcript",
            duration_seconds=120,
        )

        await service._send_result_email(mock_email, result)

        # Verify email was sent to default destination
        service.smtp.send_email.assert_called_once()
        call_kwargs = service.smtp.send_email.call_args
        assert call_kwargs.kwargs["to_addr"] == "default@example.com"
```

### Step 2: Run tests to verify they fail

```bash
pytest tests/test_main.py -v
```

Expected: FAIL with AttributeError (no _tag_config attribute)

### Step 3: Update EmailerService to track tag config and resolve destination

Modify `emailer/emailer/main.py`:

**In `__init__` method, add:**
```python
self._tag_config = None  # Current tag config for email processing
```

**Replace the `_process_email` method (lines 111-162) with:**
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

    # Fetch tag config for destination email resolution
    try:
        self._tag_config = await self.processor.frontend.get_tag_config(tag)
    except Exception as e:
        logger.warning(f"Failed to fetch tag config for '{tag}': {e}")
        self._tag_config = None

    # Process each URL
    results = []
    for url in urls:
        result = await self.processor.process_url(url, tag=tag)
        results.append(result)
        await self._send_result_email(email, result)

    # Clear tag config after processing
    self._tag_config = None

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

**Replace the `_send_result_email` method (lines 184-207) with:**
```python
async def _send_result_email(self, email: EmailMessage, result: JobResult) -> None:
    """Send result or error email based on job result."""
    if result.success:
        subject, body = format_success_email(
            url=result.url,
            title=result.title or "Untitled",
            duration_seconds=result.duration_seconds or 0,
            summary=result.summary or "",
            transcript=result.transcript or "",
        )
        # Use tag's destination_email if set, otherwise default
        if self._tag_config and self._tag_config.get("destination_email"):
            to_addr = self._tag_config["destination_email"]
        else:
            to_addr = self.settings.result_email_address
    else:
        subject, body = format_error_email(
            url=result.url,
            error_message=result.error or "Unknown error",
        )
        to_addr = email.sender

    await self.smtp.send_email(
        from_addr=self.settings.from_email_address,
        to_addr=to_addr,
        subject=subject,
        body=body,
    )
```

### Step 4: Run tests to verify they pass

```bash
pytest tests/test_main.py -v
```

Expected: PASS

### Step 5: Run full emailer test suite

```bash
pytest -v
```

Expected: 51 passed, 2 failed (pre-existing failures)

### Step 6: Commit

```bash
git add emailer/emailer/main.py emailer/tests/test_main.py
git commit -m "feat(emailer): use tag destination_email for result routing

Fetches tag config after resolving tag name.
Uses destination_email from tag config if set.
Falls back to default result_email_address otherwise."
```

---

## Task 4: Add destination_email to sample tag config

**Files:**
- Modify: `frontend/frontend/config/tag_configs.json`

### Step 1: Update tag_configs.json with example destination_email

Update `frontend/frontend/config/tag_configs.json`:

```json
{
  "default": {
    "api_endpoint": "http://10.100.2.50:1234/v1",
    "model": "openai/gpt-oss-20b",
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
    },
    "kindle": {
      "api_endpoint": "http://10.100.2.50:11434/v1",
      "model": "openai/gpt-oss-20b",
      "api_key_ref": null,
      "system_prompt": "Summarize the following podcast subscription. Pay special attention to main topics, questions asked and hot takes or counter-intuitive opinions.",
      "destination_email": null
    }
  }
}
```

Note: `destination_email` is set to `null` as a placeholder. User will configure actual email addresses as needed.

### Step 2: Commit

```bash
git add frontend/frontend/config/tag_configs.json
git commit -m "docs(frontend): add destination_email field to kindle tag config

Shows the new field structure. Set to null as placeholder."
```

---

## Task 5: Final verification and integration test

### Step 1: Run all frontend tests

```bash
cd /Users/patrick/git/scribe/.worktrees/tag-destination-email/frontend
source venv/bin/activate
pytest -v
```

Expected: All pass

### Step 2: Run all emailer tests

```bash
cd /Users/patrick/git/scribe/.worktrees/tag-destination-email/emailer
source venv/bin/activate
pytest -v
```

Expected: 51 passed, 2 failed (pre-existing)

### Step 3: Manual integration verification (optional)

Start frontend temporarily and test the new endpoint:

```bash
cd /Users/patrick/git/scribe/.worktrees/tag-destination-email/frontend
source venv/bin/activate
timeout 10 python -m uvicorn frontend.main:app --host 127.0.0.1 --port 8100 &
sleep 3
curl http://127.0.0.1:8100/api/tags/kindle
```

Expected: JSON response with tag config including `destination_email`

### Step 4: Final commit (if any cleanup needed)

```bash
git status
# If clean, no action needed
```

---

## Summary

After completing all tasks, you will have:

1. **Frontend endpoint** `GET /api/tags/{name}` returning full tag config with `destination_email`
2. **Emailer method** `get_tag_config()` to fetch tag config from frontend
3. **Emailer routing** that uses tag's `destination_email` when set, falls back to default
4. **Updated config** showing the new field structure

The feature is backwards-compatible: existing tags without `destination_email` continue to use the default destination.
