"""Post-related tools for Reddit MCP server."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from mcp.server.fastmcp import FastMCP

from reddit_mcp.client import RedditClient
from reddit_mcp.errors import ValidationError, handle_tool_errors
from reddit_mcp.validators import (
    COMMENT_SORT_OPTIONS,
    POST_SORT_OPTIONS,
    validate_limit,
    validate_sort,
    validate_subreddit_name,
    validate_time_filter,
)


def register_post_tools(mcp: FastMCP, get_client: Callable[[], Awaitable[RedditClient]]) -> None:
    """Register post-related MCP tools."""

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_subreddit_posts(
        subreddits: Annotated[str, "Comma-separated subreddit names, e.g. 'devops,sre,kubernetes'"],
        sort: Annotated[str, "Sort: hot, new, top, rising"] = "hot",
        time_filter: Annotated[str, "Time filter for 'top' sort: hour, day, week, month, year, all"] = "week",
        limit: Annotated[int, "Max posts (1-100)"] = 25,
    ) -> list[dict] | dict:
        """
        Browse Reddit posts from one or more subreddits by sort order.

        Use this to see what's currently active or popular in specific Reddit communities.
        """
        sort = validate_sort(sort, POST_SORT_OPTIONS, "post sort")
        time_filter = validate_time_filter(time_filter)
        limit = validate_limit(limit)
        subs = [s.strip() for s in subreddits.split(",")]
        subs = [validate_subreddit_name(s) for s in subs]

        client = await get_client()
        return await client.get_posts(
            subreddits=subs, sort=sort, time_filter=time_filter, limit=limit
        )

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_post_details(
        post_id: Annotated[str, "Reddit post ID (e.g. 'abc123', without 't3_' prefix)"],
        include_comments: Annotated[bool, "Whether to include top comments"] = True,
        comment_limit: Annotated[int, "Max comments to include (1-200)"] = 20,
        comment_sort: Annotated[str, "Comment sort: best, top, new, controversial"] = "best",
    ) -> dict:
        """
        Fetch a specific Reddit post by ID, optionally with its top comments.

        Use this to deep-dive into a Reddit discussion found via search or browsing.
        """
        comment_sort = validate_sort(comment_sort, COMMENT_SORT_OPTIONS, "comment sort")
        comment_limit = validate_limit(comment_limit, max_val=200)

        client = await get_client()
        post = await client.get_post(post_id)

        result = {"post": post}
        if include_comments:
            result["comments"] = await client.get_comments(
                post_id, sort=comment_sort, limit=comment_limit
            )
        return result

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_posts_by_ids(
        post_ids: Annotated[str, "Comma-separated post IDs (max 10), e.g. 'abc123,def456'"],
        include_comments: Annotated[bool, "Whether to include top comments for each post"] = False,
        comment_limit: Annotated[int, "Max comments per post (1-50)"] = 5,
    ) -> list[dict] | dict:
        """
        Fetch multiple Reddit posts by their IDs in a single call.

        More efficient than calling reddit_get_post_details repeatedly when you have several post IDs.
        """
        comment_limit = validate_limit(comment_limit, max_val=50)

        ids = [pid.strip() for pid in post_ids.split(",") if pid.strip()]
        if len(ids) > 10:
            raise ValidationError("Maximum 10 post IDs per batch call")
        if not ids:
            raise ValidationError("No post IDs provided")

        client = await get_client()
        return await client.get_posts_batch(
            post_ids=ids,
            include_comments=include_comments,
            comment_limit=comment_limit,
        )

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_trending_posts(
        limit: Annotated[int, "Max posts (1-100)"] = 25,
    ) -> list[dict] | dict:
        """
        Get popular and trending posts across all of Reddit right now.

        Use this to see what's currently hot site-wide on Reddit.
        """
        limit = validate_limit(limit)

        client = await get_client()
        return await client.get_posts(subreddits=["popular"], sort="hot", limit=limit)
