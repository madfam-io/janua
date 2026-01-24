"""
Comprehensive SSO Service Test Suite
Tests for SSO/SAML enterprise authentication
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest


pytestmark = pytest.mark.asyncio


class TestIsMicrosoftOidcEndpoint:
    """Test Microsoft OIDC endpoint validation."""

    def test_valid_microsoft_endpoint(self):
        """Test valid Microsoft OIDC endpoint."""
        from app.services.sso_service import _is_microsoft_oidc_endpoint

        result = _is_microsoft_oidc_endpoint(
            "https://login.microsoftonline.com/.well-known/openid-configuration"
        )
        assert result is True

    def test_valid_microsoft_endpoint_with_tenant(self):
        """Test valid Microsoft OIDC endpoint with tenant."""
        from app.services.sso_service import _is_microsoft_oidc_endpoint

        result = _is_microsoft_oidc_endpoint(
            "https://login.microsoftonline.com/tenant-id/v2.0/.well-known/openid-configuration"
        )
        assert result is True

    def test_invalid_subdomain_bypass_attempt(self):
        """Test subdomain bypass attack is prevented."""
        from app.services.sso_service import _is_microsoft_oidc_endpoint

        # This should fail - attacker trying to use subdomain bypass
        result = _is_microsoft_oidc_endpoint(
            "https://login.microsoftonline.com.attacker.com/oidc"
        )
        assert result is False

    def test_http_not_https(self):
        """Test HTTP scheme is rejected."""
        from app.services.sso_service import _is_microsoft_oidc_endpoint

        result = _is_microsoft_oidc_endpoint(
            "http://login.microsoftonline.com/.well-known/openid-configuration"
        )
        assert result is False

    def test_wrong_host(self):
        """Test wrong host is rejected."""
        from app.services.sso_service import _is_microsoft_oidc_endpoint

        result = _is_microsoft_oidc_endpoint(
            "https://login.example.com/.well-known/openid-configuration"
        )
        assert result is False

    def test_invalid_url(self):
        """Test invalid URL returns False."""
        from app.services.sso_service import _is_microsoft_oidc_endpoint

        result = _is_microsoft_oidc_endpoint("not-a-valid-url")
        assert result is False

    def test_empty_url(self):
        """Test empty URL returns False."""
        from app.services.sso_service import _is_microsoft_oidc_endpoint

        result = _is_microsoft_oidc_endpoint("")
        assert result is False


class TestSSOServiceInitialization:
    """Test SSOService initialization."""

    def test_service_initialization_defaults(self):
        """Test service initializes with default values."""
        from app.services.sso_service import SSOService

        service = SSOService()

        assert service.db is None
        assert service.cache is None
        assert service.jwt_service is None
        assert service.saml_settings == {}
        assert service.oidc_clients == {}

    def test_service_initialization_with_dependencies(self):
        """Test service initializes with provided dependencies."""
        from app.services.sso_service import SSOService

        mock_db = AsyncMock()
        mock_cache = MagicMock()
        mock_jwt = MagicMock()

        service = SSOService(db=mock_db, cache=mock_cache, jwt_service=mock_jwt)

        assert service.db is mock_db
        assert service.cache is mock_cache
        assert service.jwt_service is mock_jwt
        assert service.redis_client is mock_cache  # Alias

    def test_supported_protocols(self):
        """Test supported protocols list."""
        from app.services.sso_service import SSOService

        service = SSOService()

        assert "saml2" in service.supported_protocols
        assert "oidc" in service.supported_protocols
        assert "oauth2" in service.supported_protocols

    def test_identity_providers_populated(self):
        """Test identity providers are pre-populated."""
        from app.services.sso_service import SSOService

        service = SSOService()

        assert "okta" in service.identity_providers
        assert "azure_ad" in service.identity_providers
        assert "google_workspace" in service.identity_providers
        assert "auth0" in service.identity_providers


class TestEncryptDecryptSecret:
    """Test secret encryption/decryption."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    def test_encrypt_secret(self, service):
        """Test secret encryption."""
        secret = "my-secret-value"
        encrypted = service._encrypt_secret(secret)

        assert encrypted != secret
        assert isinstance(encrypted, str)

    def test_decrypt_secret(self, service):
        """Test secret decryption."""
        secret = "my-secret-value"
        encrypted = service._encrypt_secret(secret)
        decrypted = service._decrypt_secret(encrypted)

        assert decrypted == secret

    def test_encrypt_decrypt_roundtrip(self, service):
        """Test encrypt/decrypt roundtrip."""
        original = "super-secret-client-secret"
        encrypted = service._encrypt_secret(original)
        decrypted = service._decrypt_secret(encrypted)

        assert decrypted == original

    def test_encrypt_empty_string(self, service):
        """Test encrypting empty string."""
        encrypted = service._encrypt_secret("")
        decrypted = service._decrypt_secret(encrypted)

        assert decrypted == ""


