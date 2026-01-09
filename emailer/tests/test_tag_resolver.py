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
