"""Tool registration for the Reddit MCP server."""

from collections.abc import Awaitable, Callable

from mcp.server.fastmcp import FastMCP

from reddit_mcp.client import RedditClient
from reddit_mcp.tools.actions import register_action_tools
from reddit_mcp.tools.comments import register_comment_tools
from reddit_mcp.tools.posts import register_post_tools
from reddit_mcp.tools.search import register_search_tools
from reddit_mcp.tools.subreddits import register_subreddit_tools
from reddit_mcp.tools.users import register_user_tools

# Type alias for the client factory used by all tool registration functions.
GetClient = Callable[[], Awaitable[RedditClient]]


def register_all_tools(mcp: FastMCP, get_client: GetClient) -> None:
    """Register all MCP tools from submodules."""
    register_search_tools(mcp, get_client)
    register_post_tools(mcp, get_client)
    register_comment_tools(mcp, get_client)
    register_user_tools(mcp, get_client)
    register_subreddit_tools(mcp, get_client)
    register_action_tools(mcp, get_client)
