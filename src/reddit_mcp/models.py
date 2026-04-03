"""TypedDict definitions for data shapes returned by the client."""

from typing import TypedDict


class ErrorDict(TypedDict):
    """Shape of an error response returned by tools."""

    error: str
    error_type: str


class PostDict(TypedDict, total=False):
    """Shape of a Reddit post as returned by the client."""

    id: str
    title: str
    body: str
    subreddit: str
    author: str
    score: int
    num_comments: int
    created_utc: str
    url: str
    permalink: str
    upvote_ratio: float
    flair: str | None
    # Content type fields
    is_self: bool
    post_type: str
    domain: str | None
    # Cross-post fields
    num_crossposts: int
    crosspost_parent: str | None
    # Award/quality signal fields
    total_awards: int
    gilded: int
    is_original_content: bool
    spoiler: bool
    over_18: bool
    locked: bool
    stickied: bool


class CommentDict(TypedDict, total=False):
    """Shape of a Reddit comment as returned by the client."""

    id: str
    post_id: str
    author: str
    body: str
    score: int
    created_utc: str
    is_op: bool
    # Threading fields
    parent_id: str
    is_root: bool
    permalink: str
    edited: bool | float
    distinguished: str | None


class SubredditInfoDict(TypedDict, total=False):
    """Shape of subreddit metadata as returned by the client."""

    name: str
    title: str
    description: str
    subscribers: int
    active_users: int
    created_utc: str
    over_18: bool
    url: str


class UserInfoDict(TypedDict, total=False):
    """Shape of user profile metadata as returned by the client."""

    name: str
    id: str
    comment_karma: int
    link_karma: int
    created_utc: str
    has_verified_email: bool
    is_mod: bool
    is_gold: bool
    icon_img: str | None
    subreddit: str | None


class WikiPageDict(TypedDict, total=False):
    """Shape of a wiki page as returned by the client."""

    name: str
    content_md: str
    revision_date: str | None
    revision_by: str | None
