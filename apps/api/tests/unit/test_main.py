"""
Unit tests for main FastAPI application
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app


class TestApplicationSetup:
    """Test FastAPI application setup and configuration."""
    
    def test_app_instance(self):
        """Test that app instance is properly configured."""
        assert app.title == "Plinto API"
        assert app.description == "Secure identity platform API"
        # FastAPI apps have a state attribute for application state management
        assert hasattr(app, 'state')
        # Also verify the app has been configured with lifespan events
        assert app.router.lifespan_context is not None
    
    def test_middleware_setup(self):
        """Test that middleware is properly configured."""
        # Check that middleware is added
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        
        expected_middleware = [
            "CORSMiddleware",
            "TrustedHostMiddleware"
        ]
        
        for middleware in expected_middleware:
            assert middleware in middleware_classes
    
    def test_router_inclusion(self):
        """Test that routers are properly included."""
        # Check that auth router is included
        route_paths = [route.path for route in app.routes]
        
        # Should have auth routes
        auth_routes = [path for path in route_paths if path.startswith("/api/v1/auth")]
        assert len(auth_routes) > 0
    
    def test_exception_handlers(self):
        """Test that exception handlers are registered."""
        # Check that exception handlers are configured
        assert len(app.exception_handlers) > 0


class TestHealthEndpoints:
    """Test health and status endpoints."""
    
    async def test_health_endpoint(self, test_client: AsyncClient):
        """Test the health check endpoint."""
        response = await test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
    
    async def test_ready_endpoint_success(self, test_client: AsyncClient):
        """Test the readiness check endpoint when services are healthy."""
        with patch('app.main.engine') as mock_engine, \
             patch('app.main.redis_client') as mock_redis:
            
            # Mock successful database connection
            mock_conn = AsyncMock()
            mock_engine.connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.execute.return_value = None
            
            # Mock successful Redis connection
            mock_redis.ping.return_value = True
            
            response = await test_client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "ready"
            assert data["database"] is True
            assert data["redis"] is True
    
    async def test_ready_endpoint_degraded(self, test_client: AsyncClient):
        """Test the readiness check endpoint when services are unhealthy."""
        with patch('app.main.engine') as mock_engine, \
             patch('app.main.redis_client') as mock_redis:
            
            # Mock failed database connection
            mock_engine.connect.side_effect = Exception("DB connection failed")
            
            # Mock failed Redis connection
            mock_redis.ping.side_effect = Exception("Redis connection failed")
            
            response = await test_client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "degraded"
            assert data["database"] is False
            assert data["redis"] is False


class TestOpenIDEndpoints:
    """Test OpenID Connect discovery endpoints."""
    
    async def test_openid_configuration(self, test_client: AsyncClient):
        """Test OpenID Connect configuration endpoint."""
        response = await test_client.get("/.well-known/openid-configuration")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required OpenID Connect fields
        required_fields = [
            "issuer",
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
            "response_types_supported",
            "subject_types_supported",
            "id_token_signing_alg_values_supported"
        ]
        
        for field in required_fields:
            assert field in data
        
        # Check that URLs are properly formatted
        assert data["authorization_endpoint"].startswith("http")
        assert data["token_endpoint"].startswith("http")
        assert data["userinfo_endpoint"].startswith("http")
        assert data["jwks_uri"].startswith("http")
    
    async def test_jwks_endpoint(self, test_client: AsyncClient):
        """Test JWKS endpoint."""
        response = await test_client.get("/.well-known/jwks.json")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return valid JWKS structure
        assert "keys" in data
        assert isinstance(data["keys"], list)


class TestTestEndpoints:
    """Test debugging/test endpoints."""
    
    async def test_test_endpoint(self, test_client: AsyncClient):
        """Test the simple test endpoint."""
        response = await test_client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "test endpoint working"
        assert "auth_router_included" in data
    
    async def test_test_json_endpoint(self, test_client: AsyncClient):
        """Test the JSON test endpoint."""
        test_data = {"test": "data", "number": 42}
        
        response = await test_client.post("/test-json", json=test_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["received"] == test_data


class TestMiddleware:
    """Test middleware behavior."""
    
    async def test_cors_middleware(self, test_client: AsyncClient):
        """Test CORS middleware configuration."""
        response = await test_client.options("/health")
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
    
    async def test_process_time_header(self, test_client: AsyncClient):
        """Test that process time header is added."""
        response = await test_client.get("/health")
        
        assert "x-process-time" in response.headers
        # Should be a valid float
        process_time = float(response.headers["x-process-time"])
        assert process_time >= 0
    
    async def test_trusted_host_middleware(self, test_client: AsyncClient):
        """Test trusted host middleware behavior."""
        # Test with valid host
        response = await test_client.get("/health")
        assert response.status_code == 200
        
        # Test with invalid host (would need custom client configuration)
        # This is more of an integration test, but validates the concept


class TestLifespan:
    """Test application lifespan events."""
    
    async def test_lifespan_startup(self):
        """Test application startup sequence."""
        with patch('app.main.init_db') as mock_init_db, \
             patch('app.main.init_redis') as mock_init_redis, \
             patch('app.main.logger') as mock_logger:
            
            # Manually trigger lifespan startup
            from app.main import lifespan
            
            # This would be called by FastAPI during startup
            async with lifespan(app):
                pass
            
            mock_init_db.assert_called_once()
            mock_init_redis.assert_called_once()
            mock_logger.info.assert_called()