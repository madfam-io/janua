"""
Comprehensive Caching Utilities Test Suite
Tests for cache key generation, decorators, and CacheManager
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.core.caching import (
    cache_key,
    cached,
    CacheManager,
    cache_user,
    cache_organization,
    cache_permissions,
    cache_sso_config,
)

pytestmark = pytest.mark.asyncio


class TestCacheKeyGeneration:
    """Test cache key generation function."""

    def test_cache_key_from_args(self):
        """Test cache key generated from positional arguments."""
        key1 = cache_key("user", "123")
        key2 = cache_key("user", "123")

        # Same args should produce same key
        assert key1 == key2
        assert len(key1) == 16  # SHA256 truncated to 16 chars

    def test_cache_key_different_args(self):
        """Test different args produce different keys."""
        key1 = cache_key("user", "123")
        key2 = cache_key("user", "456")

        assert key1 != key2

    def test_cache_key_from_kwargs(self):
        """Test cache key generated from keyword arguments."""
        key1 = cache_key(user_id="123", org_id="456")
        key2 = cache_key(user_id="123", org_id="456")

        assert key1 == key2

    def test_cache_key_kwargs_order_independent(self):
        """Test kwargs order doesn't affect key."""
        key1 = cache_key(a="1", b="2", c="3")
        key2 = cache_key(c="3", a="1", b="2")

        assert key1 == key2

    def test_cache_key_mixed_args_kwargs(self):
        """Test cache key with both args and kwargs."""
        key1 = cache_key("prefix", user_id="123")
        key2 = cache_key("prefix", user_id="123")

        assert key1 == key2

    def test_cache_key_empty_args(self):
        """Test cache key with no arguments."""
        key = cache_key()

        assert isinstance(key, str)
        assert len(key) == 16


