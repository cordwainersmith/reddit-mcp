# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reddit MCP server that exposes Reddit search and browsing as MCP tools. Uses AsyncPRAW with multi-credential rotation and per-credential rate limiting (55 req/min per credential).

## Commands

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --group dev

# Run the MCP server
uv run reddit-mcp

# Run tests
uv run pytest tests/ -v

# Run a single test file or test
uv run pytest tests/test_client.py -v
uv run pytest tests/test_client.py::test_name -v

# Run tests with coverage
uv run pytest tests/ -v --cov=reddit_mcp
```

## Architecture

Package layout under `src/reddit_mcp/`:

- **`server.py`** - FastMCP app instantiation, credential parsing, client singleton management, and `main()` entry point. Registers all tools via `tools/__init__.py`.
- **`client.py`** - Async Reddit API client wrapping AsyncPRAW. Implements credential rotation across multiple API key pairs with per-credential rate limit windows. Contains all data serialization (`_submission_to_dict`, `_comment_to_dict`).
- **`models.py`** - TypedDict definitions for `PostDict`, `CommentDict`, `SubredditInfoDict`, `UserInfoDict`, `WikiPageDict`.
- **`validators.py`** - Input validation functions for `sort`, `time_filter`, `limit`, subreddit names, and usernames. Raises `ValidationError` with descriptive messages.
- **`errors.py`** - Custom exception hierarchy: `RedditMCPError` (base), `CredentialError`, `SubredditNotFoundError`, `PostNotFoundError`, `UserNotFoundError`, `ValidationError`, `RateLimitExhaustedError`.
- **`cache.py`** - TTL caching decorator using `cachetools.TTLCache`. Applied to `get_subreddit_info` (5min), hot posts (2min), `search_subreddits` (10min), and wiki methods (10min).
- **`tools/`** - MCP tool definitions split by domain:
  - `search.py` - `search_reddit`, `search_subreddits`
  - `posts.py` - `get_subreddit_posts`, `get_post_details`, `get_posts_batch`, `get_trending`
  - `comments.py` - `get_comment_thread`
  - `users.py` - `get_user_info`, `get_user_posts`, `get_user_comments`
  - `subreddits.py` - `get_subreddit_info`, `get_subreddit_wiki`, `list_subreddit_wiki_pages`

### Key patterns

- **Tool registration**: Each `tools/*.py` file exports a `register_*_tools(mcp, get_client)` function. The `get_client` callable is a lazy async factory passed from `server.py`. Tools call `client = await get_client()` to obtain the singleton `RedditClient`.
- **Error handling in tools**: All tool functions use the `@handle_tool_errors` decorator from `errors.py`, which catches `RedditMCPError` and returns `{"error": ..., "error_type": ...}` dicts instead of raising.
- **Exception translation**: `client.py` uses an `_translate_exceptions` async context manager to convert asyncpraw exceptions into the custom error hierarchy.
- **Credential rotation**: `RedditClient` cycles through multiple API credential pairs, each with a 55 req/min sliding window. When all are exhausted, it sleeps until the nearest reset.

### Environment variables

- `REDDIT_CREDENTIALS` (required) - comma-separated `client_id:secret` pairs
- `REDDIT_USER_AGENT` - custom user agent string (default: `reddit-mcp/1.0`)
- `REDDIT_BODY_TRUNCATE_LENGTH` - post body truncation (default: 2000)
- `REDDIT_COMMENT_TRUNCATE_LENGTH` - comment truncation (default: 2000)
- `REDDIT_WIKI_TRUNCATE_LENGTH` - wiki page truncation (default: 5000)
- `REDDIT_MCP_IGNORE_SSL` - set to `1` to skip SSL verification (for corporate proxies like Zscaler)

Example `.env`:

```
REDDIT_CREDENTIALS=client_id1:secret1,client_id2:secret2
REDDIT_MCP_IGNORE_SSL=1
```

## Testing

pytest-asyncio is configured with `asyncio_mode = "auto"`, so async test functions are detected automatically without `@pytest.mark.asyncio`.

Tests use a custom `MockObj` class from `conftest.py` (not `MagicMock`) so that `hasattr()` returns `False` for attributes not explicitly set, matching AsyncPRAW's real behavior. Use the `make_submission()` and `make_comment()` helpers to create test fixtures.

## Git Conventions

Branch names: `<type>/<TICKET>-<description>` where type is `feature/`, `bugfix/`, or `infra/`.


