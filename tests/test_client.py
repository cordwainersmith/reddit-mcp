"""Tests for RedditClient methods with mocked PRAW."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reddit_mcp.client import RedditClient, RedditCredential
from reddit_mcp.errors import (
    CommentNotFoundError,
    CredentialError,
    PostNotFoundError,
    RedditAPIError,
    SubredditNotFoundError,
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
