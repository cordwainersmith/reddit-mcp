"""Custom exception hierarchy and error-handling utilities for the Reddit MCP server."""

import functools
import logging
from typing import Callable

logger = logging.getLogger(__name__)


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


class AuthenticationRequiredError(RedditMCPError):
    """Raised when a write tool is called but no user credentials are configured."""


class UnknownUsernameError(RedditMCPError):
    """Raised when the specified username is not in the configured REDDIT_USERS."""


class SubmissionError(RedditMCPError):
    """Raised when post creation or submission fails."""


_ERROR_CODES: dict[type, str] = {
    ValidationError: "INVALID_INPUT",
    SubredditNotFoundError: "NOT_FOUND",
    PostNotFoundError: "NOT_FOUND",
    CommentNotFoundError: "NOT_FOUND",
    WikiPageNotFoundError: "NOT_FOUND",
    UserNotFoundError: "NOT_FOUND",
    RateLimitExhaustedError: "RATE_LIMITED",
    AuthenticationRequiredError: "AUTH_REQUIRED",
    UnknownUsernameError: "UNKNOWN_USER",
    CredentialError: "CREDENTIAL_ERROR",
    RedditAPIError: "API_ERROR",
    SubmissionError: "SUBMISSION_ERROR",
}


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator that catches RedditMCPError and returns an error dict.

    Also catches unexpected exceptions with a generic fallback so that
    MCP tools never crash silently.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except RedditMCPError as e:
            error_code = _ERROR_CODES.get(type(e), "ERROR")
            return {"error": str(e), "error_type": error_code}
        except Exception as e:
            logger.exception("Unexpected error in tool %s", func.__name__)
            return {"error": f"Internal error: {e}", "error_type": "INTERNAL_ERROR"}

    return wrapper
