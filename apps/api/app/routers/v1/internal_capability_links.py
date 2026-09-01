"""Internal capability-link endpoints — create / resolve / revoke / rotate.

A capability link is a shareable secret granting a NAMED SET OF SCOPES over ONE
SUBJECT inside ONE TENANT, for a bounded time. It generalizes a pattern three
sibling apps had each hand-rolled (crea-map's «liga de familia», kalya's guest
booking links, nauta's portal/NDA links). Full rationale, prior art and
non-goals: ``docs/architecture/ADR-004_CAPABILITY_LINKS.md``.

Auth
----
Every endpoint uses ``verify_internal_api_key`` — the same ``X-Internal-API-Key``
dependency as ``internal_users.py``, and the same trust janua already extends to
sibling apps. As there, the dependency is a swappable seam: it is declared once
per route and no handler body depends on the shared key, so the ratified move to
janua-issued service tokens is a dependency swap, not a rewrite.

What janua deliberately does NOT know
-------------------------------------
``subject_type``/``subject_id`` and every scope string are OPAQUE. Janua stores
them, scopes lookups by them, and hands them back verbatim. It never parses
them, joins on them, or validates them against any vocabulary. That opacity is
the whole reason one primitive can serve a clinical roster, a booking, and an
NDA without janua learning three domain models.

Two security properties the handlers below exist to hold
--------------------------------------------------------
1. THE PLAINTEXT TOKEN IS RETURNED ONCE AND NEVER LOGGED. It appears in the
   create and rotate response bodies and nowhere else — not in a log line, not
   in an audit ``details`` blob, not in an error message. Janua stores only
   SHA-256 and cannot reproduce it.
2. EVERY RESOLVE FAILURE LOOKS IDENTICAL. Unknown, expired, revoked, spent, and
   wrong-tenant all return the SAME 404 with the SAME body. A caller cannot use
   the response to learn that a token once existed, which is what makes the
   surface enumeration-resistant.

Scope guarantee
---------------
There is NO delete endpoint and must not be one. Revocation and rotation set
``revoked_at``; the row survives. Same reasoning as ``internal_users.py``'s
missing purge: destroying the record destroys the evidence that access was ever
granted, to whom, and over what.
"""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_internal_api_key
from app.models.capability_link import (
    CapabilityLink,
    CapabilityLinkUseMode,
    generate_token,
    hash_token,
)
from app.routers.v1.oauth_clients import INTERNAL_API_KEY_PRINCIPAL
from app.schemas.capability_link import (
    CapabilityLinkCreatedResponse,
    CapabilityLinkStatusResponse,
    CreateCapabilityLinkRequest,
    ResolveCapabilityLinkRequest,
    ResolveCapabilityLinkResponse,
    RevokeCapabilityLinkRequest,
    RotateCapabilityLinkRequest,
)
from app.services.audit_logger import AuditEventType, AuditLogger

logger = structlog.get_logger()

router = APIRouter(prefix="/capability-links", tags=["internal"])

# THE ONLY refusal text this router emits for a token that does not resolve.
# Deliberately says nothing about WHY. See the module docstring's property 2.
GENERIC_RESOLVE_REFUSAL = "Invalid or expired capability link"

# Reasons stamped into `revoked_reason`, distinguishing the two ways a row dies.
REVOKED_BY_CALLER = "revoked"
REVOKED_BY_ROTATION = "rotated"


def _utcnow() -> datetime:
    """Naive UTC, matching every other timestamp in this schema."""
    return datetime.utcnow()