class TestMapSamlAttributes:
    """Test SAML attribute mapping."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    def test_map_standard_attributes(self, service):
        """Test mapping standard SAML attributes."""
        attributes = {
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": ["user@example.com"],
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": ["John"],
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": ["Doe"],
        }

        result = service._map_saml_attributes(attributes, {})

        assert result["email"] == "user@example.com"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"

    def test_map_short_attributes(self, service):
        """Test mapping short SAML attribute names."""
        attributes = {
            "email": ["user@example.com"],
            "firstName": ["John"],
            "lastName": ["Doe"],
        }

        result = service._map_saml_attributes(attributes, {})

        assert result["email"] == "user@example.com"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"

    def test_map_custom_attributes(self, service):
        """Test mapping with custom attribute mapping."""
        attributes = {
            "customEmail": ["user@example.com"],
            "customName": ["John"],
        }

        custom_mapping = {
            "email": "customEmail",
            "first_name": "customName",
        }

        result = service._map_saml_attributes(attributes, custom_mapping)

        assert result["email"] == "user@example.com"
        assert result["first_name"] == "John"

    def test_map_empty_attributes(self, service):
        """Test mapping empty attributes."""
        result = service._map_saml_attributes({}, {})

        assert result == {}

    def test_map_attribute_with_multiple_values(self, service):
        """Test mapping attribute with multiple values takes first."""
        attributes = {
            "email": ["user1@example.com", "user2@example.com"],
        }

        result = service._map_saml_attributes(attributes, {})

        assert result["email"] == "user1@example.com"

    def test_map_attribute_with_empty_list(self, service):
        """Test mapping attribute with empty list."""
        attributes = {
            "email": [],
        }

        result = service._map_saml_attributes(attributes, {})

        assert result.get("email") is None


class TestMapOidcAttributes:
    """Test OIDC attribute mapping."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    def test_map_standard_claims(self, service):
        """Test mapping standard OIDC claims."""
        claims = {
            "email": "user@example.com",
            "given_name": "John",
            "family_name": "Doe",
            "name": "John Doe",
        }

        result = service._map_oidc_attributes(claims, {})

        assert result["email"] == "user@example.com"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["display_name"] == "John Doe"

    def test_map_custom_claims(self, service):
        """Test mapping with custom claim mapping."""
        claims = {
            "custom_email": "user@example.com",
            "custom_name": "John",
        }

        custom_mapping = {
            "email": "custom_email",
            "first_name": "custom_name",
        }

        result = service._map_oidc_attributes(claims, custom_mapping)

        assert result["email"] == "user@example.com"
        assert result["first_name"] == "John"

    def test_map_empty_claims(self, service):
        """Test mapping empty claims."""
        result = service._map_oidc_attributes({}, {})

        assert result == {}

    def test_map_partial_claims(self, service):
        """Test mapping partial claims."""
        claims = {
            "email": "user@example.com",
        }

        result = service._map_oidc_attributes(claims, {})

        assert result["email"] == "user@example.com"
        assert "first_name" not in result
        assert "last_name" not in result


