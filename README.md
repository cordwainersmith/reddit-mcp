# reddit-mcp

![reddit-mcp](docs/assets/cover.png)

MCP server exposing Reddit search, browsing, and write operations (posting, commenting, voting) as tools. Uses AsyncPRAW with multi-credential rotation and per-credential rate limiting (55 req/min).

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- One or more Reddit API credentials (script-type apps via https://www.reddit.com/prefs/apps)

## Setup

```bash
uv sync
cp .env.example .env
```

Edit `.env` with your Reddit API credentials:

```env
# Single credential
REDDIT_CREDENTIALS=your_client_id:your_client_secret

# Or multiple credentials for rate limit rotation
REDDIT_CREDENTIALS=client_id1:secret1,client_id2:secret2,client_id3:secret3

# User agent string
REDDIT_USER_AGENT=reddit-mcp/1.0 (by /u/your_username)

# For write operations (vote, reply, post, save, delete, edit)
# Multiple users supported - agents specify which username to act as
REDDIT_USERS=reddit_username1:password1,reddit_username2:password2

# Or single-user fallback (used if REDDIT_USERS is not set)
# REDDIT_USERNAME=your_reddit_username
# REDDIT_PASSWORD=your_reddit_password
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

### Read

| Tool | Description |
|---|---|
| `reddit_search_posts` | Search posts by keywords across subreddits (use `"all"` for site-wide) |
| `reddit_search_subreddits` | Search for subreddits by topic or keyword |
| `reddit_get_subreddit_posts` | Browse posts from subreddits by sort order (use `"popular"` for trending) |
| `reddit_get_post_details` | Fetch a post with its comments |
| `reddit_get_posts_by_ids` | Fetch multiple posts by ID in one call (max 10) |
| `reddit_get_comment_with_replies` | Get a comment with parent chain and nested replies |
| `reddit_get_user_info` | User profile metadata |
| `reddit_get_user_posts` | User's submission history |
| `reddit_get_user_comments` | User's comment history |
| `reddit_get_subreddit_info` | Subreddit metadata |
| `reddit_get_subreddit_wiki` | Read a subreddit wiki page |
| `reddit_list_subreddit_wiki_pages` | List available wiki pages |
| `reddit_get_server_status` | Server health, credential count, and cache stats |

### Write (require `REDDIT_USERS` or `REDDIT_USERNAME`/`REDDIT_PASSWORD`)

All write tools require a `username` parameter specifying which configured user to act as. Call `reddit_get_server_status` to see available usernames.

| Tool | Description |
|---|---|
| `reddit_vote` | Upvote, downvote, or clear vote on a post or comment |
| `reddit_reply` | Reply to a post (top-level comment) or comment (nested reply) |
| `reddit_create_post` | Create a new self-post or link post in a subreddit |
| `reddit_save` | Save or unsave a post or comment |
| `reddit_delete` | Delete a post or comment you authored |
| `reddit_edit` | Edit a post or comment you authored |
