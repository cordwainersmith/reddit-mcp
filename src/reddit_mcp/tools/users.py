"""User-related tools for Reddit MCP server."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from mcp.server.fastmcp import FastMCP

from reddit_mcp.client import RedditClient
from reddit_mcp.errors import handle_tool_errors
from reddit_mcp.validators import (
    USER_SORT_OPTIONS,
    validate_limit,
    validate_sort,
    validate_time_filter,
    validate_username,
)


def register_user_tools(mcp: FastMCP, get_client: Callable[[], Awaitable[RedditClient]]) -> None:
    """Register user-related MCP tools."""

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_user_info(
        username: Annotated[str, "Reddit username (without u/ prefix)"],
    ) -> dict:
        """
        Get metadata about a Reddit user: karma, account age, verified status.

        Use this to understand a Reddit user's profile before looking at their posts or comments.

        Returns: {name, id, comment_karma, link_karma, created_utc, has_verified_email,
        is_mod, is_gold, icon_img, subreddit}.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|RATE_LIMITED|API_ERROR"}
        """
        username = validate_username(username)

        client = await get_client()
        return await client.get_user_info(username)

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_user_posts(
        username: Annotated[str, "Reddit username (without u/ prefix)"],
        sort: Annotated[str, "Sort: new, hot, top, controversial"] = "new",
        time_filter: Annotated[str, "Time filter for 'top' or 'controversial' sort only: hour, day, week, month, year, all. Ignored for other sort orders."] = "all",
        limit: Annotated[int, "Max posts (1-100)"] = 25,
    ) -> list[dict] | dict:
        """
        Get posts submitted by a specific Reddit user.

        Use this to see a Reddit user's submission history.

        Returns: List of post dicts, each with keys: id, title, body, subreddit, author,
        score, num_comments, created_utc, url, permalink, upvote_ratio, is_self, post_type.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|RATE_LIMITED|API_ERROR"}
        """
        username = validate_username(username)
        sort = validate_sort(sort, USER_SORT_OPTIONS, "user sort")
        time_filter = validate_time_filter(time_filter)
        limit = validate_limit(limit)

        client = await get_client()
        return await client.get_user_posts(
            username=username, sort=sort, time_filter=time_filter, limit=limit
        )

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_user_comments(
        username: Annotated[str, "Reddit username (without u/ prefix)"],
        sort: Annotated[str, "Sort: new, hot, top, controversial"] = "new",
        time_filter: Annotated[str, "Time filter for 'top' or 'controversial' sort only: hour, day, week, month, year, all. Ignored for other sort orders."] = "all",
        limit: Annotated[int, "Max comments (1-100)"] = 25,
    ) -> list[dict] | dict:
        """
        Get comments made by a specific Reddit user.

        Use this to see a Reddit user's comment history.

        Returns: List of comment dicts, each with keys: id, post_id, author, body, score,
        created_utc, is_op, parent_id, is_root, permalink, edited, distinguished.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|RATE_LIMITED|API_ERROR"}
        """
        username = validate_username(username)
        sort = validate_sort(sort, USER_SORT_OPTIONS, "user sort")
        time_filter = validate_time_filter(time_filter)
        limit = validate_limit(limit)

        client = await get_client()
        return await client.get_user_comments(
            username=username, sort=sort, time_filter=time_filter, limit=limit
        )