class TestIdentityProviderManagement:
    """Test identity provider management methods."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_add_identity_provider(self, service):
        """Test adding identity provider."""
        config = {"name": "Custom IDP", "protocol": "oidc"}
        result = await service.add_identity_provider("custom-idp", config)

        assert result["id"] == "custom-idp"
        assert result["status"] == "configured"
        assert result["name"] == "Custom IDP"
        assert "custom-idp" in service.identity_providers

    async def test_add_identity_provider_generates_id(self, service):
        """Test adding identity provider generates ID if not provided."""
        config = {"name": "Auto ID IDP", "protocol": "saml2"}
        result = await service.add_identity_provider(None, config)

        assert result["id"] is not None
        assert result["status"] == "configured"

    async def test_remove_identity_provider(self, service):
        """Test removing identity provider."""
        # First add a provider
        await service.add_identity_provider("test-idp", {"name": "Test"})

        # Then remove it
        result = await service.remove_identity_provider("test-idp")

        assert result["status"] == "removed"
        assert "test-idp" not in service.identity_providers

    async def test_remove_nonexistent_provider(self, service):
        """Test removing non-existent provider."""
        result = await service.remove_identity_provider("nonexistent")

        assert result["status"] == "not_found"

    async def test_list_identity_providers(self, service):
        """Test listing identity providers."""
        result = await service.list_identity_providers()

        assert isinstance(result, list)
        assert len(result) >= 4  # Default providers
        assert any(p["id"] == "okta" for p in result)
        assert any(p["id"] == "azure_ad" for p in result)

    async def test_test_identity_provider_connection_exists(self, service):
        """Test connection to existing provider."""
        result = await service.test_identity_provider_connection("okta")

        assert result["success"] is True
        assert "message" in result

    async def test_test_identity_provider_connection_not_found(self, service):
        """Test connection to non-existent provider."""
        result = await service.test_identity_provider_connection("nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestUserProvisioning:
    """Test user provisioning methods."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_provision_user_from_saml(self, service):
        """Test provisioning user from SAML attributes."""
        attributes = {
            "email": "user@example.com",
            "firstName": "John",
            "lastName": "Doe",
        }

        result = await service.provision_user_from_saml(attributes)

        assert result["provisioned"] is True
        assert result["email"] == "user@example.com"
        assert result["user_id"] is not None

    async def test_provision_user_from_attributes(self, service):
        """Test provisioning user from mapped attributes."""
        attributes = {
            "saml_email": ["user@example.com"],
            "saml_first": ["John"],
            "saml_last": ["Doe"],
        }

        mapping = {
            "email": "saml_email",
            "firstName": "saml_first",
            "lastName": "saml_last",
        }

        result = await service.provision_user_from_attributes(attributes, mapping)

        assert result["created"] is True
        assert result["email"] == "user@example.com"
        assert result["first_name"] == "John"

    async def test_provision_user_from_oidc(self, service):
        """Test provisioning user from OIDC userinfo."""
        userinfo = {
            "email": "user@example.com",
            "name": "John Doe",
            "given_name": "John",
        }

        result = await service.provision_user_from_oidc(userinfo)

        assert result["created"] is True
        assert result["email"] == "user@example.com"
        assert result["name"] == "John Doe"

    async def test_jit_provision_user(self, service):
        """Test just-in-time user provisioning."""
        sso_data = {
            "email": "jit@example.com",
            "name": "JIT User",
        }

        result = await service.jit_provision_user(sso_data)

        assert result["jit_provisioned"] is True
        assert result["email"] == "jit@example.com"
        assert result["user_id"] is not None

    async def test_update_user_attributes(self, service):
        """Test updating user attributes from SSO."""
        attributes = {"first_name": "Updated", "last_name": "User"}

        result = await service.update_user_attributes("user-123", attributes)

        assert result["attributes_updated"] is True
        assert result["user_id"] == "user-123"
        assert result["attributes"] == attributes

    async def test_update_user_from_sso(self, service):
        """Test updating user from SSO attributes."""
        sso_attrs = {"email": "updated@example.com", "name": "Updated Name"}

        result = await service.update_user_from_sso("user-123", sso_attrs)

        assert result["updated"] is True
        assert result["user_id"] == "user-123"

    async def test_handle_jit_provisioning(self, service):
        """Test handling JIT provisioning."""
        sso_response = {
            "email": "newuser@example.com",
            "name": "New User",
        }

        result = await service.handle_jit_provisioning(sso_response)

        assert result["user_created"] is True
        assert result["provisioning_method"] == "jit"
        assert result["email"] == "newuser@example.com"


