"""Read operations for the Reddit client."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from reddit_mcp.cache import cached
from reddit_mcp.client.base import RedditClient
from reddit_mcp.client.exceptions import translate_exceptions
from reddit_mcp.client.serializers import (
    WIKI_TRUNCATE_LENGTH,
    comment_to_dict,
    submission_to_dict,
)
from reddit_mcp.errors import (
    CommentNotFoundError,
    PostNotFoundError,
    RedditMCPError,
    SubredditNotFoundError,
    UserNotFoundError,
    WikiPageNotFoundError,
)
from reddit_mcp.models import (
    CommentDict,
    PostDict,
    SubredditInfoDict,
    UserInfoDict,
    WikiPageDict,
)

logger = logging.getLogger(__name__)


async def search(
    self: RedditClient,
    subreddits: list[str],
    query: str,
    sort: str = "relevance",
    time_filter: str = "week",
    limit: int = 25,
) -> list[PostDict]:
    """Search for posts across one or more subreddits."""
    reddit = await self._get_reddit()
    sub_str = "+".join(subreddits) if subreddits else "all"
    async with translate_exceptions(SubredditNotFoundError, f"Subreddit '{sub_str}'"):
        subreddit = await reddit.subreddit(sub_str)
        posts = []
        async for submission in subreddit.search(
            query, sort=sort, time_filter=time_filter, limit=limit
        ):
            posts.append(submission_to_dict(submission))
        return posts


async def get_posts(
    self: RedditClient,
    subreddits: list[str],
    sort: str = "hot",
    time_filter: str = "week",
    limit: int = 25,
) -> list[PostDict]:
    """Browse posts from one or more subreddits."""
    # Use cached path for hot posts (semi-stable, reduces API calls)
    if sort == "hot":
        sub_str = "+".join(sorted(subreddits)) if subreddits else "all"
        return await self._get_hot_posts(sub_str, limit)
    return await _get_posts_uncached(self, subreddits, sort, time_filter, limit)


@cached(ttl=120, maxsize=32)
async def _get_hot_posts(
    self: RedditClient, sub_str: str, limit: int
) -> list[PostDict]:
    """Cached fetch of hot posts."""
    reddit = await self._get_reddit()
    async with translate_exceptions(SubredditNotFoundError, f"Subreddit '{sub_str}'"):
        subreddit = await reddit.subreddit(sub_str)
        posts = []
        async for submission in subreddit.hot(limit=limit):
            posts.append(submission_to_dict(submission))
        return posts


async def _get_posts_uncached(
    self: RedditClient,
    subreddits: list[str],
    sort: str = "hot",
    time_filter: str = "week",
    limit: int = 25,
) -> list[PostDict]:
    """Fetch posts without caching."""
    reddit = await self._get_reddit()
    sub_str = "+".join(subreddits) if subreddits else "all"
    async with translate_exceptions(SubredditNotFoundError, f"Subreddit '{sub_str}'"):
        subreddit = await reddit.subreddit(sub_str)
        posts = []
        if sort == "new":
            listing = subreddit.new(limit=limit)
        elif sort == "top":
            listing = subreddit.top(time_filter=time_filter, limit=limit)
        elif sort == "rising":
            listing = subreddit.rising(limit=limit)
        else:
            listing = subreddit.hot(limit=limit)

        async for submission in listing:
            posts.append(submission_to_dict(submission))
        return posts


async def get_post(self: RedditClient, post_id: str) -> PostDict:
    """Fetch a single post by ID with full body (no truncation)."""
    reddit = await self._get_reddit()
    async with translate_exceptions(PostNotFoundError, f"Post '{post_id}'"):
        submission = await reddit.submission(id=post_id)
        await submission.load()
        return submission_to_dict(submission, truncate_body=False)


async def get_comments(
    self: RedditClient,
    post_id: str,
    sort: str = "best",
    limit: int = 20,
) -> list[CommentDict]:
    """Fetch comments for a post."""
    reddit = await self._get_reddit()
    async with translate_exceptions(PostNotFoundError, f"Post '{post_id}'"):
        submission = await reddit.submission(id=post_id)
        submission.comment_sort = sort
        await submission.comments.replace_more(limit=0)

        comments = []
        for comment in submission.comments[:limit]:
            if hasattr(comment, "body"):
                comments.append(comment_to_dict(comment, post_id))
        return comments


@cached(ttl=300, maxsize=64)
async def get_subreddit_info(self: RedditClient, subreddit_name: str) -> SubredditInfoDict:
    """Get metadata about a subreddit."""
    reddit = await self._get_reddit()
    async with translate_exceptions(SubredditNotFoundError, f"Subreddit '{subreddit_name}'"):
        subreddit = await reddit.subreddit(subreddit_name)
        await subreddit.load()
        return {
            "name": subreddit.display_name,
            "title": subreddit.title,
            "description": subreddit.public_description,
            "subscribers": subreddit.subscribers,
            "active_users": subreddit.accounts_active,
            "created_utc": datetime.fromtimestamp(
                subreddit.created_utc, tz=timezone.utc
            ).isoformat(),
            "over_18": subreddit.over18,
            "url": f"https://reddit.com{subreddit.url}",
        }


@cached(ttl=600, maxsize=64)
async def search_subreddits(
    self: RedditClient,
    query: str,
    limit: int = 10,
) -> list[SubredditInfoDict]:
    """Search for subreddits by topic."""
    reddit = await self._get_reddit()
    async with translate_exceptions(
        SubredditNotFoundError,
        f"Subreddit search for '{query}'",
        forbidden_msg=f"Subreddit search for '{query}' is restricted",
    ):
        results = []
        async for subreddit in reddit.subreddits.search(query, limit=limit):
            created_utc = getattr(subreddit, "created_utc", None)
            results.append({
                "name": subreddit.display_name,
                "title": subreddit.title,
                "description": getattr(subreddit, "public_description", ""),
                "subscribers": getattr(subreddit, "subscribers", 0),
                "active_users": getattr(subreddit, "accounts_active", None),
                "created_utc": datetime.fromtimestamp(
                    created_utc, tz=timezone.utc
                ).isoformat() if created_utc else None,
                "over_18": getattr(subreddit, "over18", False),
                "url": f"https://reddit.com{subreddit.url}",
            })
        return results


async def get_user_info(self: RedditClient, username: str) -> UserInfoDict:
    """Get user profile metadata."""
    reddit = await self._get_reddit()
    async with translate_exceptions(
        UserNotFoundError,
        f"User '{username}'",
        forbidden_msg=f"User '{username}' is suspended or not accessible",
    ):
        redditor = await reddit.redditor(username)
        await redditor.load()
        subreddit_desc = None
        if hasattr(redditor, "subreddit") and redditor.subreddit:
            try:
                subreddit_desc = getattr(redditor.subreddit, "public_description", None)
            except (AttributeError, TypeError) as exc:
                logger.debug("Could not read subreddit description for user '%s': %s", username, exc)
        return {
            "name": redditor.name,
            "id": redditor.id,
            "comment_karma": redditor.comment_karma,
            "link_karma": redditor.link_karma,
            "created_utc": datetime.fromtimestamp(
                redditor.created_utc, tz=timezone.utc
            ).isoformat(),
            "has_verified_email": getattr(redditor, "has_verified_email", False),
            "is_mod": getattr(redditor, "is_mod", False),
            "is_gold": getattr(redditor, "is_gold", False),
            "icon_img": getattr(redditor, "icon_img", None),
            "subreddit": subreddit_desc,
        }


async def get_user_posts(
    self: RedditClient,
    username: str,
    sort: str = "new",
    time_filter: str = "all",
    limit: int = 25,
) -> list[PostDict]:
    """Get a user's submitted posts."""
    reddit = await self._get_reddit()
    async with translate_exceptions(
        UserNotFoundError,
        f"User '{username}'",
        forbidden_msg=f"User '{username}' is suspended or not accessible",
    ):
        redditor = await reddit.redditor(username)
        if sort == "top":
            listing = redditor.submissions.top(time_filter=time_filter, limit=limit)
        elif sort == "controversial":
            listing = redditor.submissions.controversial(time_filter=time_filter, limit=limit)
        elif sort == "hot":
            listing = redditor.submissions.hot(limit=limit)
        else:
            listing = redditor.submissions.new(limit=limit)

        posts = []
        async for submission in listing:
            posts.append(submission_to_dict(submission))
        return posts


