"""Search tools for Reddit MCP server."""

from typing import Annotated

from reddit_mcp.errors import handle_tool_errors
from reddit_mcp.validators import (
    SEARCH_SORT_OPTIONS,
    validate_limit,
    validate_sort,
    validate_subreddit_name,
    validate_time_filter,
)


def register_search_tools(mcp, get_client):
    """Register search-related MCP tools."""

    @mcp.tool()
    @handle_tool_errors
    async def reddit_search_posts(
        query: Annotated[str, "Search query string (keywords)"],
        subreddits: Annotated[str, "Comma-separated subreddit names, e.g. 'devops,sre,kubernetes'. Use 'all' for site-wide."] = "all",
        sort: Annotated[str, "Sort order: relevance, hot, top, new, comments"] = "relevance",
        time_filter: Annotated[str, "Time filter: hour, day, week, month, year, all"] = "week",
        limit: Annotated[int, "Max results (1-100)"] = 25,
    ) -> list[dict] | dict:
        """
        Search Reddit posts by keywords across one or more subreddits.

        Use this to find Reddit discussions about specific topics, products, or technologies.
        """
        sort = validate_sort(sort, SEARCH_SORT_OPTIONS, "search sort")
        time_filter = validate_time_filter(time_filter)
        limit = validate_limit(limit)
        subs = [s.strip() for s in subreddits.split(",")]
        if subs != ["all"]:
            subs = [validate_subreddit_name(s) for s in subs]

        client = await get_client()
        return await client.search(
            subreddits=subs, query=query, sort=sort, time_filter=time_filter, limit=limit
        )

    @mcp.tool()
    @handle_tool_errors
    async def reddit_find_subreddits(
        query: Annotated[str, "Search terms to find subreddits"],
        limit: Annotated[int, "Max results (1-50)"] = 10,
    ) -> list[dict] | dict:
        """
        Find Reddit subreddits by topic or keyword.

        Use this to discover which Reddit communities discuss a given subject.
        """
        limit = validate_limit(limit, max_val=50)

        client = await get_client()
        return await client.search_subreddits(query=query, limit=limit)
