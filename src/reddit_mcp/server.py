"""Reddit MCP server for searching and browsing Reddit posts."""

import asyncio
import logging
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from reddit_mcp.cache import cache_stats
from reddit_mcp.client import RedditClient
from reddit_mcp.errors import CredentialError, handle_tool_errors
from reddit_mcp.tools import register_all_tools

load_dotenv()

logger = logging.getLogger(__name__)

mcp = FastMCP("Reddit Search")

_client: RedditClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> RedditClient:
    """Get or create RedditClient from environment credentials."""
    global _client
    if _client is not None:
        return _client

    async with _client_lock:
        # Double-check after acquiring lock
        if _client is not None:
            return _client

        creds_raw = os.environ.get("REDDIT_CREDENTIALS", "")
        if not creds_raw:
            raise CredentialError(
                "REDDIT_CREDENTIALS env var is required. "
                "Format: client_id1:secret1,client_id2:secret2"
            )

        credentials = []
        for i, entry in enumerate(creds_raw.split(",")):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(":")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                raise CredentialError(
                    f"Malformed credential at position {i + 1}. "
                    "Each entry must be exactly 'client_id:client_secret'."
                )
            credentials.append((parts[0].strip(), parts[1].strip()))

        if not credentials:
            raise CredentialError(
                "No valid credentials found in REDDIT_CREDENTIALS. "
                "Format: client_id1:secret1,client_id2:secret2"
            )

        # Parse REDDIT_USERS for multi-user write operations
        users: dict[str, str] = {}
        users_raw = os.environ.get("REDDIT_USERS", "")
        if users_raw:
            for i, entry in enumerate(users_raw.split(",")):
                entry = entry.strip()
                if not entry:
                    continue
                parts = entry.split(":", 1)
                if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                    raise CredentialError(
                        f"Malformed user entry at position {i + 1} in REDDIT_USERS. "
                        "Each entry must be exactly 'username:password'."
                    )
                users[parts[0].strip()] = parts[1].strip()

        # Backward compat: single-user fallback via REDDIT_USERNAME/REDDIT_PASSWORD
        legacy_username = os.environ.get("REDDIT_USERNAME") or None
        legacy_password = os.environ.get("REDDIT_PASSWORD") or None
        if legacy_username and legacy_password and legacy_username not in users:
            users[legacy_username] = legacy_password

        user_agent = os.environ.get("REDDIT_USER_AGENT", "reddit-mcp/1.0")
        _client = RedditClient(
            credentials=credentials,
            user_agent=user_agent,
            users=users if users else None,
        )
    return _client


async def shutdown_client() -> None:
    """Close the Reddit client and release resources."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("Reddit client closed")


# Register all tools
register_all_tools(mcp, get_client)


@mcp.tool()
@handle_tool_errors
async def reddit_get_server_status() -> dict:
    """
    Get Reddit MCP server health, diagnostics, and available usernames for write operations.

    Use this to check server health and discover which usernames can be passed to write tools
    (reddit_vote, reddit_reply, reddit_create_post, reddit_save, reddit_delete, reddit_edit).

    Returns: {
        "credentials": [{index, request_count, seconds_until_reset, is_available}],
        "users": {"configured_usernames": [...], "count": N},
        "cache_stats": {...}
    }.
    On error: {"error": "...", "error_type": "CREDENTIAL_ERROR|INTERNAL_ERROR"}
    """
    client = await get_client()
    status = client.credentials_status()
    return {
        **status,
        "cache_stats": cache_stats(),
    }


def main():
    try:
        mcp.run()
    finally:
        # Ensure client is closed on shutdown
        if _client is not None:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(shutdown_client())
            except RuntimeError:
                # No running loop -- run synchronously
                asyncio.run(shutdown_client())


if __name__ == "__main__":
    main()
