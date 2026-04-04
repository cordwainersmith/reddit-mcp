"""Write-action tools for Reddit MCP server (vote, reply, post, save, delete, edit)."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from mcp.server.fastmcp import FastMCP

from reddit_mcp.client import RedditClient
from reddit_mcp.errors import ValidationError, handle_tool_errors
from reddit_mcp.validators import (
    validate_body_text,
    validate_post_title,
    validate_subreddit_name,
    validate_thing_type,
    validate_url,
    validate_vote_direction,
)


def register_action_tools(mcp: FastMCP, get_client: Callable[[], Awaitable[RedditClient]]) -> None:
    """Register write-action MCP tools."""

    @mcp.tool()
    @handle_tool_errors
    async def reddit_vote(
        thing_id: Annotated[str, "The ID of the post or comment to vote on (without t1_/t3_ prefix)"],
        thing_type: Annotated[str, "Type of thing to vote on: 'post' or 'comment'"],
        direction: Annotated[str, "Vote direction: 'up' (upvote), 'down' (downvote), or 'clear' (remove vote)"],
    ) -> dict:
        """
        Upvote, downvote, or clear vote on a Reddit post or comment.

        Requires REDDIT_USERNAME and REDDIT_PASSWORD to be configured.

        Returns: {success, id, permalink, message}.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|AUTH_REQUIRED|API_ERROR"}
        """
        thing_type = validate_thing_type(thing_type)
        direction = validate_vote_direction(direction)

        client = await get_client()
        return await client.vote(
            thing_id=thing_id.strip(),
            thing_type=thing_type,
            direction=direction,
        )

    @mcp.tool()
    @handle_tool_errors
    async def reddit_reply(
        thing_id: Annotated[str, "The ID of the post or comment to reply to (without t1_/t3_ prefix)"],
        thing_type: Annotated[str, "Type of thing to reply to: 'post' (top-level comment) or 'comment' (nested reply)"],
        body: Annotated[str, "The markdown body of your reply"],
    ) -> dict:
        """
        Reply to a Reddit post or comment.

        Use thing_type 'post' to add a top-level comment, or 'comment' to add a nested reply.
        Requires REDDIT_USERNAME and REDDIT_PASSWORD to be configured.

        Returns: {success, id, permalink, message}.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|AUTH_REQUIRED|API_ERROR"}
        """
        thing_type = validate_thing_type(thing_type)
        body = validate_body_text(body)

        client = await get_client()
        if thing_type == "post":
            return await client.reply_to_post(post_id=thing_id.strip(), body=body)
        return await client.reply_to_comment(comment_id=thing_id.strip(), body=body)

    @mcp.tool()
    @handle_tool_errors
    async def reddit_create_post(
        subreddit: Annotated[str, "Subreddit name to post in (without r/ prefix)"],
        title: Annotated[str, "Post title (max 300 characters)"],
        body: Annotated[str | None, "Self-post body text (markdown). Mutually exclusive with url."] = None,
        url: Annotated[str | None, "Link URL for link posts. Mutually exclusive with body."] = None,
        flair_id: Annotated[str | None, "Optional flair ID (UUID from subreddit flair settings)"] = None,
        flair_text: Annotated[str | None, "Optional flair text for the post"] = None,
    ) -> dict:
        """
        Create a new Reddit post (self-post or link post) in a subreddit.

        Provide either 'body' for a self-post or 'url' for a link post, not both.
        Requires REDDIT_USERNAME and REDDIT_PASSWORD to be configured.

        Returns: {success, id, permalink, message}.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|AUTH_REQUIRED|SUBMISSION_ERROR|API_ERROR"}
        """
        subreddit = validate_subreddit_name(subreddit)
        title = validate_post_title(title)

        if body is not None and url is not None:
            raise ValidationError("Provide either 'body' (for self-post) or 'url' (for link post), not both.")
        if body is None and url is None:
            raise ValidationError("Either 'body' (for self-post) or 'url' (for link post) must be provided.")

        if body is not None:
            body = validate_body_text(body)
        if url is not None:
            url = validate_url(url)

        client = await get_client()
        return await client.create_post(
            subreddit_name=subreddit,
            title=title,
            body=body,
            url=url,
            flair_id=flair_id,
            flair_text=flair_text,
        )

    @mcp.tool()
    @handle_tool_errors
    async def reddit_save(
        thing_id: Annotated[str, "The ID of the post or comment to save/unsave (without t1_/t3_ prefix)"],
        thing_type: Annotated[str, "Type of thing: 'post' or 'comment'"],
        unsave: Annotated[bool, "Set to true to unsave a previously saved item"] = False,
    ) -> dict:
        """
        Save or unsave a Reddit post or comment for later reference.

        Requires REDDIT_USERNAME and REDDIT_PASSWORD to be configured.

        Returns: {success, id, permalink, message}.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|AUTH_REQUIRED|API_ERROR"}
        """
        thing_type = validate_thing_type(thing_type)

        client = await get_client()
        return await client.save_thing(
            thing_id=thing_id.strip(),
            thing_type=thing_type,
            unsave=unsave,
        )

    @mcp.tool()
    @handle_tool_errors
    async def reddit_delete(
        thing_id: Annotated[str, "The ID of the post or comment to delete (without t1_/t3_ prefix)"],
        thing_type: Annotated[str, "Type of thing to delete: 'post' or 'comment'"],
    ) -> dict:
        """
        Delete a Reddit post or comment authored by the authenticated user.

        This action is permanent and cannot be undone.
        Requires REDDIT_USERNAME and REDDIT_PASSWORD to be configured.

        Returns: {success, id, permalink, message}.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|AUTH_REQUIRED|API_ERROR"}
        """
        thing_type = validate_thing_type(thing_type)

        client = await get_client()
        return await client.delete_thing(
            thing_id=thing_id.strip(),
            thing_type=thing_type,
        )

    @mcp.tool()
    @handle_tool_errors
    async def reddit_edit(
        thing_id: Annotated[str, "The ID of the post or comment to edit (without t1_/t3_ prefix)"],
        thing_type: Annotated[str, "Type of thing to edit: 'post' or 'comment'"],
        body: Annotated[str, "The new markdown body text"],
    ) -> dict:
        """
        Edit a Reddit post or comment authored by the authenticated user.

        Only self-posts can be edited (not link posts).
        Requires REDDIT_USERNAME and REDDIT_PASSWORD to be configured.

        Returns: {success, id, permalink, message}.
        On error: {"error": "...", "error_type": "INVALID_INPUT|NOT_FOUND|AUTH_REQUIRED|API_ERROR"}
        """
        thing_type = validate_thing_type(thing_type)
        body = validate_body_text(body)

        client = await get_client()
        return await client.edit_thing(
            thing_id=thing_id.strip(),
            thing_type=thing_type,
            body=body,
        )
