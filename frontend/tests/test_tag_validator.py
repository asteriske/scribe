"""Tests for tag validation utilities."""
import pytest
from frontend.utils.tag_validator import normalize_tags, validate_tag


def test_normalize_tags_to_lowercase():
    """Test tags are converted to lowercase."""
    result = normalize_tags(["Kindle", "FORMAT", "Review"])
    assert result == ["kindle", "format", "review"]


def test_normalize_tags_removes_duplicates():
    """Test duplicate tags are removed."""
    result = normalize_tags(["kindle", "format", "kindle", "review"])
    assert result == ["kindle", "format", "review"]


def test_normalize_tags_strips_whitespace():
    """Test whitespace is stripped from tags."""
    result = normalize_tags([" kindle ", "  format", "review  "])
    assert result == ["kindle", "format", "review"]


def test_normalize_tags_removes_empty():
    """Test empty strings are filtered out."""
    result = normalize_tags(["kindle", "", "  ", "format"])
    assert result == ["kindle", "format"]


def test_normalize_tags_case_insensitive_duplicates():
    """Test case-insensitive duplicate removal."""
    result = normalize_tags(["Kindle", "kindle", "KINDLE"])
    assert result == ["kindle"]


def test_validate_tag_valid():
    """Test valid tags pass validation."""
    assert validate_tag("kindle") is True
    assert validate_tag("my-tag") is True
    assert validate_tag("tag_123") is True


def test_validate_tag_invalid_characters():
    """Test tags with invalid characters fail."""
    assert validate_tag("tag with spaces") is False
    assert validate_tag("tag@symbol") is False
    assert validate_tag("tag!") is False


def test_validate_tag_too_long():
    """Test tags exceeding max length fail."""
    long_tag = "a" * 51
    assert validate_tag(long_tag) is False


def test_validate_tag_empty():
    """Test empty tags fail."""
    assert validate_tag("") is False
    assert validate_tag("   ") is False


def test_normalize_tags_enforces_max_count():
    """Test max tag count is enforced."""
    tags = [f"tag{i}" for i in range(25)]
    result = normalize_tags(tags)
    assert len(result) <= 20
