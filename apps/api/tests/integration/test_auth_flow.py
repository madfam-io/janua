"""
Integration tests for authentication flow
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
class TestAuthFlow:
    """Test complete authentication flow"""
    
    async def test_health_check(self):
        """Test health endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
