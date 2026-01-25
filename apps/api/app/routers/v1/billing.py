"""
Billing and subscription management endpoints
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.v1.auth import get_current_user

from ...models import Plan, User

router = APIRouter(prefix="/billing", tags=["billing"])


class PlanResponse(BaseModel):
    """Plan response model"""

    id: str
    name: str
    description: Optional[str]
    price_monthly: int  # Price in cents
    price_yearly: int  # Price in cents
    features: List[str]
    max_users: Optional[int]
    max_organizations: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PlansListResponse(BaseModel):
    """List of available plans"""

    plans: List[PlanResponse]
    total: int


@router.get("/plans", response_model=PlansListResponse)
async def list_plans(
    include_inactive: bool = Query(False, description="Include inactive plans"),
    db: Session = Depends(get_db),
):
    """
    List available billing plans.

    Returns all active plans by default. Admin users can request inactive plans.
    """
    stmt = select(Plan)

    if not include_inactive:
        stmt = stmt.where(Plan.is_active == True)

    stmt = stmt.order_by(Plan.price_monthly.asc())

    result = await db.execute(stmt)
    plans = result.scalars().all()

    return PlansListResponse(
        plans=[
            PlanResponse(
                id=str(plan.id),
                name=plan.name,
                description=plan.description,
                price_monthly=plan.price_monthly or 0,
                price_yearly=plan.price_yearly or 0,
                features=plan.features or [],
                max_users=plan.max_users,
                max_organizations=plan.max_organizations,
                is_active=plan.is_active,
                created_at=plan.created_at,
                updated_at=plan.updated_at,
            )
            for plan in plans
        ],
        total=len(plans),
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a specific billing plan by ID.
    """
    import uuid

    try:
        plan_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    result = await db.execute(select(Plan).where(Plan.id == plan_uuid))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        description=plan.description,
        price_monthly=plan.price_monthly or 0,
        price_yearly=plan.price_yearly or 0,
        features=plan.features or [],
        max_users=plan.max_users,
        max_organizations=plan.max_organizations,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("/current", response_model=dict)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current user's subscription status.
    """
    # TODO: Implement full subscription management
    # For now, return a basic structure indicating free tier
    return {
        "user_id": str(current_user.id),
        "plan": "free",
        "status": "active",
        "features": {
            "max_organizations": 1,
            "max_users_per_org": 5,
            "api_rate_limit": 1000,
            "sso_enabled": False,
            "audit_logs": False,
            "custom_branding": False,
        },
        "billing_cycle": None,
        "next_billing_date": None,
        "created_at": current_user.created_at.isoformat(),
    }
