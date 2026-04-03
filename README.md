# reddit-mcp

![reddit-mcp](docs/assets/cover.png)

MCP server exposing Reddit search and browsing as tools. Uses AsyncPRAW with multi-credential rotation and per-credential rate limiting (55 req/min).

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- One or more Reddit API credentials (script-type apps via https://www.reddit.com/prefs/apps)

## Setup

```bash
uv sync
```

Set the environment variable with your Reddit API credentials:

```bash
export REDDIT_CREDENTIALS="client_id1:secret1,client_id2:secret2"
```

Optionally set a custom user agent:

```bash
export REDDIT_USER_AGENT="my-app/1.0"
```

## Run

```bash
uv run reddit-mcp
```

## Tests

```bash
uv sync --group dev
uv run pytest tests/ -v
```

## Tools

| Tool | Description |
|---|---|
| `search_reddit` | Search posts by keywords across subreddits |
| `search_subreddits` | Find subreddits by topic |
| `get_subreddit_posts` | Browse posts by sort order |
| `get_post_details` | Fetch a post with comments |
| `get_posts_batch` | Fetch multiple posts at once (max 10) |
| `get_trending` | Popular posts site-wide |
| `get_comment_thread` | Follow a conversation thread with parent/reply context |
| `get_user_info` | User profile metadata |
| `get_user_posts` | User's submission history |
| `get_user_comments` | User's comment history |
| `get_subreddit_info` | Subreddit metadata |
| `get_subreddit_wiki` | Read a subreddit wiki page |
| `list_subreddit_wiki_pages` | List available wiki pages |
