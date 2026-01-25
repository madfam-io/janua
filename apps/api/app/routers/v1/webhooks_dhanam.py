"""
Dhanam Billing Webhooks - Updates organization subscription_tier

Handles subscription events from Dhanam billing system to keep Janua
organization tiers in sync for Enclii feature gating via foundry_tier JWT claim.

Tier Mapping:
- Dhanam "sovereign" -> Janua "pro" -> Enclii "sovereign" foundry_tier
- Dhanam "ecosystem" -> Janua "enterprise" -> Enclii "ecosystem" foundry_tier

The SSO orchestrator (sso_orchestrator.py) maps Janua tiers to Enclii foundry_tier:
- community -> community
- pro/sovereign -> sovereign
- enterprise/ecosystem -> ecosystem
"""

import hashlib
import hmac
from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.models import Organization

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks/dhanam", tags=["webhooks"])

# Dhanam plan_id -> Janua subscription_tier mapping
# These align with DHANAM_TO_JANUA_TIER in billing.py for consistency
DHANAM_PLAN_TIER_MAP = {
    # Community tier
    "free": "community",
    "community": "community",
    "trial": "community",
    "enclii_community": "community",
    # Pro tier (maps to sovereign in Enclii via SSO orchestrator)
    "pro": "pro",
    "sovereign": "pro",
    "pro_monthly": "pro",
    "pro_annual": "pro",
    "enclii_sovereign": "pro",
    # Scale tier
    "scale": "scale",
    "scale_monthly": "scale",
    "scale_annual": "scale",
    # Enterprise tier (maps to ecosystem in Enclii via SSO orchestrator)
    "enterprise": "enterprise",
    "ecosystem": "enterprise",
    "enterprise_monthly": "enterprise",
    "enterprise_annual": "enterprise",
    "enclii_ecosystem": "enterprise",
}


def verify_dhanam_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Dhanam webhook HMAC-SHA256 signature."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def map_dhanam_plan_to_tier(plan_id: str) -> str:
    """Map Dhanam plan_id to Janua subscription_tier."""
    if not plan_id:
        return "community"
    return DHANAM_PLAN_TIER_MAP.get(plan_id.lower(), "community")


async def find_organization(
    db: AsyncSession,
    customer_id: str | None,
    org_id: str | None,
    metadata: dict | None = None,
) -> Organization | None:
    """
    Find organization using multiple lookup strategies:
    1. By billing_customer_id (primary)
    2. By organization_id in metadata
    3. By explicit org_id parameter
    """
    organization = None

    # Strategy 1: Lookup by billing_customer_id
    if customer_id:
        result = await db.execute(
            select(Organization).where(Organization.billing_customer_id == customer_id)
        )
        organization = result.scalar_one_or_none()
        if organization:
            logger.debug(
                "Found organization by billing_customer_id",
                org_id=str(organization.id),
                customer_id=customer_id,
            )
            return organization

    # Strategy 2: Lookup by org_id from metadata
    if metadata and metadata.get("organization_id"):
        try:
            org_uuid = UUID(metadata["organization_id"])
            result = await db.execute(
                select(Organization).where(Organization.id == org_uuid)
            )
            organization = result.scalar_one_or_none()
            if organization:
                logger.debug(
                    "Found organization by metadata.organization_id",
                    org_id=str(organization.id),
                )
                # Also link the customer_id if we have it
                if customer_id and not organization.billing_customer_id:
                    organization.billing_customer_id = customer_id
                    logger.info(
                        "Linked billing_customer_id to organization",
                        org_id=str(organization.id),
                        customer_id=customer_id,
                    )
                return organization
        except (ValueError, TypeError) as e:
            logger.warning(
                "Invalid organization_id in metadata",
                org_id=metadata.get("organization_id"),
                error=str(e),
            )

    # Strategy 3: Direct org_id lookup
    if org_id:
        try:
            org_uuid = UUID(org_id)
            result = await db.execute(
                select(Organization).where(Organization.id == org_uuid)
            )
            organization = result.scalar_one_or_none()
            if organization:
                logger.debug(
                    "Found organization by direct org_id",
                    org_id=str(organization.id),
                )
                return organization
        except (ValueError, TypeError) as e:
            logger.warning(
                "Invalid org_id parameter",
                org_id=org_id,
                error=str(e),
            )

    return None


