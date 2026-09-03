"""Internal application-role endpoints — grant / revoke / list.

An **application role** is authority INSIDE A PRODUCT, granted to one person in
one organization: ``hcm:hr``, ``hcm:admin``. It is deliberately not the same
thing as an organization role (``owner``/``admin``/``member``), which is
authority over the janua ACCOUNT. Grants made here are resolved into the token's
``roles`` claim by ``services/org_claims_service.py``, the SSOT every minting
seam already shares.

Why this surface exists
-----------------------
symbiosis-hcm authorizes on namespaced application roles read from ``roles``
(``symbiosis-hcm/apps/api/core/permissions.py``), and until now NOTHING in janua
emitted a single ``hcm:*`` string. CTM's Dirección could hold a valid membership,
receive a token with a correct ``org_id``, and still be refused every HR feature:
membership answered *which tenant*, and nothing answered *which product
authority*. This is where an operator answers the second question.

Auth
----
Every endpoint uses ``verify_internal_api_key`` — the same ``X-Internal-API-Key``
dependency as ``internal_users.py`` and ``internal_capability_links.py``, and the
same trust janua already extends to sibling apps. As there, the dependency is a
swappable seam: declared once per route, with no handler body depending on the
shared key, so the ratified move to janua-issued service tokens is a dependency
swap rather than a rewrite.

What janua deliberately does NOT know
-------------------------------------
``app`` and ``role`` are OPAQUE. Janua stores them, scopes lookups by them, and
concatenates them into ``"<app>:<role>"``. It holds no table of valid apps and no
vocabulary of role names — exactly as it holds none for capability-link scopes.
The resource server owns its role vocabulary, which is the ecosystem rule this
change fills the gap in without breaking: a new HCM role must not require a janua
deploy. What janua validates is SHAPE (see ``schemas/app_role.py``), never
meaning.

Two properties the handlers exist to hold
-----------------------------------------
1. NOTHING IS IMPLICIT. A role exists in a token because an operator granted it
   and there is a row saying who and when. There is no derivation from
   ``member.role``, no default set, and no mapping that turns an org ``admin``
   into an ``hcm:admin`` — any of those would rebuild the org-role-to-payroll
   bridge that the ``madfam_org_roles`` namespace exists to prevent.
2. A GRANT CANNOT CROSS AN ORGANIZATION. The grant hangs off the MEMBERSHIP, so
   naming an org the user is not an active member of is a 404, not a grant that
   quietly lands somewhere else.

Scope guarantee
---------------
There is NO delete endpoint and must not be one. Revocation stamps
``revoked_at``; the row survives, and a later re-grant is a NEW row. Same
reasoning as ``internal_users.py``'s missing purge and ``capability_links``'s:
destroying the record destroys the evidence that authority over payroll was ever
granted, to whom, and by whom.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_internal_api_key
from app.models import OrganizationMember
from app.models.app_role import OrganizationMemberAppRole, format_app_role
from app.routers.v1.oauth_clients import INTERNAL_API_KEY_PRINCIPAL
from app.schemas.app_role import (
    AppRoleEntry,
    AppRoleGrantRequest,
    AppRoleGrantResponse,
    AppRoleListResponse,
    AppRoleRevokeRequest,
)
from app.services.audit_logger import AuditEventType, AuditLogger

logger = structlog.get_logger()

router = APIRouter(prefix="/app-roles", tags=["internal"])

# THE refusal text for "no such active membership". Deliberately one message for
# both "no such organization" and "that user is not an active member of it": an
# internal caller has no business distinguishing the two, and a differentiated
# answer would let this surface be used to probe which users belong to which org.
NO_MEMBERSHIP_DETAIL = "No active membership for that user in that organization"


async def _get_active_membership(
    db: AsyncSession,
    organization_id,
    user_id,
) -> OrganizationMember:
    """Resolve the ONE active membership a grant hangs off, or 404.

    ``status == "active"`` matches the filter the claims resolver applies, so a
    grant can never be made against a membership that would not feed a token
    anyway — an operator who grants HR to a removed member should be told, not
    left believing it worked.
    """
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "active",
        )
    )
    membership = result.scalars().first()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NO_MEMBERSHIP_DETAIL,
        )
    return membership


async def _get_live_grant(
    db: AsyncSession,
    membership_id,
    app: str,
    role: str,
) -> OrganizationMemberAppRole | None:
    """The live (un-revoked) grant for this exact triple, if any."""
    result = await db.execute(
        select(OrganizationMemberAppRole).where(
            OrganizationMemberAppRole.organization_member_id == membership_id,
            OrganizationMemberAppRole.app == app,
            OrganizationMemberAppRole.role == role,
            OrganizationMemberAppRole.revoked_at.is_(None),
        )
    )
    return result.scalars().first()


async def _audit(
    db: AsyncSession,
    *,
    event_type: AuditEventType,
    organization_id,
    grant_id: str,
    details: dict,
) -> None:
    """Best-effort audit on the working AuditLogger hash-chain trail.

    Wrapped and swallowed for the same reason ``internal_users.py`` wraps its
    audit calls: a failure in the trail must not roll back the authorization
    write the operator asked for. The row itself carries ``granted_by`` /
    ``revoked_by``, so the durable who-and-when survives even if this fails.
    """
    try:
        audit_logger = AuditLogger(db)
        await audit_logger.log(
            event_type=event_type,
            tenant_id=str(organization_id),
            identity_id=None,
            resource_type="organization_member_app_role",
            resource_id=grant_id,
            details={"actor": INTERNAL_API_KEY_PRINCIPAL, **details},
            severity="info",
        )
    except Exception:
        pass


# -------------------------------------------------------------------- grant


@router.post(
    "/grant",
    response_model=AppRoleGrantResponse,
    # 201 is the DECLARED default (the create case, what OpenAPI advertises).
    # The handler downgrades to 200 on the already-granted path by writing
    # `response.status_code` — a per-call status cannot be expressed statically.
    # Same shape as internal_users.provision.
    status_code=status.HTTP_201_CREATED,
)
async def grant_app_role(
    body: AppRoleGrantRequest,
    response: Response,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> AppRoleGrantResponse:
    """Grant an application role to a member. Idempotent.

    Returns 201 when this call created the grant, 200 when a live one already
    existed. An existing grant is returned UNTOUCHED — its ``granted_at`` and
    ``granted_by`` are not refreshed, because the answer to "when was this
    person given access to payroll" must be the first time, not the last retry.

    404 when the user has no ACTIVE membership in that organization: a grant
    that could never feed a token is an operator error worth surfacing.
    """
    membership = await _get_active_membership(db, body.organization_id, body.user_id)

    existing = await _get_live_grant(db, membership.id, body.app, body.role)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return AppRoleGrantResponse(
            id=str(existing.id),
            organization_id=str(body.organization_id),
            user_id=str(body.user_id),
            app=existing.app,
            role=existing.role,
            claim_value=format_app_role(existing.app, existing.role),
            granted_at=existing.granted_at,
            revoked_at=None,
            changed=False,
        )

    grant = OrganizationMemberAppRole(
        organization_member_id=membership.id,
        app=body.app,
        role=body.role,
        granted_by=INTERNAL_API_KEY_PRINCIPAL,
        granted_at=datetime.utcnow(),
    )
    db.add(grant)
    await db.flush()  # assign grant.id without ending the transaction

    _grant_id = str(grant.id)
    _granted_at = grant.granted_at

    await _audit(
        db,
        event_type=AuditEventType.APP_ROLE_GRANT,
        organization_id=body.organization_id,
        grant_id=_grant_id,
        details={
            "via": "internal.app_roles.grant",
            "user_id": str(body.user_id),
            "organization_member_id": str(membership.id),
            "app": body.app,
            "role": body.role,
            "claim_value": format_app_role(body.app, body.role),
        },
    )

    await db.commit()

    logger.info(
        "Granted application role via internal API",
        grant_id=_grant_id,
        organization_id=str(body.organization_id),
        user_id=str(body.user_id),
        claim_value=format_app_role(body.app, body.role),
    )

    return AppRoleGrantResponse(
        id=_grant_id,
        organization_id=str(body.organization_id),
        user_id=str(body.user_id),
        app=body.app,
        role=body.role,
        claim_value=format_app_role(body.app, body.role),
        granted_at=_granted_at,
        revoked_at=None,
        changed=True,
    )


# ------------------------------------------------------------------- revoke


@router.post("/revoke", response_model=AppRoleGrantResponse)
async def revoke_app_role(
    body: AppRoleRevokeRequest,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> AppRoleGrantResponse:
    """Retire an application role. Idempotent; the row is never deleted.

    Always 200 when the membership exists: ``changed`` reports whether THIS call
    was the one that revoked it, matching ``internal_users.py``'s suspend. A role
    that was never granted is the caller's desired end state, so it is success
    with ``changed: false`` rather than a 404 — the same rule that keeps
    ``reactivate`` from erroring on an already-active user.

    The revocation reaches a live session at its next refresh: the claims
    resolver filters ``revoked_at IS NULL`` and every mint path re-resolves.
    """
    membership = await _get_active_membership(db, body.organization_id, body.user_id)

    grant = await _get_live_grant(db, membership.id, body.app, body.role)
    if grant is None:
        return AppRoleGrantResponse(
            id=None,
            organization_id=str(body.organization_id),
            user_id=str(body.user_id),
            app=body.app,
            role=body.role,
            claim_value=format_app_role(body.app, body.role),
            granted_at=None,
            revoked_at=None,
            changed=False,
        )

    grant.revoked_at = datetime.utcnow()
    grant.revoked_by = INTERNAL_API_KEY_PRINCIPAL

    _grant_id = str(grant.id)
    _granted_at = grant.granted_at
    _revoked_at = grant.revoked_at

    await _audit(
        db,
        event_type=AuditEventType.APP_ROLE_REVOKE,
        organization_id=body.organization_id,
        grant_id=_grant_id,
        details={
            "via": "internal.app_roles.revoke",
            "user_id": str(body.user_id),
            "organization_member_id": str(membership.id),
            "app": body.app,
            "role": body.role,
            "claim_value": format_app_role(body.app, body.role),
        },
    )

    await db.commit()

    logger.info(
        "Revoked application role via internal API",
        grant_id=_grant_id,
        organization_id=str(body.organization_id),
        user_id=str(body.user_id),
        claim_value=format_app_role(body.app, body.role),
    )

    return AppRoleGrantResponse(
        id=_grant_id,
        organization_id=str(body.organization_id),
        user_id=str(body.user_id),
        app=grant.app,
        role=grant.role,
        claim_value=format_app_role(grant.app, grant.role),
        granted_at=_granted_at,
        revoked_at=_revoked_at,
        changed=True,
    )


# --------------------------------------------------------------------- list


@router.get(
    "/{organization_id}/{user_id}",
    response_model=AppRoleListResponse,
)
async def list_app_roles(
    organization_id: str,
    user_id: str,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> AppRoleListResponse:
    """Every grant for one membership, live and retired.

    ``claim_values`` is the resolved LIVE set — exactly what this person's next
    token carries under ``roles`` — so an operator can answer "why can they not
    see HR?" without decoding a JWT. ``grants`` includes revoked rows, because
    who removed an authority and when is the question this table exists to
    answer.

    Scoped to ONE membership by construction, so this cannot report another
    organization's grants.
    """
    membership = await _get_active_membership(db, organization_id, user_id)

    result = await db.execute(
        select(OrganizationMemberAppRole)
        .where(OrganizationMemberAppRole.organization_member_id == membership.id)
        .order_by(
            OrganizationMemberAppRole.app,
            OrganizationMemberAppRole.role,
            OrganizationMemberAppRole.granted_at,
        )
    )
    grants = result.scalars().all()

    return AppRoleListResponse(
        organization_id=str(organization_id),
        user_id=str(user_id),
        # Sorted and deduplicated exactly as the claims resolver does it, so an
        # operator reading this list sees the token's contents, not a variant.
        claim_values=sorted(
            {format_app_role(g.app, g.role) for g in grants if g.revoked_at is None}
        ),
        grants=[
            AppRoleEntry(
                id=str(g.id),
                app=g.app,
                role=g.role,
                claim_value=format_app_role(g.app, g.role),
                granted_by=g.granted_by,
                granted_at=g.granted_at,
                revoked_at=g.revoked_at,
                revoked_by=g.revoked_by,
            )
            for g in grants
        ],
    )


__all__ = ["router"]
