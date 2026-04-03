"""Base RedditClient class with credential rotation and connection management."""

import asyncio
import logging
import os
from typing import Any

import asyncpraw

from reddit_mcp.client.credentials import RedditCredential
from reddit_mcp.errors import (
    AuthenticationRequiredError,
    CredentialError,
    RateLimitExhaustedError,
)

logger = logging.getLogger(__name__)

BATCH_CONCURRENCY = 3


class RedditClient:
    """Async Reddit API client wrapping AsyncPRAW with credential rotation.

    Read and write operations are defined in the read_ops and write_ops mixins.
    """

    def __init__(
        self,
        credentials: list[tuple[str, str]],
        user_agent: str,
        username: str | None = None,
        password: str | None = None,
    ):
        if not credentials:
            raise CredentialError("At least one credential pair (client_id, client_secret) is required")
        for i, (cid, cs) in enumerate(credentials):
            if not cid or not cid.strip() or not cs or not cs.strip():
                raise CredentialError(
                    f"Credential at position {i + 1} has empty client_id or client_secret"
                )
        self._user_agent = user_agent
        self._username = username
        self._password = password
        self._credentials = [
            RedditCredential(client_id=cid, client_secret=cs)
            for cid, cs in credentials
        ]
        self._current_index = 0
        self._rotation_lock = asyncio.Lock()
        self._batch_semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def _get_credential(self) -> RedditCredential:
        """Get the next available credential, waiting if all are exhausted."""
        async with self._rotation_lock:
            for i in range(len(self._credentials)):
                idx = (self._current_index + i) % len(self._credentials)
                cred = self._credentials[idx]
                cred.reset_if_needed()
                if cred.is_available():
                    self._current_index = idx
                    cred.record_request()
                    return cred

            # All exhausted, wait for the one that resets soonest
            min_wait = min(c.seconds_until_reset() for c in self._credentials)
            logger.debug("All credentials exhausted, waiting %.1fs", min_wait)
            await asyncio.sleep(min_wait + 0.1)

            # Reset and pick the first available
            for cred in self._credentials:
                cred.reset_if_needed()
                if cred.is_available():
                    cred.record_request()
                    return cred

            raise RateLimitExhaustedError(
                "All credentials have exhausted their rate limits. Try again later."
            )

    async def _get_reddit(self) -> asyncpraw.Reddit:
        """Get an AsyncPRAW client from the next available credential."""
        cred = await self._get_credential()
        if cred.reddit is None:
            kwargs: dict[str, Any] = {
                "client_id": cred.client_id,
                "client_secret": cred.client_secret,
                "user_agent": self._user_agent,
            }
            if self._username and self._password:
                kwargs["username"] = self._username
                kwargs["password"] = self._password
            if os.environ.get("REDDIT_MCP_IGNORE_SSL", "").lower() in ("1", "true", "yes"):
                import aiohttp
                connector = aiohttp.TCPConnector(ssl=False)
                kwargs["requestor_kwargs"] = {"session": aiohttp.ClientSession(connector=connector)}
            cred.reddit = asyncpraw.Reddit(**kwargs)
        return cred.reddit

    def _require_auth(self) -> None:
        """Raise AuthenticationRequiredError if user credentials are not configured."""
        if not self._username or not self._password:
            raise AuthenticationRequiredError(
                "Write operations require REDDIT_USERNAME and REDDIT_PASSWORD env vars. "
                "Set these environment variables to enable voting, replying, and posting."
            )

    async def _resolve_thing(self, thing_id: str, thing_type: str):
        """Resolve a post or comment by ID and type.

        Args:
            thing_id: The ID of the post or comment.
            thing_type: Either "post" or "comment".

        Returns:
            The asyncpraw Submission or Comment object.
        """
        reddit = await self._get_reddit()
        if thing_type == "post":
            return await reddit.submission(id=thing_id)
        thing = await reddit.comment(id=thing_id)
        await thing.load()
        return thing

    async def close(self) -> None:
        for cred in self._credentials:
            if cred.reddit:
                await cred.reddit.close()
                cred.reddit = None

    def credentials_status(self) -> list[dict[str, Any]]:
        """Return diagnostic info about all credentials for server status."""
        return [
            {
                "index": i,
                "request_count": cred.request_count,
                "seconds_until_reset": round(cred.seconds_until_reset(), 1),
                "is_available": cred.is_available(),
            }
            for i, cred in enumerate(self._credentials)
        ]

    async def __aenter__(self) -> "RedditClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
