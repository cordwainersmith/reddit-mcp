"""User-related tools for Reddit MCP server."""

from typing import Annotated

from reddit_mcp.errors import handle_tool_errors
from reddit_mcp.validators import (
    USER_SORT_OPTIONS,
    validate_limit,
    validate_sort,
    validate_time_filter,
    validate_username,
)


def register_user_tools(mcp, get_client):
    """Register user-related MCP tools."""

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_user_info(
        username: Annotated[str, "Reddit username (without u/ prefix)"],
    ) -> dict:
        """
        Get metadata about a Reddit user: karma, account age, verified status.

        Use this to understand a Reddit user's profile before looking at their posts or comments.
        """
        username = validate_username(username)

        client = await get_client()
        return await client.get_user_info(username)

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_user_posts(
        username: Annotated[str, "Reddit username (without u/ prefix)"],
        sort: Annotated[str, "Sort: new, hot, top, controversial"] = "new",
        time_filter: Annotated[str, "Time filter for top/controversial: hour, day, week, month, year, all"] = "all",
        limit: Annotated[int, "Max posts (1-100)"] = 25,
    ) -> list[dict] | dict:
        """
        Get posts submitted by a specific Reddit user.

        Use this to see a Reddit user's submission history.
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
        time_filter: Annotated[str, "Time filter for top/controversial: hour, day, week, month, year, all"] = "all",
        limit: Annotated[int, "Max comments (1-100)"] = 25,
    ) -> list[dict] | dict:
        """
        Get comments made by a specific Reddit user.

        Use this to see a Reddit user's comment history.
        """
        username = validate_username(username)
        sort = validate_sort(sort, USER_SORT_OPTIONS, "user sort")
        time_filter = validate_time_filter(time_filter)
        limit = validate_limit(limit)

        client = await get_client()
        return await client.get_user_comments(
            username=username, sort=sort, time_filter=time_filter, limit=limit
        )
