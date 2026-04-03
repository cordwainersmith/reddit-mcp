"""Tests for RedditClient methods with mocked PRAW."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reddit_mcp.client import RedditClient, RedditCredential
from reddit_mcp.errors import (
    AuthenticationRequiredError,
    CommentNotFoundError,
    CredentialError,
    PostNotFoundError,
    RedditAPIError,
    SubredditNotFoundError,
    SubmissionError,
    UserNotFoundError,
    WikiPageNotFoundError,
)
from tests.conftest import make_comment, make_submission


@pytest.fixture
def client():
    """Create a RedditClient with dummy credentials."""
    return RedditClient(
        credentials=[("id1", "secret1"), ("id2", "secret2")],
        user_agent="test/1.0",
    )


class TestCredentialRotation:
    def test_initial_credential_index(self, client):
        assert client._current_index == 0

    def test_multiple_credentials_created(self, client):
        assert len(client._credentials) == 2

    def test_empty_credentials_raises(self):
        with pytest.raises(CredentialError, match="At least one credential"):
            RedditClient(credentials=[], user_agent="test")

    def test_empty_client_id_raises(self):
        with pytest.raises(CredentialError, match="empty client_id"):
            RedditClient(credentials=[("", "secret")], user_agent="test")

    def test_empty_client_secret_raises(self):
        with pytest.raises(CredentialError, match="empty client_id"):
            RedditClient(credentials=[("id", "")], user_agent="test")

    def test_whitespace_only_credential_raises(self):
        with pytest.raises(CredentialError, match="empty client_id"):
            RedditClient(credentials=[("  ", "secret")], user_agent="test")

    @pytest.mark.asyncio
    async def test_credential_rotation(self, client):
        """Verify credentials rotate when first is exhausted."""
        # Exhaust first credential
        cred0 = client._credentials[0]
        cred0.request_count = 55  # At limit

        cred = await client._get_credential()
        assert cred is client._credentials[1]

    @pytest.mark.asyncio
    async def test_credential_reset(self, client):
        """Verify credential resets after 60s window."""
        from datetime import datetime, timedelta, timezone

        cred0 = client._credentials[0]
        cred0.request_count = 55
        # Set window start to 61 seconds ago
        cred0.window_start = datetime.now(timezone.utc) - timedelta(seconds=61)

        cred = await client._get_credential()
        assert cred is client._credentials[0]
        assert cred.request_count == 1  # Reset and recorded one new request


class TestClientMethods:
    @pytest.mark.asyncio
    async def test_get_post_not_found(self, client):
        """Test that NotFound exception is converted to PostNotFoundError."""
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=asyncprawcore.exceptions.NotFound(MagicMock())
        )

        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(PostNotFoundError, match="not found"):
                await client.get_post("nonexistent")

    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, client):
        """Test that NotFound for user is converted to UserNotFoundError."""
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.redditor = AsyncMock(
            side_effect=asyncprawcore.exceptions.NotFound(MagicMock())
        )

        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(UserNotFoundError, match="not found"):
                await client.get_user_info("nonexistent_user")

    @pytest.mark.asyncio
    async def test_get_subreddit_info_not_found(self, client):
        """Test that NotFound for subreddit is converted to SubredditNotFoundError."""
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_sub = AsyncMock()
        mock_sub.load = AsyncMock(
            side_effect=asyncprawcore.exceptions.NotFound(MagicMock())
        )
        mock_reddit.subreddit = AsyncMock(return_value=mock_sub)

        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(SubredditNotFoundError, match="not found"):
                await client.get_subreddit_info("nonexistent_sub")


class TestForbiddenAndRedirectErrors:
    """Test that Forbidden and Redirect are properly caught across all methods."""

    @pytest.mark.asyncio
    async def test_get_post_forbidden(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=asyncprawcore.exceptions.Forbidden(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(PostNotFoundError, match="private or quarantined"):
                await client.get_post("test")

    @pytest.mark.asyncio
    async def test_get_user_info_forbidden(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.redditor = AsyncMock(
            side_effect=asyncprawcore.exceptions.Forbidden(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(UserNotFoundError, match="suspended"):
                await client.get_user_info("testuser")

    @pytest.mark.asyncio
    async def test_get_user_info_redirect(self, client):
        import asyncprawcore.exceptions

        mock_response = MagicMock()
        mock_response.headers = {"location": "https://reddit.com/other"}
        mock_response.status_code = 302
        mock_reddit = AsyncMock()
        mock_reddit.redditor = AsyncMock(
            side_effect=asyncprawcore.exceptions.Redirect(mock_response)
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(UserNotFoundError, match="redirect"):
                await client.get_user_info("testuser")

    @pytest.mark.asyncio
    async def test_get_user_posts_forbidden(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.redditor = AsyncMock(
            side_effect=asyncprawcore.exceptions.Forbidden(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(UserNotFoundError, match="suspended"):
                await client.get_user_posts("testuser")

    @pytest.mark.asyncio
    async def test_get_user_comments_forbidden(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.redditor = AsyncMock(
            side_effect=asyncprawcore.exceptions.Forbidden(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(UserNotFoundError, match="suspended"):
                await client.get_user_comments("testuser")

    @pytest.mark.asyncio
    async def test_get_comment_thread_forbidden(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.comment = AsyncMock(
            side_effect=asyncprawcore.exceptions.Forbidden(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(CommentNotFoundError, match="not accessible"):
                await client.get_comment_thread("testcomment")

    @pytest.mark.asyncio
    async def test_get_comment_thread_not_found(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.comment = AsyncMock(
            side_effect=asyncprawcore.exceptions.NotFound(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(CommentNotFoundError, match="not found"):
                await client.get_comment_thread("testcomment")

    @pytest.mark.asyncio
    async def test_search_subreddits_forbidden(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.subreddits = MagicMock()
        mock_reddit.subreddits.search = MagicMock(
            side_effect=asyncprawcore.exceptions.Forbidden(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(SubredditNotFoundError, match="restricted"):
                await client.search_subreddits("test")


class TestNetworkErrors:
    """Test that ServerError and network errors are wrapped in RedditAPIError."""

    @pytest.mark.asyncio
    async def test_get_post_server_error(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=asyncprawcore.exceptions.ServerError(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(RedditAPIError, match="server error"):
                await client.get_post("test")

    @pytest.mark.asyncio
    async def test_get_post_timeout_error(self, client):
        import asyncio

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(RedditAPIError, match="Network error"):
                await client.get_post("test")

    @pytest.mark.asyncio
    async def test_get_user_info_server_error(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.redditor = AsyncMock(
            side_effect=asyncprawcore.exceptions.ServerError(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(RedditAPIError, match="server error"):
                await client.get_user_info("testuser")

    @pytest.mark.asyncio
    async def test_search_server_error(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.subreddit = AsyncMock(
            side_effect=asyncprawcore.exceptions.ServerError(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(RedditAPIError, match="server error"):
                await client.search(["python"], "test query")

    @pytest.mark.asyncio
    async def test_get_comments_server_error(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=asyncprawcore.exceptions.ServerError(MagicMock())
        )
        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(RedditAPIError, match="server error"):
                await client.get_comments("test")


class TestWikiErrors:
    """Test that wiki methods use WikiPageNotFoundError."""

    @pytest.mark.asyncio
    async def test_get_wiki_page_not_found(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_sub = AsyncMock()
        mock_sub.wiki = MagicMock()
        mock_sub.wiki.get_page = AsyncMock(
            side_effect=asyncprawcore.exceptions.NotFound(MagicMock())
        )
        mock_reddit.subreddit = AsyncMock(return_value=mock_sub)

        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(WikiPageNotFoundError, match="not found"):
                await client.get_wiki_page("test_sub", "nonexistent")

    @pytest.mark.asyncio
    async def test_get_wiki_page_forbidden(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_sub = AsyncMock()
        mock_sub.wiki = MagicMock()
        mock_sub.wiki.get_page = AsyncMock(
            side_effect=asyncprawcore.exceptions.Forbidden(MagicMock())
        )
        mock_reddit.subreddit = AsyncMock(return_value=mock_sub)

        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(WikiPageNotFoundError, match="private or restricted"):
                await client.get_wiki_page("test_sub", "restricted_page")

    @pytest.mark.asyncio
    async def test_list_wiki_pages_not_found(self, client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_sub = AsyncMock()

        # Mock the wiki as an async iterator that raises NotFound
        mock_wiki = MagicMock()

        async def mock_aiter(self_):
            raise asyncprawcore.exceptions.NotFound(MagicMock())
            yield  # noqa: unreachable - makes this an async generator

        mock_wiki.__aiter__ = mock_aiter
        mock_sub.wiki = mock_wiki
        mock_reddit.subreddit = AsyncMock(return_value=mock_sub)

        with patch.object(client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(WikiPageNotFoundError, match="not found"):
                await client.list_wiki_pages("test_sub")


class TestAsyncContextManager:
    """Test __aenter__ and __aexit__."""

    @pytest.mark.asyncio
    async def test_context_manager_returns_self(self):
        client = RedditClient(
            credentials=[("id1", "secret1")],
            user_agent="test/1.0",
        )
        async with client as ctx:
            assert ctx is client

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exit(self):
        client = RedditClient(
            credentials=[("id1", "secret1")],
            user_agent="test/1.0",
        )
        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            async with client:
                pass
            mock_close.assert_called_once()


class TestBatchConcurrency:
    """Test that get_posts_batch uses semaphore and narrows exceptions."""

    @pytest.mark.asyncio
    async def test_batch_has_semaphore(self, client):
        assert hasattr(client, "_batch_semaphore")

    @pytest.mark.asyncio
    async def test_batch_narrows_exceptions(self, client):
        """Non-RedditMCPError exceptions should propagate, not be swallowed."""
        async def mock_get_post(pid):
            raise RuntimeError("unexpected bug")

        with patch.object(client, "get_post", side_effect=RuntimeError("unexpected bug")):
            with pytest.raises(RuntimeError, match="unexpected bug"):
                await client.get_posts_batch(["id1"])

    @pytest.mark.asyncio
    async def test_batch_catches_mcp_errors(self, client):
        """RedditMCPError should be caught and returned as error dict."""
        with patch.object(client, "get_post", side_effect=PostNotFoundError("not found")):
            results = await client.get_posts_batch(["id1"])
            assert len(results) == 1
            assert results[0]["error_type"] == "PostNotFoundError"


class TestCacheKeyNormalization:
    """Test that subreddit order is normalized for cache keys."""

    @pytest.mark.asyncio
    async def test_subreddit_order_normalized(self, client):
        """Verify that different orderings produce the same cache key path."""
        # We verify that get_posts sorts subreddits before calling _get_hot_posts
        with patch.object(client, "_get_hot_posts", new_callable=AsyncMock, return_value=[]) as mock:
            await client.get_posts(subreddits=["java", "python"], sort="hot")
            mock.assert_called_once_with("java+python", 25)  # sorted: java before python

        with patch.object(client, "_get_hot_posts", new_callable=AsyncMock, return_value=[]) as mock:
            await client.get_posts(subreddits=["python", "java"], sort="hot")
            mock.assert_called_once_with("java+python", 25)  # same sorted order


class TestAuthGuard:
    """Test that _require_auth raises when credentials are not set."""

    def test_require_auth_no_credentials(self, client):
        """Client without username/password should raise AuthenticationRequiredError."""
        with pytest.raises(AuthenticationRequiredError, match="REDDIT_USERNAME"):
            client._require_auth()

    def test_require_auth_with_credentials(self):
        """Client with username/password should not raise."""
        authed_client = RedditClient(
            credentials=[("id1", "secret1")],
            user_agent="test/1.0",
            username="testuser",
            password="testpass",
        )
        # Should not raise
        authed_client._require_auth()

    def test_require_auth_partial_credentials_username_only(self):
        """Client with only username should raise."""
        partial_client = RedditClient(
            credentials=[("id1", "secret1")],
            user_agent="test/1.0",
            username="testuser",
        )
        with pytest.raises(AuthenticationRequiredError):
            partial_client._require_auth()

    def test_require_auth_partial_credentials_password_only(self):
        """Client with only password should raise."""
        partial_client = RedditClient(
            credentials=[("id1", "secret1")],
            user_agent="test/1.0",
            password="testpass",
        )
        with pytest.raises(AuthenticationRequiredError):
            partial_client._require_auth()


@pytest.fixture
def authed_client():
    """Create a RedditClient with auth credentials for write operation tests."""
    return RedditClient(
        credentials=[("id1", "secret1")],
        user_agent="test/1.0",
        username="testuser",
        password="testpass",
    )


class TestWriteMethods:
    """Test write methods (vote, reply, create_post, save, delete, edit)."""

    @pytest.mark.asyncio
    async def test_vote_no_auth(self, client):
        """Vote should raise AuthenticationRequiredError without credentials."""
        with pytest.raises(AuthenticationRequiredError):
            await client.vote("test123", "post", "up")

    @pytest.mark.asyncio
    async def test_vote_upvote_post(self, authed_client):
        mock_reddit = AsyncMock()
        mock_submission = AsyncMock()
        mock_reddit.submission = AsyncMock(return_value=mock_submission)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.vote("test123", "post", "up")
            assert result["success"] is True
            assert result["id"] == "test123"
            mock_submission.upvote.assert_called_once()

    @pytest.mark.asyncio
    async def test_vote_downvote_comment(self, authed_client):
        mock_reddit = AsyncMock()
        mock_comment = AsyncMock()
        mock_reddit.comment = AsyncMock(return_value=mock_comment)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.vote("c123", "comment", "down")
            assert result["success"] is True
            mock_comment.downvote.assert_called_once()

    @pytest.mark.asyncio
    async def test_vote_clear(self, authed_client):
        mock_reddit = AsyncMock()
        mock_submission = AsyncMock()
        mock_reddit.submission = AsyncMock(return_value=mock_submission)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.vote("test123", "post", "clear")
            assert result["success"] is True
            mock_submission.clear_vote.assert_called_once()

    @pytest.mark.asyncio
    async def test_vote_not_found(self, authed_client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=asyncprawcore.exceptions.NotFound(MagicMock())
        )
        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(PostNotFoundError, match="not found"):
                await authed_client.vote("bad", "post", "up")

    @pytest.mark.asyncio
    async def test_vote_forbidden(self, authed_client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=asyncprawcore.exceptions.Forbidden(MagicMock())
        )
        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(RedditAPIError, match="insufficient permissions"):
                await authed_client.vote("test", "post", "up")

    @pytest.mark.asyncio
    async def test_reply_to_post_no_auth(self, client):
        with pytest.raises(AuthenticationRequiredError):
            await client.reply_to_post("test123", "Hello!")

    @pytest.mark.asyncio
    async def test_reply_to_post_success(self, authed_client):
        mock_reddit = AsyncMock()
        mock_submission = AsyncMock()
        mock_comment = AsyncMock()
        mock_comment.id = "new_comment"
        mock_comment.permalink = "/r/test/comments/test123/test/new_comment/"
        mock_submission.reply = AsyncMock(return_value=mock_comment)
        mock_reddit.submission = AsyncMock(return_value=mock_submission)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.reply_to_post("test123", "Hello!")
            assert result["success"] is True
            assert result["id"] == "new_comment"
            assert "reddit.com" in result["permalink"]

    @pytest.mark.asyncio
    async def test_reply_to_comment_no_auth(self, client):
        with pytest.raises(AuthenticationRequiredError):
            await client.reply_to_comment("c123", "Reply!")

    @pytest.mark.asyncio
    async def test_reply_to_comment_success(self, authed_client):
        mock_reddit = AsyncMock()
        mock_parent = AsyncMock()
        mock_reply = AsyncMock()
        mock_reply.id = "new_reply"
        mock_reply.permalink = "/r/test/comments/test123/test/new_reply/"
        mock_parent.reply = AsyncMock(return_value=mock_reply)
        mock_reddit.comment = AsyncMock(return_value=mock_parent)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.reply_to_comment("c123", "Reply!")
            assert result["success"] is True
            assert result["id"] == "new_reply"

    @pytest.mark.asyncio
    async def test_create_post_no_auth(self, client):
        with pytest.raises(AuthenticationRequiredError):
            await client.create_post("test", "Title", body="Body")

    @pytest.mark.asyncio
    async def test_create_self_post_success(self, authed_client):
        mock_reddit = AsyncMock()
        mock_subreddit = AsyncMock()
        mock_submission = AsyncMock()
        mock_submission.id = "new_post"
        mock_submission.permalink = "/r/test/comments/new_post/title/"
        mock_subreddit.submit = AsyncMock(return_value=mock_submission)
        mock_reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.create_post("test", "Title", body="Body content")
            assert result["success"] is True
            assert result["id"] == "new_post"
            mock_subreddit.submit.assert_called_once_with(title="Title", selftext="Body content")

    @pytest.mark.asyncio
    async def test_create_link_post_success(self, authed_client):
        mock_reddit = AsyncMock()
        mock_subreddit = AsyncMock()
        mock_submission = AsyncMock()
        mock_submission.id = "new_link"
        mock_submission.permalink = "/r/test/comments/new_link/title/"
        mock_subreddit.submit = AsyncMock(return_value=mock_submission)
        mock_reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.create_post("test", "Title", url="https://example.com")
            assert result["success"] is True
            mock_subreddit.submit.assert_called_once_with(title="Title", url="https://example.com")

    @pytest.mark.asyncio
    async def test_create_post_with_flair(self, authed_client):
        mock_reddit = AsyncMock()
        mock_subreddit = AsyncMock()
        mock_submission = AsyncMock()
        mock_submission.id = "new_post"
        mock_submission.permalink = "/r/test/comments/new_post/title/"
        mock_subreddit.submit = AsyncMock(return_value=mock_submission)
        mock_reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.create_post(
                "test", "Title", body="Body",
                flair_id="flair123", flair_text="Discussion",
            )
            assert result["success"] is True
            mock_subreddit.submit.assert_called_once_with(
                title="Title", selftext="Body",
                flair_id="flair123", flair_text="Discussion",
            )

    @pytest.mark.asyncio
    async def test_create_post_reddit_api_exception(self, authed_client):
        import asyncpraw.exceptions

        mock_reddit = AsyncMock()
        mock_subreddit = AsyncMock()
        mock_subreddit.submit = AsyncMock(
            side_effect=asyncpraw.exceptions.RedditAPIException(
                [["SUBREDDIT_NOEXIST", "Subreddit does not exist", "subreddit"]]
            )
        )
        mock_reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(SubmissionError, match="failed"):
                await authed_client.create_post("nonexistent", "Title", body="Body")

    @pytest.mark.asyncio
    async def test_save_thing_no_auth(self, client):
        with pytest.raises(AuthenticationRequiredError):
            await client.save_thing("test123", "post")

    @pytest.mark.asyncio
    async def test_save_post_success(self, authed_client):
        mock_reddit = AsyncMock()
        mock_submission = AsyncMock()
        mock_reddit.submission = AsyncMock(return_value=mock_submission)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.save_thing("test123", "post")
            assert result["success"] is True
            mock_submission.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsave_comment_success(self, authed_client):
        mock_reddit = AsyncMock()
        mock_comment = AsyncMock()
        mock_reddit.comment = AsyncMock(return_value=mock_comment)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.save_thing("c123", "comment", unsave=True)
            assert result["success"] is True
            assert "unsaved" in result["message"]
            mock_comment.unsave.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_thing_no_auth(self, client):
        with pytest.raises(AuthenticationRequiredError):
            await client.delete_thing("test123", "post")

    @pytest.mark.asyncio
    async def test_delete_post_success(self, authed_client):
        mock_reddit = AsyncMock()
        mock_submission = AsyncMock()
        mock_reddit.submission = AsyncMock(return_value=mock_submission)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.delete_thing("test123", "post")
            assert result["success"] is True
            mock_submission.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_thing_no_auth(self, client):
        with pytest.raises(AuthenticationRequiredError):
            await client.edit_thing("test123", "post", "New body")

    @pytest.mark.asyncio
    async def test_edit_comment_success(self, authed_client):
        mock_reddit = AsyncMock()
        mock_comment = AsyncMock()
        mock_edited = AsyncMock()
        mock_edited.permalink = "/r/test/comments/test123/test/c123/"
        mock_comment.edit = AsyncMock(return_value=mock_edited)
        mock_reddit.comment = AsyncMock(return_value=mock_comment)

        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            result = await authed_client.edit_thing("c123", "comment", "Updated text")
            assert result["success"] is True
            mock_comment.edit.assert_called_once_with("Updated text")


class TestWriteExceptionTranslation:
    """Test that _translate_write_exceptions properly translates exceptions."""

    @pytest.mark.asyncio
    async def test_write_server_error(self, authed_client):
        import asyncprawcore.exceptions

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=asyncprawcore.exceptions.ServerError(MagicMock())
        )
        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(RedditAPIError, match="server error"):
                await authed_client.vote("test", "post", "up")

    @pytest.mark.asyncio
    async def test_write_timeout_error(self, authed_client):
        import asyncio as aio

        mock_reddit = AsyncMock()
        mock_reddit.submission = AsyncMock(
            side_effect=aio.TimeoutError()
        )
        with patch.object(authed_client, "_get_reddit", return_value=mock_reddit):
            with pytest.raises(RedditAPIError, match="Network error"):
                await authed_client.vote("test", "post", "up")
