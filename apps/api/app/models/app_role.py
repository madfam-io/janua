"""Application role grants — per-organization-member, per-app authority.

An **application role** answers a question `madfam_org_roles` deliberately
cannot: "may this person use *this product's* HR module?". Organization roles
(`owner`/`admin`/`member`) describe authority over the janua **account** —
inviting a colleague, rotating a secret, paying the invoice. They must never
authorize anything inside a product; the whole point of the
`madfam_org_roles` namespace (see `services/org_claims_service.py`) is that
symbiosis-hcm's `HR_ROLES` set contains the literal string ``"admin"``, so an
org-account admin arriving under a bare ``roles`` key would silently become an
HR admin over payroll.

That fix left a hole, and this table is the other half of it. symbiosis-hcm
authorizes on namespaced application roles — ``hcm:hr``, ``hcm:admin``,
``employee`` — read from the token's ``roles`` claim
(`symbiosis-hcm/apps/api/core/permissions.py`). **Nothing in janua emitted a
single ``hcm:*`` string**, so CTM's Dirección could hold a perfectly valid
membership, receive a token with a correct ``org_id``, and still be refused
every HR feature. Membership answered "which tenant"; nothing answered "which
product authority", so the answer was always none.

WHY A TABLE AND NOT A JSONB COLUMN ON THE MEMBERSHIP
----------------------------------------------------
A JSONB blob on `organization_members` would be shorter to write and strictly
worse to live with. This is a **grant of authority over payroll and labour
files**, so the two facts an auditor asks for — *who granted it* and *when it
was taken away* — have to survive the grant itself. A JSONB list holds the
current state and nothing else: revoking is an in-place rewrite that erases the
evidence the grant ever existed. A row per grant, retired with ``revoked_at``
rather than deleted, is the same shape `capability_links` uses and for the same
reason (`models/capability_link.py`: "rows are never deleted"), and it is why
`internal_users.py` has no purge endpoint.

ROWS ARE NEVER DELETED. Revocation stamps ``revoked_at`` + ``revoked_by``. A
re-grant after a revocation is a NEW row, so the history reads as the sequence
of decisions it actually was.

WHY IT HANGS OFF THE MEMBERSHIP AND NOT OFF THE USER
----------------------------------------------------
``organization_member_id``, not ``user_id`` + ``organization_id``. A grant is
meaningless outside the membership that carries it: a user removed from an org
loses the tenant, and their HR authority inside it must go with it rather than
linger as an orphan row that a future re-add would silently reanimate. It also
makes the cross-org leak structurally hard to write — the resolver joins from
ONE membership, so it cannot reach another org's grants even by mistake.

APP AND ROLE ARE OPAQUE TO JANUA
--------------------------------
``app`` ("hcm") and ``role`` ("hr") are strings janua stores, scopes, and
concatenates into ``"<app>:<role>"``. Janua holds no table of valid apps and no
vocabulary of roles, exactly as it holds none for capability-link scopes. The
resource server owns its own role vocabulary — that is the ecosystem rule this
change is careful not to break while filling the gap. Janua's job is to record
*that CTM's Dirección was granted hcm:hr, by whom, and when*, and to put it in
the token; what ``hr`` may do is symbiosis-hcm's to decide.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, String

from app.models import Base
from app.models.types import GUID as UUID

#: Separator between app slug and role in the emitted claim value. A colon,
#: matching the vocabulary symbiosis-hcm already reads (`hcm:hr`, `hcm:admin`)
#: and the `product:tier` shape of `madfam_entitled_products`.
APP_ROLE_SEPARATOR = ":"

#: Bounds mirroring the capability-link scope bounds. Neither is a vocabulary
#: check — janua validates SHAPE, never MEANING.
MAX_APP_LENGTH = 64
MAX_ROLE_LENGTH = 64


def format_app_role(app: str, role: str) -> str:
    """Render one grant as the string a resource server reads: ``"hcm:hr"``.

    The single place the claim value is constructed, so the resolver and the
    admin surface can never disagree about the shape a consumer must match.
    """
    return f"{app}{APP_ROLE_SEPARATOR}{role}"


class OrganizationMemberAppRole(Base):
    """One application-role grant, over one membership, in one app."""

    __tablename__ = "organization_member_app_roles"

    __table_args__ = (
        # THE resolver index. Every token mint asks exactly one question: "which
        # live grants does THIS membership hold?" — so the index is on the
        # membership, and `revoked_at` rides along so the live-only filter is
        # answered from the index rather than by fetching retired rows.
        sa.Index(
            "ix_org_member_app_roles_member",
            "organization_member_id",
            "revoked_at",
        ),
        # At most ONE live grant per (membership, app, role). Partial on
        # `revoked_at IS NULL` on purpose: a revoked grant must not block the
        # person being granted the same role again later, and the re-grant has
        # to be a new row (history is the point) rather than an UPDATE that
        # rewrites when and by whom it was first given.
        # `sqlite_where` mirrors `postgresql_where` on purpose. SQLite supports
        # partial indexes, but SQLAlchemy emits the predicate only for the
        # dialect it is named for — so with the Postgres clause alone the test
        # suite (SQLite) built an UNCONDITIONAL unique index and refused to
        # re-grant a role that had been revoked, which production would have
        # allowed. A test bed that disagrees with prod about an authorization
        # constraint is worse than no test, so both dialects carry the predicate.
        sa.Index(
            "uq_org_member_app_roles_live",
            "organization_member_id",
            "app",
            "role",
            unique=True,
            postgresql_where=sa.text("revoked_at IS NULL"),
            sqlite_where=sa.text("revoked_at IS NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # The membership, not the user. See the module docstring: a grant that
    # outlives the membership it was made under is an orphan that a future
    # re-add would silently reanimate.
    organization_member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organization_members.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Opaque to janua. No enum, no lookup table, no vocabulary — same rule as
    # capability-link scopes. The resource server owns its role names.
    app = Column(String(MAX_APP_LENGTH), nullable=False)
    role = Column(String(MAX_ROLE_LENGTH), nullable=False)

    # WHO granted it. The internal-API principal today; a named operator once
    # service tokens land. Nullable only so a row written by a path that
    # predates a caller identity is not a hard failure.
    granted_by = Column(String(255), nullable=True)
    granted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Retire, never erase — the only "gone" signal, and the reason this is a
    # table rather than a JSONB list.
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(255), nullable=True)

    def is_live(self) -> bool:
        """The one predicate the claim resolver trusts."""
        return self.revoked_at is None


__all__ = [
    "APP_ROLE_SEPARATOR",
    "MAX_APP_LENGTH",
    "MAX_ROLE_LENGTH",
    "OrganizationMemberAppRole",
    "format_app_role",
]
