"""
Comprehensive RBAC Service Test Suite
Tests for Role-Based Access Control functionality
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.rbac_service import RBACService, RBACPolicy, Permission

pytestmark = pytest.mark.asyncio


class TestRBACServiceInitialization:
    """Test RBAC service initialization."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis

    def test_service_initialization(self, mock_db, mock_redis):
        """Test service initializes correctly."""
        service = RBACService(mock_db, mock_redis)

        assert service.db is mock_db
        assert service.redis is mock_redis

    def test_service_has_role_hierarchy(self, mock_db, mock_redis):
        """Test service has role hierarchy."""
        service = RBACService(mock_db, mock_redis)

        assert "super_admin" in service.ROLE_HIERARCHY
        assert "owner" in service.ROLE_HIERARCHY
        assert "admin" in service.ROLE_HIERARCHY
        assert "member" in service.ROLE_HIERARCHY
        assert "viewer" in service.ROLE_HIERARCHY

    def test_service_has_permissions(self, mock_db, mock_redis):
        """Test service has permissions matrix."""
        service = RBACService(mock_db, mock_redis)

        assert "super_admin" in service.PERMISSIONS
        assert "owner" in service.PERMISSIONS
        assert "admin" in service.PERMISSIONS


class TestRoleHierarchy:
    """Test role hierarchy functionality."""

    @pytest.fixture
    def service(self):
        return RBACService(MagicMock(), AsyncMock())

    def test_super_admin_is_highest(self, service):
        """Test super_admin has highest level."""
        assert service.get_role_level("super_admin") == 4

    def test_owner_level(self, service):
        """Test owner level."""
        assert service.get_role_level("owner") == 3

    def test_admin_level(self, service):
        """Test admin level."""
        assert service.get_role_level("admin") == 2

    def test_member_level(self, service):
        """Test member level."""
        assert service.get_role_level("member") == 1

    def test_viewer_is_lowest(self, service):
        """Test viewer has lowest level."""
        assert service.get_role_level("viewer") == 0

    def test_unknown_role_returns_negative(self, service):
        """Test unknown role returns -1."""
        assert service.get_role_level("unknown_role") == -1

    def test_empty_role_returns_negative(self, service):
        """Test empty role returns -1."""
        assert service.get_role_level("") == -1


class TestRoleComparison:
    """Test role comparison functionality."""

    @pytest.fixture
    def service(self):
        return RBACService(MagicMock(), AsyncMock())

    def test_super_admin_higher_than_owner(self, service):
        """Test super_admin is higher than owner."""
        assert service.has_higher_role("super_admin", "owner") is True

    def test_owner_higher_than_admin(self, service):
        """Test owner is higher than admin."""
        assert service.has_higher_role("owner", "admin") is True

    def test_admin_higher_than_member(self, service):
        """Test admin is higher than member."""
        assert service.has_higher_role("admin", "member") is True

    def test_member_higher_than_viewer(self, service):
        """Test member is higher than viewer."""
        assert service.has_higher_role("member", "viewer") is True

    def test_viewer_not_higher_than_member(self, service):
        """Test viewer is not higher than member."""
        assert service.has_higher_role("viewer", "member") is False

    def test_same_role_is_equal(self, service):
        """Test same role is equal (returns True)."""
        assert service.has_higher_role("admin", "admin") is True

    def test_unknown_role_not_higher(self, service):
        """Test unknown role is not higher than any role."""
        assert service.has_higher_role("unknown", "viewer") is False


