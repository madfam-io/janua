"""
Service for managing organization invitations.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Organization, OrganizationMember
from app.models.invitation import Invitation, InvitationCreate, InvitationResponse, InvitationStatus
from app.models.policy import Role
from app.models.user import User
from app.services.audit_logger import AuditAction, AuditLogger
from app.services.cache import CacheService
from app.services.email_service import EmailService

logger = structlog.get_logger()


class InvitationService:
    """
    Service for managing organization invitations.
    """

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self.audit_logger = AuditLogger(db)
        self.cache = CacheService()

    async def create_invitation(
        self, invitation_data: InvitationCreate, invited_by: User, tenant_id: str
    ) -> InvitationResponse:
        """
        Create a new invitation.
        """
        # Verify the organization exists.
        #
        # This used to filter on `Organization.tenant_id`, a column the
        # organizations table does not have, so the query raised before it
        # could scope anything. The scoping it was reaching for is restored
        # below against columns that exist — it must not simply be dropped:
        # `require_org_admin` only proves the caller administers SOME
        # organization, so without a per-organization check any org admin
        # could invite members into an organization they have nothing to do
        # with.
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == invitation_data.organization_id)
            .first()
        )

        if not organization:
            raise ValueError("Organization not found")

        # The caller must administer THIS organization — as its owner, or via
        # an admin/owner membership row. Both ids must be present before they
        # can match: an ownerless organization and an id-less caller would
        # otherwise compare equal as "None" and grant access to neither party's
        # organization.
        owner_id = getattr(organization, "owner_id", None)
        is_owner = bool(owner_id) and bool(invited_by.id) and str(owner_id) == str(invited_by.id)
        if not is_owner:
            admin_membership = (
                self.db.query(OrganizationMember)
                .filter(
                    and_(
                        OrganizationMember.organization_id == organization.id,
                        OrganizationMember.user_id == invited_by.id,
                        OrganizationMember.role.in_(["admin", "owner"]),
                    )
                )
                .first()
            )
            if not admin_membership:
                raise ValueError("Organization not found")

        # Check if the invitee is already a member. Membership is keyed by
        # user_id, not by email, so resolve the address first; an address with
        # no account cannot already be a member. Resolve in the untenanted /
        # staff pool: invitees are platform identities and membership is via
        # OrganizationMember (decoupled from tenant_id). Email is per-tenant
        # since migration 013, so scope the lookup to that pool (sync session
        # here, so this filters inline rather than via get_user_by_email).
        invitee = (
            self.db.query(User)
            .filter(User.email == invitation_data.email, User.tenant_id.is_(None))
            .first()
        )
        if invitee is not None:
            existing_member = (
                self.db.query(OrganizationMember)
                .filter(
                    and_(
                        OrganizationMember.organization_id == organization.id,
                        OrganizationMember.user_id == invitee.id,
                    )
                )
                .first()
            )

            if existing_member:
                raise ValueError("User is already a member of this organization")

        # Check for existing pending invitation
        existing_invitation = (
            self.db.query(Invitation)
            .filter(
                and_(
                    Invitation.organization_id == invitation_data.organization_id,
                    Invitation.email == invitation_data.email,
                    Invitation.status == InvitationStatus.PENDING.value,
                )
            )
            .first()
        )

        if existing_invitation and not existing_invitation.is_expired:
            raise ValueError("An active invitation already exists for this email")

        # Get role if specified
        role = None
        if invitation_data.role:
            role = (
                self.db.query(Role)
                .filter(or_(Role.id == invitation_data.role, Role.name == invitation_data.role))
                .first()
            )

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=invitation_data.expires_in or 7)

        # Create invitation.
        #
        # `token` is NOT NULL and unique, and it is the only thing
        # /invitations/validate/{token} and /invitations/accept look up — yet
        # nothing here ever generated one. Every invitation was therefore
        # un-redeemable even before the email failed to send. Mint it here so
        # the value that gets mailed is the value the verify path validates.
        invitation = Invitation(
            organization_id=invitation_data.organization_id,
            email=invitation_data.email,
            role=(role.name if role else invitation_data.role) or "member",
            status=InvitationStatus.PENDING.value,
            token=secrets.token_urlsafe(32),
            created_by=invited_by.id,
            expires_at=expires_at,
        )

        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)

        # Send invitation email
        email_sent = await self._send_invitation_email(invitation, organization, invited_by)

        # Log audit event
        await self.audit_logger.log(
            event_type=AuditAction.INVITATION_CREATE,
            tenant_id=tenant_id,
            identity_id=str(invited_by.id),
            resource_type="invitation",
            resource_id=str(invitation.id),
            details={"email": invitation_data.email, "organization": organization.name},
        )

        # Create response. `email_sent` reports what actually happened on this
        # request rather than reading a column that does not exist.
        response = InvitationResponse(
            id=str(invitation.id),
            organization_id=str(invitation.organization_id),
            email=invitation.email,
            role=invitation.role,
            status=invitation.status,
            invited_by=str(invitation.created_by),
            message=invitation_data.message,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            invite_url=invitation.generate_invite_url(settings.FRONTEND_URL or settings.BASE_URL),
            email_sent=email_sent,
        )

        return response

    async def create_bulk_invitations(
        self,
        emails: List[str],
        organization_id: str,
        role: Optional[str],
        message: Optional[str],
        expires_in: Optional[int],
        invited_by: User,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """
        Create multiple invitations at once.
        """
        successful = []
        failed = []

        for email in emails:
            try:
                invitation_data = InvitationCreate(
                    organization_id=organization_id,
                    email=email,
                    role=role,
                    message=message,
                    expires_in=expires_in,
                )

                response = await self.create_invitation(
                    invitation_data=invitation_data, invited_by=invited_by, tenant_id=tenant_id
                )

                successful.append(response)

            except Exception as e:
                failed.append({"email": email, "error": str(e)})

        return {
            "successful": successful,
            "failed": failed,
            "total_sent": len(successful),
            "total_failed": len(failed),
        }

    async def accept_invitation(
        self,
        token: str,
        user: Optional[User] = None,
        new_user_data: Optional[Dict[str, Any]] = None,
        locale: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Accept an invitation.

        `locale` is the language negotiated from the acceptance request. It is
        applied only to a user created here — an existing account keeps the
        preference it already has.
        """
        # Find invitation by token
        invitation = self.db.query(Invitation).filter(Invitation.token == token).first()

        if not invitation:
            raise ValueError("Invalid invitation token")

        if not invitation.is_valid:
            if invitation.is_expired:
                raise ValueError("Invitation has expired")
            else:
                raise ValueError(f"Invitation is {invitation.status}")

        # Create user if needed.
        # `name` is a read-only property on User (derived from first/last/display),
        # and invitations carry no tenant of their own — both kwargs used to
        # raise before a single account could be created this way. The tenant
        # comes from the organization being joined, which is the only place it
        # is actually recorded.
        if not user and new_user_data:
            organization = (
                self.db.query(Organization)
                .filter(Organization.id == invitation.organization_id)
                .first()
            )
            user = User(
                email=invitation.email,
                display_name=new_user_data.get("name") or invitation.email.split("@")[0],
                password_hash=new_user_data.get("password_hash"),
                tenant_id=getattr(organization, "tenant_id", None),
                email_verified=True,  # Auto-verify since they have the invitation
                locale=locale,
            )
            self.db.add(user)
            self.db.flush()
        elif not user:
            raise ValueError("User account required to accept invitation")

        # Verify email matches
        if user.email != invitation.email:
            raise ValueError("Invitation email does not match user email")

        # Add user to organization. Membership is keyed by user_id; there is
        # no user_email column, and passing one raised before any invitation
        # could ever be redeemed.
        org_member = OrganizationMember(
            organization_id=invitation.organization_id,
            user_id=user.id,
            role=invitation.role or "member",
        )
        self.db.add(org_member)

        # Update invitation status. There is no accepted_by column; accepted_at
        # plus the membership row record who redeemed it.
        invitation.status = InvitationStatus.ACCEPTED.value
        invitation.accepted_at = datetime.utcnow()

        self.db.commit()

        # Clear cache
        await self.cache.delete(f"user:organizations:{user.id}")

        # Log audit event
        await self.audit_logger.log(
            event_type=AuditAction.INVITATION_ACCEPT,
            tenant_id=str(invitation.tenant_id) if hasattr(invitation, "tenant_id") else "",
            identity_id=str(user.id),
            resource_type="invitation",
            resource_id=str(invitation.id),
            details={"organization_id": str(invitation.organization_id)},
        )

        return {
            "success": True,
            "message": "Invitation accepted successfully",
            "user_id": str(user.id),
            "organization_id": str(invitation.organization_id),
            "role": invitation.role,
            "redirect_url": f"/dashboard/org/{invitation.organization_id}",
        }

    async def revoke_invitation(self, invitation_id: str, revoked_by: User) -> bool:
        """
        Revoke a pending invitation.
        """
        invitation = self.db.query(Invitation).filter(Invitation.id == invitation_id).first()

        if not invitation:
            raise ValueError("Invitation not found")

        if invitation.status != InvitationStatus.PENDING.value:
            raise ValueError(f"Cannot revoke invitation with status: {invitation.status}")

        # Update status
        invitation.status = InvitationStatus.REVOKED.value
        invitation.updated_at = datetime.utcnow()

        self.db.commit()

        # Log audit event
        await self.audit_logger.log(
            event_type=AuditAction.INVITATION_REVOKE,
            tenant_id=str(invitation.tenant_id) if hasattr(invitation, "tenant_id") else "",
            identity_id=str(revoked_by.id),
            resource_type="invitation",
            resource_id=str(invitation.id),
            details={"email": invitation.email},
        )

        return True

    async def resend_invitation(self, invitation_id: str, resent_by: User) -> InvitationResponse:
        """
        Resend an invitation email.
        """
        invitation = self.db.query(Invitation).filter(Invitation.id == invitation_id).first()

        if not invitation:
            raise ValueError("Invitation not found")

        if invitation.status != InvitationStatus.PENDING.value:
            raise ValueError(f"Cannot resend invitation with status: {invitation.status}")

        # Get organization
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == invitation.organization_id)
            .first()
        )

        # Resend email
        email_sent = await self._send_invitation_email(invitation, organization, resent_by)

        # Log audit event
        await self.audit_logger.log(
            event_type=AuditAction.INVITATION_RESEND,
            tenant_id=str(invitation.tenant_id) if hasattr(invitation, "tenant_id") else "",
            identity_id=str(resent_by.id),
            resource_type="invitation",
            resource_id=str(invitation.id),
            details={"email": invitation.email},
        )

        # Create response
        response = InvitationResponse(
            id=str(invitation.id),
            organization_id=str(invitation.organization_id),
            email=invitation.email,
            role=invitation.role,
            status=invitation.status,
            invited_by=str(invitation.created_by),
            message=None,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            invite_url=invitation.generate_invite_url(settings.FRONTEND_URL or settings.BASE_URL),
            email_sent=email_sent,
        )

        return response

    async def _send_invitation_email(
        self, invitation: Invitation, organization: Organization, inviter: User
    ) -> bool:
        """
        Send invitation email to the invitee. Returns whether it was sent.

        This used to compose its own HTML and hand it to
        `EmailService.send_email`, a method that does not exist on that class,
        so every invitation raised AttributeError into a bare `except` that
        printed and moved on. Nothing was ever mailed and nothing ever said so.

        It now renders the maintained invitation templates and reports the
        outcome instead of swallowing it. A send failure still does not undo
        the invitation — the row is real and the link stays redeemable — but
        the caller can now tell the difference.
        """
        try:
            invite_url = invitation.generate_invite_url(settings.FRONTEND_URL or settings.BASE_URL)
            sent = await self.email_service.send_invitation_email(
                email=invitation.email,
                invite_url=invite_url,
                organization_name=getattr(organization, "name", None) or "your organization",
                inviter_name=(getattr(inviter, "name", None) or inviter.email),
                role=invitation.role or "member",
                expires_at=invitation.expires_at,
            )
        except Exception:
            logger.exception(
                "Invitation email raised", invitation_id=str(getattr(invitation, "id", ""))
            )
            return False

        if not sent:
            logger.warning(
                "Invitation email NOT sent — the recipient will never receive a link",
                invitation_id=str(getattr(invitation, "id", "")),
            )
        return sent

    def get_pending_invitations(
        self, organization_id: str, skip: int = 0, limit: int = 100
    ) -> List[Invitation]:
        """
        Get pending invitations for an organization.
        """
        return (
            self.db.query(Invitation)
            .filter(
                and_(
                    Invitation.organization_id == organization_id,
                    Invitation.status == InvitationStatus.PENDING.value,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def cleanup_expired_invitations(self):
        """
        Mark expired invitations as expired.
        """
        expired_invitations = (
            self.db.query(Invitation)
            .filter(
                and_(
                    Invitation.status == InvitationStatus.PENDING.value,
                    Invitation.expires_at < datetime.utcnow(),
                )
            )
            .all()
        )

        for invitation in expired_invitations:
            invitation.status = InvitationStatus.EXPIRED.value

        self.db.commit()

        return len(expired_invitations)