async def _audit(
    db: AsyncSession,
    *,
    event_type: AuditEventType,
    tenant_id: str,
    link_id: str,
    details: dict,
) -> None:
    """Best-effort audit on the AuditLogger hash-chain trail.

    Mirrors ``internal_users.py``: a failure here must never block the operation,
    and we do NOT use ``AuthService.create_audit_log`` (it references AuditLog
    columns that do not exist and raises AttributeError).

    CALLERS MUST NEVER PASS TOKEN MATERIAL IN ``details``. The audit trail is a
    long-lived, widely-readable store; a plaintext token written here would
    outlive the link and defeat hash-at-rest entirely.
    """
    try:
        audit_logger = AuditLogger(db)
        await audit_logger.log(
            event_type=event_type,
            tenant_id=tenant_id,
            identity_id=None,
            resource_type="capability_link",
            resource_id=link_id,
            details={"actor": INTERNAL_API_KEY_PRINCIPAL, **details},
            severity="info",
        )
    except Exception:
        pass


def _created_response(link: CapabilityLink, token: str) -> CapabilityLinkCreatedResponse:
    """Build the once-only response. The single place plaintext leaves janua."""
    return CapabilityLinkCreatedResponse(
        id=str(link.id),
        tenant_id=str(link.tenant_id),
        subject_type=link.subject_type,
        subject_id=link.subject_id,
        scopes=list(link.scopes or []),
        use_mode=link.use_mode,
        token=token,
        expires_at=link.expires_at,
        created_at=link.created_at,
    )