class TestPermissionPatterns:
    """Test permission pattern matching."""

    @pytest.fixture
    def service(self):
        return RBACService(MagicMock(), AsyncMock())

    def test_super_admin_has_wildcard(self, service):
        """Test super_admin has wildcard permission."""
        assert "*" in service.PERMISSIONS["super_admin"]

    def test_owner_has_org_permissions(self, service):
        """Test owner has org permissions."""
        assert "org:*" in service.PERMISSIONS["owner"]

    def test_member_has_limited_permissions(self, service):
        """Test member has limited permissions."""
        permissions = service.PERMISSIONS["member"]
        assert "org:read" in permissions
        assert "org:*" not in permissions

    def test_viewer_has_read_only(self, service):
        """Test viewer has read-only permissions."""
        permissions = service.PERMISSIONS["viewer"]
        assert "org:read" in permissions
        assert len(permissions) == 2  # org:read and users:read:self

    def test_check_role_permission_super_admin(self, service):
        """Test super_admin has all permissions via wildcard."""
        assert service._check_role_permission("super_admin", "any:permission") is True
        assert service._check_role_permission("super_admin", "users:delete") is True

    def test_check_role_permission_owner(self, service):
        """Test owner has org permissions."""
        assert service._check_role_permission("owner", "org:read") is True
        assert service._check_role_permission("owner", "org:delete") is True

    def test_check_role_permission_member_limited(self, service):
        """Test member has limited permissions."""
        assert service._check_role_permission("member", "org:read") is True
        assert service._check_role_permission("member", "org:delete") is False

    def test_check_role_permission_unknown_role(self, service):
        """Test unknown role has no permissions."""
        assert service._check_role_permission("unknown", "org:read") is False


class TestPermissionMatching:
    """Test wildcard permission matching."""

    @pytest.fixture
    def service(self):
        return RBACService(MagicMock(), AsyncMock())

    def test_exact_match(self, service):
        """Test exact permission match."""
        assert service._match_permission("org:read", "org:read") is True

    def test_wildcard_match(self, service):
        """Test wildcard permission match."""
        assert service._match_permission("org:*", "org:read") is True
        assert service._match_permission("org:*", "org:delete") is True

    def test_global_wildcard(self, service):
        """Test global wildcard matches everything."""
        assert service._match_permission("*", "anything:here") is True
        assert service._match_permission("*", "users:delete:all") is True

    def test_no_match(self, service):
        """Test non-matching permissions."""
        assert service._match_permission("org:read", "users:read") is False

    def test_partial_no_match(self, service):
        """Test partial patterns don't match incorrectly."""
        assert service._match_permission("org:read", "org:read:extended") is False


class TestCheckPermission:
    """Test permission checking logic."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis

    @pytest.fixture
    def service(self, mock_db, mock_redis):
        return RBACService(mock_db, mock_redis)

    async def test_check_permission_cached_true(self, service, mock_redis):
        """Test permission check uses cache when available (true)."""
        mock_redis.get.return_value = "true"

        result = await service.check_permission(
            user_id=uuid4(), organization_id=uuid4(), permission="org:read"
        )

        assert result is True

    async def test_check_permission_cached_false(self, service, mock_redis):
        """Test permission check uses cache when available (false)."""
        mock_redis.get.return_value = "false"

        result = await service.check_permission(
            user_id=uuid4(), organization_id=uuid4(), permission="org:read"
        )

        assert result is False

    async def test_check_permission_no_role(self, service, mock_redis):
        """Test permission denied when user has no role."""
        mock_redis.get.return_value = None

        with patch.object(service, "get_user_role", return_value=None):
            result = await service.check_permission(
                user_id=uuid4(), organization_id=uuid4(), permission="org:read"
            )

        assert result is False

    async def test_check_permission_super_admin(self, service, mock_redis):
        """Test super_admin has all permissions."""
        mock_redis.get.return_value = None

        with patch.object(service, "get_user_role", return_value="super_admin"):
            result = await service.check_permission(
                user_id=uuid4(), organization_id=uuid4(), permission="any:permission"
            )

        assert result is True


class TestGetUserRole:
    """Test user role retrieval."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis

    @pytest.fixture
    def service(self, mock_db, mock_redis):
        return RBACService(mock_db, mock_redis)

    async def test_get_role_from_cache(self, service, mock_redis):
        """Test role retrieval from cache."""
        mock_redis.get.return_value = "admin"

        result = await service.get_user_role(uuid4(), uuid4())

        assert result == "admin"

    async def test_get_role_cached_null(self, service, mock_redis):
        """Test cached null role."""
        mock_redis.get.return_value = "null"

        result = await service.get_user_role(uuid4(), uuid4())

        assert result is None

    async def test_get_role_super_admin_user(self, service, mock_db, mock_redis):
        """Test super admin user gets super_admin role."""
        mock_redis.get.return_value = None
        mock_user = MagicMock()
        mock_user.is_super_admin = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = await service.get_user_role(uuid4(), uuid4())

        assert result == "super_admin"


