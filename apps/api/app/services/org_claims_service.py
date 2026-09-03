"""Organization claims service — the SSOT for org/tenant/role token claims.

Computes the organization-membership claims that org-scoped resource servers
(symbiosis-hcm, and any future tenant-partitioned API) need in order to
authorize a caller at all. Every token-minting seam in janua — the OIDC
authorization-code grant, the OIDC refresh grant, `AuthService.create_session`
(magic link, password login, MFA completion, passkey) and
`AuthService.refresh_tokens` — resolves these claims *here*, not locally.

This module exists because the resolver used to live inline in
``routers/v1/oauth_provider.py``, which made it structurally unreachable from
the session path: a magic-link token carried no ``org_id`` at all, so
symbiosis-hcm answered 403 to every CTM team member who arrived through the
MAP's «Mi espacio (RH)» link. Two hand-maintained copies of a claim resolver
drift, and a drifted authorization claim fails either closed (someone stops
working) or open (someone gains a tenant) — so there is exactly one copy, and
the OIDC router imports it.

Claim contract
--------------

``orgs``
    Every ACTIVE membership as ``{id, slug, role}``. Omitted entirely when the
    user has none.

``org_id`` / ``tenant_id`` / ``org_slug``
    Emitted ONLY when unambiguous — exactly one active membership, or
    ``user.tenant_id`` names one of them. Ambiguity emits ``orgs`` alone;
    consumers must not guess a tenant. This is deliberate: guessing a primary
    org for a multi-org user is how one tenant's operator reads another
    tenant's payroll.

``madfam_org_roles``
    The user's organization roles (``owner`` / ``admin`` / ``member``) for the
    resolved primary org, under a namespace that says *which* authority issued
    them. **This is not, and must never be read as, an application role.**

Why ``madfam_org_roles`` and not ``roles``
-----------------------------------------

The legacy ``roles`` claim (OIDC only) carries organization-membership roles —
``owner``/``admin``/``member`` — but its name promises nothing about the
namespace those strings live in. symbiosis-hcm read it as its HR role list, and
its ``HR_ROLES`` set contains the literal string ``"admin"``. So the moment
``org_id`` reached an HCM-bound token, every janua org *account* admin would
have become an HR admin over payroll and labour files. Sealing the org claim
without namespacing the role claim converts today's honest 403 into a payroll
leak.

Session tokens therefore stamp the namespaced ``madfam_org_roles`` and
**deliberately do NOT stamp a bare ``roles``**. A resource server that wants
org roles asks for them by their real name; a resource server that wants
application roles must source them from its own authority (HCM does exactly
this — see ``symbiosis-hcm/apps/api/core/permissions.py``). The OIDC path keeps
emitting ``roles`` unchanged for existing clients — this module adds the
namespaced claim alongside it, it does not remove anything.

Resolution never raises: a failure emits no org claims at all (fail-closed —
downstream org-scoped services reject, and never mis-scope).
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, OrganizationMember, User

logger = structlog.get_logger()

#: Namespaced claim key for organization-membership roles. Namespaced on
#: purpose: see the module docstring. Do not rename without a coordinated
#: change in every consumer — the name IS the contract about the authority.
ORG_ROLES_CLAIM = "madfam_org_roles"


async def get_user_org_claims(user: User, db: AsyncSession) -> dict[str, Any]:
    """Resolve organization claims for a human token.

    Returns a dict ready to merge into a JWT payload. Empty when the user has
    no active membership, or when resolution fails.

    Memberships with status other than ``active`` (pending/inactive/removed)
    never contribute — a removed member must not keep tenant access through a
    long-lived refresh chain.
    """
    try:
        result = await db.execute(
            select(OrganizationMember, Organization)
            .join(
                Organization,
                Organization.id == OrganizationMember.organization_id,
            )
            .where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.status == "active",
            )
        )
        rows = result.all()
    except Exception as e:
        logger.warning(
            "Failed to fetch org claims, omitting from token",
            user_id=str(user.id),
            error=str(e),
        )
        try:
            await db.rollback()
        except Exception:  # pragma: no cover - defensive; rollback may itself fail
            pass
        return {}

    if not rows:
        return {}

    claims: dict[str, Any] = {
        "orgs": [
            {"id": str(org.id), "slug": org.slug, "role": member.role or "member"}
            for member, org in rows
        ]
    }

    primary_member = None
    primary = None
    if len(rows) == 1:
        primary_member, primary = rows[0]
    else:
        tenant_id = getattr(user, "tenant_id", None)
        if tenant_id:
            tenant_id = str(tenant_id)
            for member, org in rows:
                if str(org.id) == tenant_id:
                    primary_member, primary = member, org
                    break

    if primary is not None:
        claims.update(
            {
                "org_id": str(primary.id),
                "tenant_id": str(primary.id),
                "org_slug": primary.slug,
                # Namespaced. NOT `roles`. See module docstring: HCM's HR_ROLES
                # contains "admin", so an org-account admin landing in a bare
                # `roles` claim would read as an HR admin over payroll.
                ORG_ROLES_CLAIM: [(primary_member.role if primary_member else None) or "member"],
            }
        )

    return claims


async def get_user_org_claims_safe(user: User, db: AsyncSession) -> dict[str, Any]:
    """`get_user_org_claims` that can never raise, for the session-mint path.

    Org claims enrich a session; they must never be able to block a login.
    ``get_user_org_claims`` already degrades its own DB reads, and this guard
    covers anything unexpected above them — matching how the entitlement claim
    is resolved in ``AuthService.create_session``.
    """
    try:
        return await get_user_org_claims(user, db)
    except Exception:  # pragma: no cover - defensive; never fail login on this
        logger.warning(
            "Failed to resolve org claims for session token; stamping none",
            user_id=str(user.id),
        )
        return {}


__all__ = ["ORG_ROLES_CLAIM", "get_user_org_claims", "get_user_org_claims_safe"]
