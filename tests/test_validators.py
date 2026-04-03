"""Tests for input validators."""

import pytest

from reddit_mcp.errors import ValidationError
from reddit_mcp.validators import (
    COMMENT_SORT_OPTIONS,
    POST_SORT_OPTIONS,
    SEARCH_SORT_OPTIONS,
    USER_SORT_OPTIONS,
    validate_body_text,
    validate_limit,
    validate_post_title,
    validate_sort,
    validate_subreddit_name,
    validate_thing_type,
    validate_time_filter,
    validate_url,
    validate_username,
    validate_vote_direction,
)


class TestValidateSort:
    def test_valid_search_sorts(self):
        for s in SEARCH_SORT_OPTIONS:
            assert validate_sort(s, SEARCH_SORT_OPTIONS) == s

    def test_valid_post_sorts(self):
        for s in POST_SORT_OPTIONS:
            assert validate_sort(s, POST_SORT_OPTIONS) == s

    def test_valid_comment_sorts(self):
        for s in COMMENT_SORT_OPTIONS:
            assert validate_sort(s, COMMENT_SORT_OPTIONS) == s

    def test_valid_user_sorts(self):
        for s in USER_SORT_OPTIONS:
            assert validate_sort(s, USER_SORT_OPTIONS) == s

    def test_case_insensitive(self):
        assert validate_sort("HOT", POST_SORT_OPTIONS) == "hot"
        assert validate_sort("New", POST_SORT_OPTIONS) == "new"

    def test_strips_whitespace(self):
        assert validate_sort("  hot  ", POST_SORT_OPTIONS) == "hot"

    def test_invalid_sort_raises(self):
        with pytest.raises(ValidationError, match="Invalid sort"):
            validate_sort("invalid", POST_SORT_OPTIONS)

    def test_invalid_sort_message_lists_options(self):
        with pytest.raises(ValidationError, match="hot"):
            validate_sort("nope", POST_SORT_OPTIONS)

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_sort("", POST_SORT_OPTIONS)


class TestValidateTimeFilter:
    def test_valid_time_filters(self):
        for tf in ("hour", "day", "week", "month", "year", "all"):
            assert validate_time_filter(tf) == tf

    def test_case_insensitive(self):
        assert validate_time_filter("WEEK") == "week"

    def test_strips_whitespace(self):
        assert validate_time_filter("  day  ") == "day"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError, match="Invalid time_filter"):
            validate_time_filter("yesterday")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_time_filter("")


class TestValidateLimit:
    def test_valid_limits(self):
        assert validate_limit(1) == 1
        assert validate_limit(50) == 50
        assert validate_limit(100) == 100

    def test_min_boundary(self):
        with pytest.raises(ValidationError, match="at least 1"):
            validate_limit(0)

    def test_max_boundary(self):
        with pytest.raises(ValidationError, match="at most 100"):
            validate_limit(101)

    def test_negative(self):
        with pytest.raises(ValidationError, match="at least 1"):
            validate_limit(-1)

    def test_custom_range(self):
        assert validate_limit(5, min_val=5, max_val=10) == 5
        assert validate_limit(10, min_val=5, max_val=10) == 10
        with pytest.raises(ValidationError):
            validate_limit(4, min_val=5, max_val=10)
        with pytest.raises(ValidationError):
            validate_limit(11, min_val=5, max_val=10)


class TestValidateSubredditName:
    def test_valid_names(self):
        assert validate_subreddit_name("python") == "python"
        assert validate_subreddit_name("Ask_Reddit") == "Ask_Reddit"
        assert validate_subreddit_name("a") == "a"
        assert validate_subreddit_name("A" * 21) == "A" * 21

    def test_strips_whitespace(self):
        assert validate_subreddit_name("  python  ") == "python"

    def test_too_long(self):
        with pytest.raises(ValidationError, match="1-21 characters"):
            validate_subreddit_name("A" * 22)

    def test_empty(self):
        with pytest.raises(ValidationError):
            validate_subreddit_name("")

    def test_special_chars(self):
        with pytest.raises(ValidationError):
            validate_subreddit_name("sub-reddit")
        with pytest.raises(ValidationError):
            validate_subreddit_name("sub reddit")
        with pytest.raises(ValidationError):
            validate_subreddit_name("sub.reddit")


class TestValidateUsername:
    def test_valid_usernames(self):
        assert validate_username("testuser") == "testuser"
        assert validate_username("test_user") == "test_user"
        assert validate_username("test-user") == "test-user"
        assert validate_username("a") == "a"

    def test_strips_whitespace(self):
        assert validate_username("  testuser  ") == "testuser"

    def test_too_long(self):
        with pytest.raises(ValidationError, match="1-20 characters"):
            validate_username("A" * 21)

    def test_empty(self):
        with pytest.raises(ValidationError):
            validate_username("")

    def test_special_chars(self):
        with pytest.raises(ValidationError):
            validate_username("user@name")
        with pytest.raises(ValidationError):
            validate_username("user name")


class TestValidateVoteDirection:
    def test_valid_directions(self):
        assert validate_vote_direction("up") == "up"
        assert validate_vote_direction("down") == "down"
        assert validate_vote_direction("clear") == "clear"

    def test_case_insensitive(self):
        assert validate_vote_direction("UP") == "up"
        assert validate_vote_direction("Down") == "down"

    def test_strips_whitespace(self):
        assert validate_vote_direction("  up  ") == "up"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError, match="Invalid vote direction"):
            validate_vote_direction("sideways")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_vote_direction("")


class TestValidateThingType:
    def test_valid_types(self):
        assert validate_thing_type("post") == "post"
        assert validate_thing_type("comment") == "comment"

    def test_case_insensitive(self):
        assert validate_thing_type("POST") == "post"
        assert validate_thing_type("Comment") == "comment"

    def test_strips_whitespace(self):
        assert validate_thing_type("  post  ") == "post"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError, match="Invalid thing type"):
            validate_thing_type("subreddit")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_thing_type("")


class TestValidatePostTitle:
    def test_valid_title(self):
        assert validate_post_title("Hello World") == "Hello World"

    def test_strips_whitespace(self):
        assert validate_post_title("  Hello  ") == "Hello"

    def test_max_length(self):
        title = "A" * 300
        assert validate_post_title(title) == title

    def test_too_long(self):
        with pytest.raises(ValidationError, match="300"):
            validate_post_title("A" * 301)

    def test_empty_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_post_title("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_post_title("   ")


class TestValidateBodyText:
    def test_valid_body(self):
        assert validate_body_text("Hello World") == "Hello World"

    def test_strips_whitespace(self):
        assert validate_body_text("  Hello  ") == "Hello"

    def test_max_length(self):
        body = "A" * 40_000
        assert validate_body_text(body) == body

    def test_too_long(self):
        with pytest.raises(ValidationError, match="40,000"):
            validate_body_text("A" * 40_001)

    def test_empty_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_body_text("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_body_text("   ")


class TestValidateUrl:
    def test_valid_http(self):
        assert validate_url("http://example.com") == "http://example.com"

    def test_valid_https(self):
        assert validate_url("https://example.com/path?q=1") == "https://example.com/path?q=1"

    def test_strips_whitespace(self):
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_invalid_no_scheme(self):
        with pytest.raises(ValidationError, match="Must start with"):
            validate_url("example.com")

    def test_invalid_ftp(self):
        with pytest.raises(ValidationError, match="Must start with"):
            validate_url("ftp://example.com")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_url("")