class TestRBACPolicyModel:
    """Test RBACPolicy mock model."""

    def test_policy_has_id(self):
        """Test policy has id attribute."""
        assert hasattr(RBACPolicy, "id")

    def test_policy_has_name(self):
        """Test policy has name attribute."""
        assert hasattr(RBACPolicy, "name")

    def test_policy_has_resource_type(self):
        """Test policy has resource_type attribute."""
        assert hasattr(RBACPolicy, "resource_type")

    def test_policy_has_permission(self):
        """Test policy has permission attribute."""
        assert hasattr(RBACPolicy, "permission")

    def test_policy_default_effect(self):
        """Test policy default effect is allow."""
        assert RBACPolicy.effect == "allow"


class TestPermissionModel:
    """Test Permission mock model."""

    def test_permission_has_id(self):
        """Test permission has id attribute."""
        assert hasattr(Permission, "id")

    def test_permission_has_name(self):
        """Test permission has name attribute."""
        assert hasattr(Permission, "name")

    def test_permission_has_resource(self):
        """Test permission has resource attribute."""
        assert hasattr(Permission, "resource")

    def test_permission_has_action(self):
        """Test permission has action attribute."""
        assert hasattr(Permission, "action")


class TestServiceMethods:
    """Test service method existence and signatures."""

    @pytest.fixture
    def service(self):
        return RBACService(MagicMock(), AsyncMock())

    def test_has_check_permission(self, service):
        """Test service has check_permission method."""
        assert hasattr(service, "check_permission")
        import asyncio

        assert asyncio.iscoroutinefunction(service.check_permission)

    def test_has_get_user_role(self, service):
        """Test service has get_user_role method."""
        assert hasattr(service, "get_user_role")
        import asyncio

        assert asyncio.iscoroutinefunction(service.get_user_role)

    def test_has_get_user_permissions(self, service):
        """Test service has get_user_permissions method."""
        assert hasattr(service, "get_user_permissions")
        import asyncio

        assert asyncio.iscoroutinefunction(service.get_user_permissions)

    def test_has_create_policy(self, service):
        """Test service has create_policy method."""
        assert hasattr(service, "create_policy")
        import asyncio

        assert asyncio.iscoroutinefunction(service.create_policy)

    def test_has_update_policy(self, service):
        """Test service has update_policy method."""
        assert hasattr(service, "update_policy")
        import asyncio

        assert asyncio.iscoroutinefunction(service.update_policy)

    def test_has_delete_policy(self, service):
        """Test service has delete_policy method."""
        assert hasattr(service, "delete_policy")
        import asyncio

        assert asyncio.iscoroutinefunction(service.delete_policy)

    def test_has_enforce_permission(self, service):
        """Test service has enforce_permission method."""
        assert hasattr(service, "enforce_permission")
        import asyncio

        assert asyncio.iscoroutinefunction(service.enforce_permission)

    def test_has_bulk_check_permissions(self, service):
        """Test service has bulk_check_permissions method."""
        assert hasattr(service, "bulk_check_permissions")
        import asyncio

        assert asyncio.iscoroutinefunction(service.bulk_check_permissions)


class TestCacheBehavior:
    """Test caching behavior."""

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis

    @pytest.fixture
    def service(self, mock_redis):
        return RBACService(MagicMock(), mock_redis)

    async def test_permission_result_cached(self, service, mock_redis):
        """Test permission check result is cached."""
        mock_redis.get.return_value = None

        with patch.object(service, "get_user_role", return_value="admin"):
            await service.check_permission(
                user_id=uuid4(), organization_id=uuid4(), permission="org:read"
            )

        mock_redis.set.assert_called()

    async def test_cache_key_format(self, service, mock_redis):
        """Test cache key includes user, org, and permission."""
        user_id = uuid4()
        org_id = uuid4()
        permission = "org:read"

        mock_redis.get.return_value = None

        with patch.object(service, "get_user_role", return_value="admin"):
            await service.check_permission(
                user_id=user_id, organization_id=org_id, permission=permission
            )

        # Verify the cache key was used
        call_args = mock_redis.get.call_args[0][0]
        assert str(user_id) in call_args
        assert str(org_id) in call_args
        assert permission in call_args


