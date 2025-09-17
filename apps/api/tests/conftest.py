"""
Global test configuration and fixtures
"""
import os
import sys
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, Mock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Mock slowapi before any app imports to prevent rate limiting in tests
class MockLimiter:
    """Mock limiter that bypasses rate limiting"""
    def __init__(self, *args, **kwargs):
        pass

    def limit(self, *args, **kwargs):
        """Return a decorator that doesn't modify the function"""
        def decorator(f):
            return f
        return decorator

    def shared_limit(self, *args, **kwargs):
        """Return a decorator that doesn't modify the function"""
        def decorator(f):
            return f
        return decorator

# Patch slowapi.Limiter before any imports
import slowapi
slowapi.Limiter = MockLimiter

# Set test environment variables
TEST_ENV = {
    'ENVIRONMENT': 'test',
    'DATABASE_URL': 'sqlite+aiosqlite:///:memory:',
    'JWT_SECRET_KEY': 'test-secret-key-for-testing-only',
    'REDIS_URL': 'redis://localhost:6379/1',
    'SECRET_KEY': 'test-secret-key',
    'JWT_ALGORITHM': 'HS256',
    'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': '60',
    'JWT_ISSUER': 'test-issuer',
    'JWT_AUDIENCE': 'test-audience',
    'ACCESS_TOKEN_EXPIRE_MINUTES': '60',
    'REFRESH_TOKEN_EXPIRE_DAYS': '7'
}

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables for all tests"""
    with patch.dict(os.environ, TEST_ENV):
        yield

@pytest.fixture(autouse=True)
def mock_database_dependency():
    """Mock database dependency globally for all tests"""
    from app.main import app
    from app.database import get_db

    # Override database dependency with mock
    def override_get_db():
        mock_session = MagicMock()  # Use regular Mock, not AsyncMock for old-style queries
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()
        mock_session.rollback = MagicMock()
        mock_session.close = MagicMock()
        mock_session.execute = MagicMock()
        mock_session.scalar = MagicMock()
        mock_session.scalars = MagicMock()

        # Mock for old-style SQLAlchemy query() usage
        mock_query_result = MagicMock()
        mock_query_result.filter.return_value = mock_query_result
        mock_query_result.first.return_value = None  # No user found by default
        mock_session.query.return_value = mock_query_result

        return mock_session

    app.dependency_overrides[get_db] = override_get_db
    yield
    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.fixture
async def client():
    """Async HTTP client for testing"""
    from app.main import app
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac

@pytest.fixture
async def db_session():
    """Mock async database session"""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.query = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.scalar = AsyncMock()
    mock_session.scalars = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    return mock_session

@pytest.fixture
def mock_database():
    """Mock database session"""
    return MagicMock()

@pytest.fixture
def mock_redis():
    """Mock Redis connection"""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=0)
    return mock

@pytest.fixture
def anyio_backend():
    """Specify the async backend for pytest"""
    return 'asyncio'