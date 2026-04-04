"""Write operations for the Reddit client (vote, reply, post, save, delete, edit)."""

from typing import Any

from reddit_mcp.client.base import RedditClient
from reddit_mcp.client.exceptions import translate_write_exceptions
from reddit_mcp.models import ActionResultDict


async def vote(
    self: RedditClient,
    thing_id: str,
    thing_type: str,
    direction: str,
    username: str,
) -> ActionResultDict:
    """Vote on a post or comment.

    Args:
        thing_id: The ID of the post or comment.
        thing_type: Either "post" or "comment".
        direction: One of "up", "down", "clear".
        username: The configured Reddit username to act as.
    """
    self._require_user(username)
    async with translate_write_exceptions(f"Vote on {thing_type} '{thing_id}'"):
        thing = await self._resolve_thing(thing_id, thing_type, username=username)

        if direction == "up":
            await thing.upvote()
        elif direction == "down":
            await thing.downvote()
        else:
            await thing.clear_vote()

        return {
            "success": True,
            "id": thing_id,
            "permalink": "",
            "message": f"Successfully voted '{direction}' on {thing_type} '{thing_id}'",
        }


async def reply_to_post(
    self: RedditClient,
    post_id: str,
    body: str,
    username: str,
) -> ActionResultDict:
    """Submit a top-level comment on a post.

    Args:
        post_id: The ID of the post to reply to.
        body: The markdown body of the comment.
        username: The configured Reddit username to act as.
    """
    self._require_user(username)
    reddit = await self._get_reddit_for_user(username)
    async with translate_write_exceptions(f"Reply to post '{post_id}'"):
        submission = await reddit.submission(id=post_id)
        comment = await submission.reply(body)
        await comment.load()
        return {
            "success": True,
            "id": comment.id,
            "permalink": f"https://reddit.com{comment.permalink}",
            "message": f"Successfully replied to post '{post_id}'",
        }


async def reply_to_comment(
    self: RedditClient,
    comment_id: str,
    body: str,
    username: str,
) -> ActionResultDict:
    """Submit a reply to an existing comment.

    Args:
        comment_id: The ID of the comment to reply to.
        body: The markdown body of the reply.
        username: The configured Reddit username to act as.
    """
    self._require_user(username)
    reddit = await self._get_reddit_for_user(username)
    async with translate_write_exceptions(f"Reply to comment '{comment_id}'"):
        comment = await reddit.comment(id=comment_id)
        await comment.refresh()
        reply = await comment.reply(body)
        await reply.load()
        return {
            "success": True,
            "id": reply.id,
            "permalink": f"https://reddit.com{reply.permalink}",
            "message": f"Successfully replied to comment '{comment_id}'",
        }


async def create_post(
    self: RedditClient,
    subreddit_name: str,
    title: str,
    username: str,
    body: str | None = None,
    url: str | None = None,
    flair_id: str | None = None,
    flair_text: str | None = None,
) -> ActionResultDict:
    """Create a new post in a subreddit.

    Args:
        subreddit_name: The subreddit to post to.
        title: The post title.
        username: The configured Reddit username to act as.
        body: Self-post body text (mutually exclusive with url).
        url: Link URL (mutually exclusive with body).
        flair_id: Optional flair ID.
        flair_text: Optional flair text.
    """
    self._require_user(username)
    reddit = await self._get_reddit_for_user(username)
    async with translate_write_exceptions(f"Create post in r/{subreddit_name}"):
        subreddit = await reddit.subreddit(subreddit_name)
        kwargs: dict[str, Any] = {"title": title}
        if flair_id:
            kwargs["flair_id"] = flair_id
        if flair_text:
            kwargs["flair_text"] = flair_text

        if url:
            kwargs["url"] = url
            submission = await subreddit.submit(**kwargs)
        else:
            kwargs["selftext"] = body or ""
            submission = await subreddit.submit(**kwargs)

        await submission.load()
        return {
            "success": True,
            "id": submission.id,
            "permalink": f"https://reddit.com{submission.permalink}",
            "message": f"Successfully created post in r/{subreddit_name}",
        }


async def save_thing(
    self: RedditClient,
    thing_id: str,
    thing_type: str,
    username: str,
    unsave: bool = False,
) -> ActionResultDict:
    """Save or unsave a post or comment.

    Args:
        thing_id: The ID of the post or comment.
        thing_type: Either "post" or "comment".
        username: The configured Reddit username to act as.
        unsave: If True, unsave instead of save.
    """
    self._require_user(username)
    action = "unsave" if unsave else "save"
    async with translate_write_exceptions(f"{action.title()} {thing_type} '{thing_id}'"):
        thing = await self._resolve_thing(thing_id, thing_type, username=username)

        if unsave:
            await thing.unsave()
        else:
            await thing.save()

        return {
            "success": True,
            "id": thing_id,
            "permalink": "",
            "message": f"Successfully {'unsaved' if unsave else 'saved'} {thing_type} '{thing_id}'",
        }


async def delete_thing(
    self: RedditClient,
    thing_id: str,
    thing_type: str,
    username: str,
) -> ActionResultDict:
    """Delete a post or comment authored by the authenticated user.

    Args:
        thing_id: The ID of the post or comment.
        thing_type: Either "post" or "comment".
        username: The configured Reddit username to act as.
    """
    self._require_user(username)
    async with translate_write_exceptions(f"Delete {thing_type} '{thing_id}'"):
        thing = await self._resolve_thing(thing_id, thing_type, username=username)
        await thing.delete()
        return {
            "success": True,
            "id": thing_id,
            "permalink": "",
            "message": f"Successfully deleted {thing_type} '{thing_id}'",
        }


async def edit_thing(
    self: RedditClient,
    thing_id: str,
    thing_type: str,
    body: str,
    username: str,
) -> ActionResultDict:
    """Edit a post or comment authored by the authenticated user.

    Args:
        thing_id: The ID of the post or comment.
        thing_type: Either "post" or "comment".
        body: The new markdown body text.
        username: The configured Reddit username to act as.
    """
    self._require_user(username)
    async with translate_write_exceptions(f"Edit {thing_type} '{thing_id}'"):
        thing = await self._resolve_thing(thing_id, thing_type, username=username)
        edited = await thing.edit(body)
        permalink = getattr(edited, "permalink", "")
        if permalink and not permalink.startswith("http"):
            permalink = f"https://reddit.com{permalink}"

        return {
            "success": True,
            "id": thing_id,
            "permalink": permalink,
            "message": f"Successfully edited {thing_type} '{thing_id}'",
        }
