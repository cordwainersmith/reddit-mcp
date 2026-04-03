"""Subreddit-related tools for Reddit MCP server."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from mcp.server.fastmcp import FastMCP

from reddit_mcp.client import RedditClient
from reddit_mcp.errors import handle_tool_errors
from reddit_mcp.validators import validate_subreddit_name, validate_wiki_page_name


def register_subreddit_tools(mcp: FastMCP, get_client: Callable[[], Awaitable[RedditClient]]) -> None:
    """Register subreddit-related MCP tools."""

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_subreddit_info(
        subreddit: Annotated[str, "Subreddit name without r/ prefix"],
    ) -> dict:
        """
        Get metadata about a Reddit subreddit: subscriber count, description, active users.

        Use this for context before searching or browsing a specific subreddit.
        """
        subreddit = validate_subreddit_name(subreddit)

        client = await get_client()
        return await client.get_subreddit_info(subreddit)

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_subreddit_wiki(
        subreddit: Annotated[str, "Subreddit name without r/ prefix"],
        page: Annotated[str, "Wiki page name (default: 'index')"] = "index",
    ) -> dict:
        """
        Read a wiki page from a Reddit subreddit.

        Many subreddits maintain FAQs, tool lists, and guides in their wikis.
        """
        subreddit = validate_subreddit_name(subreddit)
        page = validate_wiki_page_name(page)

        client = await get_client()
        return await client.get_wiki_page(subreddit, page)

    @mcp.tool()
    @handle_tool_errors
    async def reddit_list_subreddit_wiki_pages(
        subreddit: Annotated[str, "Subreddit name without r/ prefix"],
    ) -> list[str] | dict:
        """
        List available wiki pages in a Reddit subreddit.

        Use this to discover what wiki content a subreddit offers before fetching specific pages.
        """
        subreddit = validate_subreddit_name(subreddit)

        client = await get_client()
        return await client.list_wiki_pages(subreddit)
