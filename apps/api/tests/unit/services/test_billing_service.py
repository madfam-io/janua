"""
Comprehensive Billing Service Test Suite
Tests for multi-provider billing (Conekta, Polar, Stripe)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.billing_service import BillingService, PRICING_TIERS

pytestmark = pytest.mark.asyncio


class TestBillingServiceInitialization:
    """Test billing service initialization."""

    def test_service_initialization(self):
        """Test service initializes with default API keys."""
        service = BillingService()

        assert service.conekta_api_url == "https://api.conekta.io"
        assert service.polar_api_url == "https://api.polar.sh/v1"
        assert service.stripe_api_url == "https://api.stripe.com/v1"

    def test_service_has_api_keys(self):
        """Test service has API keys configured."""
        service = BillingService()

        assert hasattr(service, "conekta_api_key")
        assert hasattr(service, "polar_api_key")
        assert hasattr(service, "stripe_api_key")


class TestPricingTiers:
    """Test pricing tier constants."""

    def test_community_tier_is_free(self):
        """Test community tier is free."""
        assert PRICING_TIERS["community"]["price_mxn"] == 0
        assert PRICING_TIERS["community"]["price_usd"] == 0

    def test_pro_tier_pricing(self):
        """Test pro tier pricing."""
        assert PRICING_TIERS["pro"]["price_mxn"] == 1380
        assert PRICING_TIERS["pro"]["price_usd"] == 69

    def test_scale_tier_pricing(self):
        """Test scale tier pricing."""
        assert PRICING_TIERS["scale"]["price_mxn"] == 5980
        assert PRICING_TIERS["scale"]["price_usd"] == 299

    def test_enterprise_tier_is_custom(self):
        """Test enterprise tier has custom pricing."""
        assert PRICING_TIERS["enterprise"]["price_mxn"] is None
        assert PRICING_TIERS["enterprise"]["price_usd"] is None

    def test_community_mau_limit(self):
        """Test community tier MAU limit."""
        assert PRICING_TIERS["community"]["mau_limit"] == 2000

    def test_pro_mau_limit(self):
        """Test pro tier MAU limit."""
        assert PRICING_TIERS["pro"]["mau_limit"] == 10000

    def test_scale_mau_limit(self):
        """Test scale tier MAU limit."""
        assert PRICING_TIERS["scale"]["mau_limit"] == 50000

    def test_enterprise_unlimited_mau(self):
        """Test enterprise tier has unlimited MAU."""
        assert PRICING_TIERS["enterprise"]["mau_limit"] is None

    def test_all_tiers_have_features(self):
        """Test all tiers have features list."""
        for tier, info in PRICING_TIERS.items():
            assert "features" in info
            assert isinstance(info["features"], list)


class TestPaymentProviderDetermination:
    """Test payment provider determination logic."""

    @pytest.fixture
    def service(self):
        return BillingService()

    async def test_mexico_uses_conekta(self, service):
        """Test Mexico uses Conekta."""
        provider = await service.determine_payment_provider("MX")
        assert provider == "conekta"

    async def test_mexico_lowercase_uses_conekta(self, service):
        """Test lowercase mx uses Conekta."""
        provider = await service.determine_payment_provider("mx")
        assert provider == "conekta"

    async def test_us_uses_polar(self, service):
        """Test US uses Polar."""
        provider = await service.determine_payment_provider("US")
        assert provider == "polar"

    async def test_uk_uses_polar(self, service):
        """Test UK uses Polar."""
        provider = await service.determine_payment_provider("GB")
        assert provider == "polar"

    async def test_canada_uses_polar(self, service):
        """Test Canada uses Polar."""
        provider = await service.determine_payment_provider("CA")
        assert provider == "polar"

    async def test_fallback_uses_stripe(self, service):
        """Test fallback mode uses Stripe."""
        provider = await service.determine_payment_provider("MX", fallback=True)
        assert provider == "stripe"

    async def test_fallback_overrides_country(self, service):
        """Test fallback overrides country-based selection."""
        provider = await service.determine_payment_provider("US", fallback=True)
        assert provider == "stripe"


class TestPlanValidation:
    """Test plan validation methods."""

    @pytest.fixture
    def service(self):
        return BillingService()

    def test_validate_community_plan(self, service):
        """Test community plan is valid."""
        assert service.validate_plan("community") is True

    def test_validate_pro_plan(self, service):
        """Test pro plan is valid."""
        assert service.validate_plan("pro") is True

    def test_validate_scale_plan(self, service):
        """Test scale plan is valid."""
        assert service.validate_plan("scale") is True

    def test_validate_enterprise_plan(self, service):
        """Test enterprise plan is valid."""
        assert service.validate_plan("enterprise") is True

    def test_validate_invalid_plan(self, service):
        """Test invalid plan returns False."""
        assert service.validate_plan("invalid") is False

    def test_validate_empty_plan(self, service):
        """Test empty plan returns False."""
        assert service.validate_plan("") is False


class TestPlanFeatures:
    """Test plan features retrieval."""

    @pytest.fixture
    def service(self):
        return BillingService()

    def test_get_community_features(self, service):
        """Test getting community features."""
        features = service.get_plan_features("community")
        assert features is not None
        assert "basic_auth" in features

    def test_get_pro_features(self, service):
        """Test getting pro features."""
        features = service.get_plan_features("pro")
        assert features is not None
        assert "sso" in features
        assert "webhooks" in features

    def test_get_scale_features(self, service):
        """Test getting scale features."""
        features = service.get_plan_features("scale")
        assert features is not None
        assert "compliance" in features

    def test_get_enterprise_features(self, service):
        """Test getting enterprise features."""
        features = service.get_plan_features("enterprise")
        assert features is not None
        assert "saml" in features
        assert "scim" in features

    def test_get_invalid_plan_features(self, service):
        """Test getting features for invalid plan."""
        features = service.get_plan_features("invalid")
        assert features is None


class TestMAULimits:
    """Test MAU limit retrieval and overage calculation."""

    @pytest.fixture
    def service(self):
        return BillingService()

    def test_get_community_mau_limit(self, service):
        """Test getting community MAU limit."""
        limit = service.get_plan_mau_limit("community")
        assert limit == 2000

    def test_get_pro_mau_limit(self, service):
        """Test getting pro MAU limit."""
        limit = service.get_plan_mau_limit("pro")
        assert limit == 10000

    def test_get_scale_mau_limit(self, service):
        """Test getting scale MAU limit."""
        limit = service.get_plan_mau_limit("scale")
        assert limit == 50000

    def test_get_enterprise_mau_limit(self, service):
        """Test getting enterprise MAU limit (unlimited)."""
        limit = service.get_plan_mau_limit("enterprise")
        assert limit is None

    def test_get_invalid_plan_mau_limit(self, service):
        """Test getting MAU limit for invalid plan."""
        limit = service.get_plan_mau_limit("invalid")
        assert limit is None


class TestOverageCalculation:
    """Test overage cost calculation."""

    @pytest.fixture
    def service(self):
        return BillingService()

    def test_no_overage_under_limit(self, service):
        """Test no overage when under limit."""
        cost = service.calculate_overage_cost("community", 1000)
        assert cost == 0.0

    def test_no_overage_at_limit(self, service):
        """Test no overage at exact limit."""
        cost = service.calculate_overage_cost("community", 2000)
        assert cost == 0.0

    def test_overage_above_limit(self, service):
        """Test overage calculated when above limit."""
        cost = service.calculate_overage_cost("community", 2100)
        assert cost == 1.0  # 100 * $0.01

    def test_overage_pro_tier(self, service):
        """Test overage for pro tier."""
        cost = service.calculate_overage_cost("pro", 11000)
        assert cost == 10.0  # 1000 * $0.01

    def test_overage_invalid_tier(self, service):
        """Test overage for invalid tier returns 0."""
        cost = service.calculate_overage_cost("invalid", 10000)
        assert cost == 0.0

    def test_no_overage_enterprise(self, service):
        """Test enterprise has no overage (unlimited)."""
        cost = service.calculate_overage_cost("enterprise", 1000000)
        assert cost == 0.0


class TestCountryPricing:
    """Test country-specific pricing."""

    @pytest.fixture
    def service(self):
        return BillingService()

    def test_mexico_pricing_uses_mxn(self, service):
        """Test Mexico uses MXN pricing."""
        pricing = service.get_pricing_for_country("MX")
        assert pricing["currency"] == "MXN"
        assert pricing["provider"] == "conekta"

    def test_us_pricing_uses_usd(self, service):
        """Test US uses USD pricing."""
        pricing = service.get_pricing_for_country("US")
        assert pricing["currency"] == "USD"
        assert pricing["provider"] == "polar"

    def test_pricing_includes_all_tiers(self, service):
        """Test pricing includes all tiers."""
        pricing = service.get_pricing_for_country("US")
        assert "community" in pricing["tiers"]
        assert "pro" in pricing["tiers"]
        assert "scale" in pricing["tiers"]
        assert "enterprise" in pricing["tiers"]

    def test_community_is_free_everywhere(self, service):
        """Test community is free in all countries."""
        mx_pricing = service.get_pricing_for_country("MX")
        us_pricing = service.get_pricing_for_country("US")

        assert mx_pricing["tiers"]["community"]["price"] == 0
        assert us_pricing["tiers"]["community"]["price"] == 0

    def test_enterprise_is_custom_everywhere(self, service):
        """Test enterprise is custom in all countries."""
        mx_pricing = service.get_pricing_for_country("MX")
        us_pricing = service.get_pricing_for_country("US")

        assert mx_pricing["tiers"]["enterprise"]["price"] == "custom"
        assert us_pricing["tiers"]["enterprise"]["price"] == "custom"


class TestConektaIntegration:
    """Test Conekta integration methods."""

    @pytest.fixture
    def service(self):
        return BillingService()

    async def test_create_conekta_customer_success(self, service):
        """Test creating Conekta customer successfully."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"id": "cus_123", "email": "test@example.com"})
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        with patch("app.services.billing_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await service.create_conekta_customer(
                email="test@example.com", name="Test User", phone="+521234567890"
            )

        assert result["id"] == "cus_123"

    async def test_create_conekta_checkout_session_invalid_tier(self, service):
        """Test creating checkout session with invalid tier raises error."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await service.create_conekta_checkout_session(
                customer_email="test@example.com",
                tier="invalid",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )

    async def test_create_conekta_checkout_session_community_tier(self, service):
        """Test creating checkout session with community tier raises error."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await service.create_conekta_checkout_session(
                customer_email="test@example.com",
                tier="community",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )


