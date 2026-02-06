# Show Notes Context Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich podcast summarization by fetching Apple Podcasts show notes at submission time and using them as context for LLM summarization.

**Architecture:** Add `source_context` field to Transcription model. Create Apple Podcasts scraper that fetches show notes at URL submission. Inject context into summarization prompt. Update email output to include Creator's Notes section.

**Tech Stack:** Python, SQLAlchemy, httpx, BeautifulSoup4

---

### Task 1: Add source_context Field to Database

**Files:**
- Modify: `frontend/frontend/core/models.py:56` (add field after `full_text`)
- Modify: `frontend/frontend/core/migrations.py` (add migration function)
- Test: `frontend/tests/test_models.py`

**Step 1: Write the failing test**

Add to `frontend/tests/test_models.py`:

```python
def test_transcription_source_context_field(test_db):
    """Test that source_context field can store show notes."""
    Session = sessionmaker(bind=test_db)
    session = Session()

    transcription = Transcription(
        id="test_context_123",
        source_type="apple_podcasts",
        source_url="https://podcasts.apple.com/test",
        status="pending",
        source_context="Episode about Python programming. Topics: decorators, generators."
    )
    session.add(transcription)
    session.commit()

    loaded = session.query(Transcription).filter_by(id="test_context_123").first()
    assert loaded.source_context == "Episode about Python programming. Topics: decorators, generators."
    session.close()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_models.py::test_transcription_source_context_field -v`

Expected: FAIL with "unexpected keyword argument 'source_context'"

**Step 3: Add source_context field to model**

In `frontend/frontend/core/models.py`, after line 56 (`full_text = Column(Text)`), add:

```python
    # Creator-provided context (show notes, description, etc.)
    source_context = Column(Text)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_models.py::test_transcription_source_context_field -v`

Expected: PASS

**Step 5: Add database migration**

In `frontend/frontend/core/migrations.py`, add after `create_summaries_table_if_missing`:

```python
def add_source_context_column_if_missing(engine):
    """Add source_context column to transcriptions table if it doesn't exist."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('transcriptions')]

    if 'source_context' not in columns:
        logger.info("Adding source_context column to transcriptions table")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE transcriptions ADD COLUMN source_context TEXT"))
            conn.commit()
        logger.info("source_context column added successfully")
    else:
        logger.debug("source_context column already exists")
```

Update `run_migrations` to call it:

```python
def run_migrations(engine):
    """Run all pending migrations."""
    logger.info("Running database migrations")
    add_tags_column_if_missing(engine)
    create_summaries_table_if_missing(engine)
    add_source_context_column_if_missing(engine)
    logger.info("Migrations complete")
```

**Step 6: Run all model tests**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_models.py -v`

Expected: All tests pass

**Step 7: Commit**

```bash
cd /Users/patrick/git/scribe/.worktrees/show-notes-context
git add frontend/frontend/core/models.py frontend/frontend/core/migrations.py frontend/tests/test_models.py
git commit -m "feat: add source_context field to Transcription model"
```

---

### Task 2: Create Apple Podcasts Scraper

**Files:**
- Create: `frontend/frontend/services/apple_podcasts_scraper.py`
- Test: `frontend/tests/test_apple_podcasts_scraper.py`

**Step 1: Write the failing test**

Create `frontend/tests/test_apple_podcasts_scraper.py`:

```python
"""Tests for the Apple Podcasts scraper."""
import pytest
from unittest.mock import patch, MagicMock

from frontend.services.apple_podcasts_scraper import ApplePodcastsScraper


