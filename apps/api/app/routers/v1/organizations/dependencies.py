"""
Shared dependencies and utilities for organization routes
"""

import uuid
from typing import Optional
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models import User, Organization, organization_members
from app.routers.v1.auth import get_current_user
from .schemas import OrganizationRole


def get_user_organization_role(db: Session, user_id: uuid.UUID, org_id: uuid.UUID) -> Optional[str]:
    """Get user's role in an organization"""
    member = db.query(organization_members).filter(
        and_(
            organization_members.c.user_id == user_id,
            organization_members.c.organization_id == org_id
        )
    ).first()

    return member.role if member else None


def check_organization_permission(
    db: Session,
    user: User,
    org_id: uuid.UUID,
    required_role: str = "member"
) -> Organization:
    """Check if user has required permission in organization"""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Owner always has access
    if org.owner_id == user.id:
        return org

    # Check membership and role
    user_role = get_user_organization_role(db, user.id, org_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    # Role hierarchy: owner > admin > member > guest
    role_hierarchy = {
        "guest": 0,
        "member": 1,
        "admin": 2,
        "owner": 3
    }

    if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return org


def check_organization_admin_permission(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Organization:
    """Dependency to check admin permission for organization"""
    return check_organization_permission(
        db, current_user, uuid.UUID(org_id), "admin"
    )


def check_organization_member_permission(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Organization:
    """Dependency to check member permission for organization"""
    return check_organization_permission(
        db, current_user, uuid.UUID(org_id), "member"
    )


def check_organization_owner_permission(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Organization:
    """Dependency to check owner permission for organization"""
    org = db.query(Organization).filter(Organization.id == uuid.UUID(org_id)).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only organization owner can perform this action")

    return org


def validate_unique_slug(db: Session, slug: str, exclude_org_id: Optional[uuid.UUID] = None) -> bool:
    """Validate that organization slug is unique"""
    query = db.query(Organization).filter(Organization.slug == slug)

    if exclude_org_id:
        query = query.filter(Organization.id != exclude_org_id)

    existing_org = query.first()
    if existing_org:
        raise HTTPException(status_code=400, detail="Organization slug already exists")

    return True


def validate_invitation_email(db: Session, org_id: uuid.UUID, email: str) -> bool:
    """Validate invitation email (not already a member or pending invitation)"""
    from app.models import OrganizationInvitation

    # Check if user is already a member
    user_query = db.query(User).filter(User.email == email).first()
    if user_query:
        member_exists = db.query(organization_members).filter(
            and_(
                organization_members.c.user_id == user_query.id,
                organization_members.c.organization_id == org_id
            )
        ).first()

        if member_exists:
            raise HTTPException(status_code=400, detail="User is already a member of this organization")

    # Check if there's already a pending invitation
    pending_invitation = db.query(OrganizationInvitation).filter(
        and_(
            OrganizationInvitation.organization_id == org_id,
            OrganizationInvitation.email == email,
            OrganizationInvitation.status == "pending"
        )
    ).first()

    if pending_invitation:
        raise HTTPException(status_code=400, detail="There is already a pending invitation for this email")

    return True


def get_organization_permissions(role: str, custom_permissions: Optional[list] = None) -> list:
    """Get permissions for a given role"""
    base_permissions = {
        "guest": ["view_organization"],
        "member": ["view_organization", "view_members"],
        "admin": ["view_organization", "view_members", "manage_members", "manage_settings"],
        "owner": ["view_organization", "view_members", "manage_members", "manage_settings", "manage_billing", "delete_organization"]
    }

    permissions = base_permissions.get(role, [])

    if custom_permissions:
        permissions.extend(custom_permissions)

    return list(set(permissions))  # Remove duplicates