"""Tag validation and normalization utilities."""
import re
from typing import List

# Constants
MAX_TAG_LENGTH = 50
MAX_TAGS_PER_TRANSCRIPTION = 20
TAG_PATTERN = re.compile(r'^[a-z0-9-_]+$')


def validate_tag(tag: str) -> bool:
    """
    Validate a single tag.

    Args:
        tag: Tag string to validate

    Returns:
        True if tag is valid, False otherwise
    """
    if not tag or not tag.strip():
        return False

    tag = tag.strip().lower()

    if len(tag) > MAX_TAG_LENGTH:
        return False

    return bool(TAG_PATTERN.match(tag))


def normalize_tags(tags: List[str]) -> List[str]:
    """
    Normalize and validate a list of tags.

    - Converts to lowercase
    - Strips whitespace
    - Removes duplicates
    - Filters out empty strings
    - Validates format
    - Enforces max count

    Args:
        tags: List of tag strings

    Returns:
        Normalized list of valid tags
    """
    if not tags:
        return []

    # Normalize: lowercase, strip whitespace
    normalized = [tag.strip().lower() for tag in tags]

    # Remove empty strings
    normalized = [tag for tag in normalized if tag]

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for tag in normalized:
        if tag not in seen and validate_tag(tag):
            seen.add(tag)
            unique.append(tag)

    # Enforce max count
    return unique[:MAX_TAGS_PER_TRANSCRIPTION]
