"""
Test Fixtures - User Models
Created: January 13, 2025
Purpose: Reusable user fixtures for integration and E2E testing

Usage:
    @pytest.mark.asyncio
    async def test_example(test_user, test_admin):
        # test_user and test_admin are ready to use
        assert test_user.email == "test@example.com"
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import AuthService


# Standard test password (use for all test users)
TEST_PASSWORD = "TestPassword123!"
TEST_PASSWORD_HASH = AuthService.hash_password(TEST_PASSWORD)


@pytest_asyncio.fixture
async def test_user(async_db_session: AsyncSession) -> AsyncGenerator[User, None]:
    """
    Create standard test user with verified email

    Properties:
    - Email: test@example.com
    - Password: TestPassword123!
    - Status: Active, Verified
    - No MFA enabled
    """
    user = User(
        email="test@example.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name="Test User",
        is_active=True,
        is_verified=True,
        email_verified_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    yield user

    # Cleanup after test
    await async_db_session.delete(user)
    await async_db_session.commit()


@pytest_asyncio.fixture
async def test_user_unverified(async_db_session: AsyncSession) -> AsyncGenerator[User, None]:
    """
    Create test user with unverified email

    Properties:
    - Email: unverified@example.com
    - Password: TestPassword123!
    - Status: Active, NOT Verified
    - Email verification pending
    """
    user = User(
        email="unverified@example.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name="Unverified User",
        is_active=True,
        is_verified=False,
        email_verified_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    yield user

    await async_db_session.delete(user)
    await async_db_session.commit()


@pytest_asyncio.fixture
async def test_user_suspended(async_db_session: AsyncSession) -> AsyncGenerator[User, None]:
    """
    Create suspended/locked test user

    Properties:
    - Email: suspended@example.com
    - Password: TestPassword123!
    - Status: SUSPENDED/Locked
    - Verified email
    """
    user = User(
        email="suspended@example.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name="Suspended User",
        is_active=False,  # Suspended
        is_verified=True,
        email_verified_at=datetime.utcnow() - timedelta(days=30),
        locked_at=datetime.utcnow(),
        created_at=datetime.utcnow() - timedelta(days=30),
        updated_at=datetime.utcnow(),
    )

    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    yield user

    await async_db_session.delete(user)
    await async_db_session.commit()


@pytest_asyncio.fixture
async def test_admin(async_db_session: AsyncSession) -> AsyncGenerator[User, None]:
    """
    Create test admin user with elevated privileges

    Properties:
    - Email: admin@example.com
    - Password: TestPassword123!
    - Role: Admin
    - Status: Active, Verified
    """
    admin = User(
        email="admin@example.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name="Admin User",
        is_active=True,
        is_verified=True,
        is_admin=True,  # Admin privileges
        email_verified_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    async_db_session.add(admin)
    await async_db_session.commit()
    await async_db_session.refresh(admin)

    yield admin

    await async_db_session.delete(admin)
    await async_db_session.commit()


@pytest_asyncio.fixture
async def test_user_with_mfa(async_db_session: AsyncSession) -> AsyncGenerator[User, None]:
    """
    Create test user with MFA enabled

    Properties:
    - Email: mfa-user@example.com
    - Password: TestPassword123!
    - MFA: TOTP enabled
    - Status: Active, Verified
    """
    user = User(
        email="mfa-user@example.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name="MFA User",
        is_active=True,
        is_verified=True,
        mfa_enabled=True,
        mfa_secret="JBSWY3DPEHPK3PXP",  # Test TOTP secret
        email_verified_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    yield user

    await async_db_session.delete(user)
    await async_db_session.commit()


@pytest_asyncio.fixture
async def test_users_batch(async_db_session: AsyncSession) -> AsyncGenerator[list[User], None]:
    """
    Create batch of 10 test users for list/pagination testing

    Properties:
    - Emails: user1@example.com ... user10@example.com
    - All verified and active
    - Created at different times (for sorting tests)
    """
    users = []

    for i in range(1, 11):
        user = User(
            email=f"user{i}@example.com",
            password_hash=TEST_PASSWORD_HASH,
            full_name=f"Test User {i}",
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.utcnow() - timedelta(days=i),
            created_at=datetime.utcnow() - timedelta(days=i),
            updated_at=datetime.utcnow(),
        )
        async_db_session.add(user)
        users.append(user)

    await async_db_session.commit()

    # Refresh all users to get IDs
    for user in users:
        await async_db_session.refresh(user)

    yield users

    # Cleanup
    for user in users:
        await async_db_session.delete(user)
    await async_db_session.commit()


# Helper function for creating custom test users
async def create_test_user(
    async_db_session: AsyncSession,
    email: str,
    password: str = TEST_PASSWORD,
    full_name: str = "Test User",
    is_verified: bool = True,
    is_active: bool = True,
    is_admin: bool = False,
    mfa_enabled: bool = False,
) -> User:
    """
    Factory function for creating custom test users

    Usage:
        user = await create_test_user(
            async_session,
            email="custom@example.com",
            full_name="Custom User",
            is_admin=True
        )
    """
    user = User(
        email=email,
        hashed_password=AuthService.hash_password(password),
        full_name=full_name,
        is_active=is_active,
        is_verified=is_verified,
        is_admin=is_admin,
        mfa_enabled=mfa_enabled,
        email_verified_at=datetime.utcnow() if is_verified else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    return user
