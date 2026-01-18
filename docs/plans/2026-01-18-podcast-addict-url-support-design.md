# Podcast Addict URL Support

## Overview

Add `podcastaddict.com` as a supported URL source, extracting the episode ID from URLs like `https://podcastaddict.com/hard-fork/episode/215066511`. Audio download is handled by yt-dlp's generic extractor (no custom scraping needed).

## URL Pattern

```
https://podcastaddict.com/{podcast-name}/episode/{episode_id}
```

Example: `https://podcastaddict.com/hard-fork/episode/215066511`

## Generated ID Format

```
podcast_addict_{episode_id}
```

Example: `podcast_addict_215066511`

## Changes

### `frontend/frontend/utils/url_parser.py`

1. Add enum value:
```python
class SourceType(str, Enum):
    YOUTUBE = "youtube"
    APPLE_PODCASTS = "apple_podcasts"
    PODCAST_ADDICT = "podcast_addict"  # new
    DIRECT_AUDIO = "direct_audio"
```

2. Add extraction function:
```python
def extract_podcast_addict_id(url: str) -> Optional[str]:
    """Extract episode ID from podcastaddict.com/*/episode/{id}"""
    match = re.search(r'podcastaddict\.com/[^/]+/episode/(\d+)', url, re.IGNORECASE)
    return match.group(1) if match else None
```

3. Update `generate_id()` to detect `podcastaddict.com` and return `podcast_addict_{episode_id}`.

4. Update `parse_url()` to detect `podcastaddict.com` and return `URLInfo` with `SourceType.PODCAST_ADDICT`.

### `frontend/tests/test_url_parser.py`

Add tests:
```python
def test_parse_podcast_addict_url():
    """Test parsing Podcast Addict URL"""
    url = "https://podcastaddict.com/hard-fork/episode/215066511"
    info = parse_url(url)
    assert info.source_type == SourceType.PODCAST_ADDICT
    assert info.podcast_id == "215066511"
    assert info.id == "podcast_addict_215066511"

def test_podcast_addict_case_insensitive():
    """Test Podcast Addict URLs are case-insensitive"""
    url = "https://PodcastAddict.com/Hard-Fork/episode/215066511"
    info = parse_url(url)
    assert info.source_type == SourceType.PODCAST_ADDICT
    assert info.id == "podcast_addict_215066511"
```
