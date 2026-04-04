"""Reddit API credential with rate limit tracking."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

MAX_REQUESTS_PER_MINUTE = 55


@dataclass
class RedditCredential:
    """A single Reddit API credential with its own rate limit tracking."""

    client_id: str
    client_secret: str
    reddit: "asyncpraw.Reddit | None" = None
    user_reddit: dict[str, "asyncpraw.Reddit"] = field(default_factory=dict)
    request_count: int = 0
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def seconds_until_reset(self) -> float:
        elapsed = (datetime.now(timezone.utc) - self.window_start).total_seconds()
        return max(0, 60 - elapsed)

    def is_available(self) -> bool:
        now = datetime.now(timezone.utc)
        elapsed = (now - self.window_start).total_seconds()
        if elapsed >= 60:
            return True
        return self.request_count < MAX_REQUESTS_PER_MINUTE

    def reset_if_needed(self) -> None:
        now = datetime.now(timezone.utc)
        elapsed = (now - self.window_start).total_seconds()
        if elapsed >= 60:
            self.request_count = 0
            self.window_start = now

    def record_request(self) -> None:
        self.reset_if_needed()
        self.request_count += 1


# Deferred import to avoid circular dependency at module level
import asyncpraw  # noqa: E402
