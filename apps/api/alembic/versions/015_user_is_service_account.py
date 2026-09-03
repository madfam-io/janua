"""Add users.is_service_account — a technical login is not a person.

Every multi-app tenant grows technical logins: a development access account, an
importer, an integration principal. Today janua's `User` distinguishes
`status`, `is_active`, `is_admin` and `tenant_id` — and NONE of those answer the
question a consuming app actually asks, which is "is this row a human being?".
So a technical login renders in every roster, every assignee picker and every
document-signature field as if it were a colleague.

The concrete instance that motivated this column: crea-map (the CTM clinical
MAP) carries a synthetic member row for development access. Its own domain doc
(`crea-map/docs/CTM_DOMAIN.md`) deliberately declined to invent a local boolean
for a single row — correctly, because the fact is not crea-map's to own. The
fact belongs to identity, which is janua, and every app that binds to a janua
`sub` can then read it from one place.

WHY A COLUMN AND NOT A SEPARATE TABLE. A service principal in this sense is
still a `User`: it has a tenant pool, sessions, memberships, an audit trail. A
parallel table would fork every one of those code paths and give the ecosystem
two half-implemented identity models. This is a fact ABOUT a user, so it is a
column on the user. (Machine-to-machine identity, which has no user row at all,
is a different and already-solved thing: `client_credentials` OAuth clients —
see docs/service-tokens.md. This column is for the *human-shaped* logins that
are nonetheless not humans.)

NOT NULL DEFAULT FALSE. Every existing row is a person until an operator says
otherwise; there is no backfill to guess, and no NULL third state to interpret.
Server-side default so rows written by paths that predate the column (or by raw
SQL) land correct rather than NULL.

NON-DESTRUCTIVE AND ADDITIVE. One new column with a safe default. No existing
column is altered or dropped, no index is touched, no data is rewritten.
Rolling forward cannot change the behaviour of any current endpoint: nothing
reads the column until the code in the same change is deployed, and everything
that does read it treats False (the value every existing row gets) as today's
behaviour exactly.

DEPLOY NOTE (operator step, not automatic): `promote` runs NO migrations in
this ecosystem. This revision must be applied deliberately against the target
database. Until it is, the ORM's SELECT of the column raises loudly against a
database that lacks it — the intended failure, not a silent wrong answer.

RE-ENTRANT ON PURPOSE, matching 003/006/007/009/010/011/012/014: environments
that ran `Base.metadata.create_all` (settings.AUTO_MIGRATE, and the test suite)
already carry this column while `alembic_version` still reads an older
revision. An unguarded add_column there raises DuplicateColumn and rolls back
the WHOLE chain, not just this step.

Revision ID: 015_user_is_service_acct
Revises: 014_capability_links
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
# Keep revision ids <= 32 characters: `alembic_version.version_num` is
# VARCHAR(32) and a longer id fails the stamp write, rolling back the upgrade
# it just performed. Enforced by tests/unit/test_alembic_revision_graph.py.
revision = "015_user_is_service_acct"
down_revision = "014_capability_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in inspect(bind).get_columns("users")}

    if "is_service_account" not in existing:
        op.add_column(
            "users",
            sa.Column(
                "is_service_account",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in inspect(bind).get_columns("users")}

    if "is_service_account" in existing:
        op.drop_column("users", "is_service_account")
