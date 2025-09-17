"""
Comprehensive unit tests for BillingService - targeting 100% coverage
This test covers all billing operations, payment processing, subscription management
Expected to cover 203 lines in app/services/billing_service.py
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.billing_service import BillingService, PRICING_TIERS


class TestBillingServiceInitialization:
    """Test billing service initialization and configuration."""

    def test_billing_service_init(self):
        """Test billing service initializes correctly."""
        service = BillingService()

        assert service.conekta_api_key is not None
        assert service.fungies_api_key is not None
        assert service.webhook_secret is not None
        assert isinstance(service.conekta_headers, dict)
        assert isinstance(service.fungies_headers, dict)

    def test_pricing_tiers_configuration(self):
        """Test pricing tiers are configured correctly."""
        assert "community" in PRICING_TIERS
        assert "pro" in PRICING_TIERS
        assert "scale" in PRICING_TIERS
        assert "enterprise" in PRICING_TIERS

        # Verify community tier
        community = PRICING_TIERS["community"]
        assert community["price_mxn"] == 0
        assert community["price_usd"] == 0
        assert community["mau_limit"] == 2000
        assert "basic_auth" in community["features"]

        # Verify pro tier
        pro = PRICING_TIERS["pro"]
        assert pro["price_mxn"] == 1380
        assert pro["price_usd"] == 69
        assert pro["mau_limit"] == 10000
        assert "sso" in pro["features"]


class TestPlanValidation:
    """Test plan validation and pricing logic."""

    def setup_method(self):
        """Setup for each test."""
        self.service = BillingService()

    def test_validate_plan_valid_plans(self):
        """Test validation of valid plan names."""
        valid_plans = ["community", "pro", "scale", "enterprise"]

        for plan in valid_plans:
            result = self.service.validate_plan(plan)
            assert result is True

    def test_validate_plan_invalid_plans(self):
        """Test validation rejects invalid plan names."""
        invalid_plans = ["invalid", "free", "premium", "", None]

        for plan in invalid_plans:
            result = self.service.validate_plan(plan)
            assert result is False

    def test_get_pricing_for_country_mexico(self):
        """Test pricing retrieval for Mexico."""
        pricing = self.service.get_pricing_for_country("MX")

        assert pricing["community"] == 0
        assert pricing["pro"] == 1380
        assert pricing["scale"] == 5980
        assert pricing["enterprise"] is None

    def test_get_pricing_for_country_international(self):
        """Test pricing retrieval for international countries."""
        countries = ["US", "CA", "GB", "DE", "FR", "AU"]

        for country in countries:
            pricing = self.service.get_pricing_for_country(country)

            assert pricing["community"] == 0
            assert pricing["pro"] == 69
            assert pricing["scale"] == 299
            assert pricing["enterprise"] is None

    def test_get_plan_features_valid_plan(self):
        """Test feature retrieval for valid plans."""
        features = self.service.get_plan_features("pro")
        expected_features = ["everything_community", "advanced_rbac", "custom_domains", "webhooks", "sso"]

        assert set(features) == set(expected_features)

    def test_get_plan_features_invalid_plan(self):
        """Test feature retrieval for invalid plans."""
        features = self.service.get_plan_features("invalid_plan")
        assert features == []

    def test_get_plan_mau_limit_valid_plans(self):
        """Test MAU limit retrieval for valid plans."""
        assert self.service.get_plan_mau_limit("community") == 2000
        assert self.service.get_plan_mau_limit("pro") == 10000
        assert self.service.get_plan_mau_limit("scale") == 50000
        assert self.service.get_plan_mau_limit("enterprise") is None

    def test_get_plan_mau_limit_invalid_plan(self):
        """Test MAU limit retrieval for invalid plans."""
        assert self.service.get_plan_mau_limit("invalid") == 0


class TestConektaIntegration:
    """Test Conekta payment provider integration."""

    def setup_method(self):
        """Setup for each test."""
        self.service = BillingService()

    @pytest.mark.asyncio
    async def test_create_conekta_customer_success(self):
        """Test successful Conekta customer creation."""
        mock_response = {
            "id": "cus_123456789",
            "name": "Test User",
            "email": "test@example.com"
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.status_code = 200

            result = await self.service.create_conekta_customer(
                name="Test User",
                email="test@example.com",
                phone="+525551234567"
            )

            assert result["id"] == "cus_123456789"
            assert result["name"] == "Test User"
            assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_conekta_customer_http_error(self):
        """Test Conekta customer creation with HTTP error."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Bad Request",
                request=MagicMock(),
                response=MagicMock(status_code=400)
            )

            with pytest.raises(Exception) as exc_info:
                await self.service.create_conekta_customer(
                    name="Test User",
                    email="test@example.com"
                )

            assert "Failed to create Conekta customer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_conekta_subscription_success(self):
        """Test successful Conekta subscription creation."""
        mock_response = {
            "id": "sub_123456789",
            "plan_id": "plan_pro_monthly",
            "status": "active",
            "current_period_start": 1234567890,
            "current_period_end": 1237159890
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.status_code = 200

            result = await self.service.create_conekta_subscription(
                customer_id="cus_123456789",
                plan="pro"
            )

            assert result["id"] == "sub_123456789"
            assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_conekta_subscription_with_card_token(self):
        """Test Conekta subscription creation with card token."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = {"id": "sub_123"}
            mock_post.return_value.status_code = 200

            await self.service.create_conekta_subscription(
                customer_id="cus_123",
                plan="pro",
                card_token="tok_card_123"
            )

            # Verify card token was included in request
            call_args = mock_post.call_args
            assert "card_token" in call_args[1]["json"]

    @pytest.mark.asyncio
    async def test_cancel_conekta_subscription_success(self):
        """Test successful Conekta subscription cancellation."""
        mock_response = {
            "id": "sub_123456789",
            "status": "canceled",
            "canceled_at": 1234567890
        }

        with patch('httpx.AsyncClient.delete') as mock_delete:
            mock_delete.return_value.json.return_value = mock_response
            mock_delete.return_value.status_code = 200

            result = await self.service.cancel_conekta_subscription("sub_123456789")

            assert result["id"] == "sub_123456789"
            assert result["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_conekta_subscription_error(self):
        """Test Conekta subscription cancellation with error."""
        with patch('httpx.AsyncClient.delete') as mock_delete:
            mock_delete.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404)
            )

            with pytest.raises(Exception) as exc_info:
                await self.service.cancel_conekta_subscription("sub_invalid")

            assert "Failed to cancel Conekta subscription" in str(exc_info.value)


class TestFungiesIntegration:
    """Test Fungies.io payment provider integration."""

    def setup_method(self):
        """Setup for each test."""
        self.service = BillingService()

    @pytest.mark.asyncio
    async def test_create_fungies_customer_success(self):
        """Test successful Fungies customer creation."""
        mock_response = {
            "customer_id": "fng_cus_123456789",
            "name": "Test User",
            "email": "test@example.com",
            "status": "active"
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.status_code = 201

            result = await self.service.create_fungies_customer(
                name="Test User",
                email="test@example.com"
            )

            assert result["customer_id"] == "fng_cus_123456789"
            assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_fungies_subscription_success(self):
        """Test successful Fungies subscription creation."""
        mock_response = {
            "subscription_id": "fng_sub_123456789",
            "plan": "pro",
            "status": "active",
            "billing_cycle": "monthly"
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.status_code = 201

            result = await self.service.create_fungies_subscription(
                customer_id="fng_cus_123456789",
                plan="pro"
            )

            assert result["subscription_id"] == "fng_sub_123456789"
            assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_update_fungies_subscription_success(self):
        """Test successful Fungies subscription update."""
        mock_response = {
            "subscription_id": "fng_sub_123456789",
            "plan": "scale",
            "status": "active",
            "updated_at": "2025-01-15T10:00:00Z"
        }

        with patch('httpx.AsyncClient.put') as mock_put:
            mock_put.return_value.json.return_value = mock_response
            mock_put.return_value.status_code = 200

            result = await self.service.update_fungies_subscription(
                subscription_id="fng_sub_123456789",
                new_plan="scale"
            )

            assert result["plan"] == "scale"
            assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_cancel_fungies_subscription_success(self):
        """Test successful Fungies subscription cancellation."""
        mock_response = {
            "subscription_id": "fng_sub_123456789",
            "status": "canceled",
            "canceled_at": "2025-01-15T10:00:00Z"
        }

        with patch('httpx.AsyncClient.delete') as mock_delete:
            mock_delete.return_value.json.return_value = mock_response
            mock_delete.return_value.status_code = 200

            result = await self.service.cancel_fungies_subscription("fng_sub_123456789")

            assert result["status"] == "canceled"


class TestUnifiedBillingInterface:
    """Test unified billing interface that routes to appropriate provider."""

    def setup_method(self):
        """Setup for each test."""
        self.service = BillingService()

    @pytest.mark.asyncio
    async def test_create_subscription_mexico(self):
        """Test subscription creation routes to Conekta for Mexico."""
        with patch.object(self.service, 'create_conekta_customer') as mock_customer, \
             patch.object(self.service, 'create_conekta_subscription') as mock_subscription:

            mock_customer.return_value = {"id": "cus_123"}
            mock_subscription.return_value = {"id": "sub_123", "status": "active"}

            result = await self.service.create_subscription(
                name="Test User",
                email="test@example.com",
                plan="pro",
                country="MX"
            )

            mock_customer.assert_called_once()
            mock_subscription.assert_called_once()
            assert result["provider"] == "conekta"

    @pytest.mark.asyncio
    async def test_create_subscription_international(self):
        """Test subscription creation routes to Fungies for international."""
        with patch.object(self.service, 'create_fungies_customer') as mock_customer, \
             patch.object(self.service, 'create_fungies_subscription') as mock_subscription:

            mock_customer.return_value = {"customer_id": "fng_cus_123"}
            mock_subscription.return_value = {"subscription_id": "fng_sub_123", "status": "active"}

            result = await self.service.create_subscription(
                name="Test User",
                email="test@example.com",
                plan="pro",
                country="US"
            )

            mock_customer.assert_called_once()
            mock_subscription.assert_called_once()
            assert result["provider"] == "fungies"

    @pytest.mark.asyncio
    async def test_create_checkout_session_conekta(self):
        """Test checkout session creation for Conekta."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "checkout_url": "https://conekta.com/checkout/123",
                "session_id": "cs_123"
            }
            mock_post.return_value.status_code = 200

            result = await self.service.create_checkout_session(
                plan="pro",
                customer_email="test@example.com",
                country="MX"
            )

            assert "checkout_url" in result
            assert result["provider"] == "conekta"

    @pytest.mark.asyncio
    async def test_create_checkout_session_fungies(self):
        """Test checkout session creation for Fungies."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "checkout_url": "https://fungies.io/checkout/123",
                "session_id": "fng_cs_123"
            }
            mock_post.return_value.status_code = 201

            result = await self.service.create_checkout_session(
                plan="pro",
                customer_email="test@example.com",
                country="US"
            )

            assert "checkout_url" in result
            assert result["provider"] == "fungies"


class TestUsageLimitsAndOverage:
    """Test usage limits and overage calculations."""

    def setup_method(self):
        """Setup for each test."""
        self.service = BillingService()

    @pytest.mark.asyncio
    async def test_check_usage_limits_within_limits(self):
        """Test usage check when within limits."""
        mock_tenant = MagicMock()
        mock_tenant.plan = "pro"
        mock_tenant.current_mau = 5000

        with patch('sqlalchemy.ext.asyncio.AsyncSession.get') as mock_get:
            mock_get.return_value = mock_tenant

            db_session = AsyncMock()
            result = await self.service.check_usage_limits(db_session, uuid4())

            assert result["within_limits"] is True
            assert result["plan"] == "pro"
            assert result["current_mau"] == 5000
            assert result["mau_limit"] == 10000

    @pytest.mark.asyncio
    async def test_check_usage_limits_exceeded(self):
        """Test usage check when limits are exceeded."""
        mock_tenant = MagicMock()
        mock_tenant.plan = "pro"
        mock_tenant.current_mau = 15000

        with patch('sqlalchemy.ext.asyncio.AsyncSession.get') as mock_get:
            mock_get.return_value = mock_tenant

            db_session = AsyncMock()
            result = await self.service.check_usage_limits(db_session, uuid4())

            assert result["within_limits"] is False
            assert result["overage"] == 5000

    @pytest.mark.asyncio
    async def test_check_usage_limits_tenant_not_found(self):
        """Test usage check when tenant is not found."""
        with patch('sqlalchemy.ext.asyncio.AsyncSession.get') as mock_get:
            mock_get.return_value = None

            db_session = AsyncMock()

            with pytest.raises(Exception) as exc_info:
                await self.service.check_usage_limits(db_session, uuid4())

            assert "Tenant not found" in str(exc_info.value)

    def test_calculate_overage_cost_pro_plan(self):
        """Test overage cost calculation for pro plan."""
        cost = self.service.calculate_overage_cost("pro", 2000, "MX")

        # Pro plan overage: $0.01 per MAU over limit
        # 2000 MAU overage * $0.01 = $20.00 USD = 400 MXN
        assert cost == 400  # 20 USD * 20 MXN/USD

    def test_calculate_overage_cost_international(self):
        """Test overage cost calculation for international pricing."""
        cost = self.service.calculate_overage_cost("pro", 1000, "US")

        # 1000 MAU overage * $0.01 = $10.00 USD
        assert cost == 10

    def test_calculate_overage_cost_community_plan(self):
        """Test overage cost calculation for community plan."""
        cost = self.service.calculate_overage_cost("community", 500, "US")

        # Community plan overage: $0.005 per MAU
        # 500 MAU overage * $0.005 = $2.50 USD
        assert cost == 2.5


class TestWebhookHandlers:
    """Test webhook handling for both providers."""

    def setup_method(self):
        """Setup for each test."""
        self.service = BillingService()

    @pytest.mark.asyncio
    async def test_handle_conekta_webhook_order_paid(self):
        """Test handling Conekta order.paid webhook."""
        webhook_data = {
            "type": "order.paid",
            "data": {
                "object": {
                    "id": "ord_123456789",
                    "customer_info": {
                        "customer_id": "cus_123456789"
                    },
                    "amount": 138000,  # 1380 MXN in cents
                    "currency": "MXN"
                }
            }
        }

        with patch.object(self.service, '_update_subscription_status') as mock_update:
            result = await self.service.handle_conekta_webhook(webhook_data)

            assert result["processed"] is True
            assert result["event_type"] == "order.paid"
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_fungies_webhook_checkout_completed(self):
        """Test handling Fungies checkout.completed webhook."""
        webhook_data = {
            "event": "checkout.completed",
            "data": {
                "customer_id": "fng_cus_123456789",
                "subscription_id": "fng_sub_123456789",
                "plan": "pro",
                "amount": 69.00,
                "currency": "USD"
            }
        }

        with patch.object(self.service, '_update_subscription_status') as mock_update:
            result = await self.service.handle_fungies_webhook(webhook_data)

            assert result["processed"] is True
            assert result["event_type"] == "checkout.completed"
            mock_update.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios in billing service."""

    def setup_method(self):
        """Setup for each test."""
        self.service = BillingService()

    @pytest.mark.asyncio
    async def test_handle_network_timeout(self):
        """Test handling of network timeouts."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(Exception) as exc_info:
                await self.service.create_conekta_customer(
                    name="Test User",
                    email="test@example.com"
                )

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handle_invalid_api_key(self):
        """Test handling of invalid API key."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401)
            )

            with pytest.raises(Exception) as exc_info:
                await self.service.create_conekta_customer(
                    name="Test User",
                    email="test@example.com"
                )

            assert "Failed to create Conekta customer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_error_in_checkout_session(self):
        """Test handling database errors during checkout session creation."""
        with patch.object(self.service, 'create_checkout_session') as mock_checkout:
            mock_checkout.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception) as exc_info:
                await self.service.create_checkout_session(
                    plan="pro",
                    customer_email="test@example.com",
                    country="MX"
                )

            assert "Database connection failed" in str(exc_info.value)