class TestApplePodcastsScraper:
    """Tests for ApplePodcastsScraper."""

    def test_is_apple_podcasts_url_true(self):
        """Test detection of Apple Podcasts URLs."""
        scraper = ApplePodcastsScraper()
        assert scraper.is_apple_podcasts_url("https://podcasts.apple.com/us/podcast/test/id123?i=456")
        assert scraper.is_apple_podcasts_url("https://podcasts.apple.com/gb/podcast/test/id123")
        assert scraper.is_apple_podcasts_url("http://podcasts.apple.com/us/podcast/test/id123")

    def test_is_apple_podcasts_url_false(self):
        """Test rejection of non-Apple Podcasts URLs."""
        scraper = ApplePodcastsScraper()
        assert not scraper.is_apple_podcasts_url("https://youtube.com/watch?v=123")
        assert not scraper.is_apple_podcasts_url("https://spotify.com/episode/123")
        assert not scraper.is_apple_podcasts_url("https://example.com/audio.mp3")

    def test_extract_show_notes_success(self):
        """Test successful extraction of show notes."""
        html_content = """
        <html>
        <head>
            <meta name="description" content="Episode description here">
        </head>
        <body>
            <section class="product-hero-desc">
                <div>
                    <p>In this episode, we discuss Python programming.</p>
                    <p>Topics covered:</p>
                    <ul>
                        <li>Decorators</li>
                        <li>Generators</li>
                    </ul>
                </div>
            </section>
        </body>
        </html>
        """

        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            scraper = ApplePodcastsScraper()
            result = scraper.fetch_show_notes("https://podcasts.apple.com/us/podcast/test/id123")

            assert result is not None
            assert "Python programming" in result or "Episode description" in result

    def test_extract_show_notes_network_error_returns_none(self):
        """Test that network errors return None instead of raising."""
        import httpx

        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Connection failed")

            scraper = ApplePodcastsScraper()
            result = scraper.fetch_show_notes("https://podcasts.apple.com/us/podcast/test/id123")

            assert result is None

    def test_extract_show_notes_retries_on_transient_error(self):
        """Test that transient errors trigger retries."""
        import httpx

        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = "<html><body><p>Show notes</p></body></html>"
            mock_response.raise_for_status = MagicMock()

            # First two calls fail, third succeeds
            mock_client.return_value.__enter__.return_value.get.side_effect = [
                httpx.RequestError("Timeout"),
                httpx.RequestError("Timeout"),
                mock_response
            ]

            scraper = ApplePodcastsScraper(max_retries=3)
            result = scraper.fetch_show_notes("https://podcasts.apple.com/us/podcast/test/id123")

            # Should have tried 3 times
            assert mock_client.return_value.__enter__.return_value.get.call_count == 3

    def test_extract_show_notes_gives_up_after_max_retries(self):
        """Test that scraper gives up after max retries."""
        import httpx

        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Timeout")

            scraper = ApplePodcastsScraper(max_retries=3)
            result = scraper.fetch_show_notes("https://podcasts.apple.com/us/podcast/test/id123")

            assert result is None
            assert mock_client.return_value.__enter__.return_value.get.call_count == 3
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_apple_podcasts_scraper.py -v`

Expected: FAIL with "No module named 'frontend.services.apple_podcasts_scraper'"

**Step 3: Create the scraper module**

Create `frontend/frontend/services/apple_podcasts_scraper.py`:

```python
"""Apple Podcasts show notes scraper."""

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Request timeout in seconds
REQUEST_TIMEOUT = 30