class TestTimeRangeChecking:
    """Test time-based policy conditions."""

    @pytest.fixture
    def service(self):
        return RBACService(MagicMock(), AsyncMock())

    def test_time_range_within_range(self, service):
        """Test time range check when current time is within range."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        time_range = {
            "start": (now - timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=1)).isoformat(),
        }

        result = service._check_time_range(time_range)
        assert result is True

    def test_time_range_before_start(self, service):
        """Test time range check when current time is before start."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        time_range = {
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
        }

        result = service._check_time_range(time_range)
        assert result is False

    def test_time_range_after_end(self, service):
        """Test time range check when current time is after end."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        time_range = {
            "start": (now - timedelta(hours=2)).isoformat(),
            "end": (now - timedelta(hours=1)).isoformat(),
        }

        result = service._check_time_range(time_range)
        assert result is False

    def test_time_range_no_start(self, service):
        """Test time range with only end specified."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        time_range = {"end": (now + timedelta(hours=1)).isoformat()}

        result = service._check_time_range(time_range)
        assert result is True

    def test_time_range_no_end(self, service):
        """Test time range with only start specified."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        time_range = {"start": (now - timedelta(hours=1)).isoformat()}

        result = service._check_time_range(time_range)
        assert result is True

    def test_time_range_empty(self, service):
        """Test time range with no constraints."""
        result = service._check_time_range({})
        assert result is True


class TestPolicyEvaluation:
    """Test individual policy evaluation."""

    @pytest.fixture
    def service(self):
        return RBACService(MagicMock(), AsyncMock())

    def test_evaluate_policy_no_conditions(self, service):
        """Test policy with no conditions always matches."""
        policy = MagicMock()
        policy.conditions = None

        result = service._evaluate_policy(policy, uuid4(), None, {})
        assert result is True

    def test_evaluate_policy_user_id_match(self, service):
        """Test policy with matching user_id condition."""
        user_id = uuid4()
        policy = MagicMock()
        policy.conditions = {"user_id": str(user_id)}

        result = service._evaluate_policy(policy, user_id, None, {})
        assert result is True

    def test_evaluate_policy_user_id_mismatch(self, service):
        """Test policy with non-matching user_id condition."""
        policy = MagicMock()
        policy.conditions = {"user_id": str(uuid4())}

        result = service._evaluate_policy(policy, uuid4(), None, {})
        assert result is False

    def test_evaluate_policy_resource_id_match(self, service):
        """Test policy with matching resource_id condition."""
        resource_id = uuid4()
        policy = MagicMock()
        policy.conditions = {"resource_id": str(resource_id)}

        result = service._evaluate_policy(policy, uuid4(), resource_id, {})
        assert result is True

    def test_evaluate_policy_resource_id_mismatch(self, service):
        """Test policy with non-matching resource_id condition."""
        policy = MagicMock()
        policy.conditions = {"resource_id": str(uuid4())}

        result = service._evaluate_policy(policy, uuid4(), uuid4(), {})
        assert result is False

    def test_evaluate_policy_resource_id_none(self, service):
        """Test policy with resource_id condition but no resource provided."""
        policy = MagicMock()
        policy.conditions = {"resource_id": str(uuid4())}

        result = service._evaluate_policy(policy, uuid4(), None, {})
        assert result is False

    def test_evaluate_policy_custom_conditions_match(self, service):
        """Test policy with matching custom conditions."""
        policy = MagicMock()
        policy.conditions = {"custom": {"department": "engineering", "level": "senior"}}

        context = {"department": "engineering", "level": "senior"}
        result = service._evaluate_policy(policy, uuid4(), None, context)
        assert result is True

    def test_evaluate_policy_custom_conditions_mismatch(self, service):
        """Test policy with non-matching custom conditions."""
        policy = MagicMock()
        policy.conditions = {"custom": {"department": "engineering"}}

        context = {"department": "sales"}
        result = service._evaluate_policy(policy, uuid4(), None, context)
        assert result is False


class TestGetUserPermissions:
    """Test getting all user permissions."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        # Mock the query chain to return empty list for RBACPolicy queries
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        db.query.return_value = mock_query
        return db

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis

    @pytest.fixture
    def service(self, mock_db, mock_redis):
        return RBACService(mock_db, mock_redis)

    async def test_get_permissions_no_role(self, service):
        """Test getting permissions for user with no role."""
        with patch.object(service, "get_user_role", return_value=None):
            result = await service.get_user_permissions(uuid4(), uuid4())

        assert result == set()

    async def test_get_permissions_super_admin(self, service):
        """Test super_admin gets wildcard permission."""
        # Patch RBACPolicy to add missing attributes for SQLAlchemy filter
        with patch("app.services.rbac_service.RBACPolicy") as mock_policy_class:
            mock_policy_class.organization_id = MagicMock()
            mock_policy_class.is_active = MagicMock()
            with patch.object(service, "get_user_role", return_value="super_admin"):
                result = await service.get_user_permissions(uuid4(), uuid4())

        assert "*" in result

    async def test_get_permissions_owner(self, service):
        """Test owner gets organization-wide permissions."""
        # Patch RBACPolicy to add missing attributes for SQLAlchemy filter
        with patch("app.services.rbac_service.RBACPolicy") as mock_policy_class:
            mock_policy_class.organization_id = MagicMock()
            mock_policy_class.is_active = MagicMock()
            with patch.object(service, "get_user_role", return_value="owner"):
                result = await service.get_user_permissions(uuid4(), uuid4())

        assert "org:*" in result
        assert "users:*" in result
        assert "billing:*" in result

    async def test_get_permissions_viewer(self, service):
        """Test viewer gets read-only permissions."""
        # Patch RBACPolicy to add missing attributes for SQLAlchemy filter
        with patch("app.services.rbac_service.RBACPolicy") as mock_policy_class:
            mock_policy_class.organization_id = MagicMock()
            mock_policy_class.is_active = MagicMock()
            with patch.object(service, "get_user_role", return_value="viewer"):
                result = await service.get_user_permissions(uuid4(), uuid4())

        assert "org:read" in result
        assert "users:read:self" in result
        assert len(result) == 2

    async def test_get_permissions_no_org(self, service):
        """Test getting permissions without organization returns base permissions."""
        with patch.object(service, "get_user_role", return_value="member"):
            result = await service.get_user_permissions(uuid4(), None)

        assert "org:read" in result
        assert "users:read" in result


