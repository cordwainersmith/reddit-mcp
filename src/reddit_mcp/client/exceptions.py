"""Context managers for translating asyncpraw exceptions into RedditMCPError subclasses."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpraw.exceptions
import asyncprawcore.exceptions

from reddit_mcp.errors import (
    PostNotFoundError,
    RedditAPIError,
    RedditMCPError,
    SubmissionError,
)


@asynccontextmanager
async def translate_exceptions(
    not_found_cls: type[RedditMCPError],
    subject: str,
    forbidden_msg: str | None = None,
) -> AsyncIterator[None]:
    """Translate asyncpraw exceptions into RedditMCPError subclasses.

    Args:
        not_found_cls: The specific error class for NotFound/Forbidden/Redirect.
        subject: A human-readable subject string for error messages,
                 e.g. "Subreddit 'python'" or "Post 'abc123'".
        forbidden_msg: Optional custom message for Forbidden errors.
                       Defaults to "{subject} is private or quarantined".
    """
    try:
        yield
    except asyncprawcore.exceptions.NotFound:
        raise not_found_cls(f"{subject} not found")
    except asyncprawcore.exceptions.Redirect:
        raise not_found_cls(f"{subject} not found (redirect)")
    except asyncprawcore.exceptions.Forbidden:
        raise not_found_cls(forbidden_msg or f"{subject} is private or quarantined")
    except asyncprawcore.exceptions.ServerError as e:
        raise RedditAPIError(f"Reddit API server error: {e}")
    except (asyncio.TimeoutError, OSError) as e:
        raise RedditAPIError(f"Network error: {e}")


@asynccontextmanager
async def translate_write_exceptions(subject: str) -> AsyncIterator[None]:
    """Translate asyncpraw exceptions for write operations into RedditMCPError subclasses.

    Args:
        subject: A human-readable subject string for error messages,
                 e.g. "Vote on post 'abc123'" or "Reply to comment 'xyz'".
    """
    try:
        yield
    except asyncprawcore.exceptions.NotFound:
        raise PostNotFoundError(f"{subject}: target not found")
    except asyncprawcore.exceptions.Forbidden as e:
        raise RedditAPIError(
            f"{subject}: insufficient permissions. "
            "Check that the account has the required privileges. "
            f"Reddit response: {e}"
        )
    except asyncprawcore.exceptions.Redirect:
        raise PostNotFoundError(f"{subject}: target not found (redirect)")
    except asyncprawcore.exceptions.ServerError as e:
        raise RedditAPIError(f"Reddit API server error during {subject}: {e}")
    except asyncpraw.exceptions.RedditAPIException as e:
        # Surface Reddit's specific error messages (rate limits, subreddit rules, etc.)
        raise SubmissionError(f"{subject} failed: {e}")
    except (asyncio.TimeoutError, OSError) as e:
        raise RedditAPIError(f"Network error during {subject}: {e}")
