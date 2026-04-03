"""Comment-related tools for Reddit MCP server."""

from typing import Annotated

from reddit_mcp.errors import handle_tool_errors
from reddit_mcp.validators import validate_limit


def register_comment_tools(mcp, get_client):
    """Register comment-related MCP tools."""

    @mcp.tool()
    @handle_tool_errors
    async def reddit_get_comment_with_replies(
        comment_id: Annotated[str, "The comment ID to focus on"],
        context: Annotated[int, "How many parent comments to include (1-10)"] = 5,
        reply_depth: Annotated[int, "How many levels of replies to include (1-5)"] = 2,
        reply_limit: Annotated[int, "Max replies per level (1-25)"] = 10,
    ) -> dict:
        """
        Get a Reddit comment with its parent chain and nested replies.

        Use this to read the full context of a Reddit comment thread, including
        ancestor comments and reply trees.
        """
        context = validate_limit(context, min_val=1, max_val=10)
        reply_depth = validate_limit(reply_depth, min_val=1, max_val=5)
        reply_limit = validate_limit(reply_limit, min_val=1, max_val=25)

        client = await get_client()
        return await client.get_comment_thread(
            comment_id=comment_id,
            context=context,
            reply_depth=reply_depth,
            reply_limit=reply_limit,
        )
