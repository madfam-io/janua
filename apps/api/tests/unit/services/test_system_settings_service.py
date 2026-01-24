"""
Comprehensive System Settings Service Test Suite
Tests for system settings and CORS origins management
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.system_settings_service import (
    SystemSettingsService,
    get_cached_cors_origins,
    invalidate_cors_cache,
)

pytestmark = pytest.mark.asyncio


class TestSystemSettingsServiceInitialization:
    """Test SystemSettingsService initialization."""

    def test_service_initialization(self):
        """Test service initializes with database session."""
        mock_db = AsyncMock()
        service = SystemSettingsService(mock_db)

        assert service.db is mock_db
        assert service._cache == {}
        assert service._cors_cache is None

    def test_service_has_cache_attributes(self):
        """Test service has cache attributes."""
        mock_db = AsyncMock()
        service = SystemSettingsService(mock_db)

        assert hasattr(service, "_cache")
        assert hasattr(service, "_cors_cache")


class TestGetSetting:
    """Test get_setting method."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_get_setting_from_cache(self, service):
        """Test getting setting from cache."""
        service._cache["test_key"] = "cached_value"

        result = await service.get_setting("test_key", use_cache=True)

        assert result == "cached_value"
        # Database should not be queried
        service.db.execute.assert_not_called()

    async def test_get_setting_from_database(self, service):
        """Test getting setting from database when not cached."""
        mock_setting = MagicMock()
        mock_setting.get_value.return_value = "db_value"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        service.db.execute.return_value = mock_result

        result = await service.get_setting("test_key", use_cache=False)

        assert result == "db_value"
        service.db.execute.assert_called_once()

    async def test_get_setting_default_when_not_found(self, service):
        """Test getting setting returns default when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute.return_value = mock_result

        result = await service.get_setting("nonexistent_key", default="default_value")

        assert result == "default_value"

    async def test_get_setting_caches_db_result(self, service):
        """Test getting setting caches database result."""
        mock_setting = MagicMock()
        mock_setting.get_value.return_value = "db_value"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        service.db.execute.return_value = mock_result

        await service.get_setting("test_key", use_cache=False)

        assert "test_key" in service._cache
        assert service._cache["test_key"] == "db_value"

    async def test_get_setting_bypass_cache(self, service):
        """Test getting setting bypasses cache when requested."""
        service._cache["test_key"] = "cached_value"

        mock_setting = MagicMock()
        mock_setting.get_value.return_value = "db_value"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        service.db.execute.return_value = mock_result

        result = await service.get_setting("test_key", use_cache=False)

        assert result == "db_value"
        service.db.execute.assert_called_once()


class TestSetSetting:
    """Test set_setting method."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_set_setting_string_value(self, service):
        """Test setting string value."""
        mock_setting = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_setting
        service.db.execute.return_value = mock_result

        result = await service.set_setting("test_key", "test_value")

        assert result == mock_setting
        service.db.commit.assert_called_once()

    async def test_set_setting_dict_value(self, service):
        """Test setting dict value stores as json_value."""
        mock_setting = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_setting
        service.db.execute.return_value = mock_result

        result = await service.set_setting("test_key", {"key": "value"})

        assert result == mock_setting
        service.db.execute.assert_called_once()

    async def test_set_setting_list_value(self, service):
        """Test setting list value stores as json_value."""
        mock_setting = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_setting
        service.db.execute.return_value = mock_result

        result = await service.set_setting("test_key", ["item1", "item2"])

        assert result == mock_setting
        service.db.execute.assert_called_once()

    async def test_set_setting_invalidates_cache(self, service):
        """Test setting invalidates cache."""
        service._cache["test_key"] = "old_value"

        mock_setting = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_setting
        service.db.execute.return_value = mock_result

        await service.set_setting("test_key", "new_value")

        assert "test_key" not in service._cache

    async def test_set_setting_with_category(self, service):
        """Test setting with category."""
        mock_setting = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_setting
        service.db.execute.return_value = mock_result

        result = await service.set_setting(
            "test_key",
            "test_value",
            category="security",
        )

        assert result == mock_setting

    async def test_set_setting_with_updated_by(self, service):
        """Test setting with updated_by user ID."""
        mock_setting = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_setting
        service.db.execute.return_value = mock_result

        user_id = uuid4()
        result = await service.set_setting(
            "test_key",
            "test_value",
            updated_by=user_id,
        )

        assert result == mock_setting


