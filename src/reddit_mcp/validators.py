"""Input validation functions for tool parameters."""

import re

from reddit_mcp.errors import ValidationError

SEARCH_SORT_OPTIONS = ("relevance", "hot", "top", "new", "comments")
POST_SORT_OPTIONS = ("hot", "new", "top", "rising")
COMMENT_SORT_OPTIONS = ("best", "top", "new", "controversial", "old", "qa")
USER_SORT_OPTIONS = ("new", "hot", "top", "controversial")
TIME_FILTER_OPTIONS = ("hour", "day", "week", "month", "year", "all")

_SUBREDDIT_NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,21}$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,20}$")
_WIKI_PAGE_NAME_RE = re.compile(r"^[A-Za-z0-9_/.-]{1,128}$")


def validate_sort(value: str, allowed: tuple[str, ...], context: str = "sort") -> str:
    """Validate a sort parameter against allowed values.

    Returns the validated (lowered) value or raises ValidationError.
    """
    value = value.strip().lower()
    if value not in allowed:
        raise ValidationError(
            f"Invalid {context} value '{value}'. Valid options: {', '.join(allowed)}"
        )
    return value


def validate_time_filter(value: str) -> str:
    """Validate a time_filter parameter."""
    value = value.strip().lower()
    if value not in TIME_FILTER_OPTIONS:
        raise ValidationError(
            f"Invalid time_filter '{value}'. "
            f"Valid options: {', '.join(TIME_FILTER_OPTIONS)}"
        )
    return value


def validate_limit(value: int, min_val: int = 1, max_val: int = 100) -> int:
    """Validate and clamp a limit parameter."""
    if not isinstance(value, int):
        raise ValidationError(f"limit must be an integer, got {type(value).__name__}")
    if value < min_val:
        raise ValidationError(f"limit must be at least {min_val}, got {value}")
    if value > max_val:
        raise ValidationError(f"limit must be at most {max_val}, got {value}")
    return value


def validate_subreddit_name(value: str) -> str:
    """Validate subreddit name format (alphanumeric + underscores, 1-21 chars)."""
    value = value.strip()
    if not _SUBREDDIT_NAME_RE.match(value):
        raise ValidationError(
            f"Invalid subreddit name '{value}'. "
            "Must be 1-21 characters, alphanumeric and underscores only."
        )
    return value


def validate_username(value: str) -> str:
    """Validate Reddit username format."""
    value = value.strip()
    if not _USERNAME_RE.match(value):
        raise ValidationError(
            f"Invalid username '{value}'. "
            "Must be 1-20 characters, alphanumeric, underscores, and hyphens only."
        )
    return value


def validate_wiki_page_name(value: str) -> str:
    """Validate wiki page name format (alphanumeric, underscores, slashes, dots, hyphens, 1-128 chars)."""
    value = value.strip()
    if not _WIKI_PAGE_NAME_RE.match(value):
        raise ValidationError(
            f"Invalid wiki page name '{value}'. "
            "Must be 1-128 characters, alphanumeric, underscores, slashes, dots, and hyphens only."
        )
    return value