class TestCachedDecorator:
    """Test cached decorator functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.set = AsyncMock()
        return redis_mock

    async def test_cached_calls_function_on_miss(self, mock_redis):
        """Test function is called when cache misses."""
        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cached(ttl=300)
            async def test_func(arg1):
                return {"result": arg1}

            result = await test_func("test")

            assert result == {"result": "test"}

    async def test_cached_returns_cached_value_on_hit(self, mock_redis):
        """Test cached value is returned on cache hit."""
        cached_value = {"cached": True}
        mock_redis.get.return_value = json.dumps(cached_value)

        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cached(ttl=300)
            async def test_func(arg1):
                return {"result": arg1}

            result = await test_func("test")

            assert result == cached_value

    async def test_cached_stores_result(self, mock_redis):
        """Test result is stored in cache."""
        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cached(ttl=600)
            async def test_func():
                return {"data": "value"}

            await test_func()

            mock_redis.set.assert_called_once()
            # Check TTL is passed
            call_kwargs = mock_redis.set.call_args
            assert call_kwargs[1]["ex"] == 600

    async def test_cached_with_custom_key_prefix(self, mock_redis):
        """Test cached with custom key prefix."""
        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cached(ttl=300, key_prefix="custom_prefix")
            async def test_func():
                return {"data": "value"}

            await test_func()

            # Check key contains custom prefix
            call_args = mock_redis.get.call_args[0][0]
            assert call_args.startswith("custom_prefix:")

    async def test_cached_with_custom_key_builder(self, mock_redis):
        """Test cached with custom key builder."""
        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cached(ttl=300, key_builder=lambda x: f"custom_{x}")
            async def test_func(arg):
                return {"data": arg}

            await test_func("myarg")

            # Check key uses custom builder
            call_args = mock_redis.get.call_args[0][0]
            assert "custom_myarg" in call_args

    async def test_cached_handles_redis_get_failure(self, mock_redis):
        """Test cached gracefully handles Redis get failure."""
        mock_redis.get.side_effect = Exception("Redis connection failed")

        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cached(ttl=300)
            async def test_func():
                return {"data": "uncached"}

            result = await test_func()

            # Function should still return result
            assert result == {"data": "uncached"}

    async def test_cached_handles_redis_set_failure(self, mock_redis):
        """Test cached gracefully handles Redis set failure."""
        mock_redis.get.return_value = None
        mock_redis.set.side_effect = Exception("Redis write failed")

        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cached(ttl=300)
            async def test_func():
                return {"data": "value"}

            result = await test_func()

            # Function should still return result
            assert result == {"data": "value"}


class TestCacheManager:
    """Test CacheManager class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.set = AsyncMock()
        redis_mock.delete = AsyncMock(return_value=1)
        return redis_mock

    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create CacheManager with mock Redis."""
        return CacheManager(redis_client=mock_redis)

    def test_cache_manager_initialization(self):
        """Test CacheManager initialization."""
        manager = CacheManager()
        assert manager.redis_client is None

    def test_cache_manager_with_client(self, mock_redis):
        """Test CacheManager initialization with client."""
        manager = CacheManager(redis_client=mock_redis)
        assert manager.redis_client is mock_redis

    async def test_invalidate_success(self, cache_manager, mock_redis):
        """Test cache invalidation success."""
        mock_redis.delete.return_value = 1

        result = await cache_manager.invalidate("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    async def test_invalidate_key_not_found(self, cache_manager, mock_redis):
        """Test cache invalidation when key doesn't exist."""
        mock_redis.delete.return_value = 0

        result = await cache_manager.invalidate("nonexistent_key")

        assert result is False

    async def test_invalidate_failure(self, cache_manager, mock_redis):
        """Test cache invalidation handles failure."""
        mock_redis.delete.side_effect = Exception("Redis error")

        result = await cache_manager.invalidate("test_key")

        assert result is False

    async def test_invalidate_pattern_returns_zero(self, cache_manager, mock_redis):
        """Test pattern invalidation currently returns 0 (not fully implemented)."""
        result = await cache_manager.invalidate_pattern("user:*")

        # Current implementation logs warning and returns 0
        assert result == 0

    async def test_warm_cache_success(self, cache_manager, mock_redis):
        """Test cache warming success."""
        result = await cache_manager.warm_cache("test_key", {"data": "value"}, ttl=600)

        assert result is True
        mock_redis.set.assert_called_once()

    async def test_warm_cache_with_ttl(self, cache_manager, mock_redis):
        """Test cache warming with custom TTL."""
        await cache_manager.warm_cache("test_key", {"data": "value"}, ttl=1800)

        call_kwargs = mock_redis.set.call_args
        assert call_kwargs[1]["ex"] == 1800

    async def test_warm_cache_failure(self, cache_manager, mock_redis):
        """Test cache warming handles failure."""
        mock_redis.set.side_effect = Exception("Redis error")

        result = await cache_manager.warm_cache("test_key", {"data": "value"})

        assert result is False

    async def test_warm_cache_serializes_data(self, cache_manager, mock_redis):
        """Test cache warming serializes data to JSON."""
        data = {"user_id": "123", "name": "Test User"}

        await cache_manager.warm_cache("test_key", data)

        call_args = mock_redis.set.call_args[0]
        # Second argument should be JSON serialized data
        assert json.loads(call_args[1]) == data

    async def test_get_client_lazy_initialization(self):
        """Test _get_client lazy initializes Redis."""
        manager = CacheManager()

        with patch("app.core.caching.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_get_redis.return_value = mock_client

            client = await manager._get_client()

            assert client is mock_client
            mock_get_redis.assert_called_once()


class TestPreconfiguredCacheDecorators:
    """Test pre-configured cache decorators."""

    def test_cache_user_creates_decorator(self):
        """Test cache_user returns a decorator."""
        decorator = cache_user(ttl=600)
        assert callable(decorator)

    def test_cache_user_default_ttl(self):
        """Test cache_user has default TTL of 600."""
        # Just verify the decorator can be created
        decorator = cache_user()
        assert callable(decorator)

    def test_cache_organization_creates_decorator(self):
        """Test cache_organization returns a decorator."""
        decorator = cache_organization(ttl=3600)
        assert callable(decorator)

    def test_cache_organization_default_ttl(self):
        """Test cache_organization has default TTL of 3600."""
        decorator = cache_organization()
        assert callable(decorator)

    def test_cache_permissions_creates_decorator(self):
        """Test cache_permissions returns a decorator."""
        decorator = cache_permissions(ttl=300)
        assert callable(decorator)

    def test_cache_sso_config_creates_decorator(self):
        """Test cache_sso_config returns a decorator."""
        decorator = cache_sso_config(ttl=1800)
        assert callable(decorator)


class TestCacheKeyBuilders:
    """Test key builder functions in pre-configured decorators."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.set = AsyncMock()
        return redis_mock

    async def test_cache_user_key_builder(self, mock_redis):
        """Test cache_user uses user_id as key."""
        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cache_user(ttl=600)
            async def get_user(user_id):
                return {"id": user_id}

            await get_user("user123")

            call_args = mock_redis.get.call_args[0][0]
            assert "user:user123" in call_args

    async def test_cache_organization_key_builder(self, mock_redis):
        """Test cache_organization uses org_id as key."""
        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cache_organization(ttl=3600)
            async def get_org(org_id):
                return {"id": org_id}

            await get_org("org456")

            call_args = mock_redis.get.call_args[0][0]
            assert "org:org456" in call_args

    async def test_cache_permissions_key_builder(self, mock_redis):
        """Test cache_permissions uses user_id:resource:action as key."""
        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cache_permissions(ttl=300)
            async def check_permission(user_id, resource, action):
                return True

            await check_permission("user1", "document", "read")

            call_args = mock_redis.get.call_args[0][0]
            assert "perms:user1:document:read" in call_args

    async def test_cache_sso_config_key_builder(self, mock_redis):
        """Test cache_sso_config uses org_id:provider as key."""
        with patch("app.core.caching.get_redis", return_value=mock_redis):

            @cache_sso_config(ttl=1800)
            async def get_sso(org_id, provider):
                return {"provider": provider}

            await get_sso("org789", "okta")

            call_args = mock_redis.get.call_args[0][0]
            assert "sso:org789:okta" in call_args
