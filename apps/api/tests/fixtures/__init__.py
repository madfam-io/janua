"""
Test Fixtures Package
Created: January 13, 2025

This package contains reusable pytest fixtures for integration testing.

Available Fixtures:
- users.py: User model fixtures (test_user, test_admin, etc.)
- organizations.py: Organization model fixtures
- sessions.py: Session model fixtures

Usage in conftest.py:
    from tests.fixtures.users import *
    from tests.fixtures.organizations import *
    from tests.fixtures.sessions import *
"""

# Export commonly used test constants
TEST_PASSWORD = "TestPassword123!"

__all__ = ["TEST_PASSWORD"]