class TestSSOSession:
    """Test SSO session management."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_create_sso_session(self, service):
        """Test creating SSO session."""
        session_data = {"attributes": {"email": "user@example.com"}}

        result = await service.create_sso_session("user-123", "okta", session_data)

        assert result["session_id"] is not None
        assert result["user_id"] == "user-123"
        assert result["provider"] == "okta"
        assert "expires_at" in result

    async def test_validate_sso_session(self, service):
        """Test validating SSO session."""
        result = await service.validate_sso_session("session-123")

        assert result["valid"] is True
        assert result["session_id"] == "session-123"
        assert "expires_at" in result

    async def test_invalidate_sso_session(self, service):
        """Test invalidating SSO session."""
        result = await service.invalidate_sso_session("session-123")

        assert result is True

    async def test_handle_single_logout(self, service):
        """Test handling single logout."""
        logout_request = {"return_url": "https://example.com/logged-out"}

        result = await service.handle_single_logout("session-123", logout_request)

        assert result["logout_successful"] is True
        assert result["session_invalidated"] is True
        assert result["redirect_url"] == "https://example.com/logged-out"


class TestSAMLMetadata:
    """Test SAML metadata generation."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_generate_saml_metadata(self, service):
        """Test generating SAML SP metadata."""
        entity_id = "https://app.example.com/saml"
        acs_url = "https://app.example.com/saml/callback"

        result = await service.generate_saml_metadata(entity_id, acs_url)

        assert result["entity_id"] == entity_id
        assert result["acs_url"] == acs_url
        assert "metadata_xml" in result
        assert entity_id in result["metadata_xml"]
        assert acs_url in result["metadata_xml"]


class TestOIDCFlow:
    """Test OIDC authentication flow."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_initiate_oidc_login(self, service):
        """Test initiating OIDC login."""
        provider_config = {
            "authorization_url": "https://provider.com/authorize",
            "client_id": "test-client",
        }

        result = await service.initiate_oidc_login("test-provider", provider_config)

        assert "auth_url" in result
        assert "state" in result
        assert "nonce" in result
        assert result["protocol"] == "oidc"

    async def test_initiate_oidc_login_microsoft(self, service):
        """Test initiating OIDC login with Microsoft discovery URL."""
        provider_config = {
            "discovery_url": "https://login.microsoftonline.com/.well-known/openid-configuration",
            "client_id": "test-client",
        }

        result = await service.initiate_oidc_login("azure-ad", provider_config)

        assert urlparse(result["auth_url"]).netloc == "login.microsoftonline.com"

    async def test_process_oidc_callback(self, service):
        """Test processing OIDC callback."""
        callback_data = {
            "email": "user@example.com",
            "name": "Test User",
        }
        provider_config = {"client_id": "test-client"}

        result = await service.process_oidc_callback(
            callback_data, provider_config, "state-123"
        )

        assert result["session_created"] is True
        assert result["email"] == "user@example.com"

    async def test_validate_id_token_success(self, service):
        """Test validating valid ID token."""
        import jwt

        # Create a valid token (not expired)
        token = jwt.encode(
            {
                "email": "user@example.com",
                "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            },
            "secret",
            algorithm="HS256",
        )

        result = await service.validate_id_token(token, "client-id", "https://issuer.com")

        assert result["valid"] is True
        assert "claims" in result

    async def test_validate_id_token_expired(self, service):
        """Test validating expired ID token."""
        import jwt

        # Create an expired token
        token = jwt.encode(
            {
                "email": "user@example.com",
                "exp": (datetime.utcnow() - timedelta(hours=1)).timestamp(),
            },
            "secret",
            algorithm="HS256",
        )

        result = await service.validate_id_token(token, "client-id", "https://issuer.com")

        assert result["valid"] is False
        assert "error" in result


class TestSAMLFlow:
    """Test SAML authentication flow."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_initiate_saml_sso_with_provider_config(self, service):
        """Test initiating SAML SSO with provider config."""
        # Patch SAML_AVAILABLE to False to avoid OneLogin_Saml2_Auth call
        with patch("app.services.sso_service.SAML_AVAILABLE", False):
            service.cache = AsyncMock()
            service.cache.set = AsyncMock()

            provider_config = {
                "sso_url": "https://idp.example.com/sso",
                "organization_id": "test-org",
            }

            result = await service.initiate_saml_sso("provider-id", provider_config)

            assert "auth_url" in result or "sso_url" in result
            assert "saml_request" in result
            assert result["protocol"] == "saml2"