async def get_user_comments(
    self: RedditClient,
    username: str,
    sort: str = "new",
    time_filter: str = "all",
    limit: int = 25,
) -> list[CommentDict]:
    """Get a user's comments."""
    reddit = await self._get_reddit()
    async with translate_exceptions(
        UserNotFoundError,
        f"User '{username}'",
        forbidden_msg=f"User '{username}' is suspended or not accessible",
    ):
        redditor = await reddit.redditor(username)
        if sort == "top":
            listing = redditor.comments.top(time_filter=time_filter, limit=limit)
        elif sort == "controversial":
            listing = redditor.comments.controversial(time_filter=time_filter, limit=limit)
        elif sort == "hot":
            listing = redditor.comments.hot(limit=limit)
        else:
            listing = redditor.comments.new(limit=limit)

        comments = []
        async for comment in listing:
            if hasattr(comment, "body"):
                post_id = comment.link_id
                if post_id.startswith("t3_"):
                    post_id = post_id[3:]
                comments.append(comment_to_dict(comment, post_id))
        return comments


async def get_comment_thread(
    self: RedditClient,
    comment_id: str,
    context: int = 5,
    reply_depth: int = 2,
    reply_limit: int = 10,
) -> dict[str, Any]:
    """Fetch a comment with its parent context and replies."""
    reddit = await self._get_reddit()
    async with translate_exceptions(
        CommentNotFoundError,
        f"Comment '{comment_id}'",
        forbidden_msg=f"Comment '{comment_id}' is not accessible",
    ):
        comment = await reddit.comment(id=comment_id)
        await comment.refresh()

        # Determine post_id from link_id
        post_id = comment.link_id
        if post_id.startswith("t3_"):
            post_id = post_id[3:]

        target = comment_to_dict(comment, post_id)

        # Walk up to collect ancestors
        ancestors = []
        current = comment
        for _ in range(min(context, 10)):
            parent_id = current.parent_id
            if parent_id.startswith("t3_"):
                break  # Reached the submission, no more parent comments
            parent = await reddit.comment(id=parent_id[3:])
            await parent.load()
            ancestors.insert(0, comment_to_dict(parent, post_id))
            current = parent

        # Collect replies
        replies: list[dict[str, Any]] = []
        await comment.replies.replace_more(limit=0)
        _collect_replies(comment.replies, post_id, replies, reply_depth, reply_limit)

        return {
            "ancestors": ancestors,
            "target": target,
            "replies": replies,
        }


