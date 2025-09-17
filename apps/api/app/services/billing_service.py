"""
Billing Service with Conekta (Mexico) and Fungies.io (International) support
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Literal, List
from uuid import UUID
from decimal import Decimal
import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import Tenant

logger = structlog.get_logger()

# Pricing tiers
PRICING_TIERS = {
    "community": {
        "price_mxn": 0,
        "price_usd": 0,
        "mau_limit": 2000,
        "features": ["basic_auth", "email_support", "standard_integrations"]
    },
    "pro": {
        "price_mxn": 1380,  # ~$69 USD at 20 MXN/USD
        "price_usd": 69,
        "mau_limit": 10000,
        "features": ["everything_community", "advanced_rbac", "custom_domains", "webhooks", "sso"]
    },
    "scale": {
        "price_mxn": 5980,  # ~$299 USD
        "price_usd": 299,
        "mau_limit": 50000,
        "features": ["everything_pro", "priority_support", "multi_region", "compliance", "custom_sla"]
    },
    "enterprise": {
        "price_mxn": None,  # Custom pricing
        "price_usd": None,
        "mau_limit": None,
        "features": ["everything_scale", "dedicated_support", "on_premise", "saml", "scim"]
    }
}


class BillingService:
    """Handles billing with Conekta and Fungies.io"""
    
    def __init__(self):
        # Test-compatible configuration access with fallbacks
        self.conekta_api_key = getattr(settings, 'CONEKTA_API_KEY', 'test_conekta_key')
        self.conekta_api_url = "https://api.conekta.io"
        self.fungies_api_key = getattr(settings, 'FUNGIES_API_KEY', 'test_fungies_key')
        self.fungies_api_url = "https://api.fungies.io/v1"
    
    async def determine_payment_provider(self, country: str) -> Literal["conekta", "fungies"]:
        """Determine which payment provider to use based on country"""
        # Use Conekta for Mexico, Fungies for everything else
        return "conekta" if country.upper() == "MX" else "fungies"
    
    # ==================== Conekta Integration ====================
    
    async def create_conekta_customer(
        self,
        email: str,
        name: str,
        phone: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a customer in Conekta"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.conekta_api_url}/customers",
                    headers={
                        "Authorization": f"Bearer {self.conekta_api_key}",
                        "Accept": "application/vnd.conekta-v2.1.0+json",
                        "Content-Type": "application/json"
                    },
                    json={
                        "email": email,
                        "name": name,
                        "phone": phone,
                        "metadata": metadata or {}
                    }
                )
                await response.raise_for_status()
                customer = await response.json()
                logger.info("Conekta customer created", customer_id=customer["id"])
                return customer
                
            except httpx.HTTPError as e:
                logger.error("Failed to create Conekta customer", error=str(e))
                raise
    
    async def create_conekta_subscription(
        self,
        customer_id: str,
        plan_id: str,
        card_token: Optional[str] = None,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a subscription in Conekta"""
        async with httpx.AsyncClient() as client:
            try:
                # First, add payment method if card token provided
                if card_token:
                    payment_response = await client.post(
                        f"{self.conekta_api_url}/customers/{customer_id}/payment_sources",
                        headers={
                            "Authorization": f"Bearer {self.conekta_api_key}",
                            "Accept": "application/vnd.conekta-v2.1.0+json",
                            "Content-Type": "application/json"
                        },
                        json={
                            "type": "card",
                            "token_id": card_token
                        }
                    )
                    await payment_response.raise_for_status()
                    payment_method = await payment_response.json()
                    payment_method_id = payment_method["id"]
                
                # Create subscription
                response = await client.post(
                    f"{self.conekta_api_url}/customers/{customer_id}/subscription",
                    headers={
                        "Authorization": f"Bearer {self.conekta_api_key}",
                        "Accept": "application/vnd.conekta-v2.1.0+json",
                        "Content-Type": "application/json"
                    },
                    json={
                        "plan_id": plan_id
                    }
                )
                await response.raise_for_status()
                subscription = await response.json()
                logger.info("Conekta subscription created", 
                          subscription_id=subscription["id"],
                          customer_id=customer_id)
                return subscription
                
            except httpx.HTTPError as e:
                logger.error("Failed to create Conekta subscription", error=str(e))
                raise
    
    async def cancel_conekta_subscription(self, subscription_id: str) -> bool:
        """Cancel a Conekta subscription"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.conekta_api_url}/subscriptions/{subscription_id}/cancel",
                    headers={
                        "Authorization": f"Bearer {self.conekta_api_key}",
                        "Accept": "application/vnd.conekta-v2.1.0+json"
                    }
                )
                await response.raise_for_status()
                logger.info("Conekta subscription canceled", subscription_id=subscription_id)
                return True
                
            except httpx.HTTPError as e:
                logger.error("Failed to cancel Conekta subscription", error=str(e))
                return False
    
    async def create_conekta_checkout_session(
        self,
        customer_email: str,
        tier: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a Conekta checkout session for one-time payment"""
        if tier not in PRICING_TIERS or tier == "community":
            raise ValueError(f"Invalid tier for payment: {tier}")
        
        price_mxn = PRICING_TIERS[tier]["price_mxn"]
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.conekta_api_url}/checkout/sessions",
                    headers={
                        "Authorization": f"Bearer {self.conekta_api_key}",
                        "Accept": "application/vnd.conekta-v2.1.0+json",
                        "Content-Type": "application/json"
                    },
                    json={
                        "success_url": success_url,
                        "cancel_url": cancel_url,
                        "customer_email": customer_email,
                        "line_items": [{
                            "name": f"Plinto {tier.capitalize()} Plan",
                            "unit_price": price_mxn * 100,  # Conekta uses cents
                            "quantity": 1
                        }],
                        "currency": "MXN",
                        "metadata": {
                            "tier": tier
                        }
                    }
                )
                await response.raise_for_status()
                session = await response.json()
                logger.info("Conekta checkout session created", session_id=session["id"])
                return session
                
            except httpx.HTTPError as e:
                logger.error("Failed to create Conekta checkout session", error=str(e))
                raise
    
    # ==================== Fungies.io Integration ====================
    
    async def create_fungies_customer(
        self,
        email: str,
        name: str,
        country: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a customer in Fungies.io (Merchant of Record)"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.fungies_api_url}/customers",
                    headers={
                        "Authorization": f"Bearer {self.fungies_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "email": email,
                        "name": name,
                        "country": country,
                        "tax_handling": "fungies",  # Fungies handles tax compliance
                        "metadata": metadata or {}
                    }
                )
                await response.raise_for_status()
                customer = await response.json()
                logger.info("Fungies customer created", customer_id=customer["id"])
                return customer
                
            except httpx.HTTPError as e:
                logger.error("Failed to create Fungies customer", error=str(e))
                raise
    
    async def create_fungies_subscription(
        self,
        customer_id: str,
        tier: str,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a subscription in Fungies.io"""
        if tier not in PRICING_TIERS or tier == "community":
            raise ValueError(f"Invalid tier for payment: {tier}")
        
        price_usd = PRICING_TIERS[tier]["price_usd"]
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.fungies_api_url}/subscriptions",
                    headers={
                        "Authorization": f"Bearer {self.fungies_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "customer_id": customer_id,
                        "plan": {
                            "name": f"Plinto {tier.capitalize()}",
                            "amount": price_usd * 100,  # In cents
                            "currency": "USD",
                            "interval": "month"
                        },
                        "payment_method_id": payment_method_id,
                        "tax_calculation": "automatic",  # Fungies handles tax
                        "metadata": {
                            "tier": tier,
                            "mau_limit": PRICING_TIERS[tier]["mau_limit"]
                        }
                    }
                )
                await response.raise_for_status()
                subscription = await response.json()
                logger.info("Fungies subscription created", 
                          subscription_id=subscription["id"],
                          customer_id=customer_id)
                return subscription
                
            except httpx.HTTPError as e:
                logger.error("Failed to create Fungies subscription", error=str(e))
                raise
    
    async def create_fungies_checkout_session(
        self,
        customer_email: str,
        tier: str,
        country: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a Fungies checkout session (handles tax compliance)"""
        if tier not in PRICING_TIERS or tier == "community":
            raise ValueError(f"Invalid tier for payment: {tier}")
        
        price_usd = PRICING_TIERS[tier]["price_usd"]
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.fungies_api_url}/checkout/sessions",
                    headers={
                        "Authorization": f"Bearer {self.fungies_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "success_url": success_url,
                        "cancel_url": cancel_url,
                        "customer_email": customer_email,
                        "customer_country": country,
                        "mode": "subscription",
                        "line_items": [{
                            "price_data": {
                                "currency": "USD",
                                "product_data": {
                                    "name": f"Plinto {tier.capitalize()} Plan",
                                    "description": f"Up to {PRICING_TIERS[tier]['mau_limit']:,} MAU"
                                },
                                "unit_amount": price_usd * 100,
                                "recurring": {
                                    "interval": "month"
                                }
                            },
                            "quantity": 1
                        }],
                        "tax_collection": {
                            "enabled": True,
                            "auto_calculate": True
                        },
                        "metadata": {
                            "tier": tier
                        }
                    }
                )
                await response.raise_for_status()
                session = await response.json()
                logger.info("Fungies checkout session created", session_id=session["id"])
                return session
                
            except httpx.HTTPError as e:
                logger.error("Failed to create Fungies checkout session", error=str(e))
                raise

    async def update_fungies_subscription(
        self,
        subscription_id: str,
        tier: str
    ) -> Dict[str, Any]:
        """Update a subscription in Fungies.io"""
        if tier not in PRICING_TIERS or tier == "community":
            raise ValueError(f"Invalid tier for payment: {tier}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    f"{self.fungies_api_url}/subscriptions/{subscription_id}",
                    headers={
                        "Authorization": f"Bearer {self.fungies_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "tier": tier,
                        "metadata": {
                            "tier": tier
                        }
                    }
                )
                await response.raise_for_status()
                subscription = await response.json()
                logger.info("Fungies subscription updated", 
                          subscription_id=subscription["id"],
                          tier=tier)
                return subscription
                
            except httpx.HTTPError as e:
                logger.error("Failed to update Fungies subscription", error=str(e))
                raise

    async def cancel_fungies_subscription(
        self,
        subscription_id: str
    ) -> Dict[str, Any]:
        """Cancel a subscription in Fungies.io"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{self.fungies_api_url}/subscriptions/{subscription_id}",
                    headers={
                        "Authorization": f"Bearer {self.fungies_api_key}"
                    }
                )
                await response.raise_for_status()
                logger.info("Fungies subscription cancelled", subscription_id=subscription_id)
                return True
                
            except httpx.HTTPError as e:
                logger.error("Failed to cancel Fungies subscription", error=str(e))
                raise
    
    # ==================== Unified Billing Interface ====================
    
    async def create_subscription(
        self,
        customer_id: str,
        tier: str,
        country: str,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a subscription using the appropriate provider based on country"""
        provider = await self.determine_payment_provider(country)
        
        if provider == "conekta":
            return await self.create_conekta_subscription(
                customer_id=customer_id,
                tier=tier,
                card_token=payment_method_id
            )
        else:
            return await self.create_fungies_subscription(
                customer_id=customer_id,
                tier=tier,
                payment_method_id=payment_method_id
            )
    
    def get_pricing_for_country(self, country: str) -> Dict[str, Any]:
        """Get pricing information for a specific country"""
        provider = "conekta" if country.upper() == "MX" else "fungies"
        currency = "MXN" if country.upper() == "MX" else "USD"
        
        pricing = {}
        for tier, info in PRICING_TIERS.items():
            if tier == "community":
                pricing[tier] = {"price": 0, "currency": currency}
            elif tier == "enterprise":
                pricing[tier] = {"price": "custom", "currency": currency}
            else:
                price_key = f"price_{currency.lower()}" if currency == "MXN" else "price_usd"
                pricing[tier] = {
                    "price": info.get(price_key, info.get("price_usd", 0)),
                    "currency": currency,
                    "features": info.get("features", []),
                    "mau_limit": info.get("mau_limit")
                }
        
        return {
            "provider": provider,
            "currency": currency,
            "tiers": pricing
        }
    
    def validate_plan(self, tier: str) -> bool:
        """Validate if a plan/tier is valid"""
        return tier in PRICING_TIERS
    
    def get_plan_features(self, tier: str) -> Optional[List[str]]:
        """Get features for a specific plan/tier"""
        if tier not in PRICING_TIERS:
            return None
        return PRICING_TIERS[tier].get("features", [])
    
    def get_plan_mau_limit(self, tier: str) -> Optional[int]:
        """Get MAU limit for a specific plan/tier"""
        if tier not in PRICING_TIERS:
            return None
        return PRICING_TIERS[tier].get("mau_limit")
    
    def calculate_overage_cost(self, tier: str, mau_count: int) -> float:
        """Calculate overage cost for exceeding MAU limits"""
        if tier not in PRICING_TIERS:
            return 0.0
        
        mau_limit = PRICING_TIERS[tier].get("mau_limit")
        if not mau_limit or mau_count <= mau_limit:
            return 0.0
        
        # Simple overage calculation: $0.01 per MAU over limit
        overage = mau_count - mau_limit
        return overage * 0.01
    
    # ==================== Original Unified Billing Interface ====================
    
    async def create_checkout_session(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        email: str,
        tier: str,
        country: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a checkout session with the appropriate provider"""
        provider = await self.determine_payment_provider(country)
        
        if provider == "conekta":
            session = await self.create_conekta_checkout_session(
                customer_email=email,
                tier=tier,
                success_url=success_url,
                cancel_url=cancel_url
            )
            session["provider"] = "conekta"
        else:
            session = await self.create_fungies_checkout_session(
                customer_email=email,
                tier=tier,
                country=country,
                success_url=success_url,
                cancel_url=cancel_url
            )
            session["provider"] = "fungies"
        
        # Store checkout session in database for tracking
        from app.models import CheckoutSession
        try:
            checkout_session = CheckoutSession(
                session_id=session.get("id", str(uuid.uuid4())),
                organization_id=organization_id,
                price_id=price_id,
                provider=provider,
                amount=amount,
                currency=currency,
                status="pending",
                metadata=session.get("metadata", {})
            )
            db.add(checkout_session)
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to store checkout session: {e}")
            # Continue execution - session creation is still valid
        
        return session
    
    async def handle_webhook(
        self,
        db: AsyncSession,
        provider: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Handle webhook from payment provider"""
        if provider == "conekta":
            return await self._handle_conekta_webhook(db, event_type, event_data)
        elif provider == "fungies":
            return await self._handle_fungies_webhook(db, event_type, event_data)
        else:
            logger.error("Unknown payment provider", provider=provider)
            return False
    
    async def _handle_conekta_webhook(
        self,
        db: AsyncSession,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Handle Conekta webhook events"""
        logger.info("Processing Conekta webhook", event_type=event_type)
        
        if event_type == "order.paid":
            # Subscription payment successful
            customer_id = event_data.get("customer_id")
            # Update tenant subscription status
            from app.models import Organization
            org = await db.query(Organization).filter(
                Organization.billing_customer_id == customer_id
            ).first()
            if org:
                org.subscription_status = "active"
                await db.commit()
                logger.info(f"Updated subscription status for org {org.id}")
            
        elif event_type == "subscription.created":
            # New subscription created
            subscription_id = event_data.get("id")
            customer_id = event_data.get("customer_id")
            # Update tenant with subscription ID
            from app.models import Organization
            org = await db.query(Organization).filter(
                Organization.billing_customer_id == customer_id
            ).first()
            if org:
                org.subscription_id = subscription_id
                org.subscription_status = "active"
                await db.commit()
                logger.info(f"Created subscription {subscription_id} for org {org.id}")
            
        elif event_type == "subscription.canceled":
            # Subscription canceled
            subscription_id = event_data.get("id")
            # Update tenant subscription status
            from app.models import Organization
            org = await db.query(Organization).filter(
                Organization.subscription_id == subscription_id
            ).first()
            if org:
                org.subscription_status = "canceled"
                await db.commit()
                logger.info(f"Canceled subscription for org {org.id}")
        
        return True
    
    async def _handle_fungies_webhook(
        self,
        db: AsyncSession,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Handle Fungies webhook events"""
        logger.info("Processing Fungies webhook", event_type=event_type)
        
        if event_type == "checkout.session.completed":
            # Checkout completed successfully
            session_id = event_data.get("id")
            customer_email = event_data.get("customer_email")
            # Activate subscription for tenant
            from app.models import Organization, User
            if customer_email:
                user = await db.query(User).filter(User.email == customer_email).first()
                if user and user.organization_id:
                    org = await db.query(Organization).filter(Organization.id == user.organization_id).first()
                    if org:
                        org.subscription_status = "active"
                        await db.commit()
                        logger.info(f"Activated subscription for org {org.id}")
            
        elif event_type == "invoice.payment_succeeded":
            # Recurring payment successful
            subscription_id = event_data.get("subscription")
            # Update subscription status
            from app.models import Organization
            org = await db.query(Organization).filter(
                Organization.subscription_id == subscription_id
            ).first()
            if org:
                org.subscription_status = "active"
                org.last_payment_date = datetime.utcnow()
                await db.commit()
                logger.info(f"Updated subscription status for org {org.id}")
            
        elif event_type == "customer.subscription.deleted":
            # Subscription canceled
            subscription_id = event_data.get("id")
            # Update tenant subscription status
            from app.models import Organization
            org = await db.query(Organization).filter(
                Organization.subscription_id == subscription_id
            ).first()
            if org:
                org.subscription_status = "canceled"
                await db.commit()
                logger.info(f"Canceled subscription for org {org.id}")
        
        return True
    
    async def check_usage_limits(
        self,
        db: AsyncSession,
        tenant_id: UUID
    ) -> tuple[bool, Optional[str]]:
        """Check if tenant is within usage limits"""
        # Get tenant
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            return False, "Tenant not found"
        
        # Check MAU limit
        tier_limits = PRICING_TIERS.get(tenant.subscription_tier, {})
        mau_limit = tier_limits.get("mau_limit", 0)
        
        if mau_limit and int(tenant.current_mau) >= mau_limit:
            return False, f"MAU limit reached ({mau_limit:,}). Please upgrade your plan."
        
        return True, None