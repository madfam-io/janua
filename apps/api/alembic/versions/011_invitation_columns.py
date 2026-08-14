"""Add the two invitation columns the router has always read and written.

`app/routers/v1/invitations.py` returns `message` and `email_sent` from every
read endpoint, and `PATCH /invitations/{id}` writes `message`. Neither column
existed: alembic `000_init` created `invitations` with only (id,
organization_id, email, role, status, token, expires_at, accepted_at,
created_by, created_at) and the SQLAlchemy model matched that exactly. So the
reads raised AttributeError before reaching the database, and PATCH's write
landed on a plain Python attribute that no commit could ever persist -- the
endpoint reported the new message back to the caller and stored nothing.

`message` is offered by `InvitationCreate`, returned by `InvitationResponse`
and updatable through `InvitationUpdate`. Persisting it is what lets those
three schemas describe the same field; the alternative -- deleting it from the
request and response models -- would remove a documented field from the public
API and every generated SDK to work around a missing column on an empty table.

`email_sent` is reported by the list/get/update responses, which read a row
back from the database and therefore have no request-scoped send outcome to
borrow. It defaults to false and is set by the delivery path.

The table is empty everywhere (verified 0 rows in production on 2026-08-13
before this migration was written), so the new NOT NULL column can take a
server default without a backfill step.

`IF NOT EXISTS` keeps this idempotent against environments that ran
`Base.metadata.create_all` instead of migrations (the test suite does).

Revision ID: 011_invitation_columns
Revises: 010_policy_authz_columns
"""

from alembic import op

revision = "011_invitation_columns"
down_revision = "010_policy_authz_columns"
branch_labels = None
depends_on = None


# (column, DDL type + constraints)
_COLUMNS = [
    ("message", "text"),
    ("email_sent", "boolean NOT NULL DEFAULT false"),
]


def upgrade() -> None:
    for name, ddl in _COLUMNS:
        op.execute(f"ALTER TABLE invitations ADD COLUMN IF NOT EXISTS {name} {ddl}")

    # Every list/count query scopes to a set of organizations and then filters
    # or groups by status.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_invitations_organization_id_status "
        "ON invitations (organization_id, status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_invitations_organization_id_status")
    for name, _ in reversed(_COLUMNS):
        op.execute(f"ALTER TABLE invitations DROP COLUMN IF EXISTS {name}")