class TestErrorHandling:
    """Test error handling methods."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_handle_saml_error(self, service):
        """Test handling SAML error."""
        error = Exception("SAML parsing failed")

        result = await service.handle_saml_error(error)

        assert result["error_handled"] is True
        assert "SAML parsing failed" in result["error"]

    async def test_handle_oidc_discovery_failure(self, service):
        """Test handling OIDC discovery failure."""
        error = Exception("Discovery endpoint unreachable")

        result = await service.handle_oidc_discovery_failure("provider-123", error)

        assert result["success"] is False
        assert result["provider_id"] == "provider-123"
        assert "unreachable" in result["error"].lower()


class TestCertificateValidation:
    """Test certificate validation."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_validate_provider_certificate(self, service):
        """Test validating provider certificate."""
        provider_config = {
            "name": "Test Provider",
            "certificate": "MIIC...",
        }

        result = await service.validate_provider_certificate(provider_config)

        assert result["valid"] is True
        assert result["provider"] == "Test Provider"


class TestProviderConnectionTest:
    """Test provider connection testing."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    async def test_test_provider_connection(self, service):
        """Test testing provider connection."""
        provider_config = {
            "name": "Test Provider",
            "endpoint": "https://idp.example.com",
        }

        result = await service.test_provider_connection("test-provider", provider_config)

        assert result["provider"] == "test-provider"
        assert result["status"] == "connected"
        assert "latency" in result
        assert result["metadata_valid"] is True


class TestServiceMethodExistence:
    """Test that all expected service methods exist."""

    @pytest.fixture
    def service(self):
        """Create SSOService instance."""
        from app.services.sso_service import SSOService
        return SSOService()

    def test_has_configure_sso(self, service):
        """Test service has configure_sso method."""
        assert hasattr(service, "configure_sso")
        import asyncio
        assert asyncio.iscoroutinefunction(service.configure_sso)

    def test_has_initiate_saml_sso(self, service):
        """Test service has initiate_saml_sso method."""
        assert hasattr(service, "initiate_saml_sso")
        import asyncio
        assert asyncio.iscoroutinefunction(service.initiate_saml_sso)

    def test_has_handle_saml_response(self, service):
        """Test service has handle_saml_response method."""
        assert hasattr(service, "handle_saml_response")
        import asyncio
        assert asyncio.iscoroutinefunction(service.handle_saml_response)

    def test_has_initiate_oidc_sso(self, service):
        """Test service has initiate_oidc_sso method."""
        assert hasattr(service, "initiate_oidc_sso")
        import asyncio
        assert asyncio.iscoroutinefunction(service.initiate_oidc_sso)

    def test_has_handle_oidc_callback(self, service):
        """Test service has handle_oidc_callback method."""
        assert hasattr(service, "handle_oidc_callback")
        import asyncio
        assert asyncio.iscoroutinefunction(service.handle_oidc_callback)

    def test_has_encrypt_secret(self, service):
        """Test service has _encrypt_secret method."""
        assert hasattr(service, "_encrypt_secret")

    def test_has_decrypt_secret(self, service):
        """Test service has _decrypt_secret method."""
        assert hasattr(service, "_decrypt_secret")

    def test_has_map_saml_attributes(self, service):
        """Test service has _map_saml_attributes method."""
        assert hasattr(service, "_map_saml_attributes")

    def test_has_map_oidc_attributes(self, service):
        """Test service has _map_oidc_attributes method."""
        assert hasattr(service, "_map_oidc_attributes")

    def test_has_add_identity_provider(self, service):
        """Test service has add_identity_provider method."""
        assert hasattr(service, "add_identity_provider")
        import asyncio
        assert asyncio.iscoroutinefunction(service.add_identity_provider)

    def test_has_remove_identity_provider(self, service):
        """Test service has remove_identity_provider method."""
        assert hasattr(service, "remove_identity_provider")
        import asyncio
        assert asyncio.iscoroutinefunction(service.remove_identity_provider)

    def test_has_list_identity_providers(self, service):
        """Test service has list_identity_providers method."""
        assert hasattr(service, "list_identity_providers")
        import asyncio
        assert asyncio.iscoroutinefunction(service.list_identity_providers)
