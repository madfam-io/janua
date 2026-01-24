"""
Comprehensive unit tests for rate limiting middleware
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, status

from app.middleware.rate_limit import RateLimitMiddleware, RateLimitExceeded, AdaptiveRateLimiter

pytestmark = pytest.mark.asyncio


class TestRateLimitExceeded:
    """Test rate limit exception."""

    def test_rate_limit_exceeded_creation(self):
        """Test RateLimitExceeded exception creation."""
        retry_after = 60
        exception = RateLimitExceeded(retry_after)

        assert exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exception.detail == "Rate limit exceeded"
        assert exception.headers["Retry-After"] == str(retry_after)

    def test_rate_limit_exceeded_different_retry_values(self):
        """Test RateLimitExceeded with different retry values."""
        for retry_after in [10, 30, 60, 120, 300]:
            exception = RateLimitExceeded(retry_after)
            assert exception.headers["Retry-After"] == str(retry_after)


class TestRateLimitMiddlewareInitialization:
    """Test rate limiting middleware initialization."""

    def test_middleware_initialization_default(self):
        """Test middleware initialization with default values."""
        middleware = RateLimitMiddleware()

        assert middleware.app is None
        assert middleware.redis_client is None
        assert middleware.default_limit == 100
        assert middleware.window_seconds == 60
        assert middleware.enable_tenant_limits is True

    def test_middleware_initialization_custom_values(self):
        """Test middleware initialization with custom values."""
        app = MagicMock()
        redis_client = AsyncMock()
        middleware = RateLimitMiddleware(
            app=app,
            redis_client=redis_client,
            default_limit=200,
            window_seconds=120,
            enable_tenant_limits=False,
        )

        assert middleware.app == app
        assert middleware.redis_client == redis_client
        assert middleware.default_limit == 200
        assert middleware.window_seconds == 120
        assert middleware.enable_tenant_limits is False

    def test_middleware_has_endpoint_limits(self):
        """Test middleware has predefined endpoint limits."""
        middleware = RateLimitMiddleware()

        assert "/auth/signin" in middleware.endpoint_limits
        assert "/auth/signup" in middleware.endpoint_limits
        assert middleware.endpoint_limits["/auth/signin"] == 10
        assert middleware.endpoint_limits["/auth/signup"] == 5

    def test_middleware_has_tenant_tier_limits(self):
        """Test middleware has predefined tenant tier limits."""
        middleware = RateLimitMiddleware()

        assert "community" in middleware.tenant_tier_limits
        assert "pro" in middleware.tenant_tier_limits
        assert "scale" in middleware.tenant_tier_limits
        assert "enterprise" in middleware.tenant_tier_limits
        assert middleware.tenant_tier_limits["community"] == 100
        assert middleware.tenant_tier_limits["enterprise"] == 10000


class TestRateLimitMiddlewareDispatch:
    """Test rate limiting middleware dispatch functionality."""

    @pytest.fixture
    def middleware_no_redis(self):
        """Middleware without Redis (skips rate limiting)."""
        app = MagicMock()
        return RateLimitMiddleware(app, redis_client=None)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.client.host = "192.168.1.1"
        request.headers = {}
        request.query_params = {}
        request.state = MagicMock()
        delattr(request.state, "tenant_id")  # Simulate no tenant_id
        return request

    async def test_dispatch_skips_health_endpoint(self, middleware_no_redis, mock_request):
        """Test middleware skips health check endpoint."""
        mock_request.url.path = "/health"
        call_next = AsyncMock(return_value=MagicMock())

        _ = await middleware_no_redis.dispatch(mock_request, call_next)

        call_next.assert_called_once_with(mock_request)

    async def test_dispatch_skips_ready_endpoint(self, middleware_no_redis, mock_request):
        """Test middleware skips ready endpoint."""
        mock_request.url.path = "/ready"
        call_next = AsyncMock(return_value=MagicMock())

        _ = await middleware_no_redis.dispatch(mock_request, call_next)

        call_next.assert_called_once_with(mock_request)

    async def test_dispatch_skips_jwks_endpoint(self, middleware_no_redis, mock_request):
        """Test middleware skips JWKS endpoint."""
        mock_request.url.path = "/.well-known/jwks.json"
        call_next = AsyncMock(return_value=MagicMock())

        _ = await middleware_no_redis.dispatch(mock_request, call_next)

        call_next.assert_called_once_with(mock_request)

    async def test_dispatch_without_redis_proceeds(self, middleware_no_redis, mock_request):
        """Test middleware proceeds when Redis is not available."""
        call_next = AsyncMock(return_value=MagicMock())

        _ = await middleware_no_redis.dispatch(mock_request, call_next)

        # Should proceed without rate limiting when Redis is not available
        call_next.assert_called_once_with(mock_request)


class TestRateLimitMiddlewareHelpers:
    """Test helper methods."""

    @pytest.fixture
    def middleware(self):
        """Basic middleware instance."""
        return RateLimitMiddleware()

    def test_normalize_endpoint_removes_trailing_slash(self, middleware):
        """Test endpoint normalization removes trailing slash."""
        assert middleware._normalize_endpoint("/api/test/") == "/api/test"

    def test_normalize_endpoint_replaces_uuid(self, middleware):
        """Test endpoint normalization replaces UUID with placeholder."""
        path = "/api/users/12345678-1234-1234-1234-123456789abc/profile"
        normalized = middleware._normalize_endpoint(path)
        assert "12345678" not in normalized
        assert "/:id" in normalized

    def test_normalize_endpoint_replaces_numeric_id(self, middleware):
        """Test endpoint normalization replaces numeric ID with placeholder."""
        path = "/api/items/12345"
        normalized = middleware._normalize_endpoint(path)
        assert "12345" not in normalized
        assert "/:id" in normalized

    def test_get_ip_limit_default(self, middleware):
        """Test default IP limit."""
        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_WHITELIST = []
            limit = middleware._get_ip_limit("203.0.113.1")
            assert limit == middleware.default_limit

    def test_get_ip_limit_internal_network(self, middleware):
        """Test IP limit for internal networks."""
        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_WHITELIST = []
            # 10.x.x.x gets 2x limit
            limit = middleware._get_ip_limit("10.0.0.1")
            assert limit == middleware.default_limit * 2

            # 192.168.x.x gets 2x limit
            limit = middleware._get_ip_limit("192.168.1.1")
            assert limit == middleware.default_limit * 2

    def test_get_tenant_id_from_header(self, middleware):
        """Test tenant ID extraction from header."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Tenant-ID": "tenant-123"}
        request.query_params = {}
        request.state = MagicMock()
        delattr(request.state, "tenant_id")

        tenant_id = middleware._get_tenant_id(request)
        assert tenant_id == "tenant-123"

    def test_get_tenant_id_from_query_param(self, middleware):
        """Test tenant ID extraction from query parameter."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = {"tenant_id": "tenant-456"}
        request.state = MagicMock()
        delattr(request.state, "tenant_id")

        tenant_id = middleware._get_tenant_id(request)
        assert tenant_id == "tenant-456"

    def test_get_tenant_id_from_state(self, middleware):
        """Test tenant ID extraction from request state."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.state.tenant_id = "tenant-789"

        tenant_id = middleware._get_tenant_id(request)
        assert tenant_id == "tenant-789"

    def test_get_tenant_id_none(self, middleware):
        """Test tenant ID returns None when not available."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.state = MagicMock()
        delattr(request.state, "tenant_id")

        tenant_id = middleware._get_tenant_id(request)
        assert tenant_id is None


class TestRateLimitClientIP:
    """Test client IP extraction."""

    @pytest.fixture
    def middleware(self):
        """Basic middleware instance."""
        return RateLimitMiddleware()

    def test_get_client_ip_direct(self, middleware):
        """Test direct client IP extraction."""
        request = MagicMock(spec=Request)
        request.client.host = "203.0.113.5"
        request.headers = {}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ""
            ip = middleware._get_client_ip(request)
            assert ip == "203.0.113.5"

    def test_get_client_ip_from_forwarded_with_trusted_proxy(self, middleware):
        """Test IP extraction from X-Forwarded-For with trusted proxy."""
        request = MagicMock(spec=Request)
        request.client.host = "10.0.0.1"
        request.headers = {"X-Forwarded-For": "203.0.113.5, 10.0.0.2"}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = "10.0.0.1"
            ip = middleware._get_client_ip(request)
            assert ip == "203.0.113.5"

    def test_get_client_ip_ignores_forwarded_from_untrusted(self, middleware):
        """Test IP extraction ignores X-Forwarded-For from untrusted proxy."""
        request = MagicMock(spec=Request)
        request.client.host = "203.0.113.100"  # Untrusted proxy
        request.headers = {"X-Forwarded-For": "spoofed-ip"}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = "10.0.0.1"  # Only this is trusted
            ip = middleware._get_client_ip(request)
            # Should use direct IP, not spoofed header
            assert ip == "203.0.113.100"

    def test_get_client_ip_no_client(self, middleware):
        """Test IP extraction when client is None."""
        request = MagicMock(spec=Request)
        request.client = None
        request.headers = {}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.TRUSTED_PROXIES = ""
            ip = middleware._get_client_ip(request)
            assert ip == "unknown"


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiter."""

    @pytest.fixture
    def redis_client(self):
        """Mock Redis client."""
        return AsyncMock()

    @pytest.fixture
    def limiter(self, redis_client):
        """Create adaptive rate limiter."""
        return AdaptiveRateLimiter(redis_client)

    def test_base_limits_defined(self, limiter):
        """Test base limits are defined."""
        assert limiter.base_limits["low"] == 1.5
        assert limiter.base_limits["normal"] == 1.0
        assert limiter.base_limits["high"] == 0.7
        assert limiter.base_limits["critical"] == 0.3

    async def test_get_adaptive_limit_normal(self, limiter, redis_client):
        """Test adaptive limit under normal load."""
        redis_client.get.return_value = None  # No metrics

        limit = await limiter.get_adaptive_limit(100, "/api/test")

        # Normal load should return base limit
        assert limit == 100

    async def test_get_system_load_no_metrics(self, limiter, redis_client):
        """Test system load returns normal when no metrics."""
        redis_client.get.return_value = None

        load = await limiter._get_system_load()

        assert load == "normal"

    async def test_get_system_load_high_cpu(self, limiter, redis_client):
        """Test system load detection with high CPU."""
        import json

        redis_client.get.return_value = json.dumps({"cpu_percent": 75})

        load = await limiter._get_system_load()

        assert load == "high"

    async def test_get_system_load_critical_cpu(self, limiter, redis_client):
        """Test system load detection with critical CPU."""
        import json

        redis_client.get.return_value = json.dumps({"cpu_percent": 85})

        load = await limiter._get_system_load()

        assert load == "critical"

    async def test_get_system_load_low_cpu(self, limiter, redis_client):
        """Test system load detection with low CPU."""
        import json

        redis_client.get.return_value = json.dumps({"cpu_percent": 20})

        load = await limiter._get_system_load()

        assert load == "low"

    async def test_get_error_rate(self, limiter, redis_client):
        """Test error rate calculation."""
        redis_client.get.side_effect = [10, 100]  # 10 errors, 100 total

        error_rate = await limiter._get_error_rate("/api/test")

        assert error_rate == 0.1  # 10%