async def _get_owned_link(
    db: AsyncSession, link_id: UUID, tenant_id: UUID
) -> Optional[CapabilityLink]:
    """Fetch a link BY ID AND TENANT.

    The tenant predicate is in the WHERE clause, not an `if` after the fetch: a
    post-fetch check is one early `return` away from being skipped, and the
    consequence here is cross-tenant revocation of another org's grant.
    """
    result = await db.execute(
        select(CapabilityLink).where(
            CapabilityLink.id == link_id,
            CapabilityLink.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


# ------------------------------------------------------------------- create


@router.post(
    "",
    response_model=CapabilityLinkCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_capability_link(
    body: CreateCapabilityLinkRequest,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> CapabilityLinkCreatedResponse:
    """Mint a capability link. Returns the plaintext token ONCE.

    NOT idempotent, and deliberately so — unlike ``internal_users.provision``.
    Two calls with identical arguments mint two INDEPENDENT links with different
    tokens, because collapsing them would mean either handing back a token janua
    no longer holds (impossible) or silently re-issuing one grant to two
    recipients who can then never be revoked apart.
    """
    token = generate_token()
    now = _utcnow()

    link = CapabilityLink(
        tenant_id=body.tenant_id,
        subject_type=body.subject_type,
        subject_id=body.subject_id,
        scopes=list(body.scopes),
        token_hash=hash_token(token),
        use_mode=body.use_mode,
        expires_at=now + timedelta(seconds=body.ttl_seconds),
        use_count=0,
        link_metadata=dict(body.metadata),
        created_at=now,
        created_by=INTERNAL_API_KEY_PRINCIPAL,
    )
    db.add(link)
    await db.flush()  # assign link.id without ending the transaction

    await _audit(
        db,
        event_type=AuditEventType.API_KEY_CREATE,
        tenant_id=str(body.tenant_id),
        link_id=str(link.id),
        details={
            "via": "internal.capability_links.create",
            "subject_type": body.subject_type,
            "subject_id": body.subject_id,
            "scopes": list(body.scopes),
            "use_mode": body.use_mode,
            "expires_at": link.expires_at.isoformat(),
            # NO TOKEN. See _audit's docstring.
        },
    )

    await db.commit()
    await db.refresh(link)

    # Structured log carries the link ID, never the token.
    logger.info(
        "Created capability link",
        link_id=str(link.id),
        tenant_id=str(body.tenant_id),
        subject_type=body.subject_type,
        use_mode=body.use_mode,
    )

    return _created_response(link, token)


# ------------------------------------------------------------------ resolve


@router.post("/resolve", response_model=ResolveCapabilityLinkResponse)
async def resolve_capability_link(
    body: ResolveCapabilityLinkRequest,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> ResolveCapabilityLinkResponse:
    """Exchange a plaintext token for its subject + scopes.

    EVERY failure — unknown token, expired, revoked, single-use already spent,
    or a tenant mismatch — raises the SAME 404 with ``GENERIC_RESOLVE_REFUSAL``.
    The branches are separate below only so the server-side log can say what
    happened; the client learns nothing that distinguishes them.

    POST, not GET, because the token is the request body: a GET would put live
    credential material in the URL, where it lands in access logs, proxy logs,
    and browser history — the leak path this whole design is built to avoid.
    """
    token_hash = hash_token(body.token)

    result = await db.execute(select(CapabilityLink).where(CapabilityLink.token_hash == token_hash))
    link = result.scalar_one_or_none()

    if link is None:
        # Compare against a dummy of equal length so the not-found path does the
        # same work as the found path. The dominant timing signal on this
        # endpoint is the indexed DB lookup rather than this comparison, so this
        # is a hardening measure, not a proof of constant time — the real
        # enumeration defence is the 256-bit token plus the identical refusal.
        hmac.compare_digest(token_hash, "0" * len(token_hash))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GENERIC_RESOLVE_REFUSAL)

    # Confirm the stored hash really matches, in constant time. The indexed
    # equality above already selected this row, so this is belt-and-braces
    # against a lookup path that ever stops being an exact match.
    if not hmac.compare_digest(link.token_hash, token_hash):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GENERIC_RESOLVE_REFUSAL)

    # A caller that names a tenant must match. Same refusal as "no such token":
    # otherwise a distinguishable error would confirm the token is real and
    # merely belongs to someone else.
    if body.tenant_id is not None and link.tenant_id != body.tenant_id:
        logger.warning(
            "Capability link resolve refused: tenant mismatch",
            link_id=str(link.id),
            requested_tenant_id=str(body.tenant_id),
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GENERIC_RESOLVE_REFUSAL)

    now = _utcnow()
    if not link.is_active(now=now):
        logger.info(
            "Capability link resolve refused: inactive",
            link_id=str(link.id),
            # Server-side only. The CLIENT sees none of this.
            revoked=link.revoked_at is not None,
            expired=link.is_expired(now=now),
            exhausted=link.is_exhausted(),
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GENERIC_RESOLVE_REFUSAL)

    # Burn/count only on SUCCESS. A refused resolve must not advance use_count —
    # otherwise anyone holding a revoked or expired token could pre-spend a
    # single-use grant they are not entitled to use.
    link.use_count = (link.use_count or 0) + 1
    link.last_used_at = now

    await db.commit()
    await db.refresh(link)

    logger.info(
        "Resolved capability link",
        link_id=str(link.id),
        tenant_id=str(link.tenant_id),
        use_count=link.use_count,
    )

    return ResolveCapabilityLinkResponse(
        id=str(link.id),
        tenant_id=str(link.tenant_id),
        subject_type=link.subject_type,
        subject_id=link.subject_id,
        scopes=list(link.scopes or []),
        use_mode=link.use_mode,
        expires_at=link.expires_at,
        use_count=link.use_count,
        metadata=dict(link.link_metadata or {}),
    )


# ------------------------------------------------------------------- revoke


@router.post("/{link_id}/revoke", response_model=CapabilityLinkStatusResponse)
async def revoke_capability_link(
    link_id: UUID,
    body: RevokeCapabilityLinkRequest,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> CapabilityLinkStatusResponse:
    """Retire a link by id. Idempotent; the row is never deleted.

    Always 200 when the link exists in the caller's tenant: ``changed`` reports
    whether THIS call was the one that revoked it. 404 when there is no such
    link in that tenant — which is also the answer for a link that exists in
    ANOTHER tenant, so revoke cannot be used to probe for foreign link ids.
    """
    link = await _get_owned_link(db, link_id, body.tenant_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No capability link with that id in this tenant",
        )

    if link.revoked_at is not None:
        # Already revoked: report success without re-writing, so the audit trail
        # is not padded with repeat revocations of the same grant.
        return CapabilityLinkStatusResponse(
            id=str(link.id),
            tenant_id=str(link.tenant_id),
            revoked=True,
            revoked_at=link.revoked_at,
            changed=False,
        )

    link.revoked_at = _utcnow()
    link.revoked_reason = (body.reason or REVOKED_BY_CALLER)[:64]

    await _audit(
        db,
        event_type=AuditEventType.API_KEY_REVOKE,
        tenant_id=str(link.tenant_id),
        link_id=str(link.id),
        details={
            "via": "internal.capability_links.revoke",
            "reason": link.revoked_reason,
            "subject_type": link.subject_type,
            "subject_id": link.subject_id,
        },
    )

    await db.commit()
    await db.refresh(link)

    logger.info("Revoked capability link", link_id=str(link.id), tenant_id=str(link.tenant_id))

    return CapabilityLinkStatusResponse(
        id=str(link.id),
        tenant_id=str(link.tenant_id),
        revoked=True,
        revoked_at=link.revoked_at,
        changed=True,
    )


# ------------------------------------------------------------------- rotate


@router.post(
    "/{link_id}/rotate",
    response_model=CapabilityLinkCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def rotate_capability_link(
    link_id: UUID,
    body: RotateCapabilityLinkRequest,
    _auth: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
) -> CapabilityLinkCreatedResponse:
    """Issue a replacement token; the old one dies in the same transaction.

    Rotation is the answer to "the link leaked" and to "the recipient lost it".
    The replacement is a NEW ROW carrying the same subject, scopes and use_mode;
    the old row is revoked with reason ``rotated`` and points at its successor
    via ``replaced_by_id``, so an auditor can follow the chain of custody.

    A REVOKED OR EXPIRED LINK CANNOT BE ROTATED — that is a 409, not a silent
    re-issue. Rotating a dead grant would resurrect authority an operator
    already withdrew, turning revocation into something a caller can undo.
    Mint a new link instead; the deliberate act belongs in the caller's code.
    """
    link = await _get_owned_link(db, link_id, body.tenant_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No capability link with that id in this tenant",
        )

    now = _utcnow()
    if link.revoked_at is not None or link.is_expired(now=now):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Capability link is revoked or expired and cannot be rotated",
        )

    # Omitted TTL inherits the ORIGINAL link's full lifetime measured from now,
    # not its remaining time — a rotation of a nearly-expired link must not be
    # dead on arrival, which is the very case rotation exists to serve.
    if body.ttl_seconds is not None:
        ttl = timedelta(seconds=body.ttl_seconds)
    else:
        ttl = link.expires_at - link.created_at

    token = generate_token()
    replacement = CapabilityLink(
        tenant_id=link.tenant_id,
        subject_type=link.subject_type,
        subject_id=link.subject_id,
        scopes=list(link.scopes or []),
        token_hash=hash_token(token),
        use_mode=link.use_mode,
        expires_at=now + ttl,
        use_count=0,
        link_metadata=dict(link.link_metadata or {}),
        created_at=now,
        created_by=INTERNAL_API_KEY_PRINCIPAL,
    )
    db.add(replacement)
    await db.flush()

    # The old token dies in the SAME transaction that mints the new one, so
    # there is no window in which both are live and none in which neither is.
    link.revoked_at = now
    link.revoked_reason = REVOKED_BY_ROTATION
    link.replaced_by_id = replacement.id

    await _audit(
        db,
        event_type=AuditEventType.API_KEY_ROTATE,
        tenant_id=str(link.tenant_id),
        link_id=str(link.id),
        details={
            "via": "internal.capability_links.rotate",
            "replaced_by_id": str(replacement.id),
            "subject_type": link.subject_type,
            "subject_id": link.subject_id,
        },
    )

    await db.commit()
    await db.refresh(replacement)

    logger.info(
        "Rotated capability link",
        link_id=str(link_id),
        replacement_id=str(replacement.id),
        tenant_id=str(replacement.tenant_id),
    )

    return _created_response(replacement, token)


# Referenced so the enum is part of this module's contract surface: use_mode
# strings on the wire are exactly CapabilityLinkUseMode's values.
_USE_MODES = tuple(mode.value for mode in CapabilityLinkUseMode)
