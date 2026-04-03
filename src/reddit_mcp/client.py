"""Async Reddit API client with multi-credential rotation and rate limiting."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import asyncpraw
import asyncprawcore.exceptions
from asyncpraw.models import Submission

from reddit_mcp.cache import cached
from reddit_mcp.errors import (
    CommentNotFoundError,
    CredentialError,
    PostNotFoundError,
    RateLimitExhaustedError,
    RedditAPIError,
    RedditMCPError,
    SubredditNotFoundError,
    UserNotFoundError,
    WikiPageNotFoundError,
)
from reddit_mcp.models import CommentDict, PostDict, SubredditInfoDict, UserInfoDict, WikiPageDict

logger = logging.getLogger(__name__)

MAX_REQUESTS_PER_MINUTE = 55
BODY_TRUNCATE_LENGTH = int(os.environ.get("REDDIT_BODY_TRUNCATE_LENGTH", "2000"))
COMMENT_TRUNCATE_LENGTH = int(os.environ.get("REDDIT_COMMENT_TRUNCATE_LENGTH", "2000"))
WIKI_TRUNCATE_LENGTH = int(os.environ.get("REDDIT_WIKI_TRUNCATE_LENGTH", "5000"))
BATCH_CONCURRENCY = 3


@asynccontextmanager
async def _translate_exceptions(
    not_found_cls: type[RedditMCPError],
    subject: str,
    forbidden_msg: str | None = None,
) -> AsyncIterator[None]:
    """Translate asyncpraw exceptions into RedditMCPError subclasses.

    Args:
        not_found_cls: The specific error class for NotFound/Forbidden/Redirect.
        subject: A human-readable subject string for error messages,
                 e.g. "Subreddit 'python'" or "Post 'abc123'".
        forbidden_msg: Optional custom message for Forbidden errors.
                       Defaults to "{subject} is private or quarantined".
    """
    try:
        yield
    except asyncprawcore.exceptions.NotFound:
        raise not_found_cls(f"{subject} not found")
    except asyncprawcore.exceptions.Redirect:
        raise not_found_cls(f"{subject} not found (redirect)")
    except asyncprawcore.exceptions.Forbidden:
        raise not_found_cls(forbidden_msg or f"{subject} is private or quarantined")
    except asyncprawcore.exceptions.ServerError as e:
        raise RedditAPIError(f"Reddit API server error: {e}")
    except (asyncio.TimeoutError, OSError) as e:
        raise RedditAPIError(f"Network error: {e}")


@dataclass
class RedditCredential:
    """A single Reddit API credential with its own rate limit tracking."""

    client_id: str
    client_secret: str
    reddit: asyncpraw.Reddit | None = None
    request_count: int = 0
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def seconds_until_reset(self) -> float:
        elapsed = (datetime.now(timezone.utc) - self.window_start).total_seconds()
        return max(0, 60 - elapsed)

    def is_available(self) -> bool:
        now = datetime.now(timezone.utc)
        elapsed = (now - self.window_start).total_seconds()
        if elapsed >= 60:
            return True
        return self.request_count < MAX_REQUESTS_PER_MINUTE

    def reset_if_needed(self) -> None:
        now = datetime.now(timezone.utc)
        elapsed = (now - self.window_start).total_seconds()
        if elapsed >= 60:
            self.request_count = 0
            self.window_start = now

    def record_request(self) -> None:
        self.reset_if_needed()
        self.request_count += 1


class RedditClient:
    """Async Reddit API client wrapping AsyncPRAW with credential rotation."""

    def __init__(self, credentials: list[tuple[str, str]], user_agent: str):
        if not credentials:
            raise CredentialError("At least one credential pair (client_id, client_secret) is required")
        for i, (cid, cs) in enumerate(credentials):
            if not cid or not cid.strip() or not cs or not cs.strip():
                raise CredentialError(
                    f"Credential at position {i + 1} has empty client_id or client_secret"
                )
        self._user_agent = user_agent
        self._credentials = [
            RedditCredential(client_id=cid, client_secret=cs)
            for cid, cs in credentials
        ]
        self._current_index = 0
        self._rotation_lock = asyncio.Lock()
        self._batch_semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def _get_credential(self) -> RedditCredential:
        """Get the next available credential, waiting if all are exhausted."""
        async with self._rotation_lock:
            for i in range(len(self._credentials)):
                idx = (self._current_index + i) % len(self._credentials)
                cred = self._credentials[idx]
                cred.reset_if_needed()
                if cred.is_available():
                    self._current_index = idx
                    cred.record_request()
                    return cred

            # All exhausted, wait for the one that resets soonest
            min_wait = min(c.seconds_until_reset() for c in self._credentials)
            logger.debug("All credentials exhausted, waiting %.1fs", min_wait)
            await asyncio.sleep(min_wait + 0.1)

            # Reset and pick the first available
            for cred in self._credentials:
                cred.reset_if_needed()
                if cred.is_available():
                    cred.record_request()
                    return cred

            raise RateLimitExhaustedError(
                "All credentials have exhausted their rate limits. Try again later."
            )

    async def _get_reddit(self) -> asyncpraw.Reddit:
        """Get an AsyncPRAW client from the next available credential."""
        cred = await self._get_credential()
        if cred.reddit is None:
            kwargs: dict[str, Any] = {
                "client_id": cred.client_id,
                "client_secret": cred.client_secret,
                "user_agent": self._user_agent,
            }
            if os.environ.get("REDDIT_MCP_IGNORE_SSL", "").lower() in ("1", "true", "yes"):
                import aiohttp
                connector = aiohttp.TCPConnector(ssl=False)
                kwargs["requestor_kwargs"] = {"session": aiohttp.ClientSession(connector=connector)}
            cred.reddit = asyncpraw.Reddit(**kwargs)
        return cred.reddit

    async def close(self) -> None:
        for cred in self._credentials:
            if cred.reddit:
                await cred.reddit.close()
                cred.reddit = None

    def credentials_status(self) -> list[dict[str, Any]]:
        """Return diagnostic info about all credentials for server status."""
        return [
            {
                "index": i,
                "request_count": cred.request_count,
                "seconds_until_reset": round(cred.seconds_until_reset(), 1),
                "is_available": cred.is_available(),
            }
            for i, cred in enumerate(self._credentials)
        ]

    async def __aenter__(self) -> "RedditClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _derive_post_type(self, submission: Submission) -> str:
        """Derive the post type string from a submission."""
        if submission.is_self:
            return "self"
        post_hint = getattr(submission, "post_hint", None)
        if getattr(submission, "poll_data", None):
            return "poll"
        if hasattr(submission, "gallery_data"):
            return "gallery"
        if post_hint == "hosted:video" or getattr(submission, "is_video", False):
            return "video"
        if post_hint == "image":
            return "image"
        return "link"

    def _submission_to_dict(self, submission: Submission, truncate_body: bool = True) -> PostDict:
        body = submission.selftext or ""
        if truncate_body and len(body) > BODY_TRUNCATE_LENGTH:
            body = body[:BODY_TRUNCATE_LENGTH] + " [truncated]"

        crosspost_parent = getattr(submission, "crosspost_parent", None)
        if crosspost_parent and crosspost_parent.startswith("t3_"):
            crosspost_parent = crosspost_parent[3:]

        return {
            "id": submission.id,
            "title": submission.title,
            "body": body,
            "subreddit": str(submission.subreddit),
            "author": str(submission.author) if submission.author else "[deleted]",
            "score": submission.score,
            "num_comments": submission.num_comments,
            "created_utc": datetime.fromtimestamp(
                submission.created_utc, tz=timezone.utc
            ).isoformat(),
            "url": submission.url,
            "permalink": f"https://reddit.com{submission.permalink}",
            "upvote_ratio": submission.upvote_ratio,
            "flair": submission.link_flair_text,
            # Content type fields
            "is_self": submission.is_self,
            "post_type": self._derive_post_type(submission),
            "domain": getattr(submission, "domain", None),
            # Cross-post fields
            "num_crossposts": getattr(submission, "num_crossposts", 0),
            "crosspost_parent": crosspost_parent,
            # Award/quality signal fields
            "total_awards": getattr(submission, "total_awards_received", 0),
            "gilded": getattr(submission, "gilded", 0),
            "is_original_content": submission.is_original_content,
            "spoiler": submission.spoiler,
            "over_18": submission.over_18,
            "locked": submission.locked,
            "stickied": submission.stickied,
        }

    def _comment_to_dict(self, comment, post_id: str, truncate_body: bool = True) -> CommentDict:
        body = getattr(comment, "body", "")
        if truncate_body and len(body) > COMMENT_TRUNCATE_LENGTH:
            body = body[:COMMENT_TRUNCATE_LENGTH] + " [truncated]"

        parent_id = getattr(comment, "parent_id", "")
        return {
            "id": comment.id,
            "post_id": post_id,
            "author": str(comment.author) if comment.author else "[deleted]",
            "body": body,
            "score": getattr(comment, "score", 0),
            "created_utc": datetime.fromtimestamp(
                comment.created_utc, tz=timezone.utc
            ).isoformat(),
            "is_op": getattr(comment, "is_submitter", False),
            # Threading fields
            "parent_id": parent_id,
            "is_root": parent_id.startswith("t3_"),
            "permalink": f"https://reddit.com{getattr(comment, 'permalink', '')}",
            "edited": getattr(comment, "edited", False),
            "distinguished": getattr(comment, "distinguished", None),
        }

    async def search(
        self,
        subreddits: list[str],
        query: str,
        sort: str = "relevance",
        time_filter: str = "week",
        limit: int = 25,
    ) -> list[PostDict]:
        """Search for posts across one or more subreddits."""
        reddit = await self._get_reddit()
        sub_str = "+".join(subreddits) if subreddits else "all"
        async with _translate_exceptions(SubredditNotFoundError, f"Subreddit '{sub_str}'"):
            subreddit = await reddit.subreddit(sub_str)
            posts = []
            async for submission in subreddit.search(
                query, sort=sort, time_filter=time_filter, limit=limit
            ):
                posts.append(self._submission_to_dict(submission))
            return posts

    async def get_posts(
        self,
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
        return await self._get_posts_uncached(subreddits, sort, time_filter, limit)

    @cached(ttl=120, maxsize=32)
    async def _get_hot_posts(
        self, sub_str: str, limit: int
    ) -> list[PostDict]:
        """Cached fetch of hot posts."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(SubredditNotFoundError, f"Subreddit '{sub_str}'"):
            subreddit = await reddit.subreddit(sub_str)
            posts = []
            async for submission in subreddit.hot(limit=limit):
                posts.append(self._submission_to_dict(submission))
            return posts

    async def _get_posts_uncached(
        self,
        subreddits: list[str],
        sort: str = "hot",
        time_filter: str = "week",
        limit: int = 25,
    ) -> list[PostDict]:
        """Fetch posts without caching."""
        reddit = await self._get_reddit()
        sub_str = "+".join(subreddits) if subreddits else "all"
        async with _translate_exceptions(SubredditNotFoundError, f"Subreddit '{sub_str}'"):
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
                posts.append(self._submission_to_dict(submission))
            return posts

    async def get_post(self, post_id: str) -> PostDict:
        """Fetch a single post by ID with full body (no truncation)."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(PostNotFoundError, f"Post '{post_id}'"):
            submission = await reddit.submission(id=post_id)
            await submission.load()
            return self._submission_to_dict(submission, truncate_body=False)

    async def get_comments(
        self,
        post_id: str,
        sort: str = "best",
        limit: int = 20,
    ) -> list[CommentDict]:
        """Fetch comments for a post."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(PostNotFoundError, f"Post '{post_id}'"):
            submission = await reddit.submission(id=post_id)
            submission.comment_sort = sort
            await submission.comments.replace_more(limit=0)

            comments = []
            for comment in submission.comments[:limit]:
                if hasattr(comment, "body"):
                    comments.append(self._comment_to_dict(comment, post_id))
            return comments

    @cached(ttl=300, maxsize=64)
    async def get_subreddit_info(self, subreddit_name: str) -> SubredditInfoDict:
        """Get metadata about a subreddit."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(SubredditNotFoundError, f"Subreddit '{subreddit_name}'"):
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
        self,
        query: str,
        limit: int = 10,
    ) -> list[SubredditInfoDict]:
        """Search for subreddits by topic."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(
            SubredditNotFoundError,
            f"Subreddit search for '{query}'",
            forbidden_msg=f"Subreddit search for '{query}' is restricted",
        ):
            results = []
            async for subreddit in reddit.subreddits.search(query, limit=limit):
                results.append({
                    "name": subreddit.display_name,
                    "title": subreddit.title,
                    "description": getattr(subreddit, "public_description", ""),
                    "subscribers": getattr(subreddit, "subscribers", 0),
                    "active_users": getattr(subreddit, "accounts_active", None),
                    "over_18": getattr(subreddit, "over18", False),
                    "url": f"https://reddit.com{subreddit.url}",
                })
            return results

    async def get_user_info(self, username: str) -> UserInfoDict:
        """Get user profile metadata."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(
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
                except Exception:
                    pass
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
        self,
        username: str,
        sort: str = "new",
        time_filter: str = "all",
        limit: int = 25,
    ) -> list[PostDict]:
        """Get a user's submitted posts."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(
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
                posts.append(self._submission_to_dict(submission))
            return posts

    async def get_user_comments(
        self,
        username: str,
        sort: str = "new",
        time_filter: str = "all",
        limit: int = 25,
    ) -> list[CommentDict]:
        """Get a user's comments."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(
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
                    comments.append(self._comment_to_dict(comment, post_id))
            return comments

    async def get_comment_thread(
        self,
        comment_id: str,
        context: int = 5,
        reply_depth: int = 2,
        reply_limit: int = 10,
    ) -> dict[str, Any]:
        """Fetch a comment with its parent context and replies."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(
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

            target = self._comment_to_dict(comment, post_id)

            # Walk up to collect ancestors
            ancestors = []
            current = comment
            for _ in range(min(context, 10)):
                parent_id = current.parent_id
                if parent_id.startswith("t3_"):
                    break  # Reached the submission, no more parent comments
                parent = await reddit.comment(id=parent_id[3:])
                await parent.load()
                ancestors.insert(0, self._comment_to_dict(parent, post_id))
                current = parent

            # Collect replies
            replies = []
            await comment.replies.replace_more(limit=0)
            self._collect_replies(comment.replies, post_id, replies, reply_depth, reply_limit)

            return {
                "ancestors": ancestors,
                "target": target,
                "replies": replies,
            }

    def _collect_replies(
        self,
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
            reply_dict = self._comment_to_dict(reply, post_id)
            child_replies: list[dict[str, Any]] = []
            if hasattr(reply, "replies") and reply.replies:
                self._collect_replies(reply.replies, post_id, child_replies, depth - 1, limit)
            reply_dict["replies"] = child_replies
            results.append(reply_dict)
            count += 1

    async def get_posts_batch(
        self,
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
        self,
        subreddit_name: str,
        page_name: str = "index",
    ) -> WikiPageDict:
        """Fetch a wiki page from a subreddit."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(
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
        self,
        subreddit_name: str,
    ) -> list[str]:
        """List available wiki pages in a subreddit."""
        reddit = await self._get_reddit()
        async with _translate_exceptions(
            WikiPageNotFoundError,
            f"Wiki for r/{subreddit_name}",
            forbidden_msg=f"Wiki for r/{subreddit_name} is private or restricted",
        ):
            subreddit = await reddit.subreddit(subreddit_name)
            pages = []
            async for page in subreddit.wiki:
                pages.append(str(page))
            return pages
