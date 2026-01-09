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