class ApplePodcastsScraper:
    """Scraper for extracting show notes from Apple Podcasts pages."""

    def __init__(self, max_retries: int = 3):
        """
        Initialize scraper.

        Args:
            max_retries: Maximum number of retry attempts for transient errors
        """
        self.max_retries = max_retries

    def is_apple_podcasts_url(self, url: str) -> bool:
        """
        Check if a URL is an Apple Podcasts URL.

        Args:
            url: URL to check

        Returns:
            True if URL is from Apple Podcasts
        """
        return "podcasts.apple.com" in url.lower()

    def fetch_show_notes(self, url: str) -> Optional[str]:
        """
        Fetch and extract show notes from an Apple Podcasts URL.

        Args:
            url: Apple Podcasts episode URL

        Returns:
            Extracted show notes text, or None if extraction fails
        """
        html_content = self._fetch_page(url)
        if not html_content:
            return None

        return self._extract_content(html_content)

    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch page HTML with retry logic.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None if all retries fail
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                    response = client.get(url, headers=headers, follow_redirects=True)
                    response.raise_for_status()
                    return response.text

            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(f"Server error {e.response.status_code} fetching {url} (attempt {attempt + 1}/{self.max_retries})")
                else:
                    logger.error(f"HTTP error {e.response.status_code} fetching {url}")
                    return None
            except httpx.RequestError as e:
                logger.warning(f"Request error fetching {url}: {e} (attempt {attempt + 1}/{self.max_retries})")

        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    def _extract_content(self, html: str) -> Optional[str]:
        """
        Extract show notes content from HTML.

        Args:
            html: Page HTML content

        Returns:
            Extracted text content or None if extraction fails
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            content_parts = []

            # Try to get the episode description from meta tag
            meta_desc = soup.find("meta", {"name": "description"})
            if meta_desc and meta_desc.get("content"):
                content_parts.append(meta_desc["content"])

            # Look for the main description section
            # Apple Podcasts uses various class names for description
            desc_selectors = [
                "section.product-hero-desc",
                "div.product-hero-desc",
                "[data-testid='description']",
                ".episode-description",
                ".show-notes",
            ]

            for selector in desc_selectors:
                desc_section = soup.select_one(selector)
                if desc_section:
                    text = desc_section.get_text(separator="\n", strip=True)
                    if text and text not in content_parts:
                        content_parts.append(text)

            # Look for timestamps/chapters
            timestamp_pattern = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")
            for element in soup.find_all(string=timestamp_pattern):
                parent = element.find_parent()
                if parent:
                    text = parent.get_text(strip=True)
                    if text and len(text) < 500 and text not in content_parts:
                        content_parts.append(text)

            if content_parts:
                return "\n\n".join(content_parts)

            # Fallback: just get any substantial text content
            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
                # Truncate if too long
                if len(text) > 5000:
                    text = text[:5000] + "..."
                return text if text else None

            return None

        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return None
```

**Step 4: Add beautifulsoup4 to requirements**

Add to `frontend/requirements.txt`:

```
beautifulsoup4>=4.12.0
```

**Step 5: Install the dependency**

Run: `pip install beautifulsoup4`

**Step 6: Run tests to verify they pass**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_apple_podcasts_scraper.py -v`

Expected: All tests pass

**Step 7: Commit**

```bash
cd /Users/patrick/git/scribe/.worktrees/show-notes-context
git add frontend/frontend/services/apple_podcasts_scraper.py frontend/tests/test_apple_podcasts_scraper.py frontend/requirements.txt
git commit -m "feat: add Apple Podcasts show notes scraper"
```

---

### Task 3: Integrate Scraper at URL Submission

**Files:**
- Modify: `frontend/frontend/api/routes.py:90-152` (transcribe_url endpoint)
- Test: `frontend/tests/test_api_routes.py`

**Step 1: Write the failing test**

Add to `frontend/tests/test_api_routes.py`:

```python
def test_transcribe_apple_podcasts_fetches_show_notes(mock_db, test_client):
    """Test that Apple Podcasts URLs trigger show notes fetching."""
    with patch('frontend.api.routes.ApplePodcastsScraper') as mock_scraper_class:
        mock_scraper = MagicMock()
        mock_scraper.is_apple_podcasts_url.return_value = True
        mock_scraper.fetch_show_notes.return_value = "Show notes content here"
        mock_scraper_class.return_value = mock_scraper

        with patch('frontend.api.routes.Orchestrator'):
            response = test_client.post(
                "/api/transcribe",
                json={"url": "https://podcasts.apple.com/us/podcast/test/id123?i=456"}
            )

        assert response.status_code == 202
        mock_scraper.fetch_show_notes.assert_called_once()

        # Verify source_context was saved
        transcription = mock_db.query(Transcription).first()
        assert transcription.source_context == "Show notes content here"


def test_transcribe_non_apple_url_no_scraper(mock_db, test_client):
    """Test that non-Apple URLs don't trigger show notes fetching."""
    with patch('frontend.api.routes.ApplePodcastsScraper') as mock_scraper_class:
        mock_scraper = MagicMock()
        mock_scraper.is_apple_podcasts_url.return_value = False
        mock_scraper_class.return_value = mock_scraper

        with patch('frontend.api.routes.Orchestrator'):
            response = test_client.post(
                "/api/transcribe",
                json={"url": "https://youtube.com/watch?v=test123"}
            )

        assert response.status_code == 202
        mock_scraper.fetch_show_notes.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_api_routes.py::test_transcribe_apple_podcasts_fetches_show_notes -v`

Expected: FAIL (scraper not imported/used)

**Step 3: Integrate scraper into transcribe_url endpoint**

In `frontend/frontend/api/routes.py`, add import at top:

```python
from frontend.services.apple_podcasts_scraper import ApplePodcastsScraper
```

Modify the `transcribe_url` function (around line 99-144) to fetch show notes:

```python
@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=202,
    responses={
        409: {"model": ErrorResponse, "description": "URL already transcribed"},
        400: {"model": ErrorResponse, "description": "Invalid URL"}
    }
)
async def transcribe_url(
    request: TranscribeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submit a URL for transcription.

    The transcription job will be processed in the background.
    """
    try:
        # Parse and validate URL
        url_info = parse_url(request.url)

        # Check for duplicate
        existing = db.query(Transcription).filter_by(source_url=request.url).first()
        if existing:
            return JSONResponse(
                status_code=409,
                content=jsonable_encoder(ErrorResponse(
                    detail="This URL has already been transcribed",
                    existing_id=existing.id
                ))
            )

        # Normalize tags
        normalized_tags = normalize_tags(request.tags) if request.tags else []

        # Fetch show notes for Apple Podcasts URLs
        source_context = None
        scraper = ApplePodcastsScraper()
        if scraper.is_apple_podcasts_url(request.url):
            logger.info(f"Fetching show notes for Apple Podcasts URL: {request.url}")
            source_context = scraper.fetch_show_notes(request.url)
            if source_context:
                logger.info(f"Successfully fetched show notes ({len(source_context)} chars)")
            else:
                logger.info("No show notes found or fetch failed, continuing without context")

        # Create pending record
        transcription = Transcription(
            id=url_info.id,
            source_type=url_info.source_type.value,
            source_url=request.url,
            status='pending',
            progress=0,
            tags=json.dumps(normalized_tags),
            source_context=source_context
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)

        # Create orchestrator and start processing in background
        orchestrator = Orchestrator()
        background_tasks.add_task(orchestrator.process_url, request.url)

        return TranscriptionResponse(**transcription.to_dict())

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting transcription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_api_routes.py -v`

Expected: All tests pass

**Step 5: Commit**

```bash
cd /Users/patrick/git/scribe/.worktrees/show-notes-context
git add frontend/frontend/api/routes.py frontend/tests/test_api_routes.py
git commit -m "feat: integrate Apple Podcasts scraper at URL submission"
```

---

### Task 4: Inject Context into Summarization Prompt

**Files:**
- Modify: `frontend/frontend/services/summarizer.py:118-230` (generate_summary method)
- Test: `frontend/tests/test_summarizer.py`

**Step 1: Write the failing test**

Add to `frontend/tests/test_summarizer.py`:

```python
def test_generate_summary_includes_source_context(mock_db):
    """Test that source_context is included in the prompt when available."""
    # Create transcription with source_context
    transcription = Transcription(
        id="test_context_sum",
        source_type="apple_podcasts",
        source_url="https://podcasts.apple.com/test",
        status="completed",
        tags=json.dumps([]),
        source_context="Episode about machine learning. Topics: neural networks, transformers."
    )
    mock_db.add(transcription)
    mock_db.commit()

    with patch.object(SummarizerService, '_call_llm_api') as mock_llm:
        mock_llm.return_value = ("Summary text", {"prompt_tokens": 100}, None)

        mock_storage = MagicMock()
        mock_storage.load_transcription.return_value = {
            'transcription': {
                'segments': [{'text': 'Hello world.'}]
            }
        }

        mock_config = MagicMock()
        mock_resolved = MagicMock()
        mock_resolved.api_endpoint = "http://test.com/v1"
        mock_resolved.model = "test-model"
        mock_resolved.api_key = "test-key"
        mock_resolved.system_prompt = "Summarize this."
        mock_resolved.config_source = "default"
        mock_config.resolve_config_for_transcription.return_value = mock_resolved

        service = SummarizerService(
            config_manager=mock_config,
            storage_manager=mock_storage
        )
        result = service.generate_summary(db=mock_db, transcription_id="test_context_sum")

        # Verify the source context was included in the user content
        call_args = mock_llm.call_args
        user_content = call_args[0][4]  # 5th positional arg is user_content
        assert "machine learning" in user_content
        assert "neural networks" in user_content


def test_generate_summary_without_source_context(mock_db):
    """Test that summarization works without source_context."""
    transcription = Transcription(
        id="test_no_context",
        source_type="youtube",
        source_url="https://youtube.com/watch?v=test",
        status="completed",
        tags=json.dumps([]),
        source_context=None
    )
    mock_db.add(transcription)
    mock_db.commit()

    with patch.object(SummarizerService, '_call_llm_api') as mock_llm:
        mock_llm.return_value = ("Summary text", {"prompt_tokens": 100}, None)

        mock_storage = MagicMock()
        mock_storage.load_transcription.return_value = {
            'transcription': {
                'segments': [{'text': 'Hello world.'}]
            }
        }

        mock_config = MagicMock()
        mock_resolved = MagicMock()
        mock_resolved.api_endpoint = "http://test.com/v1"
        mock_resolved.model = "test-model"
        mock_resolved.api_key = "test-key"
        mock_resolved.system_prompt = "Summarize this."
        mock_resolved.config_source = "default"
        mock_config.resolve_config_for_transcription.return_value = mock_resolved

        service = SummarizerService(
            config_manager=mock_config,
            storage_manager=mock_storage
        )
        result = service.generate_summary(db=mock_db, transcription_id="test_no_context")

        assert result.success
        # Verify no context prefix was added
        call_args = mock_llm.call_args
        user_content = call_args[0][4]
        assert "creator provided" not in user_content.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_summarizer.py::test_generate_summary_includes_source_context -v`

Expected: FAIL (context not being included)

**Step 3: Modify generate_summary to include context**

In `frontend/frontend/services/summarizer.py`, modify `generate_summary` method. After extracting `full_text` (around line 184-186), add context injection:

```python
        # Extract full text from segments
        segments = transcription_data.get('transcription', {}).get('segments', [])
        full_text = ' '.join(segment['text'].strip() for segment in segments)

        if not full_text:
            return SummaryResult(False, None, "Transcription has no text content")

        # Inject source context if available
        user_content = full_text
        if transcription.source_context:
            context_prefix = f"""The creator provided the following show notes for this episode:

---
{transcription.source_context}
---

If any of this context is relevant to the summarization task below, use it to guide what you extract. Ignore any show notes content that isn't relevant to the specific request.

Transcript:
"""
            user_content = context_prefix + full_text

        # Call LLM API
        start_time = time.time()
        summary_text, usage, error = self._call_llm_api(
            final_endpoint,
            final_model,
            final_key,
            final_prompt,
            user_content  # Changed from full_text
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_summarizer.py -v`

Expected: All tests pass

**Step 5: Commit**

```bash
cd /Users/patrick/git/scribe/.worktrees/show-notes-context
git add frontend/frontend/services/summarizer.py frontend/tests/test_summarizer.py
git commit -m "feat: inject source context into summarization prompt"
```

---

### Task 5: Add API Endpoint to Get Source Context

**Files:**
- Modify: `frontend/frontend/api/routes.py` (add endpoint)
- Modify: `frontend/frontend/core/models.py` (update to_dict)
- Test: `frontend/tests/test_api_routes.py`

**Step 1: Write the failing test**

Add to `frontend/tests/test_api_routes.py`:

```python
def test_get_transcription_includes_source_context(mock_db, test_client):
    """Test that GET transcription includes source_context in response."""
    transcription = Transcription(
        id="test_get_context",
        source_type="apple_podcasts",
        source_url="https://podcasts.apple.com/test",
        status="completed",
        source_context="Episode show notes here"
    )
    mock_db.add(transcription)
    mock_db.commit()

    response = test_client.get("/api/transcriptions/test_get_context")
    assert response.status_code == 200
    data = response.json()
    assert data["source_context"] == "Episode show notes here"


def test_get_transcription_source_context_null_when_missing(mock_db, test_client):
    """Test that source_context is null when not present."""
    transcription = Transcription(
        id="test_no_get_context",
        source_type="youtube",
        source_url="https://youtube.com/watch?v=test",
        status="completed"
    )
    mock_db.add(transcription)
    mock_db.commit()

    response = test_client.get("/api/transcriptions/test_no_get_context")
    assert response.status_code == 200
    data = response.json()
    assert data["source_context"] is None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_api_routes.py::test_get_transcription_includes_source_context -v`

Expected: FAIL (source_context not in response)

**Step 3: Update Transcription.to_dict() to include source_context**

In `frontend/frontend/core/models.py`, modify `to_dict` method to include `source_context`:

```python
    def to_dict(self):
        """Convert to dictionary for API responses."""
        import json

        # Parse tags from JSON if it's a string
        tags_list = []
        if self.tags:
            if isinstance(self.tags, str):
                try:
                    tags_list = json.loads(self.tags)
                except (json.JSONDecodeError, TypeError):
                    tags_list = []
            elif isinstance(self.tags, list):
                tags_list = self.tags

        return {
            'id': self.id,
            'source': {
                'type': self.source_type,
                'url': self.source_url,
                'title': self.title,
                'channel': self.channel,
                'thumbnail': self.thumbnail_url,
                'upload_date': self.upload_date
            },
            'status': self.status,
            'progress': self.progress,
            'duration_seconds': self.duration_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'transcribed_at': self.transcribed_at.isoformat() if self.transcribed_at else None,
            'model': self.model_used,
            'language': self.language,
            'word_count': self.word_count,
            'segments_count': self.segments_count,
            'error': self.error_message,
            'tags': tags_list,
            'source_context': self.source_context
        }
```

**Step 4: Update TranscriptionResponse model**

In `frontend/frontend/api/models.py`, add `source_context` field:

```python
class TranscriptionResponse(BaseModel):
    # ... existing fields ...
    source_context: Optional[str] = None
```

**Step 5: Run tests to verify they pass**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/test_api_routes.py -v`

Expected: All tests pass

**Step 6: Commit**

```bash
cd /Users/patrick/git/scribe/.worktrees/show-notes-context
git add frontend/frontend/core/models.py frontend/frontend/api/models.py frontend/tests/test_api_routes.py
git commit -m "feat: expose source_context in API responses"
```

---

### Task 6: Update Email Output Format

**Files:**
- Modify: `emailer/emailer/result_formatter.py:32-112`
- Modify: `emailer/emailer/job_processor.py`
- Modify: `emailer/emailer/frontend_client.py`
- Test: `emailer/tests/test_result_formatter.py`

**Step 1: Write the failing test**

Add to `emailer/tests/test_result_formatter.py`:

```python
def test_format_success_email_with_creator_notes():
    """Test email formatting includes Creator's Notes section when provided."""
    subject, html_body, text_body = format_success_email(
        url="https://podcasts.apple.com/test",
        title="Test Episode",
        duration_seconds=3600,
        summary="<p>This is the summary.</p>",
        transcript="Full transcript text here.",
        creator_notes="Episode about Python. Topics: decorators, generators."
    )

    # Check HTML includes Creator's Notes section
    assert "Creator's Notes" in html_body
    assert "Episode about Python" in html_body

    # Check plain text includes Creator's Notes section
    assert "CREATOR'S NOTES" in text_body
    assert "Episode about Python" in text_body

    # Verify order: Summary -> Creator's Notes -> Transcript
    summary_pos = html_body.find("Summary")
    notes_pos = html_body.find("Creator's Notes")
    transcript_pos = html_body.find("Transcript")
    assert summary_pos < notes_pos < transcript_pos


def test_format_success_email_without_creator_notes():
    """Test email formatting omits Creator's Notes section when not provided."""
    subject, html_body, text_body = format_success_email(
        url="https://youtube.com/watch?v=test",
        title="Test Video",
        duration_seconds=600,
        summary="<p>Summary here.</p>",
        transcript="Transcript here.",
        creator_notes=None
    )

    assert "Creator's Notes" not in html_body
    assert "CREATOR'S NOTES" not in text_body
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/emailer && python -m pytest tests/test_result_formatter.py::test_format_success_email_with_creator_notes -v`

Expected: FAIL (creator_notes parameter doesn't exist)

**Step 3: Update format_success_email function**

In `emailer/emailer/result_formatter.py`, modify `format_success_email`:

```python
def format_success_email(
    url: str,
    title: str,
    duration_seconds: int,
    summary: str,
    transcript: str,
    creator_notes: str = None,
) -> Tuple[str, str, str]:
    """
    Format a success email with summary and transcript.

    Args:
        url: Source URL
        title: Content title
        duration_seconds: Duration in seconds
        summary: Generated summary (HTML from LLM)
        transcript: Full transcript text
        creator_notes: Optional creator-provided show notes

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

    # Build Creator's Notes section if available
    creator_notes_html = ""
    creator_notes_text = ""
    if creator_notes:
        escaped_notes = html.escape(creator_notes)
        html_notes = escaped_notes.replace("\n", "<br>\n")
        creator_notes_html = f"""
    <div class="section-title">Creator's Notes</div>
    <div class="creator-notes">{html_notes}</div>
"""
        creator_notes_text = f"""
--- CREATOR'S NOTES ---

{creator_notes}
"""

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
        .creator-notes {{ font-size: 14px; color: #555; background: #f9f9f9; padding: 16px; border-radius: 4px; }}
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
{creator_notes_html}
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
{creator_notes_text}
--- TRANSCRIPT ---

{transcript}
"""

    return subject, html_body, text_body
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/emailer && python -m pytest tests/test_result_formatter.py -v`

Expected: All tests pass

**Step 5: Update FrontendClient to fetch source_context**

In `emailer/emailer/frontend_client.py`, update `TranscriptionResult` dataclass:

```python
@dataclass
class TranscriptionResult:
    """Result from a transcription job."""

    transcription_id: str
    status: str
    title: Optional[str] = None
    full_text: Optional[str] = None
    duration_seconds: Optional[int] = None
    error: Optional[str] = None
    source_context: Optional[str] = None
```

Update `get_transcription` method to extract `source_context`:

```python
    async def get_transcription(self, transcription_id: str) -> TranscriptionResult:
        # ... existing code ...

        result = TranscriptionResult(
            transcription_id=data["id"],
            status=data["status"],
        )

        # Extract source info if available
        if "source" in data:
            result.title = data["source"].get("title")

        # Extract source_context if available
        result.source_context = data.get("source_context")

        # ... rest of existing code ...
```

**Step 6: Update JobProcessor to pass creator_notes**

In `emailer/emailer/job_processor.py`, update `JobResult` dataclass:

```python
@dataclass
class JobResult:
    """Result of processing a URL."""

    url: str
    success: bool
    title: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    duration_seconds: Optional[int] = None
    error: Optional[str] = None
    creator_notes: Optional[str] = None
```

Update `process_url` and `_process_existing` to include `creator_notes`:

```python
    async def process_url(self, url: str, tag: str | None = None) -> JobResult:
        # ... existing code up to wait_for_completion ...

        return JobResult(
            url=url,
            success=True,
            title=result.title,
            summary=summary,
            transcript=transcript,
            duration_seconds=result.duration_seconds,
            creator_notes=result.source_context,
        )
```

**Step 7: Update main.py to pass creator_notes to formatter**

In `emailer/emailer/main.py`, update the call to `format_success_email`:

```python
subject, html_body, text_body = format_success_email(
    url=result.url,
    title=result.title or "Untitled",
    duration_seconds=result.duration_seconds or 0,
    summary=result.summary,
    transcript=result.transcript,
    creator_notes=result.creator_notes,
)
```

**Step 8: Run all emailer tests**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/emailer && python -m pytest tests/ -v`

Expected: All tests pass

**Step 9: Commit**

```bash
cd /Users/patrick/git/scribe/.worktrees/show-notes-context
git add emailer/
git commit -m "feat: include Creator's Notes section in email output"
```

---

### Task 7: Integration Testing and Cleanup

**Files:**
- Modify: `frontend/tests/test_integration.py`

**Step 1: Run full test suite for frontend**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/frontend && python -m pytest tests/ -v`

Expected: All tests pass

**Step 2: Run full test suite for emailer**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/emailer && python -m pytest tests/ -v`

Expected: All tests pass

**Step 3: Run full test suite for transcriber**

Run: `cd /Users/patrick/git/scribe/.worktrees/show-notes-context/transcriber && python -m pytest tests/ -v`

Expected: All tests pass

**Step 4: Final commit**

```bash
cd /Users/patrick/git/scribe/.worktrees/show-notes-context
git add -A
git commit -m "test: add integration tests for show notes context feature"
```

---

## Summary

This plan implements the show notes context feature in 7 tasks:

1. **Database**: Add `source_context` field to Transcription model
2. **Scraper**: Create Apple Podcasts scraper with retry logic
3. **Integration**: Call scraper at URL submission time
4. **Summarization**: Inject context into LLM prompt
5. **API**: Expose source_context in responses
6. **Email**: Add Creator's Notes section to output
7. **Testing**: Full integration testing

Each task follows TDD with small, verifiable steps.
