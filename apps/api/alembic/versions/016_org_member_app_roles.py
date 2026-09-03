"""Add organization_member_app_roles — per-tenant application role grants.

THE GAP THIS CLOSES. Revision 015's change sealed `org_id` into session tokens
and namespaced organization roles as `madfam_org_roles`, on purpose: HCM's
`HR_ROLES` contains the literal string "admin", so letting org-account roles
ride under a bare `roles` key would have promoted every janua org admin to HR
admin over payroll. That was right, and it left the other half unbuilt.
symbiosis-hcm authorizes on APPLICATION roles — `hcm:hr`, `hcm:admin`,
`employee` — read from `roles` (`symbiosis-hcm/apps/api/core/permissions.py`),
and NOTHING in janua emitted a single `hcm:*` string. CTM's Dirección could
hold a valid membership, receive a token with a correct `org_id`, and still be
refused every HR feature: membership answered "which tenant", nothing answered
"which product authority".

WHY A TABLE AND NOT A JSONB COLUMN on `organization_members`. This grants
authority over payroll and labour files, so the two facts an auditor asks for —
who granted it, and when it was taken away — must survive the grant. A JSONB
list holds current state only: revoking is an in-place rewrite that erases the
evidence the grant existed. A row per grant, retired with `revoked_at` rather
than deleted, is the shape `capability_links` (014) already uses, and the same
reasoning that leaves `internal_users.py` without a purge endpoint.

WHY IT HANGS OFF THE MEMBERSHIP. `organization_member_id`, not user + org: a
grant is meaningless outside the membership carrying it, so a user removed from
an org loses the HR authority with the tenant instead of leaving an orphan row
a future re-add would silently reanimate. It also makes the cross-org leak
structurally hard to write — the resolver joins from ONE membership and cannot
reach another org's grants by mistake.

ADDITIVE ONLY. One new table, two indexes, nothing existing altered, dropped or
backfilled. Rolling this forward cannot change the behaviour of any current
endpoint: the table is empty, and an empty table contributes no role strings, so
every token minted before the grants exist has exactly the shape it has today.

RE-ENTRANT ON PURPOSE, matching 003/006/007/009/010/011/012/014/015:
environments that ran `Base.metadata.create_all` (settings.AUTO_MIGRATE, and the
test suite) already carry this table while `alembic_version` still reads an older
revision. An unguarded `create_table` there raises DuplicateTable and rolls back
the WHOLE chain, not just this step.

DEPLOY NOTE (operator step, not automatic): `promote` runs NO migrations in this
ecosystem. This revision must be applied deliberately against the target
database BEFORE the grant endpoints are exercised there. Until it is, the claims
resolver degrades fail-closed (it catches its own read failure and stamps no app
roles — the pre-change behaviour exactly), and the admin endpoints raise loudly
on the missing relation, which is the intended failure.

Revision ID: 016_org_member_app_roles
Revises: 015_user_is_service_acct
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
# Keep revision ids <= 32 characters: `alembic_version.version_num` is
# VARCHAR(32) and a longer id fails the stamp write, rolling back the upgrade it
# just performed. Enforced by tests/unit/test_alembic_revision_graph.py.
# "016_org_member_app_roles" == 24 chars.
revision = "016_org_member_app_roles"
down_revision = "015_user_is_service_acct"
branch_labels = None
depends_on = None


TABLE = "organization_member_app_roles"
MEMBER_INDEX = "ix_org_member_app_roles_member"
LIVE_UNIQUE_INDEX = "uq_org_member_app_roles_live"


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
            # ON DELETE CASCADE: unlike `capability_links.tenant_id` (which
            # references no table, because janua has no `tenants` relation), the
            # membership IS a real row here. If a membership is ever hard-deleted
            # its grants must go with it — an app-role grant pointing at a
            # membership that no longer exists is authority nobody can see or
            # revoke.
            sa.Column(
                "organization_member_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organization_members.id", ondelete="CASCADE"),
                nullable=False,
            ),
            # Opaque to janua: stored, scoped, and concatenated into
            # "<app>:<role>". No enum and no lookup table — the resource server
            # owns its role vocabulary, same rule as capability-link scopes.
            sa.Column("app", sa.String(length=64), nullable=False),
            sa.Column("role", sa.String(length=64), nullable=False),
            sa.Column("granted_by", sa.String(length=255), nullable=True),
            sa.Column(
                "granted_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            # Retire, never erase. The only "gone" signal.
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_by", sa.String(length=255), nullable=True),
        )

    existing = _index_names(bind)

    # THE resolver index. Every token mint asks one question — "which live
    # grants does THIS membership hold?" — so `revoked_at` rides along and the
    # live-only filter is answered from the index.
    if MEMBER_INDEX not in existing:
        op.create_index(MEMBER_INDEX, TABLE, ["organization_member_id", "revoked_at"])

    # At most ONE live grant per (membership, app, role), so a repeated grant is
    # idempotent at the schema level rather than only in the handler. PARTIAL on
    # `revoked_at IS NULL`: a revoked grant must not block re-granting the same
    # role later, and that re-grant has to be a NEW row — history is the point,
    # so it must not become an UPDATE that rewrites when and by whom the
    # authority was first given.
    if LIVE_UNIQUE_INDEX not in existing:
        op.create_index(
            LIVE_UNIQUE_INDEX,
            TABLE,
            ["organization_member_id", "app", "role"],
            unique=True,
            postgresql_where=sa.text("revoked_at IS NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind):
        return

    existing = _index_names(bind)
    for index_name in (LIVE_UNIQUE_INDEX, MEMBER_INDEX):
        if index_name in existing:
            op.drop_index(index_name, table_name=TABLE)

    # Dropping the table DESTROYS the grant history this design exists to
    # preserve — who was given HR authority over payroll, by whom, and when it
    # was taken away. Acceptable only as the inverse of a forward migration that
    # created the table empty; an operator rolling back a POPULATED table is
    # discarding real audit evidence and should export it first.
    op.drop_table(TABLE)
