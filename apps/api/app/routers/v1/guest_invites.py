"""Admin CRUD for guest invite link management.

Follows the same patterns as ``invitations.py`` for consistency, including its
``_require_org_admin_for`` discipline: authentication alone is not authorization,
and being an admin of *some* organization does not authorize acting on *this*
one. Every endpoint below binds the caller to the ``org_id`` in the path before
touching a row.

The invite token is a bearer credential: it is returned exactly once, in the
response to ``POST``. List responses expose only a short prefix, enough to tell
two invites apart in a UI, never enough to use one.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database_manager import get_db
from app.dependencies import get_current_user
from app.models import GuestInvite, Organization, OrganizationMember, User

#: Characters of the token surfaced in list responses. Enough to disambiguate
#: two invites in an admin UI, far too few to replay one.
TOKEN_PREFIX_LEN = 8

router = APIRouter(
    prefix="/organizations/{org_id}/guest-invites",
    tags=["guest-invites"],
)


# -- Request / Response schemas ------------------------------------------------


class CreateGuestInviteRequest(BaseModel):
    label: str = Field(default="", max_length=255)
    max_uses: int = Field(default=0, ge=0, description="0 = unlimited")
    guest_ttl_hours: int = Field(default=4, ge=1, le=24)
    room_id: Optional[str] = None
    expires_in_hours: Optional[int] = Field(default=None, ge=1, le=720)


class GuestInviteSummary(BaseModel):
    """An invite as seen after creation: metadata only, no usable credential."""

    id: str
    token_prefix: str
    label: str
    max_uses: int
    use_count: int
    guest_ttl_hours: int
    room_id: Optional[str]
    expires_at: Optional[str]
    revoked: bool
    created_at: str


class GuestInviteResponse(GuestInviteSummary):
    """Creation-time response. The only place the token is ever returned."""

    token: str
    invite_url: str


class GuestInviteListResponse(BaseModel):
    invites: list[GuestInviteSummary]
    total: int


# -- Helpers -------------------------------------------------------------------


def _invite_to_summary(invite: GuestInvite) -> GuestInviteSummary:
    """Redacted view. Never includes the token or the invite URL that embeds it."""
    return GuestInviteSummary(
        id=str(invite.id),
        token_prefix=(invite.token or "")[:TOKEN_PREFIX_LEN],
        label=invite.label or "",
        max_uses=invite.max_uses,
        use_count=invite.use_count,
        guest_ttl_hours=invite.guest_ttl_hours,
        room_id=invite.room_id,
        expires_at=invite.expires_at.isoformat() if invite.expires_at else None,
        revoked=invite.revoked,
        created_at=invite.created_at.isoformat() if invite.created_at else "",
    )


def _invite_to_response(invite: GuestInvite) -> GuestInviteResponse:
    """Full view including the token. Only valid at creation time."""
    base_url = settings.BASE_URL.rstrip("/")
    return GuestInviteResponse(
        **_invite_to_summary(invite).model_dump(),
        token=invite.token,
        invite_url=f"{base_url}/guest?invite={invite.token}",
    )


async def _require_org_admin_for(db: AsyncSession, user: User, org_id: uuid.UUID) -> None:
    """Assert the caller administers *this* organization.

    Mirrors ``invitations._require_org_admin_for``. ``get_current_user`` proves
    only that the caller is signed in, and ``require_org_admin`` proves only that
    they administer SOME organization -- neither stops an admin of org A from
    reaching org B's invites through the path parameter.

    Raises 404 rather than 403 so the endpoint does not confirm that an
    organization the caller cannot reach exists.
    """
    not_found = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Guest invite not found"
    )

    org = (
        await db.execute(select(Organization).where(Organization.id == org_id))
    ).scalar_one_or_none()
    if org is None:
        raise not_found

    owner_id = getattr(org, "owner_id", None)
    # Both ids must be present before they can match, so that an ownerless
    # organization and an id-less caller do not compare equal as "None".
    if owner_id and user.id and str(owner_id) == str(user.id):
        return

    membership = (
        await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.role.in_(["admin", "owner"]),
                OrganizationMember.status == "active",
            )
        )
    ).scalar_one_or_none()

    if membership is None:
        raise not_found


# -- Endpoints ----------------------------------------------------------------


@router.post("", response_model=GuestInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_invite(
    org_id: str,
    body: CreateGuestInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GuestInviteResponse:
    """Create a new guest invite link.

    Requires an admin or owner role in the organization named in the path. The
    returned ``token``/``invite_url`` is shown only here -- later reads expose a
    prefix only.
    """
    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid org_id"
        ) from exc

    await _require_org_admin_for(db, current_user, org_uuid)

    token = secrets.token_urlsafe(32)
    expires_at = None
    if body.expires_in_hours:
        expires_at = datetime.now(UTC) + timedelta(hours=body.expires_in_hours)

    invite = GuestInvite(
        organization_id=org_uuid,
        created_by=current_user.id,
        token=token,
        label=body.label,
        max_uses=body.max_uses,
        guest_ttl_hours=body.guest_ttl_hours,
        room_id=body.room_id,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.flush()
    await db.refresh(invite)
    return _invite_to_response(invite)


@router.get("", response_model=GuestInviteListResponse)
async def list_guest_invites(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GuestInviteListResponse:
    """List guest invites for an organization.

    Requires an admin or owner role in the organization named in the path.
    Tokens are redacted to a prefix; they cannot be recovered after creation.
    """
    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid org_id"
        ) from exc

    await _require_org_admin_for(db, current_user, org_uuid)

    result = await db.execute(
        select(GuestInvite)
        .where(GuestInvite.organization_id == org_uuid)
        .order_by(GuestInvite.created_at.desc())
    )
    invites = result.scalars().all()
    return GuestInviteListResponse(
        invites=[_invite_to_summary(i) for i in invites],
        total=len(invites),
    )


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_guest_invite(
    org_id: str,
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke a guest invite link.

    Requires an admin or owner role in the organization named in the path.
    """
    try:
        org_uuid = uuid.UUID(org_id)
        invite_uuid = uuid.UUID(invite_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID"
        ) from exc

    await _require_org_admin_for(db, current_user, org_uuid)

    result = await db.execute(
        select(GuestInvite)
        .where(GuestInvite.id == invite_uuid)
        .where(GuestInvite.organization_id == org_uuid)
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guest invite not found"
        )

    invite.revoked = True
    await db.flush()
