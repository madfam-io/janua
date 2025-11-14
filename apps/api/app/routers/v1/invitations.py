"""
Invitation management API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database import get_db
from app.dependencies import get_current_user, require_org_admin
from app.models.invitation import (
    Invitation, InvitationStatus,
    InvitationCreate, InvitationUpdate, InvitationResponse,
    InvitationAcceptRequest, InvitationAcceptResponse,
    InvitationListResponse, BulkInvitationCreate, BulkInvitationResponse
)
from app.models.user import User
from app.services.invitation_service import InvitationService
from app.services.auth_service import AuthService
from app.config import settings


router = APIRouter(prefix="/v1/invitations", tags=["invitations"])


@router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: InvitationCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new invitation for an organization (org admin only).
    """
    service = InvitationService(db)
    
    try:
        invitation = await service.create_invitation(
            invitation_data=invitation_data,
            invited_by=current_user,
            tenant_id=str(current_user.tenant_id)
        )
        
        return invitation
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/bulk", response_model=BulkInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_bulk_invitations(
    bulk_data: BulkInvitationCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Create multiple invitations at once (org admin only).
    """
    service = InvitationService(db)
    
    result = await service.create_bulk_invitations(
        emails=bulk_data.emails,
        organization_id=bulk_data.organization_id,
        role=bulk_data.role,
        message=bulk_data.message,
        expires_in=bulk_data.expires_in,
        invited_by=current_user,
        tenant_id=str(current_user.tenant_id)
    )
    
    return BulkInvitationResponse(**result)


@router.get("/", response_model=InvitationListResponse)
async def list_invitations(
    organization_id: Optional[str] = None,
    status: Optional[InvitationStatus] = None,
    email: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List invitations for organizations the user has access to.
    """
    query = db.query(Invitation).filter(
        Invitation.tenant_id == current_user.tenant_id
    )
    
    # Filter by organization if specified
    if organization_id:
        query = query.filter(Invitation.organization_id == organization_id)
    else:
        # Get user's organizations
        user_orgs = current_user.get_organizations()
        org_ids = [org.id for org in user_orgs]
        if org_ids:
            query = query.filter(Invitation.organization_id.in_(org_ids))
    
    # Filter by status
    if status:
        query = query.filter(Invitation.status == status.value)
    
    # Filter by email
    if email:
        query = query.filter(Invitation.email.ilike(f"%{email}%"))
    
    # Get total count
    total = query.count()
    
    # Get status counts
    pending_count = query.filter(Invitation.status == InvitationStatus.PENDING.value).count()
    accepted_count = query.filter(Invitation.status == InvitationStatus.ACCEPTED.value).count()
    expired_count = query.filter(Invitation.status == InvitationStatus.EXPIRED.value).count()
    
    # Get paginated results
    invitations = query.order_by(Invitation.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert to response models
    invitation_responses = []
    for inv in invitations:
        invitation_responses.append(InvitationResponse(
            id=str(inv.id),
            organization_id=str(inv.organization_id),
            email=inv.email,
            role=inv.role_name,
            status=inv.status,
            invited_by=str(inv.invited_by),
            message=inv.message,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            invite_url=inv.generate_invite_url(settings.APP_URL),
            email_sent=inv.email_sent
        ))
    
    return InvitationListResponse(
        invitations=invitation_responses,
        total=total,
        pending_count=pending_count,
        accepted_count=accepted_count,
        expired_count=expired_count
    )


@router.get("/{invitation_id}", response_model=InvitationResponse)
async def get_invitation(
    invitation_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific invitation by ID.
    """
    invitation = db.query(Invitation).filter(
        and_(
            Invitation.id == invitation_id,
            Invitation.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    return InvitationResponse(
        id=str(invitation.id),
        organization_id=str(invitation.organization_id),
        email=invitation.email,
        role=invitation.role_name,
        status=invitation.status,
        invited_by=str(invitation.invited_by),
        message=invitation.message,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        invite_url=invitation.generate_invite_url(settings.APP_URL),
        email_sent=invitation.email_sent
    )


@router.patch("/{invitation_id}", response_model=InvitationResponse)
async def update_invitation(
    invitation_id: str,
    update_data: InvitationUpdate,
    current_user=Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Update a pending invitation (org admin only).
    """
    invitation = db.query(Invitation).filter(
        and_(
            Invitation.id == invitation_id,
            Invitation.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    if invitation.status != InvitationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update invitation with status: {invitation.status}"
        )
    
    # Update fields
    if update_data.role is not None:
        invitation.role_name = update_data.role
    
    if update_data.message is not None:
        invitation.message = update_data.message
    
    if update_data.expires_at is not None:
        invitation.expires_at = update_data.expires_at
    
    await db.commit()
    await db.refresh(invitation)
    
    return InvitationResponse(
        id=str(invitation.id),
        organization_id=str(invitation.organization_id),
        email=invitation.email,
        role=invitation.role_name,
        status=invitation.status,
        invited_by=str(invitation.invited_by),
        message=invitation.message,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        invite_url=invitation.generate_invite_url(settings.APP_URL),
        email_sent=invitation.email_sent
    )


@router.post("/{invitation_id}/resend", response_model=InvitationResponse)
async def resend_invitation(
    invitation_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Resend an invitation email (org admin only).
    """
    service = InvitationService(db)
    
    try:
        invitation = await service.resend_invitation(
            invitation_id=invitation_id,
            resent_by=current_user
        )
        
        return invitation
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: str,
    current_user=Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke a pending invitation (org admin only).
    """
    service = InvitationService(db)
    
    try:
        await service.revoke_invitation(
            invitation_id=invitation_id,
            revoked_by=current_user
        )
        
        return None
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/accept", response_model=InvitationAcceptResponse)
async def accept_invitation(
    accept_data: InvitationAcceptRequest,
    db: Session = Depends(get_db)
):
    """
    Accept an invitation using the token.
    """
    service = InvitationService(db)
    auth_service = AuthService(db)
    
    try:
        # Get user if user_id provided
        user = None
        if accept_data.user_id:
            user = db.query(User).filter(
                User.id == accept_data.user_id
            ).first()
            
            if not user:
                raise ValueError("User not found")
        
        # Or create new user if registration data provided
        new_user_data = None
        if accept_data.password and accept_data.name and not user:
            password_hash = auth_service.hash_password(accept_data.password)
            new_user_data = {
                "name": accept_data.name,
                "password_hash": password_hash
            }
        
        # Accept invitation
        result = await service.accept_invitation(
            token=accept_data.token,
            user=user,
            new_user_data=new_user_data
        )
        
        return InvitationAcceptResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/validate/{token}")
async def validate_invitation_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validate an invitation token and get details.
    """
    invitation = db.query(Invitation).filter(
        Invitation.token == token
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )
    
    # Check if expired
    if invitation.is_expired:
        return {
            "valid": False,
            "reason": "Invitation has expired",
            "email": invitation.email,
            "organization_id": str(invitation.organization_id)
        }
    
    # Check if already accepted
    if invitation.status == InvitationStatus.ACCEPTED.value:
        return {
            "valid": False,
            "reason": "Invitation has already been accepted",
            "email": invitation.email,
            "organization_id": str(invitation.organization_id)
        }
    
    # Check if revoked
    if invitation.status == InvitationStatus.REVOKED.value:
        return {
            "valid": False,
            "reason": "Invitation has been revoked",
            "email": invitation.email,
            "organization_id": str(invitation.organization_id)
        }
    
    # Get organization details
    from app.models.organization import Organization
    org = db.query(Organization).filter(
        Organization.id == invitation.organization_id
    ).first()
    
    return {
        "valid": True,
        "email": invitation.email,
        "organization_id": str(invitation.organization_id),
        "organization_name": org.name if org else None,
        "role": invitation.role_name,
        "expires_at": invitation.expires_at.isoformat(),
        "message": invitation.message
    }


@router.post("/cleanup")
async def cleanup_expired_invitations(
    current_user=Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Clean up expired invitations (org admin only).
    """
    service = InvitationService(db)
    
    count = service.cleanup_expired_invitations()
    
    return {
        "message": f"Marked {count} invitations as expired",
        "count": count
    }