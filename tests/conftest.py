"""Shared test fixtures for the Reddit MCP server tests."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest


class MockObj:
    """A simple mock object that doesn't auto-create attributes on access.

    Unlike MagicMock, hasattr() returns False for attributes not explicitly set.
    Supports custom __str__ via the _str_value attribute.
    """

    def __init__(self, _str_value=None, **kwargs):
        if _str_value is not None:
            self._str_value = _str_value
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return getattr(self, "_str_value", repr(self))


def make_submission(
    id="test123",
    title="Test Post",
    selftext="Test body content",
    subreddit_name="testsubreddit",
    author_name="testuser",
    score=42,
    num_comments=10,
    created_utc=1700000000.0,
    url="https://reddit.com/r/test/comments/test123/test_post/",
    permalink="/r/test/comments/test123/test_post/",
    upvote_ratio=0.95,
    link_flair_text=None,
    is_self=True,
    is_original_content=False,
    spoiler=False,
    over_18=False,
    locked=False,
    stickied=False,
    post_hint=None,
    domain="self.testsubreddit",
    num_crossposts=0,
    crosspost_parent=None,
    total_awards_received=0,
    gilded=0,
    poll_data=None,
    is_video=False,
    gallery_data=None,
):
    """Create a mock Submission object."""
    sub = MockObj(
        id=id,
        title=title,
        selftext=selftext,
        subreddit=MockObj(_str_value=subreddit_name),
        author=MockObj(_str_value=author_name) if author_name else None,
        score=score,
        num_comments=num_comments,
        created_utc=created_utc,
        url=url,
        permalink=permalink,
        upvote_ratio=upvote_ratio,
        link_flair_text=link_flair_text,
        is_self=is_self,
        is_original_content=is_original_content,
        spoiler=spoiler,
        over_18=over_18,
        locked=locked,
        stickied=stickied,
        is_video=is_video,
        domain=domain,
        num_crossposts=num_crossposts,
        crosspost_parent=crosspost_parent,
        total_awards_received=total_awards_received,
        gilded=gilded,
        poll_data=poll_data,
    )

    # Only set optional attributes when provided (MockObj won't auto-create)
    if post_hint is not None:
        sub.post_hint = post_hint
    if gallery_data is not None:
        sub.gallery_data = gallery_data

    return sub


def make_comment(
    id="comment1",
    post_id="test123",
    author_name="commenter",
    body="Test comment body",
    score=5,
    created_utc=1700001000.0,
    is_submitter=False,
    parent_id="t3_test123",
    permalink="/r/test/comments/test123/test_post/comment1/",
    edited=False,
    distinguished=None,
):
    """Create a mock Comment object."""
    return MockObj(
        id=id,
        author=MockObj(_str_value=author_name) if author_name else None,
        body=body,
        score=score,
        created_utc=created_utc,
        is_submitter=is_submitter,
        parent_id=parent_id,
        permalink=permalink,
        edited=edited,
        distinguished=distinguished,
        link_id=f"t3_{post_id}",
    )


@pytest.fixture
def mock_submission():
    """Provide a default mock submission."""
    return make_submission()


@pytest.fixture
def mock_comment():
    """Provide a default mock comment."""
    return make_comment()
