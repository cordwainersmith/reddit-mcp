"""Tests for write-action MCP tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from reddit_mcp.errors import (
    AuthenticationRequiredError,
    PostNotFoundError,
    RedditAPIError,
    SubmissionError,
)


def register_and_capture(register_fn, get_client=None):
    """Helper to register tools and capture the registered functions."""
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


class TestVoteTool:
    @pytest.fixture
    def action_funcs(self):
        from reddit_mcp.tools.actions import register_action_tools
        return register_and_capture(register_action_tools)

    @pytest.mark.asyncio
    async def test_vote_invalid_direction(self, action_funcs):
        result = await action_funcs["reddit_vote"](
            thing_id="test123", thing_type="post", direction="sideways"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_vote_invalid_thing_type(self, action_funcs):
        result = await action_funcs["reddit_vote"](
            thing_id="test123", thing_type="subreddit", direction="up"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_vote_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.vote = AsyncMock(return_value={
            "success": True, "id": "test123", "permalink": "", "message": "Voted"
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_vote"](
            thing_id="test123", thing_type="post", direction="up"
        )
        assert result["success"] is True
        mock_client.vote.assert_called_once()

    @pytest.mark.asyncio
    async def test_vote_auth_error(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.vote = AsyncMock(
            side_effect=AuthenticationRequiredError("no auth")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_vote"](
            thing_id="test123", thing_type="post", direction="up"
        )
        assert "error" in result
        assert result["error_type"] == "AuthenticationRequiredError"


class TestReplyToPostTool:
    @pytest.mark.asyncio
    async def test_reply_to_post_empty_body(self):
        from reddit_mcp.tools.actions import register_action_tools

        funcs = register_and_capture(register_action_tools)
        result = await funcs["reddit_reply_to_post"](post_id="test123", body="")
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_reply_to_post_body_too_long(self):
        from reddit_mcp.tools.actions import register_action_tools

        funcs = register_and_capture(register_action_tools)
        result = await funcs["reddit_reply_to_post"](
            post_id="test123", body="x" * 40_001
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_reply_to_post_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.reply_to_post = AsyncMock(return_value={
            "success": True, "id": "new_comment",
            "permalink": "https://reddit.com/r/test/c/new_comment",
            "message": "Replied",
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_reply_to_post"](
            post_id="test123", body="Great post!"
        )
        assert result["success"] is True
        assert result["id"] == "new_comment"

    @pytest.mark.asyncio
    async def test_reply_to_post_client_error(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.reply_to_post = AsyncMock(
            side_effect=PostNotFoundError("not found")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_reply_to_post"](
            post_id="bad", body="Hello"
        )
        assert result["error_type"] == "PostNotFoundError"


class TestReplyToCommentTool:
    @pytest.mark.asyncio
    async def test_reply_to_comment_empty_body(self):
        from reddit_mcp.tools.actions import register_action_tools

        funcs = register_and_capture(register_action_tools)
        result = await funcs["reddit_reply_to_comment"](
            comment_id="c123", body=""
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_reply_to_comment_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.reply_to_comment = AsyncMock(return_value={
            "success": True, "id": "new_reply",
            "permalink": "https://reddit.com/r/test/c/new_reply",
            "message": "Replied",
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_reply_to_comment"](
            comment_id="c123", body="Thanks!"
        )
        assert result["success"] is True
        assert result["id"] == "new_reply"


class TestCreatePostTool:
    @pytest.fixture
    def action_funcs(self):
        from reddit_mcp.tools.actions import register_action_tools
        return register_and_capture(register_action_tools)

    @pytest.mark.asyncio
    async def test_create_post_both_body_and_url(self, action_funcs):
        result = await action_funcs["reddit_create_post"](
            subreddit="test", title="Title",
            body="Body", url="https://example.com"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"
        assert "not both" in result["error"]

    @pytest.mark.asyncio
    async def test_create_post_neither_body_nor_url(self, action_funcs):
        result = await action_funcs["reddit_create_post"](
            subreddit="test", title="Title"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_post_invalid_subreddit(self, action_funcs):
        result = await action_funcs["reddit_create_post"](
            subreddit="invalid subreddit!", title="Title", body="Body"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_post_title_too_long(self, action_funcs):
        result = await action_funcs["reddit_create_post"](
            subreddit="test", title="A" * 301, body="Body"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_post_empty_title(self, action_funcs):
        result = await action_funcs["reddit_create_post"](
            subreddit="test", title="", body="Body"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_post_invalid_url(self, action_funcs):
        result = await action_funcs["reddit_create_post"](
            subreddit="test", title="Title", url="not-a-url"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_self_post_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.create_post = AsyncMock(return_value={
            "success": True, "id": "new_post",
            "permalink": "https://reddit.com/r/test/comments/new_post/title/",
            "message": "Created",
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_create_post"](
            subreddit="test", title="My Post", body="Content here"
        )
        assert result["success"] is True
        assert result["id"] == "new_post"

    @pytest.mark.asyncio
    async def test_create_link_post_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.create_post = AsyncMock(return_value={
            "success": True, "id": "new_link",
            "permalink": "https://reddit.com/r/test/comments/new_link/title/",
            "message": "Created",
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_create_post"](
            subreddit="test", title="Check this out",
            url="https://example.com/article"
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_post_submission_error(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.create_post = AsyncMock(
            side_effect=SubmissionError("post creation failed")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_create_post"](
            subreddit="test", title="Title", body="Body"
        )
        assert result["error_type"] == "SubmissionError"


class TestSaveTools:
    @pytest.mark.asyncio
    async def test_save_invalid_thing_type(self):
        from reddit_mcp.tools.actions import register_action_tools

        funcs = register_and_capture(register_action_tools)
        result = await funcs["reddit_save"](
            thing_id="test123", thing_type="subreddit"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_save_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.save_thing = AsyncMock(return_value={
            "success": True, "id": "test123", "permalink": "",
            "message": "Saved",
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_save"](
            thing_id="test123", thing_type="post"
        )
        assert result["success"] is True
        mock_client.save_thing.assert_called_once_with(
            thing_id="test123", thing_type="post", unsave=False
        )

    @pytest.mark.asyncio
    async def test_unsave_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.save_thing = AsyncMock(return_value={
            "success": True, "id": "test123", "permalink": "",
            "message": "Unsaved",
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_unsave"](
            thing_id="test123", thing_type="comment"
        )
        assert result["success"] is True
        mock_client.save_thing.assert_called_once_with(
            thing_id="test123", thing_type="comment", unsave=True
        )


class TestDeleteTool:
    @pytest.mark.asyncio
    async def test_delete_invalid_thing_type(self):
        from reddit_mcp.tools.actions import register_action_tools

        funcs = register_and_capture(register_action_tools)
        result = await funcs["reddit_delete"](
            thing_id="test123", thing_type="wiki"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_delete_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.delete_thing = AsyncMock(return_value={
            "success": True, "id": "test123", "permalink": "",
            "message": "Deleted",
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_delete"](
            thing_id="test123", thing_type="post"
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_auth_error(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.delete_thing = AsyncMock(
            side_effect=AuthenticationRequiredError("no auth")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_delete"](
            thing_id="test123", thing_type="comment"
        )
        assert result["error_type"] == "AuthenticationRequiredError"


class TestEditTool:
    @pytest.mark.asyncio
    async def test_edit_empty_body(self):
        from reddit_mcp.tools.actions import register_action_tools

        funcs = register_and_capture(register_action_tools)
        result = await funcs["reddit_edit"](
            thing_id="test123", thing_type="comment", body=""
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_edit_invalid_thing_type(self):
        from reddit_mcp.tools.actions import register_action_tools

        funcs = register_and_capture(register_action_tools)
        result = await funcs["reddit_edit"](
            thing_id="test123", thing_type="message", body="Updated"
        )
        assert "error" in result
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_edit_success(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.edit_thing = AsyncMock(return_value={
            "success": True, "id": "test123",
            "permalink": "https://reddit.com/r/test/c/test123/",
            "message": "Edited",
        })

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_edit"](
            thing_id="test123", thing_type="post", body="New content"
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_edit_api_error(self):
        from reddit_mcp.tools.actions import register_action_tools

        mock_client = AsyncMock()
        mock_client.edit_thing = AsyncMock(
            side_effect=RedditAPIError("server error")
        )

        async def async_get_client():
            return mock_client

        funcs = register_and_capture(register_action_tools, async_get_client)
        result = await funcs["reddit_edit"](
            thing_id="test123", thing_type="comment", body="Updated"
        )
        assert result["error_type"] == "RedditAPIError"


class TestToolRegistration:
    """Verify all action tools are registered."""

    def test_all_action_tools_registered(self):
        from reddit_mcp.tools.actions import register_action_tools

        funcs = register_and_capture(register_action_tools)
        expected_tools = {
            "reddit_vote",
            "reddit_reply_to_post",
            "reddit_reply_to_comment",
            "reddit_create_post",
            "reddit_save",
            "reddit_unsave",
            "reddit_delete",
            "reddit_edit",
        }
        assert set(funcs.keys()) == expected_tools