class TestPolarIntegration:
    """Test Polar.sh integration methods."""

    @pytest.fixture
    def service(self):
        return BillingService()

    async def test_create_polar_customer_success(self, service):
        """Test creating Polar customer successfully."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"id": "cus_polar_123"})
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        with patch("app.services.billing_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await service.create_polar_customer(
                email="test@example.com", name="Test User", country="US"
            )

        assert result["id"] == "cus_polar_123"

    async def test_create_polar_subscription_invalid_tier(self, service):
        """Test creating subscription with invalid tier raises error."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await service.create_polar_subscription(customer_id="cus_123", tier="invalid")

    async def test_create_polar_checkout_session_invalid_tier(self, service):
        """Test creating checkout session with invalid tier raises error."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await service.create_polar_checkout_session(
                customer_email="test@example.com",
                tier="invalid",
                country="US",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )

    async def test_update_polar_subscription_invalid_tier(self, service):
        """Test updating subscription with invalid tier raises error."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await service.update_polar_subscription(subscription_id="sub_123", tier="invalid")


class TestStripeIntegration:
    """Test Stripe integration methods."""

    @pytest.fixture
    def service(self):
        return BillingService()

    async def test_create_stripe_customer_success(self, service):
        """Test creating Stripe customer successfully."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"id": "cus_stripe_123"})
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        with patch("app.services.billing_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await service.create_stripe_customer(
                email="test@example.com", name="Test User"
            )

        assert result["id"] == "cus_stripe_123"

    async def test_create_stripe_checkout_session_invalid_tier(self, service):
        """Test creating checkout session with invalid tier raises error."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await service.create_stripe_checkout_session(
                customer_email="test@example.com",
                tier="invalid",
                country="US",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )

    async def test_create_stripe_checkout_session_success(self, service):
        """Test creating Stripe checkout session successfully."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"id": "cs_123"})
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        with patch("app.services.billing_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await service.create_stripe_checkout_session(
                customer_email="test@example.com",
                tier="pro",
                country="MX",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )

        assert result["id"] == "cs_123"
        mock_client_instance.post.assert_called_once()


class TestUnifiedBillingInterface:
    """Test unified billing interface."""

    @pytest.fixture
    def service(self):
        return BillingService()

    async def test_create_subscription_mexico_uses_conekta(self, service):
        """Test subscription in Mexico uses Conekta."""
        with patch.object(service, "create_conekta_subscription") as mock_conekta:
            mock_conekta.return_value = {"id": "sub_conekta_123"}

            result = await service.create_subscription(
                customer_id="cus_123", tier="pro", country="MX"
            )

        mock_conekta.assert_called_once()
        assert result["id"] == "sub_conekta_123"

    async def test_create_subscription_us_uses_polar(self, service):
        """Test subscription in US uses Polar."""
        with patch.object(service, "create_polar_subscription") as mock_polar:
            mock_polar.return_value = {"id": "sub_polar_123"}

            result = await service.create_subscription(
                customer_id="cus_123", tier="pro", country="US"
            )

        mock_polar.assert_called_once()
        assert result["id"] == "sub_polar_123"

    async def test_create_subscription_fallback_raises_not_implemented(self, service):
        """Test fallback raises NotImplementedError for Stripe subscriptions."""
        with pytest.raises(NotImplementedError):
            await service.create_subscription(
                customer_id="cus_123", tier="pro", country="US", use_fallback=True
            )


class TestUsageLimits:
    """Test usage limit checking."""

    @pytest.fixture
    def service(self):
        return BillingService()

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    async def test_check_usage_limits_tenant_not_found(self, service, mock_db):
        """Test usage limits check when tenant not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        within_limits, message = await service.check_usage_limits(mock_db, uuid4())

        assert within_limits is False
        assert message == "Tenant not found"

    async def test_check_usage_limits_within_limits(self, service, mock_db):
        """Test usage limits check when within limits."""
        mock_tenant = MagicMock()
        mock_tenant.subscription_tier = "pro"
        mock_tenant.current_mau = 5000

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result

        within_limits, message = await service.check_usage_limits(mock_db, uuid4())

        assert within_limits is True
        assert message is None

    async def test_check_usage_limits_at_limit(self, service, mock_db):
        """Test usage limits check at exact limit."""
        mock_tenant = MagicMock()
        mock_tenant.subscription_tier = "community"
        mock_tenant.current_mau = 2000

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result

        within_limits, message = await service.check_usage_limits(mock_db, uuid4())

        assert within_limits is False
        assert "MAU limit reached" in message

    async def test_check_usage_limits_over_limit(self, service, mock_db):
        """Test usage limits check when over limit."""
        mock_tenant = MagicMock()
        mock_tenant.subscription_tier = "community"
        mock_tenant.current_mau = 5000

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result

        within_limits, message = await service.check_usage_limits(mock_db, uuid4())

        assert within_limits is False
        assert "MAU limit reached" in message
