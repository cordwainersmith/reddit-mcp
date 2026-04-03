"""Reddit client subpackage.

Re-exports RedditClient with all read/write operations bound as methods,
maintaining backward compatibility with ``from reddit_mcp.client import RedditClient``.
"""

from reddit_mcp.client.base import RedditClient
from reddit_mcp.client.credentials import RedditCredential
from reddit_mcp.client import read_ops, write_ops

# ── Bind read operations as methods on RedditClient ──────────────
RedditClient.search = read_ops.search
RedditClient.get_posts = read_ops.get_posts
RedditClient._get_hot_posts = read_ops._get_hot_posts
RedditClient.get_post = read_ops.get_post
RedditClient.get_comments = read_ops.get_comments
RedditClient.get_subreddit_info = read_ops.get_subreddit_info
RedditClient.search_subreddits = read_ops.search_subreddits
RedditClient.get_user_info = read_ops.get_user_info
RedditClient.get_user_posts = read_ops.get_user_posts
RedditClient.get_user_comments = read_ops.get_user_comments
RedditClient.get_comment_thread = read_ops.get_comment_thread
RedditClient.get_posts_batch = read_ops.get_posts_batch
RedditClient.get_wiki_page = read_ops.get_wiki_page
RedditClient.list_wiki_pages = read_ops.list_wiki_pages

# ── Bind write operations as methods on RedditClient ─────────────
RedditClient.vote = write_ops.vote
RedditClient.reply_to_post = write_ops.reply_to_post
RedditClient.reply_to_comment = write_ops.reply_to_comment
RedditClient.create_post = write_ops.create_post
RedditClient.save_thing = write_ops.save_thing
RedditClient.delete_thing = write_ops.delete_thing
RedditClient.edit_thing = write_ops.edit_thing

# ── Expose serializers as private methods for test compatibility ──
from reddit_mcp.client.serializers import (
    submission_to_dict as _submission_to_dict_fn,
    comment_to_dict as _comment_to_dict_fn,
    derive_post_type as _derive_post_type_fn,
)

RedditClient._submission_to_dict = lambda self, submission, truncate_body=True: _submission_to_dict_fn(submission, truncate_body)
RedditClient._comment_to_dict = lambda self, comment, post_id, truncate_body=True: _comment_to_dict_fn(comment, post_id, truncate_body)
RedditClient._derive_post_type = lambda self, submission: _derive_post_type_fn(submission)

__all__ = ["RedditClient", "RedditCredential"]
