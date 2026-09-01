"""Schemas for the internal capability-links API.

Design rules these types enforce, per ADR-004:

* The PLAINTEXT TOKEN appears in exactly two response models — the ones returned
  by create and rotate — and in no other. It is never a field on a resolve or
  revoke response, so there is no shape in which janua hands the secret back a
  second time.
* Subject and scopes are OPAQUE STRINGS. There is no enum, no validator that
  knows any app's vocabulary, and no cross-check against a janua table. Adding
  one would make the primitive un-reusable by the next app.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Bounds on the requested lifetime. The floor stops a caller from minting a link
# that is already dead on arrival in the recipient's inbox; the ceiling stops an
# effectively permanent bearer credential from being created by a typo in a
# seconds-vs-days unit. 90 days is generous next to crea-map's 30-day liga and
# still forces a deliberate rotation within a quarter.
MIN_TTL_SECONDS = 60
MAX_TTL_SECONDS = 90 * 24 * 60 * 60

MAX_SCOPES = 32
MAX_SCOPE_LENGTH = 128


class CreateCapabilityLinkRequest(BaseModel):
    """Mint a new capability link over one subject in one tenant."""

    # REQUIRED and never defaulted, for the same reason as on the internal user
    # schemas: it selects the isolation boundary. A defaulted tenant would let a
    # caller that forgot the field mint a grant in the WRONG organization — a
    # cross-tenant authority bug that reads as success.
    tenant_id: UUID

    # Opaque to janua. Janua stores these, scopes lookups by them, and echoes
    # them back. It never parses them and holds no table describing them.
    subject_type: str = Field(min_length=1, max_length=64)
    subject_id: str = Field(min_length=1, max_length=255)

    # Opaque strings the CALLING APP interprets. An empty list is rejected: a
    # capability link that grants nothing is always a caller bug, and silently
    # accepting it would mint a live token that mysteriously authorizes nothing.
    scopes: List[str] = Field(min_length=1, max_length=MAX_SCOPES)

    ttl_seconds: int = Field(ge=MIN_TTL_SECONDS, le=MAX_TTL_SECONDS)

    use_mode: Literal["single_use", "multi_use"] = "multi_use"

    # Caller context for an operator UI or the app's own audit. NEVER secret
    # material — this is stored verbatim and returned by resolve-adjacent reads.
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("scopes")
    @classmethod
    def _validate_scopes(cls, scopes: List[str]) -> List[str]:
        """Reject blank/oversized scopes and duplicates.

        Janua does not know what a scope MEANS, but it can still refuse a scope
        list that is malformed as a list: an empty string is not a capability,
        and a duplicate silently inflates the count an app may reason about.
        """
        cleaned: List[str] = []
        for scope in scopes:
            value = scope.strip()
            if not value:
                raise ValueError("scopes must not contain empty strings")
            if len(value) > MAX_SCOPE_LENGTH:
                raise ValueError(f"scope exceeds {MAX_SCOPE_LENGTH} characters")
            cleaned.append(value)
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("scopes must not contain duplicates")
        return cleaned


class CapabilityLinkCreatedResponse(BaseModel):
    """Result of create/rotate. THE ONLY SHAPE CARRYING THE PLAINTEXT TOKEN.

    ``token`` is shown ONCE. Janua stores only its SHA-256 and cannot reproduce
    it: if the caller loses this value the link must be rotated, not recovered.
    """

    id: str
    tenant_id: str
    subject_type: str
    subject_id: str
    scopes: List[str]
    use_mode: str
    token: str
    expires_at: datetime
    created_at: datetime


class ResolveCapabilityLinkRequest(BaseModel):
    """Present a plaintext token for resolution."""

    token: str = Field(min_length=1, max_length=512)

    # OPTIONAL, and when present it is an ADDITIONAL constraint, never a
    # relaxation: a resolve that names a tenant must match the link's tenant, so
    # an app serving one tenant cannot be tricked into honouring another
    # tenant's token. Omitting it resolves whatever tenant the token belongs to
    # and returns that tenant_id for the caller to check itself.
    tenant_id: Optional[UUID] = None


class ResolveCapabilityLinkResponse(BaseModel):
    """A successful resolution. Carries NO token."""

    id: str
    tenant_id: str
    subject_type: str
    subject_id: str
    scopes: List[str]
    use_mode: str
    expires_at: datetime
    # Post-resolve count, so a single-use link reports 1 here and is spent.
    use_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RevokeCapabilityLinkRequest(BaseModel):
    """Retire a link by id. Requires the tenant that owns it."""

    tenant_id: UUID
    reason: Optional[str] = Field(default=None, max_length=64)


class CapabilityLinkStatusResponse(BaseModel):
    """Result of revoke. ``changed`` is False when it was already revoked."""

    id: str
    tenant_id: str
    revoked: bool
    revoked_at: Optional[datetime] = None
    changed: bool


class RotateCapabilityLinkRequest(BaseModel):
    """Replace a link's token, keeping subject and scopes.

    ``ttl_seconds`` is optional: omitted, the replacement inherits the ORIGINAL
    link's full lifetime measured from now — not the old row's remaining time,
    which would produce a rotation that is dead on arrival for a nearly-expired
    link, the exact situation rotation exists to fix.
    """

    tenant_id: UUID
    ttl_seconds: Optional[int] = Field(default=None, ge=MIN_TTL_SECONDS, le=MAX_TTL_SECONDS)
