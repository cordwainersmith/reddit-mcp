"""Tests for data model serialization (_submission_to_dict, _comment_to_dict)."""

from datetime import datetime, timezone

import pytest

from reddit_mcp.client import RedditClient
from tests.conftest import make_comment, make_submission


@pytest.fixture
def client():
    """Create a RedditClient with dummy credentials for testing dict methods."""
    return RedditClient(
        credentials=[("dummy_id", "dummy_secret")],
        user_agent="test/1.0",
    )


class TestSubmissionToDict:
    def test_basic_fields(self, client):
        sub = make_submission()
        result = client._submission_to_dict(sub)
        assert result["id"] == "test123"
        assert result["title"] == "Test Post"
        assert result["body"] == "Test body content"
        assert result["subreddit"] == "testsubreddit"
        assert result["author"] == "testuser"
        assert result["score"] == 42
        assert result["num_comments"] == 10
        assert result["url"] is not None
        assert result["permalink"].startswith("https://reddit.com")
        assert result["upvote_ratio"] == 0.95

    def test_content_type_fields(self, client):
        sub = make_submission(is_self=True)
        result = client._submission_to_dict(sub)
        assert result["is_self"] is True
        assert result["post_type"] == "self"
        assert result["domain"] == "self.testsubreddit"

    def test_post_type_link(self, client):
        sub = make_submission(is_self=False)
        result = client._submission_to_dict(sub)
        assert result["post_type"] == "link"

    def test_post_type_image(self, client):
        sub = make_submission(is_self=False, post_hint="image")
        result = client._submission_to_dict(sub)
        assert result["post_type"] == "image"

    def test_post_type_video(self, client):
        sub = make_submission(is_self=False, is_video=True)
        result = client._submission_to_dict(sub)
        assert result["post_type"] == "video"

    def test_crosspost_fields(self, client):
        sub = make_submission(num_crossposts=3, crosspost_parent="t3_abc123")
        result = client._submission_to_dict(sub)
        assert result["num_crossposts"] == 3
        assert result["crosspost_parent"] == "abc123"  # t3_ prefix stripped

    def test_crosspost_parent_none(self, client):
        sub = make_submission(crosspost_parent=None)
        result = client._submission_to_dict(sub)
        assert result["crosspost_parent"] is None

    def test_award_fields(self, client):
        sub = make_submission(total_awards_received=5, gilded=2)
        result = client._submission_to_dict(sub)
        assert result["total_awards"] == 5
        assert result["gilded"] == 2

    def test_quality_signal_fields(self, client):
        sub = make_submission(
            is_original_content=True,
            spoiler=True,
            over_18=True,
            locked=True,
            stickied=True,
        )
        result = client._submission_to_dict(sub)
        assert result["is_original_content"] is True
        assert result["spoiler"] is True
        assert result["over_18"] is True
        assert result["locked"] is True
        assert result["stickied"] is True

    def test_body_truncation(self, client):
        long_body = "x" * 3000
        sub = make_submission(selftext=long_body)
        result = client._submission_to_dict(sub, truncate_body=True)
        assert result["body"].endswith("[truncated]")
        assert len(result["body"]) < 3000

    def test_body_no_truncation(self, client):
        long_body = "x" * 3000
        sub = make_submission(selftext=long_body)
        result = client._submission_to_dict(sub, truncate_body=False)
        assert result["body"] == long_body

    def test_deleted_author(self, client):
        sub = make_submission()
        sub.author = None
        result = client._submission_to_dict(sub)
        assert result["author"] == "[deleted]"

    def test_created_utc_iso_format(self, client):
        sub = make_submission(created_utc=1700000000.0)
        result = client._submission_to_dict(sub)
        # Should be a valid ISO datetime string
        parsed = datetime.fromisoformat(result["created_utc"])
        assert parsed.tzinfo == timezone.utc


