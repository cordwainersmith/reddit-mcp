"""TTL caching layer for the Reddit MCP server."""

import functools
import hashlib
import inspect
import logging
from typing import Callable

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Global cache stats
_stats: dict[str, dict[str, int]] = {}


def _make_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a cache key from function name and arguments."""
    key_parts = [func_name]
    for arg in args:
        key_parts.append(repr(arg))
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={repr(v)}")
    raw = "|".join(key_parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def _has_self_param(func: Callable) -> bool:
    """Check whether the function's first parameter is named 'self'."""
    try:
        params = list(inspect.signature(func).parameters)
        return bool(params) and params[0] == "self"
    except (ValueError, TypeError):
        return False


def cached(ttl: int = 300, maxsize: int = 128) -> Callable:
    """Decorator that adds TTL caching to async functions.

    Args:
        ttl: Time-to-live in seconds for cached entries.
        maxsize: Maximum number of entries in the cache.
    """
    cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def decorator(func: Callable) -> Callable:
        func_name = func.__qualname__
        ignore_first = _has_self_param(func)

        # Initialize stats for this function
        _stats[func_name] = {"hits": 0, "misses": 0}

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip 'self' from cache key for methods
            cache_args = args[1:] if ignore_first else args
            key = _make_key(func_name, cache_args, kwargs)

            if key in cache:
                _stats[func_name]["hits"] += 1
                logger.debug("Cache hit for %s", func_name)
                return cache[key]

            _stats[func_name]["misses"] += 1
            logger.debug("Cache miss for %s", func_name)
            result = await func(*args, **kwargs)
            cache[key] = result
            return result

        # Expose the cache for testing/clearing
        wrapper._cache = cache
        return wrapper

    return decorator


def cache_stats() -> dict[str, dict[str, int]]:
    """Return hit/miss counts for all cached functions."""
    return dict(_stats)
