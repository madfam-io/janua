"""
Comprehensive Policy Engine Test Suite
Tests for OPA-compatible authorization policy evaluation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_policy_engine():
    """Create a PolicyEngine with mocked dependencies."""
    with patch("app.services.policy_engine.CacheService"):
        with patch("app.services.policy_engine.AuditLogger"):
            from app.services.policy_engine import PolicyEngine
            mock_db = MagicMock()
            mock_cache = MagicMock()
            engine = PolicyEngine(db=mock_db, cache=mock_cache)
            return engine


class TestPolicyEngineInitialization:
    """Test PolicyEngine initialization."""

    def test_initialization_with_db(self):
        """Test engine initializes with database session."""
        with patch("app.services.policy_engine.CacheService"):
            with patch("app.services.policy_engine.AuditLogger"):
                from app.services.policy_engine import PolicyEngine
                mock_db = MagicMock()
                engine = PolicyEngine(db=mock_db)
                assert engine.db is mock_db

    def test_initialization_with_custom_cache(self):
        """Test engine initializes with custom cache."""
        with patch("app.services.policy_engine.AuditLogger"):
            from app.services.policy_engine import PolicyEngine
            mock_db = MagicMock()
            mock_cache = MagicMock()
            engine = PolicyEngine(db=mock_db, cache=mock_cache)
            assert engine.cache is mock_cache


class TestMatchesPattern:
    """Test pattern matching functionality."""

    def test_exact_match(self, mock_policy_engine):
        """Test exact string matching."""
        assert mock_policy_engine._matches_pattern("users:read", "users:read") is True
        assert mock_policy_engine._matches_pattern("users:read", "users:write") is False

    def test_wildcard_star(self, mock_policy_engine):
        """Test asterisk wildcard matching."""
        assert mock_policy_engine._matches_pattern("users:read", "users:*") is True
        assert mock_policy_engine._matches_pattern("users:write", "users:*") is True
        assert mock_policy_engine._matches_pattern("posts:read", "users:*") is False

    def test_wildcard_start(self, mock_policy_engine):
        """Test wildcard at start of pattern."""
        assert mock_policy_engine._matches_pattern("admin:users", "*:users") is True
        assert mock_policy_engine._matches_pattern("super:users", "*:users") is True
        assert mock_policy_engine._matches_pattern("admin:posts", "*:users") is False

    def test_wildcard_double(self, mock_policy_engine):
        """Test double wildcard pattern."""
        assert mock_policy_engine._matches_pattern("org:team:user", "*:*:*") is True
        assert mock_policy_engine._matches_pattern("a:b:c", "*:*:*") is True

    def test_question_mark_wildcard(self, mock_policy_engine):
        """Test question mark single-char wildcard."""
        assert mock_policy_engine._matches_pattern("user1", "user?") is True
        assert mock_policy_engine._matches_pattern("user12", "user?") is False

    def test_empty_values(self, mock_policy_engine):
        """Test empty values."""
        assert mock_policy_engine._matches_pattern("", "") is True
        assert mock_policy_engine._matches_pattern("test", "") is False
        assert mock_policy_engine._matches_pattern("", "test") is False


class TestIpInRange:
    """Test IP address range checking."""

    def test_exact_ip_match(self, mock_policy_engine):
        """Test exact IP address match."""
        assert mock_policy_engine._ip_in_range("192.168.1.1", "192.168.1.1") is True
        assert mock_policy_engine._ip_in_range("192.168.1.1", "192.168.1.2") is False

    def test_cidr_range_match(self, mock_policy_engine):
        """Test CIDR range matching."""
        assert mock_policy_engine._ip_in_range("192.168.1.50", "192.168.1.0/24") is True
        assert mock_policy_engine._ip_in_range("192.168.2.50", "192.168.1.0/24") is False

    def test_different_subnets(self, mock_policy_engine):
        """Test different subnet ranges."""
        assert mock_policy_engine._ip_in_range("10.0.0.1", "10.0.0.0/8") is True
        assert mock_policy_engine._ip_in_range("172.16.0.1", "10.0.0.0/8") is False


class TestGenerateCacheKey:
    """Test cache key generation."""

    def test_cache_key_basic(self, mock_policy_engine):
        """Test basic cache key generation."""
        request = MagicMock()
        request.subject = "user-123"
        request.action = "read"
        request.resource = "documents"
        request.context = None

        key = mock_policy_engine._generate_cache_key(request, "tenant-456")

        assert key.startswith("policy:eval:")
        assert len(key) > len("policy:eval:")

    def test_cache_key_with_context(self, mock_policy_engine):
        """Test cache key includes context."""
        request = MagicMock()
        request.subject = "user-123"
        request.action = "read"
        request.resource = "documents"
        request.context = {"ip": "192.168.1.1"}

        key = mock_policy_engine._generate_cache_key(request, "tenant-456")

        assert key.startswith("policy:eval:")

    def test_cache_key_deterministic(self, mock_policy_engine):
        """Test cache key is deterministic."""
        request = MagicMock()
        request.subject = "user-123"
        request.action = "read"
        request.resource = "documents"
        request.context = None

        key1 = mock_policy_engine._generate_cache_key(request, "tenant-456")
        key2 = mock_policy_engine._generate_cache_key(request, "tenant-456")

        assert key1 == key2

    def test_different_requests_different_keys(self, mock_policy_engine):
        """Test different requests produce different keys."""
        request1 = MagicMock()
        request1.subject = "user-123"
        request1.action = "read"
        request1.resource = "documents"
        request1.context = None

        request2 = MagicMock()
        request2.subject = "user-456"
        request2.action = "read"
        request2.resource = "documents"
        request2.context = None

        key1 = mock_policy_engine._generate_cache_key(request1, "tenant-456")
        key2 = mock_policy_engine._generate_cache_key(request2, "tenant-456")

        assert key1 != key2


class TestEvaluateConditions:
    """Test policy conditions evaluation."""

    async def test_empty_conditions(self, mock_policy_engine):
        """Test empty conditions always pass."""
        result = await mock_policy_engine._evaluate_conditions({}, {})
        assert result is True

    async def test_mfa_required_with_mfa(self, mock_policy_engine):
        """Test MFA condition with MFA verified."""
        conditions = {"mfa_required": True}
        context = {"mfa_verified": True}

        result = await mock_policy_engine._evaluate_conditions(conditions, context)
        assert result is True

    async def test_mfa_required_without_mfa(self, mock_policy_engine):
        """Test MFA condition without MFA verification."""
        conditions = {"mfa_required": True}
        context = {"mfa_verified": False}

        result = await mock_policy_engine._evaluate_conditions(conditions, context)
        assert result is False

    async def test_mfa_required_missing_context(self, mock_policy_engine):
        """Test MFA condition with missing context."""
        conditions = {"mfa_required": True}
        context = {}

        result = await mock_policy_engine._evaluate_conditions(conditions, context)
        assert result is False

    async def test_attributes_match(self, mock_policy_engine):
        """Test attribute matching conditions."""
        conditions = {"attributes": {"department": "engineering", "level": "senior"}}
        context = {"department": "engineering", "level": "senior"}

        result = await mock_policy_engine._evaluate_conditions(conditions, context)
        assert result is True

    async def test_attributes_mismatch(self, mock_policy_engine):
        """Test attribute mismatch."""
        conditions = {"attributes": {"department": "engineering"}}
        context = {"department": "marketing"}

        result = await mock_policy_engine._evaluate_conditions(conditions, context)
        assert result is False

    async def test_ip_range_in_range(self, mock_policy_engine):
        """Test IP range condition when IP is in range."""
        conditions = {"ip_range": "192.168.1.0/24"}
        context = {"client_ip": "192.168.1.50"}

        result = await mock_policy_engine._evaluate_conditions(conditions, context)
        assert result is True

    async def test_ip_range_out_of_range(self, mock_policy_engine):
        """Test IP range condition when IP is out of range."""
        conditions = {"ip_range": "192.168.1.0/24"}
        context = {"client_ip": "10.0.0.1"}

        result = await mock_policy_engine._evaluate_conditions(conditions, context)
        assert result is False

    async def test_ip_range_missing_ip(self, mock_policy_engine):
        """Test IP range condition with missing IP."""
        conditions = {"ip_range": "192.168.1.0/24"}
        context = {}

        result = await mock_policy_engine._evaluate_conditions(conditions, context)
        assert result is False


class TestEvaluateRules:
    """Test policy rules evaluation."""

    async def test_empty_rules(self, mock_policy_engine):
        """Test empty rules always pass."""
        request = MagicMock()
        result = await mock_policy_engine._evaluate_rules({}, request)
        assert result is True

    async def test_allow_subject_match(self, mock_policy_engine):
        """Test allow rule with matching subject."""
        rules = {"allow": {"subject": "user-*"}}
        request = MagicMock()
        request.subject = "user-123"

        result = await mock_policy_engine._evaluate_rules(rules, request)
        assert result is True

    async def test_allow_subject_no_match(self, mock_policy_engine):
        """Test allow rule with non-matching subject."""
        rules = {"allow": {"subject": "admin-*"}}
        request = MagicMock()
        request.subject = "user-123"

        result = await mock_policy_engine._evaluate_rules(rules, request)
        assert result is False

    async def test_allow_action_match(self, mock_policy_engine):
        """Test allow rule with matching action."""
        rules = {"allow": {"action": "read"}}
        request = MagicMock()
        request.action = "read"

        result = await mock_policy_engine._evaluate_rules(rules, request)
        assert result is True

    async def test_allow_action_no_match(self, mock_policy_engine):
        """Test allow rule with non-matching action."""
        rules = {"allow": {"action": "read"}}
        request = MagicMock()
        request.action = "write"

        result = await mock_policy_engine._evaluate_rules(rules, request)
        assert result is False

    async def test_allow_resource_match(self, mock_policy_engine):
        """Test allow rule with matching resource."""
        rules = {"allow": {"resource": "documents/*"}}
        request = MagicMock()
        request.resource = "documents/123"

        result = await mock_policy_engine._evaluate_rules(rules, request)
        assert result is True

    async def test_deny_subject_match(self, mock_policy_engine):
        """Test deny rule with matching subject."""
        rules = {"deny": {"subject": "blocked-*"}}
        request = MagicMock()
        request.subject = "blocked-user"

        result = await mock_policy_engine._evaluate_rules(rules, request)
        assert result is False

    async def test_deny_action_match(self, mock_policy_engine):
        """Test deny rule with matching action."""
        rules = {"deny": {"action": "delete"}}
        request = MagicMock()
        request.action = "delete"

        result = await mock_policy_engine._evaluate_rules(rules, request)
        assert result is False


class TestEvaluateSinglePolicy:
    """Test single policy evaluation."""

    async def test_policy_without_actions(self, mock_policy_engine):
        """Test policy without action restrictions."""
        policy = MagicMock()
        policy.actions = None
        policy.resource_pattern = None
        policy.conditions = None
        policy.rules = None

        request = MagicMock()
        request.action = "read"
        request.resource = "documents"
        request.context = {}

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is True

    async def test_policy_action_match(self, mock_policy_engine):
        """Test policy with matching action."""
        policy = MagicMock()
        policy.actions = ["read", "write"]
        policy.resource_pattern = None
        policy.conditions = None
        policy.rules = None

        request = MagicMock()
        request.action = "read"
        request.resource = "documents"
        request.context = {}

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is True

    async def test_policy_action_no_match(self, mock_policy_engine):
        """Test policy with non-matching action."""
        policy = MagicMock()
        policy.actions = ["read"]
        policy.resource_pattern = None
        policy.conditions = None
        policy.rules = None

        request = MagicMock()
        request.action = "delete"

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is False
        assert "not in policy actions" in reason

    async def test_policy_resource_pattern_match(self, mock_policy_engine):
        """Test policy with matching resource pattern."""
        policy = MagicMock()
        policy.actions = None
        policy.resource_pattern = "documents/*"
        policy.conditions = None
        policy.rules = None

        request = MagicMock()
        request.resource = "documents/123"
        request.context = {}

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is True

    async def test_policy_resource_pattern_no_match(self, mock_policy_engine):
        """Test policy with non-matching resource pattern."""
        policy = MagicMock()
        policy.actions = None
        policy.resource_pattern = "documents/*"
        policy.conditions = None
        policy.rules = None

        request = MagicMock()
        request.resource = "users/123"

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is False
        assert "doesn't match pattern" in reason

    async def test_policy_conditions_met(self, mock_policy_engine):
        """Test policy with conditions that are met."""
        policy = MagicMock()
        policy.actions = None
        policy.resource_pattern = None
        policy.conditions = {"mfa_required": True}
        policy.rules = None

        request = MagicMock()
        request.context = {"mfa_verified": True}

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is True

    async def test_policy_conditions_not_met(self, mock_policy_engine):
        """Test policy with conditions that are not met."""
        policy = MagicMock()
        policy.actions = None
        policy.resource_pattern = None
        policy.conditions = {"mfa_required": True}
        policy.rules = None

        request = MagicMock()
        request.context = {"mfa_verified": False}

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is False
        assert "Conditions not met" in reason

    async def test_policy_rules_pass(self, mock_policy_engine):
        """Test policy with passing rules."""
        policy = MagicMock()
        policy.actions = None
        policy.resource_pattern = None
        policy.conditions = None
        policy.rules = {"allow": {"subject": "user-*"}}

        request = MagicMock()
        request.subject = "user-123"
        request.context = {}

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is True

    async def test_policy_rules_fail(self, mock_policy_engine):
        """Test policy with failing rules."""
        policy = MagicMock()
        policy.actions = None
        policy.resource_pattern = None
        policy.conditions = None
        policy.rules = {"allow": {"subject": "admin-*"}}

        request = MagicMock()
        request.subject = "user-123"
        request.context = {}

        result, reason = await mock_policy_engine._evaluate_single_policy(policy, request)
        assert result is False


class TestEvaluate:
    """Test main evaluate method."""

    @pytest.fixture
    def engine_with_async_cache(self):
        """Create PolicyEngine with async cache mock."""
        with patch("app.services.policy_engine.CacheService"):
            with patch("app.services.policy_engine.AuditLogger"):
                from app.services.policy_engine import PolicyEngine
                mock_db = MagicMock()
                mock_cache = AsyncMock()
                mock_cache.get = AsyncMock(return_value=None)
                mock_cache.set = AsyncMock()
                engine = PolicyEngine(db=mock_db, cache=mock_cache)
                return engine

    async def test_evaluate_no_policies(self, engine_with_async_cache):
        """Test evaluate with no applicable policies."""
        request = MagicMock()
        request.subject = "user-123"
        request.action = "read"
        request.resource = "documents"
        request.context = None

        with patch.object(engine_with_async_cache, "_get_applicable_policies", return_value=[]):
            with patch.object(engine_with_async_cache, "_log_evaluation", return_value=None):
                response = await engine_with_async_cache.evaluate(request, "tenant-456")

        assert response.allowed is False

    async def test_evaluate_with_cache_hit(self, engine_with_async_cache):
        """Test evaluate returns cached result from cache."""
        request = MagicMock()
        request.subject = "user-123"
        request.action = "read"
        request.resource = "documents"
        request.context = None

        # Use a cached response matching the PolicyEvaluateResponse model schema
        cached_response = '{"allowed": true, "matched_policies": [], "denied_by": null, "reason": "cached result", "metadata": {}}'
        engine_with_async_cache.cache.get = AsyncMock(return_value=cached_response)

        response = await engine_with_async_cache.evaluate(request, "tenant-456")

        # The response should have allowed=True from cache
        assert response.allowed is True


class TestCompileToWasm:
    """Test WASM compilation functionality."""

    async def test_compile_opa_not_available(self, mock_policy_engine):
        """Test compilation when OPA is not available."""
        policy = MagicMock()
        policy.rego_code = "package test\ndefault allow = false"
        policy.name = "test_policy"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = await mock_policy_engine.compile_to_wasm(policy)

        assert result is None

    async def test_compile_timeout(self, mock_policy_engine):
        """Test compilation timeout."""
        import subprocess

        policy = MagicMock()
        policy.rego_code = "package test"
        policy.name = "test_policy"

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("opa", 5)):
            result = await mock_policy_engine.compile_to_wasm(policy)

        assert result is None

    async def test_compile_general_error(self, mock_policy_engine):
        """Test compilation general error."""
        policy = MagicMock()
        policy.rego_code = "package test"
        policy.name = "test_policy"

        with patch("subprocess.run", side_effect=Exception("Unexpected error")):
            result = await mock_policy_engine.compile_to_wasm(policy)

        assert result is None


class TestGetUserPermissions:
    """Test getting user permissions."""

    def test_get_permissions_no_roles(self):
        """Test getting permissions for user with no roles."""
        with patch("app.services.policy_engine.CacheService"):
            with patch("app.services.policy_engine.AuditLogger"):
                from app.services.policy_engine import PolicyEngine

                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.all.return_value = []

                engine = PolicyEngine(db=mock_db, cache=MagicMock())
                engine.get_user_permissions.cache_clear()

                permissions = engine.get_user_permissions("user-123", "tenant-456")
                assert permissions == []

    def test_get_permissions_with_roles(self):
        """Test getting permissions for user with roles."""
        with patch("app.services.policy_engine.CacheService"):
            with patch("app.services.policy_engine.AuditLogger"):
                from app.services.policy_engine import PolicyEngine

                mock_db = MagicMock()

                mock_user_role = MagicMock()
                mock_user_role.role_id = "role-1"

                mock_role = MagicMock()
                mock_role.permissions = ["read", "write"]

                def query_side_effect(model):
                    query_mock = MagicMock()
                    filter_mock = MagicMock()
                    filter_mock.all.return_value = [mock_user_role]
                    filter_mock.first.return_value = mock_role
                    query_mock.filter.return_value = filter_mock
                    return query_mock

                mock_db.query.side_effect = query_side_effect

                engine = PolicyEngine(db=mock_db, cache=MagicMock())
                engine.get_user_permissions.cache_clear()

                permissions = engine.get_user_permissions("user-123", "tenant-456")

                assert "read" in permissions
                assert "write" in permissions


class TestServiceMethodExistence:
    """Test service method existence and signatures."""

    def test_has_evaluate(self, mock_policy_engine):
        """Test engine has evaluate method."""
        assert hasattr(mock_policy_engine, "evaluate")
        import asyncio
        assert asyncio.iscoroutinefunction(mock_policy_engine.evaluate)

    def test_has_get_applicable_policies(self, mock_policy_engine):
        """Test engine has _get_applicable_policies method."""
        assert hasattr(mock_policy_engine, "_get_applicable_policies")
        import asyncio
        assert asyncio.iscoroutinefunction(mock_policy_engine._get_applicable_policies)

    def test_has_evaluate_single_policy(self, mock_policy_engine):
        """Test engine has _evaluate_single_policy method."""
        assert hasattr(mock_policy_engine, "_evaluate_single_policy")
        import asyncio
        assert asyncio.iscoroutinefunction(mock_policy_engine._evaluate_single_policy)

    def test_has_evaluate_conditions(self, mock_policy_engine):
        """Test engine has _evaluate_conditions method."""
        assert hasattr(mock_policy_engine, "_evaluate_conditions")
        import asyncio
        assert asyncio.iscoroutinefunction(mock_policy_engine._evaluate_conditions)

    def test_has_evaluate_rules(self, mock_policy_engine):
        """Test engine has _evaluate_rules method."""
        assert hasattr(mock_policy_engine, "_evaluate_rules")
        import asyncio
        assert asyncio.iscoroutinefunction(mock_policy_engine._evaluate_rules)

    def test_has_matches_pattern(self, mock_policy_engine):
        """Test engine has _matches_pattern method."""
        assert hasattr(mock_policy_engine, "_matches_pattern")
        assert callable(mock_policy_engine._matches_pattern)

    def test_has_ip_in_range(self, mock_policy_engine):
        """Test engine has _ip_in_range method."""
        assert hasattr(mock_policy_engine, "_ip_in_range")
        assert callable(mock_policy_engine._ip_in_range)

    def test_has_generate_cache_key(self, mock_policy_engine):
        """Test engine has _generate_cache_key method."""
        assert hasattr(mock_policy_engine, "_generate_cache_key")
        assert callable(mock_policy_engine._generate_cache_key)

    def test_has_log_evaluation(self, mock_policy_engine):
        """Test engine has _log_evaluation method."""
        assert hasattr(mock_policy_engine, "_log_evaluation")
        import asyncio
        assert asyncio.iscoroutinefunction(mock_policy_engine._log_evaluation)

    def test_has_compile_to_wasm(self, mock_policy_engine):
        """Test engine has compile_to_wasm method."""
        assert hasattr(mock_policy_engine, "compile_to_wasm")
        import asyncio
        assert asyncio.iscoroutinefunction(mock_policy_engine.compile_to_wasm)

    def test_has_get_user_permissions(self, mock_policy_engine):
        """Test engine has get_user_permissions method."""
        assert hasattr(mock_policy_engine, "get_user_permissions")
        assert callable(mock_policy_engine.get_user_permissions)


class TestPolicyEngineAttributes:
    """Test PolicyEngine attributes."""

    def test_has_db(self, mock_policy_engine):
        """Test engine has db attribute."""
        assert hasattr(mock_policy_engine, "db")

    def test_has_cache(self, mock_policy_engine):
        """Test engine has cache attribute."""
        assert hasattr(mock_policy_engine, "cache")

    def test_has_audit_logger(self, mock_policy_engine):
        """Test engine has audit_logger attribute."""
        assert hasattr(mock_policy_engine, "audit_logger")
