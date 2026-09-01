"""Add capability_links — tenant-scoped, subject-opaque bearer grants.

ADDITIVE ONLY. This creates one new table and touches nothing existing: no
column is altered, no index on another table is dropped, and no data is
backfilled. Rolling this migration forward cannot change the behaviour of any
current endpoint, because until the router in the same change is deployed
nothing reads or writes the table.

See docs/architecture/ADR-004_CAPABILITY_LINKS.md for the design. The two facts
the schema encodes and the reviewer should check for:

  * `token_hash` (not `token`). The plaintext is never stored, so this table is
    not a credential store the way `guest_invites.token` is.
  * `revoked_at` (not a delete). Grants are retired, never erased.

RE-ENTRANT ON PURPOSE, matching 003/006/007/009/010/011/012: environments that
ran `Base.metadata.create_all` (settings.AUTO_MIGRATE, and the test suite)
already carry this table while `alembic_version` still reads an older revision.
An unguarded `create_table` there raises DuplicateTable and rolls back the WHOLE
chain, not just this step — the failure mode 012's docstring records.

DEPLOY NOTE (operator step, not automatic): `promote` runs NO migrations in this
ecosystem. This revision must be applied deliberately against the target
database before the capability-links endpoints are exercised there. Until it is,
the router's handlers raise on a missing relation — loudly, which is the
intended failure. Nothing else regresses, since no existing code path touches
this table.

Revision ID: 014_capability_links
Revises: 013_per_tenant_email_uniqueness
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
# Keep revision ids <= 32 characters: `alembic_version.version_num` is
# VARCHAR(32) and a longer id fails the stamp write, rolling back the upgrade
# it just performed. Enforced by tests/unit/test_alembic_revision_graph.py.
# "014_capability_links" == 20 chars.
revision = "014_capability_links"
down_revision = "013_per_tenant_email_uniqueness"
branch_labels = None
depends_on = None


TABLE = "capability_links"
TOKEN_HASH_INDEX = "uq_capability_links_token_hash"
SUBJECT_INDEX = "ix_capability_links_tenant_subject"
TENANT_INDEX = "ix_capability_links_tenant_id"


def _has_table(bind) -> bool:
    return TABLE in set(inspect(bind).get_table_names())


def _index_names(bind) -> set:
    return {ix["name"] for ix in inspect(bind).get_indexes(TABLE)}


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind):
        op.create_table(
            TABLE,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            # No ForeignKey: janua has no `tenants` table (users.tenant_id is
            # itself an unconstrained indexed UUID). An FK here would reference
            # a relation that does not exist.
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            # Opaque to janua: stored and echoed verbatim, never parsed.
            sa.Column("subject_type", sa.String(length=64), nullable=False),
            sa.Column("subject_id", sa.String(length=255), nullable=False),
            # JSONB array of opaque scope strings. Not a delimited String: a
            # scope containing the delimiter would split into two and FABRICATE
            # authority.
            sa.Column(
                "scopes",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            # SHA-256 hex is always 64 chars. The PLAINTEXT IS NEVER STORED.
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column(
                "use_mode",
                sa.String(length=16),
                nullable=False,
                server_default="multi_use",
            ),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            # Retire, never erase. Set by BOTH revoke and rotate.
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_reason", sa.String(length=64), nullable=True),
            sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "link_metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("created_by", sa.String(length=64), nullable=True),
        )

    existing = _index_names(bind)

    # Resolve does exactly ONE lookup, by hash. UNIQUE both enforces
    # no-collision and provides the index that lookup rides.
    if TOKEN_HASH_INDEX not in existing:
        op.create_index(TOKEN_HASH_INDEX, TABLE, ["token_hash"], unique=True)

    if TENANT_INDEX not in existing:
        op.create_index(TENANT_INDEX, TABLE, ["tenant_id"])

    if SUBJECT_INDEX not in existing:
        op.create_index(SUBJECT_INDEX, TABLE, ["tenant_id", "subject_type", "subject_id"])


def downgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind):
        return

    existing = _index_names(bind)
    for index_name in (SUBJECT_INDEX, TENANT_INDEX, TOKEN_HASH_INDEX):
        if index_name in existing:
            op.drop_index(index_name, table_name=TABLE)

    # Dropping the table DESTROYS the grant history this design is careful to
    # preserve. That is acceptable only as the inverse of a migration whose
    # forward direction created the table empty; an operator rolling back a
    # populated capability_links is discarding real audit evidence and should
    # export it first.
    op.drop_table(TABLE)
