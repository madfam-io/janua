"""Internal user provisioning + lifecycle endpoints.

Called by sibling MADFAM apps that own a roster of people but do NOT own
identity. The motivating caller is crea-map: its «Alta de integrante» creates a
clinical-team member row, but until now granting that person actual access was a
MANUAL operator step in janua. These endpoints close that gap so the roster
lifecycle (alta / baja / re-alta) drives the janua identity automatically.

Auth
----
All three endpoints use ``verify_internal_api_key`` (the ``X-Internal-API-Key``
vs ``settings.INTERNAL_API_KEY`` dependency). That is the SAME trust janua
already extends to sibling apps for the internal email API — not a new or weaker
trust boundary.

The ratified long-term direction is janua-issued **service tokens** per the
2026-08-25 SoC decision. This dependency is deliberately a swappable seam: it is
declared once per route and nothing in the handler bodies depends on the shared
key, so migrating to service tokens is a dependency swap, not a rewrite.

Scope guarantee
---------------
This surface provisions and toggles lifecycle state. It has NO delete/purge
endpoint and must not grow one: a roster app removing a member is a suspension in
identity terms, never a destruction of the identity record or its audit trail.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_internal_api_key
from app.models import OrganizationMember, User, UserStatus
from app.models import Session as UserSession
from app.routers.v1.oauth_clients import INTERNAL_API_KEY_PRINCIPAL
from app.schemas.internal import (
    ProvisionUserRequest,
    ProvisionUserResponse,
    UserLifecycleRequest,
    UserLifecycleResponse,
)
from app.services.audit_logger import AuditEventType, AuditLogger
from app.services.user_lookup import get_user_by_email

logger = structlog.get_logger()

router = APIRouter(prefix="/users", tags=["internal"])


def _normalize_email(email: str) -> str:
    """Fold an inbound email to its canonical stored form.

    Idempotency here is by ``lower(email) + tenant_id``: a roster app that sends
    ``Foo@Bar.com`` today and ``foo@bar.com`` tomorrow must converge on ONE user,
    not two. janua has no pre-existing lowercasing convention (other call sites
    store whatever they were handed), so this router owns the rule explicitly and
    applies it to BOTH the lookup and the stored value — storing the raw form
    while looking up the folded one would silently break the idempotency above.
    """
    return email.strip().lower()


async def _ensure_org_membership(
    db: AsyncSession,
    *,
    user_id,
    organization_id,
    role: str,
) -> str | None:
    """Ensure an ACTIVE ``OrganizationMember`` row, idempotently. Returns its role.

    Why this exists
    ---------------
    ``org_claims_service.get_user_org_claims`` counts only memberships with
    ``status == "active"``. A user row carrying ``tenant_id`` but holding no
    membership therefore gets a token with NO ``org_id``, and symbiosis-hcm's
    ``TenantRolePermission`` (``core/permissions.py:125-126``) rejects a token
    without one — so a person provisioned from the MAP could sign in to janua
    and still get 403 at «Mi espacio (RH)». Writing ``tenant_id`` alone is not
    provisioning access; the membership is what makes the claim resolvable.

    Shape mirrors the signup path (``routers/v1/auth.py:355-364``), which is the
    existing precedent for "tenant-bound identity ⇒ also record membership":
    ``tenant_id`` names an ``organizations.id``.

    Idempotency
    -----------
    Matching the endpoint's contract, a re-provision must converge on ONE
    membership rather than stacking rows. An existing ACTIVE membership is
    returned untouched — its role is NOT rewritten to the requested one, for
    the same reason the user row is not re-synchronized: an operator may have
    promoted or demoted the person in janua, and a roster retry must not
    silently undo that. A non-active membership (pending/inactive/removed) IS
    reactivated with the requested role: re-provisioning is the roster's
    «re-alta», and leaving it removed would mean the endpoint reports success
    while the person still cannot work.

    Errors are NOT swallowed
    ------------------------
    Unlike the audit-log write below, a membership failure propagates. The
    audit log is a side record; the membership IS the access this endpoint
    exists to grant, and a call that returned 201 while leaving the person
    without ``org_id`` would be exactly the silent failure this change fixes.
    Because the write shares the handler's transaction, a raised error also
    rolls back the user row — the caller retries and converges, rather than
    being left with a half-provisioned identity that reports success.
    """
    if organization_id is None:
        return None

    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
    )
    membership = result.scalars().first()

    if membership is not None:
        if membership.status == "active":
            return membership.role or "member"
        # Re-alta: revive the existing row rather than adding a second one.
        membership.status = "active"
        membership.role = role
        membership.joined_at = datetime.utcnow()
        membership.updated_at = datetime.utcnow()
        await db.flush()
        return membership.role

    membership = OrganizationMember(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        status="active",
    )
    db.add(membership)
    # Flush inside the caller's transaction: the membership must commit together
    # with the user row, never as a second commit that can leave a user
    # provisioned without the access the call promised.
    await db.flush()
    return role


@router.post(
    "/provision",
    response_model=ProvisionUserResponse,
    # 201 is the DECLARED default (the create case, what OpenAPI advertises).
    # The handler downgrades to 200 on the already-exists path by writing
    # `response.status_code` — a per-call status cannot be expressed statically.
    status_code=status.HTTP_201_CREATED,
)
async def provision_user(
    body: ProvisionUserRequest,
    response: Response,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> ProvisionUserResponse:
    """Ensure a janua user exists for a roster member. Idempotent.

    Returns 201 when it created the user, 200 when one already existed.

    An existing USER row is returned UNTOUCHED — not even the name is refreshed.
    This is provisioning, not synchronization: the person may have edited their
    own profile in janua, and a roster-side value must not silently overwrite
    that.

    The ORGANIZATION MEMBERSHIP is the deliberate exception, and is reconciled on
    both the create and the already-exists path. It is not profile data the
    person can own — it is the access this endpoint's whole purpose is to grant,
    and without an ACTIVE membership the resulting token carries no ``org_id``
    (see ``_ensure_org_membership``). Reconciling it on the 200 path is also what
    repairs the identities provisioned before this change: they already exist, so
    the create branch would never run for them, and they would stay locked out
    of «Mi espacio (RH)» forever.
    """
    email = _normalize_email(body.email)

    # Pool-scoped lookup is mandatory: since migration 013 email is unique PER
    # TENANT, so a bare email select can match several rows across tenants.
    existing = await get_user_by_email(db, email, tenant_id=body.tenant_id)
    if existing is not None:
        org_role = await _ensure_org_membership(
            db,
            user_id=existing.id,
            organization_id=body.tenant_id,
            role=body.org_role,
        )
        await db.commit()

        response.status_code = status.HTTP_200_OK
        return ProvisionUserResponse(
            id=str(existing.id),
            email=existing.email,
            # Coalesce nullable columns: legacy rows may carry NULL status and
            # would otherwise fail response validation (see admin.py:468-471).
            status=existing.status.value if existing.status else UserStatus.ACTIVE.value,
            created=False,
            created_at=existing.created_at,
            # The STORED value, not the requested one — see the schema comment:
            # an existing identity is never re-flagged by a provisioning call.
            is_service_account=bool(getattr(existing, "is_service_account", False)),
            org_role=org_role,
        )

    user = User(
        email=email,
        # Passwordless by construction: crea-map members sign in by MAGIC LINK
        # and never hold a janua password. Unlike the admin create-user path we
        # therefore mint NO PasswordReset token — there is no password to set, so
        # a set-password token would be a credential with no purpose.
        password_hash=None,
        first_name=body.first_name,
        last_name=body.last_name,
        status=UserStatus.ACTIVE,
        email_verified=False,
        email_verified_at=None,
        is_admin=False,
        # Set explicitly rather than relying on the column default so the row has
        # a known dict shape for the suspend/reactivate metadata writes below.
        user_metadata={},
        tenant_id=body.tenant_id,
        # Honoured on CREATE only; see ProvisionUserRequest. A technical login
        # provisioned here rides `is_service_account: true` in its tokens and
        # reports it on the user/membership APIs, so consuming apps can keep it
        # out of rosters and off document signatures.
        is_service_account=bool(body.is_service_account),
        # `is_active` is deliberately left to the column default (True), matching
        # the admin create-user path which does not set it either.
    )
    db.add(user)
    await db.flush()  # assign user.id without ending the transaction

    _created_at = user.created_at
    _user_id = str(user.id)

    # Same transaction as the user row: a person is either provisioned WITH the
    # access this call promises, or not provisioned at all.
    org_role = await _ensure_org_membership(
        db,
        user_id=user.id,
        organization_id=body.tenant_id,
        role=body.org_role,
    )

    # Best-effort audit on the working AuditLogger hash-chain trail. We do NOT
    # use AuthService.create_audit_log: it references AuditLog columns that do
    # not exist and raises AttributeError (documented at admin.py:602-607).
    # A failure here must never block provisioning.
    try:
        audit_logger = AuditLogger(db)
        await audit_logger.log(
            event_type=AuditEventType.USER_CREATE,
            tenant_id=str(body.tenant_id),
            identity_id=None,
            resource_type="user",
            resource_id=_user_id,
            details={
                "email": email,
                "actor": INTERNAL_API_KEY_PRINCIPAL,
                "via": "internal.users.provision",
                "passwordless": True,
                "is_service_account": bool(body.is_service_account),
                "org_role": org_role,
            },
            severity="info",
        )
    except Exception:
        pass

    await db.commit()
    await db.refresh(user)

    logger.info(
        "Provisioned user via internal API",
        user_id=_user_id,
        tenant_id=str(body.tenant_id),
        org_role=org_role,
    )

    return ProvisionUserResponse(
        id=str(user.id),
        email=user.email,
        status=user.status.value if user.status else UserStatus.ACTIVE.value,
        created=True,
        created_at=user.created_at or _created_at,
        is_service_account=bool(user.is_service_account),
        org_role=org_role,
    )


@router.post(
    "/suspend",
    response_model=UserLifecycleResponse,
)
async def suspend_user(
    body: UserLifecycleRequest,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> UserLifecycleResponse:
    """Suspend a roster member's janua access. Idempotent.

    Always 200 when the user exists: ``changed`` reports whether this call was
    the one that suspended them. 404 only when there is no such user in the pool.
    """
    email = _normalize_email(body.email)
    user = await get_user_by_email(db, email, tenant_id=body.tenant_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No janua user for that email in this tenant",
        )

    if user.status == UserStatus.SUSPENDED:
        # Already suspended: report success without re-writing, so the audit
        # trail is not padded with repeat suspensions of the same person.
        return UserLifecycleResponse(
            id=str(user.id),
            email=user.email,
            status=UserStatus.SUSPENDED.value,
            changed=False,
        )

    # `status` is the real state machine; `is_active` is largely vestigial in
    # janua today. We set BOTH so the flag can never contradict the status.
    user.status = UserStatus.SUSPENDED
    user.is_active = False

    await db.execute(update(UserSession).where(UserSession.user_id == user.id).values(revoked=True))

    # Rebuild and REASSIGN the dict rather than mutating in place. user_metadata
    # is plain JSONB with no MutableDict wrapper, so SQLAlchemy does not track
    # in-place key writes and the change may never flush. (users.py:448-451
    # mutates in place — a latent bug we do not copy.)
    user.user_metadata = {
        **(user.user_metadata or {}),
        "suspended_at": datetime.utcnow().isoformat(),
        "suspended_by": INTERNAL_API_KEY_PRINCIPAL,
    }

    try:
        audit_logger = AuditLogger(db)
        await audit_logger.log(
            event_type=AuditEventType.USER_SUSPEND,
            tenant_id=str(body.tenant_id),
            identity_id=None,
            resource_type="user",
            resource_id=str(user.id),
            details={"actor": INTERNAL_API_KEY_PRINCIPAL, "via": "internal.users.suspend"},
            severity="info",
        )
    except Exception:
        pass

    await db.commit()

    logger.info("Suspended user via internal API", user_id=str(user.id))

    return UserLifecycleResponse(
        id=str(user.id),
        email=user.email,
        status=UserStatus.SUSPENDED.value,
        changed=True,
    )


@router.post(
    "/reactivate",
    response_model=UserLifecycleResponse,
)
async def reactivate_user(
    body: UserLifecycleRequest,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> UserLifecycleResponse:
    """Restore a suspended roster member's janua access. Idempotent.

    Deliberately does NOT reproduce users.py's ``400 "User is not suspended"``.
    On an idempotent internal surface an already-active user is the caller's
    desired end state, so it is SUCCESS with ``changed: false``, not an error.
    """
    email = _normalize_email(body.email)
    user = await get_user_by_email(db, email, tenant_id=body.tenant_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No janua user for that email in this tenant",
        )

    if user.status == UserStatus.ACTIVE:
        return UserLifecycleResponse(
            id=str(user.id),
            email=user.email,
            status=UserStatus.ACTIVE.value,
            changed=False,
        )

    user.status = UserStatus.ACTIVE
    user.is_active = True

    # Rebuild-and-reassign, same reason as in suspend: drop the suspension keys
    # and stamp the reactivation in one new dict.
    metadata = dict(user.user_metadata or {})
    metadata.pop("suspension_reason", None)
    metadata.pop("suspended_at", None)
    metadata.pop("suspended_by", None)
    metadata["reactivated_at"] = datetime.utcnow().isoformat()
    metadata["reactivated_by"] = INTERNAL_API_KEY_PRINCIPAL
    user.user_metadata = metadata

    try:
        audit_logger = AuditLogger(db)
        await audit_logger.log(
            event_type=AuditEventType.USER_REACTIVATE,
            tenant_id=str(body.tenant_id),
            identity_id=None,
            resource_type="user",
            resource_id=str(user.id),
            details={"actor": INTERNAL_API_KEY_PRINCIPAL, "via": "internal.users.reactivate"},
            severity="info",
        )
    except Exception:
        pass

    await db.commit()

    logger.info("Reactivated user via internal API", user_id=str(user.id))

    return UserLifecycleResponse(
        id=str(user.id),
        email=user.email,
        status=UserStatus.ACTIVE.value,
        changed=True,
    )