def _collect_replies(
    reply_forest,
    post_id: str,
    results: list,
    depth: int,
    limit: int,
) -> None:
    """Recursively collect replies up to a given depth and limit."""
    if depth <= 0:
        return
    count = 0
    for reply in reply_forest:
        if count >= limit:
            break
        if not hasattr(reply, "body"):
            continue
        reply_dict = comment_to_dict(reply, post_id)
        child_replies: list[dict[str, Any]] = []
        if hasattr(reply, "replies") and reply.replies:
            _collect_replies(reply.replies, post_id, child_replies, depth - 1, limit)
        reply_dict["replies"] = child_replies
        results.append(reply_dict)
        count += 1


async def get_posts_batch(
    self: RedditClient,
    post_ids: list[str],
    include_comments: bool = False,
    comment_limit: int = 5,
) -> list[dict[str, Any]]:
    """Fetch multiple posts concurrently."""
    async def _fetch_one(pid: str) -> dict[str, Any]:
        async with self._batch_semaphore:
            try:
                post = await self.get_post(pid)
                result: dict[str, Any] = {"post": post}
                if include_comments:
                    result["comments"] = await self.get_comments(pid, limit=comment_limit)
                return result
            except RedditMCPError as e:
                return {"post_id": pid, "error": str(e), "error_type": type(e).__name__}

    return await asyncio.gather(*[_fetch_one(pid) for pid in post_ids])


@cached(ttl=600, maxsize=32)
async def get_wiki_page(
    self: RedditClient,
    subreddit_name: str,
    page_name: str = "index",
) -> WikiPageDict:
    """Fetch a wiki page from a subreddit."""
    reddit = await self._get_reddit()
    async with translate_exceptions(
        WikiPageNotFoundError,
        f"Wiki page '{page_name}' in r/{subreddit_name}",
        forbidden_msg=f"Wiki for r/{subreddit_name} is private or restricted",
    ):
        subreddit = await reddit.subreddit(subreddit_name)
        page = await subreddit.wiki.get_page(page_name)
        content = page.content_md or ""
        if len(content) > WIKI_TRUNCATE_LENGTH:
            content = content[:WIKI_TRUNCATE_LENGTH] + "\n\n[truncated]"
        revision_by = None
        if page.revision_by:
            revision_by = str(page.revision_by)
        return {
            "name": page_name,
            "content_md": content,
            "revision_date": datetime.fromtimestamp(
                page.revision_date, tz=timezone.utc
            ).isoformat() if page.revision_date else None,
            "revision_by": revision_by,
        }


@cached(ttl=600, maxsize=32)
async def list_wiki_pages(
    self: RedditClient,
    subreddit_name: str,
) -> list[str]:
    """List available wiki pages in a subreddit."""
    reddit = await self._get_reddit()
    async with translate_exceptions(
        WikiPageNotFoundError,
        f"Wiki for r/{subreddit_name}",
        forbidden_msg=f"Wiki for r/{subreddit_name} is private or restricted",
    ):
        subreddit = await reddit.subreddit(subreddit_name)
        pages = []
        async for page in subreddit.wiki:
            pages.append(str(page))
        return pages