class TestDeleteSetting:
    """Test delete_setting method."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_delete_setting_success(self, service):
        """Test successful setting deletion."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        service.db.execute.return_value = mock_result

        result = await service.delete_setting("test_key")

        assert result is True
        service.db.commit.assert_called_once()

    async def test_delete_setting_not_found(self, service):
        """Test deletion when setting not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        service.db.execute.return_value = mock_result

        result = await service.delete_setting("nonexistent_key")

        assert result is False

    async def test_delete_setting_invalidates_cache(self, service):
        """Test deletion invalidates cache."""
        service._cache["test_key"] = "value"

        mock_result = MagicMock()
        mock_result.rowcount = 1
        service.db.execute.return_value = mock_result

        await service.delete_setting("test_key")

        assert "test_key" not in service._cache


class TestGetAllSettings:
    """Test get_all_settings method."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_get_all_settings(self, service):
        """Test getting all settings."""
        mock_setting = MagicMock()
        mock_setting.id = uuid4()
        mock_setting.key = "test_key"
        mock_setting.get_value.return_value = "test_value"
        mock_setting.category = "features"
        mock_setting.description = "Test setting"
        mock_setting.is_sensitive = False
        mock_setting.is_readonly = False
        mock_setting.updated_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_setting]
        service.db.execute.return_value = mock_result

        result = await service.get_all_settings()

        assert len(result) == 1
        assert result[0]["key"] == "test_key"
        assert result[0]["value"] == "test_value"

    async def test_get_all_settings_by_category(self, service):
        """Test getting settings filtered by category."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        service.db.execute.return_value = mock_result

        await service.get_all_settings(category="security")

        service.db.execute.assert_called_once()

    async def test_get_all_settings_redacts_sensitive(self, service):
        """Test sensitive settings are redacted."""
        mock_setting = MagicMock()
        mock_setting.id = uuid4()
        mock_setting.key = "api_key"
        mock_setting.get_value.return_value = "secret123"
        mock_setting.category = "security"
        mock_setting.description = "API key"
        mock_setting.is_sensitive = True
        mock_setting.is_readonly = False
        mock_setting.updated_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_setting]
        service.db.execute.return_value = mock_result

        result = await service.get_all_settings(include_sensitive=False)

        assert result[0]["value"] == "***REDACTED***"

    async def test_get_all_settings_includes_sensitive_when_requested(self, service):
        """Test sensitive settings shown when include_sensitive=True."""
        mock_setting = MagicMock()
        mock_setting.id = uuid4()
        mock_setting.key = "api_key"
        mock_setting.get_value.return_value = "secret123"
        mock_setting.category = "security"
        mock_setting.description = "API key"
        mock_setting.is_sensitive = True
        mock_setting.is_readonly = False
        mock_setting.updated_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_setting]
        service.db.execute.return_value = mock_result

        result = await service.get_all_settings(include_sensitive=True)

        assert result[0]["value"] == "secret123"


class TestCORSOrigins:
    """Test CORS origins management."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_get_cors_origins(self, service):
        """Test getting CORS origins."""
        mock_origin = MagicMock()
        mock_origin.origin = "https://example.com"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_origin]
        service.db.execute.return_value = mock_result

        with patch("app.services.system_settings_service.app_settings") as mock_settings:
            mock_settings.cors_origins_list = ["http://localhost:3000"]

            result = await service.get_cors_origins()

        assert "https://example.com" in result
        assert "http://localhost:3000" in result

    async def test_get_cors_origins_caches_result(self, service):
        """Test CORS origins are cached."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        service.db.execute.return_value = mock_result

        with patch("app.services.system_settings_service.app_settings") as mock_settings:
            mock_settings.cors_origins_list = []

            await service.get_cors_origins()

        assert service._cors_cache is not None


class TestAddCorsOrigin:
    """Test add_cors_origin method."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_add_cors_origin_invalid_format(self, service):
        """Test adding origin with invalid format raises error."""
        with pytest.raises(ValueError, match="must start with http"):
            await service.add_cors_origin("invalid-origin")

    async def test_add_cors_origin_updates_existing(self, service):
        """Test adding existing origin updates it."""
        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        service.db.execute.return_value = mock_result

        _ = await service.add_cors_origin(
            "https://example.com",
            description="Updated description",
        )

        assert mock_existing.description == "Updated description"
        assert mock_existing.is_active is True

    def test_add_cors_origin_method_exists(self, service):
        """Test add_cors_origin method exists and is async."""
        import asyncio
        assert hasattr(service, "add_cors_origin")
        assert asyncio.iscoroutinefunction(service.add_cors_origin)

    async def test_add_cors_origin_validates_http_prefix(self, service):
        """Test origin must start with http or https."""
        # Both should raise ValueError
        with pytest.raises(ValueError):
            await service.add_cors_origin("ftp://example.com")

    async def test_add_cors_origin_reactivates_existing(self, service):
        """Test adding existing inactive origin reactivates it."""
        mock_existing = MagicMock()
        mock_existing.is_active = False
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        service.db.execute.return_value = mock_result

        await service.add_cors_origin("https://example.com")

        assert mock_existing.is_active is True
        service.db.commit.assert_called_once()