class TestCommentToDict:
    def test_basic_fields(self, client):
        comment = make_comment()
        result = client._comment_to_dict(comment, "test123")
        assert result["id"] == "comment1"
        assert result["post_id"] == "test123"
        assert result["author"] == "commenter"
        assert result["body"] == "Test comment body"
        assert result["score"] == 5
        assert result["is_op"] is False

    def test_threading_fields(self, client):
        comment = make_comment(parent_id="t3_test123")
        result = client._comment_to_dict(comment, "test123")
        assert result["parent_id"] == "t3_test123"
        assert result["is_root"] is True
        assert result["permalink"].startswith("https://reddit.com")

    def test_non_root_comment(self, client):
        comment = make_comment(parent_id="t1_parentcomment")
        result = client._comment_to_dict(comment, "test123")
        assert result["is_root"] is False

    def test_edited_field(self, client):
        comment = make_comment(edited=1700002000.0)
        result = client._comment_to_dict(comment, "test123")
        assert result["edited"] == 1700002000.0

    def test_not_edited(self, client):
        comment = make_comment(edited=False)
        result = client._comment_to_dict(comment, "test123")
        assert result["edited"] is False

    def test_distinguished_field(self, client):
        comment = make_comment(distinguished="moderator")
        result = client._comment_to_dict(comment, "test123")
        assert result["distinguished"] == "moderator"

    def test_deleted_author(self, client):
        comment = make_comment()
        comment.author = None
        result = client._comment_to_dict(comment, "test123")
        assert result["author"] == "[deleted]"

    def test_comment_body_truncation(self, client):
        long_body = "y" * 3000
        comment = make_comment(body=long_body)
        result = client._comment_to_dict(comment, "test123", truncate_body=True)
        assert result["body"].endswith("[truncated]")
        assert len(result["body"]) < 3000

    def test_comment_body_no_truncation(self, client):
        long_body = "y" * 3000
        comment = make_comment(body=long_body)
        result = client._comment_to_dict(comment, "test123", truncate_body=False)
        assert result["body"] == long_body

    def test_comment_getattr_safety(self, client):
        """Test that _comment_to_dict handles missing optional attributes gracefully."""
        from tests.conftest import MockObj

        # Create a minimal comment missing optional attributes
        minimal_comment = MockObj(
            id="c1",
            author=MockObj(_str_value="user1"),
            created_utc=1700000000.0,
        )
        result = client._comment_to_dict(minimal_comment, "post1")
        # Should use defaults instead of crashing
        assert result["body"] == ""
        assert result["score"] == 0
        assert result["is_op"] is False
        assert result["parent_id"] == ""
        assert result["edited"] is False
        assert result["distinguished"] is None


class TestPostTypeDerivation:
    def test_post_type_poll(self, client):
        sub = make_submission(is_self=False, poll_data={"options": []})
        result = client._submission_to_dict(sub)
        assert result["post_type"] == "poll"

    def test_post_type_gallery(self, client):
        sub = make_submission(is_self=False, gallery_data={"items": []})
        result = client._submission_to_dict(sub)
        assert result["post_type"] == "gallery"

    def test_post_type_hosted_video(self, client):
        sub = make_submission(is_self=False, post_hint="hosted:video")
        result = client._submission_to_dict(sub)
        assert result["post_type"] == "video"

    def test_empty_selftext_produces_empty_body(self, client):
        sub = make_submission(selftext="")
        result = client._submission_to_dict(sub)
        assert result["body"] == ""

    def test_none_selftext_produces_empty_body(self, client):
        sub = make_submission(selftext=None)
        # selftext=None should be treated as ""
        sub.selftext = None
        result = client._submission_to_dict(sub)
        assert result["body"] == ""

    def test_flair_field(self, client):
        sub = make_submission(link_flair_text="Discussion")
        result = client._submission_to_dict(sub)
        assert result["flair"] == "Discussion"

    def test_flair_none(self, client):
        sub = make_submission(link_flair_text=None)
        result = client._submission_to_dict(sub)
        assert result["flair"] is None
