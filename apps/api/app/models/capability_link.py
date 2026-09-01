"""Capability links — tenant-scoped, subject-opaque bearer grants.

A capability link is a shareable secret that grants a NAMED SET OF SCOPES over
ONE SUBJECT inside ONE TENANT, for a bounded time. It is the generalization of a
pattern three MADFAM apps had each hand-rolled (crea-map's «liga de familia»,
kalya's guest booking links, nauta's portal/NDA links). See
``docs/architecture/ADR-004_CAPABILITY_LINKS.md`` for the full rationale.

Two invariants make this table different from ``guest_invites`` (janua's nearest
existing relative, which this model deliberately does NOT replace or migrate):

1. THE PLAINTEXT TOKEN IS NEVER STORED. Only ``token_hash`` — SHA-256 over the
   URL-safe token — lands in the row. The plaintext is returned exactly once, at
   create/rotate time, and janua cannot reproduce it afterwards. A dump of this
   table therefore yields no usable credential. ``guest_invites.token`` stores
   plaintext and is the counter-example this design is reacting to.

2. THE SUBJECT IS OPAQUE. ``subject_type``/``subject_id`` are free strings that
   janua stores, scopes, and hands back verbatim. Janua never parses them, never
   joins on them, and holds no table describing them. The same is true of
   ``scopes``: they are strings the CALLING APP interprets. This is what keeps
   the primitive reusable — janua does not need to learn a vocabulary per app.

ROWS ARE NEVER DELETED. Revocation and rotation set ``revoked_at`` (plus
``replaced_by_id`` for rotation), so the grant history stays auditable. There is
no delete endpoint and must not be one, for the same reason
``internal_users.py`` has no purge: destroying the record destroys the evidence
that access was ever granted.

WHY SHA-256 AND NOT A PASSWORD HASH (bcrypt/argon2): the token is 256 bits of
``secrets.token_urlsafe(32)`` entropy, not a human-chosen password. There is no
dictionary to attack, so the slow-KDF work factor buys nothing while making
every resolve expensive. This is the same reasoning the wider industry applies
to API keys, and it is what crea-map already does for the liga de familia.
"""

from __future__ import annotations

import enum
import hashlib
import secrets
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, String

from app.models import Base
from app.models.types import GUID as UUID
from app.models.types import JSON as JSONB

# Bytes of entropy handed to `secrets.token_urlsafe`. 32 bytes -> a 43-character
# URL-safe string, ~256 bits. Matches the magic-link token width already used in
# `auth.py`, so link length is nothing operators have to newly reason about.
TOKEN_ENTROPY_BYTES = 32

# `sha256().hexdigest()` is always 64 characters. Fixed-width by construction, so
# the column is CHAR-like rather than an open-ended String.
TOKEN_HASH_LENGTH = 64


class CapabilityLinkUseMode(str, enum.Enum):
    """Whether resolving the link burns it.

    SINGLE_USE burns on the FIRST SUCCESSFUL resolve (an expired or revoked
    resolve must not consume the grant — otherwise a stranger poking a dead
    link could pre-burn a live one). MULTI_USE never burns and dies only by
    expiry, revocation, or rotation.
    """

    SINGLE_USE = "single_use"
    MULTI_USE = "multi_use"


def generate_token() -> str:
    """Mint a new plaintext capability token. Returned to the caller ONCE."""
    return secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)


def hash_token(token: str) -> str:
    """Hash a plaintext token to its at-rest form.

    Unsalted on purpose: the input is full-entropy random, so a per-row salt
    would defend against a rainbow table that cannot exist. Unsalted also means
    the hash is DETERMINISTIC, which is what lets resolve find the row with a
    single indexed lookup instead of scanning every row to compare.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class CapabilityLink(Base):
    """A tenant-scoped, subject-opaque, scoped bearer grant."""

    __tablename__ = "capability_links"

    __table_args__ = (
        # Resolve does exactly one lookup, by hash. UNIQUE both enforces the
        # no-collision invariant and provides the index that lookup rides.
        sa.Index("uq_capability_links_token_hash", "token_hash", unique=True),
        # Listing/reconciling an app's links for one subject: the app asks
        # "which grants exist over THIS subject in THIS tenant".
        sa.Index("ix_capability_links_tenant_subject", "tenant_id", "subject_type", "subject_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # No ForeignKey: janua has no `tenants` table — `users.tenant_id` is itself a
    # bare indexed UUID column (models/__init__.py:71). Adding an FK here would
    # reference a relation that does not exist and fail at create_all.
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Opaque to janua. `subject_type` is the caller's namespace for the kind of
    # thing ("usuario", "booking", "engagement"); `subject_id` identifies the one
    # instance. Stored and echoed verbatim — never parsed.
    subject_type = Column(String(64), nullable=False)
    subject_id = Column(String(255), nullable=False)

    # JSON array of opaque scope strings. JSONB (not a delimited String) so a
    # scope containing the delimiter can never split into two — the ambient
    # failure mode of comma-joined permission columns, and here it would
    # FABRICATE authority rather than lose it.
    scopes = Column(JSONB, nullable=False, default=list)

    token_hash = Column(String(TOKEN_HASH_LENGTH), nullable=False)

    use_mode = Column(String(16), nullable=False, default=CapabilityLinkUseMode.MULTI_USE.value)

    expires_at = Column(DateTime, nullable=False)

    # Observability without leaking: how many times it resolved and when it last
    # did. Enough for an app to notice a shared-around link, holding no secret.
    use_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # Set for BOTH revoke and rotate; `revoked_reason` tells them apart. Rows are
    # never deleted, so this is the only "gone" signal.
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(64), nullable=True)

    # On rotate, the OLD row points at its replacement. Gives an auditor the
    # chain of custody for a grant that has been rotated several times.
    replaced_by_id = Column(UUID(as_uuid=True), nullable=True)

    # Free-form caller context (a label for an operator UI, an issuing user id).
    # NEVER the token: nothing written here is treated as secret.
    link_metadata = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(64), nullable=True)

    # ------------------------------------------------------------------ state

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """True once `expires_at` has passed. Naive UTC, matching every other
        timestamp in this schema (`datetime.utcnow` throughout models/)."""
        return (now or datetime.utcnow()) >= self.expires_at

    def is_exhausted(self) -> bool:
        """True when a single-use link has already been successfully resolved."""
        return (
            self.use_mode == CapabilityLinkUseMode.SINGLE_USE.value and (self.use_count or 0) >= 1
        )

    def is_active(self, *, now: datetime | None = None) -> bool:
        """The one predicate resolve trusts: not revoked, not expired, not spent."""
        if self.revoked_at is not None:
            return False
        if self.is_expired(now=now):
            return False
        return not self.is_exhausted()