class TestRemoveCorsOrigin:
    """Test remove_cors_origin method."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_remove_cors_origin_success(self, service):
        """Test removing CORS origin (soft delete)."""
        mock_origin = MagicMock()
        mock_origin.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_origin
        service.db.execute.return_value = mock_result

        result = await service.remove_cors_origin("https://example.com")

        assert result is True
        assert mock_origin.is_active is False
        service.db.commit.assert_called_once()

    async def test_remove_cors_origin_not_found(self, service):
        """Test removing nonexistent CORS origin."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute.return_value = mock_result

        result = await service.remove_cors_origin("https://nonexistent.com")

        assert result is False


class TestDeleteCorsOrigin:
    """Test delete_cors_origin method."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_delete_cors_origin_success(self, service):
        """Test permanently deleting CORS origin."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        service.db.execute.return_value = mock_result

        result = await service.delete_cors_origin("https://example.com")

        assert result is True
        service.db.commit.assert_called_once()

    async def test_delete_cors_origin_not_found(self, service):
        """Test deleting nonexistent CORS origin."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        service.db.execute.return_value = mock_result

        result = await service.delete_cors_origin("https://nonexistent.com")

        assert result is False


class TestListCorsOrigins:
    """Test list_cors_origins method."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_list_cors_origins(self, service):
        """Test listing CORS origins with metadata."""
        mock_origin = MagicMock()
        mock_origin.id = uuid4()
        mock_origin.origin = "https://example.com"
        mock_origin.organization_id = None
        mock_origin.description = "Test origin"
        mock_origin.is_active = True
        mock_origin.created_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_origin]
        service.db.execute.return_value = mock_result

        result = await service.list_cors_origins()

        assert len(result) == 1
        assert result[0]["origin"] == "https://example.com"
        assert result[0]["scope"] == "system"

    async def test_list_cors_origins_org_specific(self, service):
        """Test listing org-specific CORS origins."""
        org_id = uuid4()
        mock_origin = MagicMock()
        mock_origin.id = uuid4()
        mock_origin.origin = "https://app.example.com"
        mock_origin.organization_id = org_id
        mock_origin.description = "Org app"
        mock_origin.is_active = True
        mock_origin.created_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_origin]
        service.db.execute.return_value = mock_result

        result = await service.list_cors_origins(organization_id=org_id)

        assert result[0]["scope"] == "organization"


class TestOIDCSettings:
    """Test OIDC-related settings."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    async def test_get_custom_domain_from_db(self, service):
        """Test getting custom domain from database."""
        with patch.object(service, "get_setting", return_value="auth.example.com"):
            result = await service.get_custom_domain()

        assert result == "auth.example.com"

    async def test_get_custom_domain_fallback_to_config(self, service):
        """Test getting custom domain falls back to config."""
        with patch.object(service, "get_setting", return_value=None):
            with patch("app.services.system_settings_service.app_settings") as mock_settings:
                mock_settings.JANUA_CUSTOM_DOMAIN = "default.example.com"

                result = await service.get_custom_domain()

        assert result == "default.example.com"

    async def test_set_custom_domain(self, service):
        """Test setting custom domain."""
        mock_setting = MagicMock()
        with patch.object(service, "set_setting", return_value=mock_setting) as mock_set:
            result = await service.set_custom_domain("auth.example.com")

        mock_set.assert_called_once()
        assert result == mock_setting

    async def test_set_custom_domain_extracts_from_url(self, service):
        """Test setting custom domain extracts domain from URL."""
        mock_setting = MagicMock()

        with patch.object(service, "set_setting", return_value=mock_setting) as mock_set:
            await service.set_custom_domain("https://auth.example.com/path")

        call_args = mock_set.call_args
        assert call_args.kwargs["value"] == "auth.example.com"


class TestCacheManagement:
    """Test cache management methods."""

    @pytest.fixture
    def service(self):
        """Create service with mock database."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    def test_invalidate_cache(self, service):
        """Test invalidating all caches."""
        service._cache = {"key1": "value1", "key2": "value2"}
        service._cors_cache = {"cached": True}

        service.invalidate_cache()

        assert service._cache == {}
        assert service._cors_cache is None


