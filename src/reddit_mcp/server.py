"""Reddit MCP server for searching and browsing Reddit posts."""

import asyncio
import logging
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from reddit_mcp.cache import cache_stats
from reddit_mcp.client import RedditClient
from reddit_mcp.errors import CredentialError
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

        user_agent = os.environ.get("REDDIT_USER_AGENT", "reddit-mcp/1.0")
        _client = RedditClient(credentials=credentials, user_agent=user_agent)
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
async def get_server_status() -> dict:
    """
    Get server health and diagnostics.

    Returns credential count, cache hit/miss stats, and configuration info.
    """
    client = await get_client()
    return {
        "credentials": client.credentials_status(),
        "cache_stats": cache_stats(),
    }


def main():
    try:
        mcp.run()
    finally:
        # Ensure client is closed on shutdown
        if _client is not None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(shutdown_client())
                else:
                    loop.run_until_complete(shutdown_client())
            except RuntimeError:
                pass


if __name__ == "__main__":
    main()
