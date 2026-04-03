"""Tool registration for the Reddit MCP server."""

from reddit_mcp.tools.comments import register_comment_tools
from reddit_mcp.tools.posts import register_post_tools
from reddit_mcp.tools.search import register_search_tools
from reddit_mcp.tools.subreddits import register_subreddit_tools
from reddit_mcp.tools.users import register_user_tools


def register_all_tools(mcp, get_client):
    """Register all MCP tools from submodules."""
    register_search_tools(mcp, get_client)
    register_post_tools(mcp, get_client)
    register_comment_tools(mcp, get_client)
    register_user_tools(mcp, get_client)
    register_subreddit_tools(mcp, get_client)