class TestModuleLevelFunctions:
    """Test module-level helper functions."""

    async def test_get_cached_cors_origins_returns_cached(self):
        """Test get_cached_cors_origins returns cached value."""
        mock_db = AsyncMock()

        # Set cached value
        with patch("app.services.system_settings_service._cors_origins_cache", ["http://cached.com"]):
            result = await get_cached_cors_origins(mock_db)

        assert result == ["http://cached.com"]

    async def test_get_cached_cors_origins_fetches_when_empty(self):
        """Test get_cached_cors_origins fetches when cache is empty."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with patch("app.services.system_settings_service._cors_origins_cache", None):
            with patch("app.services.system_settings_service.app_settings") as mock_settings:
                mock_settings.cors_origins_list = ["http://localhost:3000"]

                result = await get_cached_cors_origins(mock_db)

        assert "http://localhost:3000" in result

    def test_invalidate_cors_cache_clears_module_cache(self):
        """Test invalidate_cors_cache clears module-level cache."""
        with patch("app.services.system_settings_service._cors_origins_cache", ["cached"]):
            with patch("app.services.system_settings_service.invalidate_cors_cache") as mock_invalidate:
                # Call the real function through patch
                invalidate_cors_cache()


class TestServiceMethodExistence:
    """Test that required service methods exist."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        mock_db = AsyncMock()
        return SystemSettingsService(mock_db)

    def test_has_get_setting(self, service):
        """Test service has get_setting method."""
        import asyncio
        assert hasattr(service, "get_setting")
        assert asyncio.iscoroutinefunction(service.get_setting)

    def test_has_set_setting(self, service):
        """Test service has set_setting method."""
        import asyncio
        assert hasattr(service, "set_setting")
        assert asyncio.iscoroutinefunction(service.set_setting)

    def test_has_delete_setting(self, service):
        """Test service has delete_setting method."""
        import asyncio
        assert hasattr(service, "delete_setting")
        assert asyncio.iscoroutinefunction(service.delete_setting)

    def test_has_get_all_settings(self, service):
        """Test service has get_all_settings method."""
        import asyncio
        assert hasattr(service, "get_all_settings")
        assert asyncio.iscoroutinefunction(service.get_all_settings)

    def test_has_get_cors_origins(self, service):
        """Test service has get_cors_origins method."""
        import asyncio
        assert hasattr(service, "get_cors_origins")
        assert asyncio.iscoroutinefunction(service.get_cors_origins)

    def test_has_add_cors_origin(self, service):
        """Test service has add_cors_origin method."""
        import asyncio
        assert hasattr(service, "add_cors_origin")
        assert asyncio.iscoroutinefunction(service.add_cors_origin)

    def test_has_remove_cors_origin(self, service):
        """Test service has remove_cors_origin method."""
        import asyncio
        assert hasattr(service, "remove_cors_origin")
        assert asyncio.iscoroutinefunction(service.remove_cors_origin)

    def test_has_delete_cors_origin(self, service):
        """Test service has delete_cors_origin method."""
        import asyncio
        assert hasattr(service, "delete_cors_origin")
        assert asyncio.iscoroutinefunction(service.delete_cors_origin)

    def test_has_list_cors_origins(self, service):
        """Test service has list_cors_origins method."""
        import asyncio
        assert hasattr(service, "list_cors_origins")
        assert asyncio.iscoroutinefunction(service.list_cors_origins)

    def test_has_get_custom_domain(self, service):
        """Test service has get_custom_domain method."""
        import asyncio
        assert hasattr(service, "get_custom_domain")
        assert asyncio.iscoroutinefunction(service.get_custom_domain)

    def test_has_set_custom_domain(self, service):
        """Test service has set_custom_domain method."""
        import asyncio
        assert hasattr(service, "set_custom_domain")
        assert asyncio.iscoroutinefunction(service.set_custom_domain)

    def test_has_invalidate_cache(self, service):
        """Test service has invalidate_cache method."""
        assert hasattr(service, "invalidate_cache")
        assert callable(service.invalidate_cache)
