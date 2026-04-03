"""Custom exception hierarchy and error-handling utilities for the Reddit MCP server."""

import functools
from typing import Callable


class RedditMCPError(Exception):
    """Base exception for all Reddit MCP errors."""


class CredentialError(RedditMCPError):
    """Raised when credentials are missing or malformed."""


class SubredditNotFoundError(RedditMCPError):
    """Raised when a subreddit cannot be found."""


class PostNotFoundError(RedditMCPError):
    """Raised when a post cannot be found."""


class CommentNotFoundError(RedditMCPError):
    """Raised when a comment cannot be found."""


class WikiPageNotFoundError(RedditMCPError):
    """Raised when a wiki page cannot be found."""


class UserNotFoundError(RedditMCPError):
    """Raised when a user cannot be found."""


class ValidationError(RedditMCPError):
    """Raised when input validation fails."""


class RateLimitExhaustedError(RedditMCPError):
    """Raised when all credentials have exhausted their rate limits."""


class RedditAPIError(RedditMCPError):
    """Raised when the Reddit API returns a server error or is unreachable."""


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator that catches RedditMCPError and returns an error dict.

    Eliminates the need for repetitive try/except blocks in each tool function.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except RedditMCPError as e:
            return {"error": str(e), "error_type": type(e).__name__}

    return wrapper
