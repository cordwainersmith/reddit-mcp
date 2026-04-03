"""Tests for the caching decorator."""

import asyncio

import pytest

from reddit_mcp.cache import _stats, cached, cache_stats


class TestCachedDecorator:
    @pytest.mark.asyncio
    async def test_cache_hit_avoids_function_execution(self):
        call_count = 0

        @cached(ttl=60, maxsize=10)
        async def my_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await my_func(5)
        result2 = await my_func(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Only called once, second was cached

    @pytest.mark.asyncio
    async def test_different_args_produce_different_entries(self):
        call_count = 0

        @cached(ttl=60, maxsize=10)
        async def my_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await my_func(5)
        result2 = await my_func(10)

        assert result1 == 10
        assert result2 == 20
        assert call_count == 2  # Called twice for different args

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        call_count = 0

        @cached(ttl=0, maxsize=10)  # TTL of 0 means immediate expiration
        async def my_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await my_func(5)
        await asyncio.sleep(0.01)  # Small delay to ensure TTL expires
        result2 = await my_func(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 2  # Called twice due to TTL expiration

    @pytest.mark.asyncio
    async def test_cache_stats_tracking(self):
        @cached(ttl=60, maxsize=10)
        async def tracked_func(x):
            return x

        # Clear any previous stats for this function
        func_name = tracked_func.__qualname__

        await tracked_func(1)  # miss
        await tracked_func(1)  # hit
        await tracked_func(2)  # miss

        stats = cache_stats()
        # The original unwrapped name is used
        assert func_name in stats or "tracked_func" in [k.split(".")[-1] for k in stats]

    @pytest.mark.asyncio
    async def test_kwargs_produce_different_keys(self):
        call_count = 0

        @cached(ttl=60, maxsize=10)
        async def my_func(x, multiplier=2):
            nonlocal call_count
            call_count += 1
            return x * multiplier

        result1 = await my_func(5, multiplier=2)
        result2 = await my_func(5, multiplier=3)

        assert result1 == 10
        assert result2 == 15
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_exposes_internal_cache(self):
        @cached(ttl=60, maxsize=10)
        async def my_func(x):
            return x

        assert hasattr(my_func, "_cache")
        await my_func(5)
        assert len(my_func._cache) == 1
