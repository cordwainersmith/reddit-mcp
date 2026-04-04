"""Tests for MCP tool functions."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from reddit_mcp.errors import (
    CommentNotFoundError,
    PostNotFoundError,
    RedditAPIError,
    SubredditNotFoundError,
    UserNotFoundError,
    WikiPageNotFoundError,
)


def register_and_capture(register_fn, get_client=None):
    """Helper to register tools and capture the registered functions.

    Returns a dict mapping function names to their implementations.
    """
    mcp_mock = MagicMock()
    registered_funcs = {}

    def mock_tool():
        def decorator(func):
            registered_funcs[func.__name__] = func
            return func
        return decorator

    mcp_mock.tool = mock_tool
    if get_client is None:
        get_client = lambda: None  # noqa: E731
    register_fn(mcp_mock, get_client)
    return registered_funcs


class TestSearchTools:
    @pytest.fixture
    def search_funcs(self):
        from reddit_mcp.tools.search import register_search_tools
        return register_and_capture(register_search_tools)

    @pytest.mark.asyncio
    async def test_search_reddit_invalid_sort(self, search_funcs):
        result = await search_funcs["reddit_search_posts"](
            query="test", sort="invalid_sort"
        )
        assert "error" in result
        assert result["error_type"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_search_reddit_invalid_limit(self, search_funcs):
        result = await search_funcs["reddit_search_posts"](
            query="test", limit=200
        )
        assert "error" in result
        assert result["error_type"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_search_reddit_success(self):
        from reddit_mcp.tools.search import register_search_tools

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[{"id": "1", "title": "Test"}])

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_search_tools, async_get_client)
        result = await funcs["reddit_search_posts"](query="test")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    @pytest.mark.asyncio
    async def test_search_reddit_client_error(self):
        from reddit_mcp.tools.search import register_search_tools

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            side_effect=SubredditNotFoundError("not found")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_search_tools, async_get_client)
        result = await funcs["reddit_search_posts"](query="test")
        assert result["error_type"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_search_reddit_api_error(self):
        from reddit_mcp.tools.search import register_search_tools

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            side_effect=RedditAPIError("server error")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_search_tools, async_get_client)
        result = await funcs["reddit_search_posts"](query="test")
        assert result["error_type"] == "API_ERROR"

    @pytest.mark.asyncio
    async def test_search_subreddits_success(self):
        from reddit_mcp.tools.search import register_search_tools

        mock_client = AsyncMock()
        mock_client.search_subreddits = AsyncMock(
            return_value=[{"name": "python", "subscribers": 1000}]
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_search_tools, async_get_client)
        result = await funcs["reddit_search_subreddits"](query="python")
        assert isinstance(result, list)
        assert result[0]["name"] == "python"


class TestPostTools:
    @pytest.fixture
    def post_funcs(self):
        from reddit_mcp.tools.posts import register_post_tools
        return register_and_capture(register_post_tools)

    @pytest.mark.asyncio
    async def test_get_posts_batch_too_many_ids(self, post_funcs):
        ids = ",".join([f"id{i}" for i in range(15)])
        result = await post_funcs["reddit_get_posts_by_ids"](post_ids=ids)
        assert "error" in result
        assert "10" in result["error"]

    @pytest.mark.asyncio
    async def test_get_posts_batch_empty_ids(self, post_funcs):
        result = await post_funcs["reddit_get_posts_by_ids"](post_ids="")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_post_details_success(self):
        from reddit_mcp.tools.posts import register_post_tools

        mock_client = AsyncMock()
        mock_client.get_post = AsyncMock(return_value={"id": "abc", "title": "Test"})
        mock_client.get_comments = AsyncMock(return_value=[{"id": "c1", "body": "hi"}])

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_post_tools, async_get_client)
        result = await funcs["reddit_get_post_details"](post_id="abc")
        assert "post" in result
        assert "comments" in result
        assert result["post"]["title"] == "Test"

    @pytest.mark.asyncio
    async def test_get_post_details_no_comments(self):
        from reddit_mcp.tools.posts import register_post_tools

        mock_client = AsyncMock()
        mock_client.get_post = AsyncMock(return_value={"id": "abc", "title": "Test"})

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_post_tools, async_get_client)
        result = await funcs["reddit_get_post_details"](post_id="abc", include_comments=False)
        assert "post" in result
        assert "comments" not in result

    @pytest.mark.asyncio
    async def test_get_post_details_not_found(self):
        from reddit_mcp.tools.posts import register_post_tools

        mock_client = AsyncMock()
        mock_client.get_post = AsyncMock(
            side_effect=PostNotFoundError("not found")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_post_tools, async_get_client)
        result = await funcs["reddit_get_post_details"](post_id="nonexistent")
        assert result["error_type"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_subreddit_posts_invalid_sort(self, post_funcs):
        result = await post_funcs["reddit_get_subreddit_posts"](
            subreddits="python", sort="invalid"
        )
        assert result["error_type"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_subreddit_posts_success(self):
        from reddit_mcp.tools.posts import register_post_tools

        mock_client = AsyncMock()
        mock_client.get_posts = AsyncMock(
            return_value=[{"id": "1", "title": "Hello"}]
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_post_tools, async_get_client)
        result = await funcs["reddit_get_subreddit_posts"](subreddits="python")
        assert isinstance(result, list)
        assert result[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_get_posts_batch_success(self):
        from reddit_mcp.tools.posts import register_post_tools

        mock_client = AsyncMock()
        mock_client.get_posts_batch = AsyncMock(
            return_value=[{"post": {"id": "1"}}, {"post": {"id": "2"}}]
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_post_tools, async_get_client)
        result = await funcs["reddit_get_posts_by_ids"](post_ids="id1,id2")
        assert isinstance(result, list)
        assert len(result) == 2


class TestCommentTools:
    @pytest.mark.asyncio
    async def test_get_comment_thread_success(self):
        from reddit_mcp.tools.comments import register_comment_tools

        mock_client = AsyncMock()
        mock_client.get_comment_thread = AsyncMock(
            return_value={"ancestors": [], "target": {"id": "c1"}, "replies": []}
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_comment_tools, async_get_client)
        result = await funcs["reddit_get_comment_with_replies"](comment_id="c1")
        assert "target" in result
        assert "ancestors" in result
        assert "replies" in result

    @pytest.mark.asyncio
    async def test_get_comment_thread_not_found(self):
        from reddit_mcp.tools.comments import register_comment_tools

        mock_client = AsyncMock()
        mock_client.get_comment_thread = AsyncMock(
            side_effect=CommentNotFoundError("not found")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_comment_tools, async_get_client)
        result = await funcs["reddit_get_comment_with_replies"](comment_id="bad")
        assert result["error_type"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_comment_thread_invalid_context(self):
        from reddit_mcp.tools.comments import register_comment_tools

        funcs = register_and_capture(register_comment_tools)
        result = await funcs["reddit_get_comment_with_replies"](comment_id="c1", context=0)
        assert result["error_type"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_comment_thread_invalid_reply_depth(self):
        from reddit_mcp.tools.comments import register_comment_tools

        funcs = register_and_capture(register_comment_tools)
        result = await funcs["reddit_get_comment_with_replies"](comment_id="c1", reply_depth=0)
        assert result["error_type"] == "INVALID_INPUT"


class TestUserTools:
    @pytest.fixture
    def user_funcs(self):
        from reddit_mcp.tools.users import register_user_tools
        return register_and_capture(register_user_tools)

    @pytest.mark.asyncio
    async def test_get_user_info_invalid_username(self, user_funcs):
        result = await user_funcs["reddit_get_user_info"](username="user@invalid!")
        assert "error" in result
        assert result["error_type"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        from reddit_mcp.tools.users import register_user_tools

        mock_client = AsyncMock()
        mock_client.get_user_info = AsyncMock(
            return_value={"name": "testuser", "comment_karma": 100}
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_user_tools, async_get_client)
        result = await funcs["reddit_get_user_info"](username="testuser")
        assert result["name"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self):
        from reddit_mcp.tools.users import register_user_tools

        mock_client = AsyncMock()
        mock_client.get_user_info = AsyncMock(
            side_effect=UserNotFoundError("not found")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_user_tools, async_get_client)
        result = await funcs["reddit_get_user_info"](username="testuser")
        assert result["error_type"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_user_posts_success(self):
        from reddit_mcp.tools.users import register_user_tools

        mock_client = AsyncMock()
        mock_client.get_user_posts = AsyncMock(
            return_value=[{"id": "1", "title": "Post"}]
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_user_tools, async_get_client)
        result = await funcs["reddit_get_user_posts"](username="testuser")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_user_posts_invalid_sort(self, user_funcs):
        result = await user_funcs["reddit_get_user_posts"](
            username="testuser", sort="invalid"
        )
        assert result["error_type"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_user_comments_success(self):
        from reddit_mcp.tools.users import register_user_tools

        mock_client = AsyncMock()
        mock_client.get_user_comments = AsyncMock(
            return_value=[{"id": "c1", "body": "Comment"}]
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_user_tools, async_get_client)
        result = await funcs["reddit_get_user_comments"](username="testuser")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_user_comments_invalid_sort(self, user_funcs):
        result = await user_funcs["reddit_get_user_comments"](
            username="testuser", sort="invalid"
        )
        assert result["error_type"] == "INVALID_INPUT"


class TestSubredditTools:
    @pytest.fixture
    def sub_funcs(self):
        from reddit_mcp.tools.subreddits import register_subreddit_tools
        return register_and_capture(register_subreddit_tools)

    @pytest.mark.asyncio
    async def test_get_subreddit_info_invalid_name(self, sub_funcs):
        result = await sub_funcs["reddit_get_subreddit_info"](subreddit="invalid subreddit!")
        assert "error" in result
        assert result["error_type"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_subreddit_info_client_error(self):
        from reddit_mcp.tools.subreddits import register_subreddit_tools

        mock_client = AsyncMock()
        mock_client.get_subreddit_info = AsyncMock(
            side_effect=SubredditNotFoundError("not found")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_subreddit_tools, async_get_client)
        result = await funcs["reddit_get_subreddit_info"](subreddit="testsubreddit")
        assert "error" in result
        assert result["error_type"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_subreddit_info_success(self):
        from reddit_mcp.tools.subreddits import register_subreddit_tools

        mock_client = AsyncMock()
        mock_client.get_subreddit_info = AsyncMock(
            return_value={"name": "python", "subscribers": 1000000}
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_subreddit_tools, async_get_client)
        result = await funcs["reddit_get_subreddit_info"](subreddit="python")
        assert result["name"] == "python"

    @pytest.mark.asyncio
    async def test_get_subreddit_wiki_success(self):
        from reddit_mcp.tools.subreddits import register_subreddit_tools

        mock_client = AsyncMock()
        mock_client.get_wiki_page = AsyncMock(
            return_value={"name": "index", "content_md": "# Wiki"}
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_subreddit_tools, async_get_client)
        result = await funcs["reddit_get_subreddit_wiki"](subreddit="python")
        assert result["name"] == "index"

    @pytest.mark.asyncio
    async def test_get_subreddit_wiki_not_found(self):
        from reddit_mcp.tools.subreddits import register_subreddit_tools

        mock_client = AsyncMock()
        mock_client.get_wiki_page = AsyncMock(
            side_effect=WikiPageNotFoundError("not found")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_subreddit_tools, async_get_client)
        result = await funcs["reddit_get_subreddit_wiki"](subreddit="python")
        assert result["error_type"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_subreddit_wiki_invalid_page(self, sub_funcs):
        result = await sub_funcs["reddit_get_subreddit_wiki"](
            subreddit="python", page="page with spaces!"
        )
        assert result["error_type"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_list_wiki_pages_success(self):
        from reddit_mcp.tools.subreddits import register_subreddit_tools

        mock_client = AsyncMock()
        mock_client.list_wiki_pages = AsyncMock(
            return_value=["index", "faq", "rules"]
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_subreddit_tools, async_get_client)
        result = await funcs["reddit_list_subreddit_wiki_pages"](subreddit="python")
        assert isinstance(result, list)
        assert "index" in result

    @pytest.mark.asyncio
    async def test_list_wiki_pages_not_found(self):
        from reddit_mcp.tools.subreddits import register_subreddit_tools

        mock_client = AsyncMock()
        mock_client.list_wiki_pages = AsyncMock(
            side_effect=WikiPageNotFoundError("wiki not found")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_subreddit_tools, async_get_client)
        result = await funcs["reddit_list_subreddit_wiki_pages"](subreddit="python")
        assert result["error_type"] == "NOT_FOUND"
