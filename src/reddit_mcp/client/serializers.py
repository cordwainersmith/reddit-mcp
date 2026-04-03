"""Data serialization helpers for converting PRAW objects to typed dicts."""

import os
from datetime import datetime, timezone

from asyncpraw.models import Submission

from reddit_mcp.models import CommentDict, PostDict

BODY_TRUNCATE_LENGTH = int(os.environ.get("REDDIT_BODY_TRUNCATE_LENGTH", "2000"))
COMMENT_TRUNCATE_LENGTH = int(os.environ.get("REDDIT_COMMENT_TRUNCATE_LENGTH", "2000"))
WIKI_TRUNCATE_LENGTH = int(os.environ.get("REDDIT_WIKI_TRUNCATE_LENGTH", "5000"))


def derive_post_type(submission: Submission) -> str:
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


def submission_to_dict(submission: Submission, truncate_body: bool = True) -> PostDict:
    """Convert an asyncpraw Submission to a PostDict."""
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
        "post_type": derive_post_type(submission),
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


def comment_to_dict(comment, post_id: str, truncate_body: bool = True) -> CommentDict:
    """Convert an asyncpraw Comment to a CommentDict."""
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