@router.post("/subscription")
async def dhanam_subscription_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_dhanam_signature: str = Header(..., alias="X-Dhanam-Signature"),
):
    """
    Handle Dhanam subscription events.

    Supported events:
    - subscription.created: New subscription, set tier
    - subscription.updated: Plan change, update tier
    - subscription.canceled: Subscription ended, downgrade to community

    Updates the organization's subscription_tier based on the Dhanam plan,
    which affects the foundry_tier claim in SSO JWT tokens for Enclii feature gating.

    Expected payload format:
    ```json
    {
        "type": "subscription.created" | "subscription.updated" | "subscription.canceled",
        "data": {
            "customer_id": "cust_xxx",
            "plan_id": "pro" | "sovereign" | "enterprise" | etc.,
            "metadata": {
                "organization_id": "uuid-optional-fallback"
            }
        }
    }
    ```
    """
    body = await request.body()

    # Verify signature
    if not settings.DHANAM_WEBHOOK_SECRET:
        logger.error("DHANAM_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=500,
            detail="Webhook secret not configured",
        )

    if not verify_dhanam_signature(body, x_dhanam_signature, settings.DHANAM_WEBHOOK_SECRET):
        logger.warning("Invalid Dhanam webhook signature")
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

    # Parse payload
    payload = await request.json()
    event_type = payload.get("type")
    event_data = payload.get("data", {})
    metadata = event_data.get("metadata", {})

    logger.info(
        "Received Dhanam webhook",
        event_type=event_type,
        customer_id=event_data.get("customer_id"),
        plan_id=event_data.get("plan_id"),
        has_metadata=bool(metadata),
    )

    # Handle supported events
    supported_events = (
        "subscription.created",
        "subscription.updated",
        "subscription.canceled",
        "subscription.deleted",
    )
    if event_type not in supported_events:
        logger.info("Ignoring unsupported event", event_type=event_type)
        return {"status": "ignored", "reason": "unsupported_event_type"}

    customer_id = event_data.get("customer_id")
    plan_id = event_data.get("plan_id")
    org_id = event_data.get("organization_id")

    # For cancel events, plan_id might be missing - that's OK
    if event_type in ("subscription.created", "subscription.updated"):
        if not plan_id:
            logger.warning("Missing plan_id for subscription event", event_type=event_type)
            raise HTTPException(
                status_code=400,
                detail="Missing plan_id in webhook payload",
            )

    # Find organization using multiple strategies
    organization = await find_organization(db, customer_id, org_id, metadata)

    if not organization:
        logger.warning(
            "Organization not found",
            customer_id=customer_id,
            org_id=org_id,
            metadata_org_id=metadata.get("organization_id"),
        )
        raise HTTPException(
            status_code=404,
            detail=f"Organization not found. Tried: customer_id={customer_id}, org_id={org_id}, metadata.organization_id={metadata.get('organization_id')}",
        )

    # Determine new tier based on event type
    old_tier = organization.subscription_tier
    if event_type in ("subscription.canceled", "subscription.deleted"):
        # Downgrade to community on cancellation
        new_tier = "community"
        logger.info(
            "Subscription canceled, downgrading to community",
            organization_id=str(organization.id),
        )
    else:
        new_tier = map_dhanam_plan_to_tier(plan_id)

    # Update organization
    organization.subscription_tier = new_tier
    organization.updated_at = datetime.utcnow()

    # Ensure billing_customer_id is linked
    if customer_id and not organization.billing_customer_id:
        organization.billing_customer_id = customer_id
        logger.info(
            "Linked billing_customer_id during webhook",
            organization_id=str(organization.id),
            customer_id=customer_id,
        )

    await db.commit()

    logger.info(
        "Subscription tier updated via Dhanam webhook",
        organization_id=str(organization.id),
        organization_name=organization.name,
        old_tier=old_tier,
        new_tier=new_tier,
        plan_id=plan_id,
        event_type=event_type,
    )

    return {
        "status": "processed",
        "organization_id": str(organization.id),
        "organization_name": organization.name,
        "old_tier": old_tier,
        "new_tier": new_tier,
        "event_type": event_type,
    }