class TestEnforcePermission:
    """Test permission enforcement with HTTP exceptions."""

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis

    @pytest.fixture
    def service(self, mock_redis):
        return RBACService(MagicMock(), mock_redis)

    async def test_enforce_permission_granted(self, service):
        """Test enforce_permission allows when permission granted."""
        from fastapi import HTTPException

        with patch.object(service, "check_permission", return_value=True):
            # Should not raise
            await service.enforce_permission(uuid4(), uuid4(), "org:read")

    async def test_enforce_permission_denied(self, service):
        """Test enforce_permission raises when permission denied."""
        from fastapi import HTTPException

        with patch.object(service, "check_permission", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await service.enforce_permission(uuid4(), uuid4(), "org:delete")

            assert exc_info.value.status_code == 403


class TestWildcardPermissions:
    """Test advanced wildcard permission patterns."""

    @pytest.fixture
    def service(self):
        return RBACService(MagicMock(), AsyncMock())

    def test_match_exact_permission(self, service):
        """Test exact permission match."""
        assert service._match_permission("org:read", "org:read") is True
        assert service._match_permission("org:read", "org:write") is False

    def test_match_single_wildcard(self, service):
        """Test single wildcard permission."""
        assert service._match_permission("org:*", "org:read") is True
        assert service._match_permission("org:*", "org:write") is True
        assert service._match_permission("org:*", "users:read") is False

    def test_match_global_wildcard(self, service):
        """Test global wildcard matches everything."""
        assert service._match_permission("*", "org:read") is True
        assert service._match_permission("*", "users:delete") is True
        assert service._match_permission("*", "anything:here:nested") is True

    def test_match_nested_wildcards(self, service):
        """Test nested permission patterns."""
        assert service._match_permission("users:read:*", "users:read:self") is True
        assert service._match_permission("users:read:*", "users:read:all") is True
        assert service._match_permission("users:read:*", "users:write:self") is False

    def test_match_no_partial_match(self, service):
        """Test that partial strings don't match incorrectly."""
        assert service._match_permission("org", "organization") is False
        assert service._match_permission("user", "users:read") is False
