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

For write operations (vote, reply, post, save, delete, edit), also set:

```bash
export REDDIT_USERNAME="your_reddit_username"
export REDDIT_PASSWORD="your_reddit_password"
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
| `reddit_search_posts` | Search posts by keywords across subreddits |
| `reddit_find_subreddits` | Find subreddits by topic or keyword |
| `reddit_get_subreddit_posts` | Browse posts from subreddits by sort order |
| `reddit_get_post_details` | Fetch a post with its comments |
| `reddit_get_posts_by_ids` | Fetch multiple posts by ID in one call (max 10) |
| `reddit_get_trending_posts` | Popular posts site-wide |
| `reddit_get_comment_with_replies` | Get a comment with parent chain and nested replies |
| `reddit_get_user_info` | User profile metadata |
| `reddit_get_user_posts` | User's submission history |
| `reddit_get_user_comments` | User's comment history |
| `reddit_get_subreddit_info` | Subreddit metadata |
| `reddit_get_subreddit_wiki` | Read a subreddit wiki page |
| `reddit_list_subreddit_wiki_pages` | List available wiki pages |
| `reddit_vote` | Upvote, downvote, or clear vote on a post or comment |
| `reddit_reply_to_post` | Reply to a post with a top-level comment |
| `reddit_reply_to_comment` | Reply to a comment with a nested reply |
| `reddit_create_post` | Create a new self-post or link post in a subreddit |
| `reddit_save` | Save a post or comment for later |
| `reddit_unsave` | Unsave a previously saved post or comment |
| `reddit_delete` | Delete a post or comment you authored |
| `reddit_edit` | Edit a post or comment you authored |
