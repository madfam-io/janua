"""Add users.spanish_formality — how Spanish should address this person.

Spanish forces a choice English does not: every sentence addressed at the
reader is either `tú` or `usted`, and there is no neutral second person.

THE PRODUCT IS CURRENTLY SPLIT, and this column is the intended way to close
that split rather than a janua-local nicety. Janua's transactional email is
written in `usted` throughout. Nauta's client portal — the thing the same
person signs into after clicking the link in that email — is written in `tú`
throughout — measured 2026-08-14 across `apps/web/src` and `packages/ui/src`:
ZERO usted markers against ~50 tú markers, down to "revisa tu bandeja de
entrada" on its login page (apps/web/src/app/login/magic-link-form.tsx). One
client, one journey, two registers.

This column is meant to be the single source of truth for both surfaces. It
only fixes the email half today: the portal hardcodes `tú` and does not read
this value yet.

Nullable, and NULL is meaningful: it means "has not chosen", which renders as
`usted`. That is deliberately NOT the same as storing 'usted' on every row —
NULL lets a later prompt ("¿te hablamos de tú o de usted?") tell the people
who have expressed a preference apart from the people who never saw the
question. A backfill would erase that distinction permanently, so there is no
backfill here.

VARCHAR(10) rather than a DB enum. The value set ('tu', 'usted') is owned by
`app/services/email_i18n.py`; a Postgres enum would put a second copy of it in
the schema and turn any future change into an ALTER TYPE on the users table.
The application normalizes and validates on the way in, and
`resolve_formality` treats anything unrecognized as "not chosen" — so an
unexpected value degrades to the safe register instead of raising.

RE-ENTRANT ON PURPOSE. Environments that ran `Base.metadata.create_all`
(settings.AUTO_MIGRATE, and the test suite) already carry this column while
`alembic_version` still reads an older revision; an unguarded add_column would
raise DuplicateColumn and roll back the WHOLE chain, not just this step. Same
idempotency contract as 003/006/007/009/010/011.

Revision ID: 012_user_spanish_formality
Revises: 011_invitation_columns
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
# Keep revision ids <= 32 characters: `alembic_version.version_num` is
# VARCHAR(32) and a longer id fails the stamp write, rolling back the upgrade
# it just performed. Enforced by tests/unit/test_alembic_revision_graph.py.
revision = "012_user_spanish_formality"
down_revision = "011_invitation_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in inspect(bind).get_columns("users")}

    if "spanish_formality" not in existing:
        op.add_column(
            "users",
            sa.Column("spanish_formality", sa.String(length=10), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in inspect(bind).get_columns("users")}

    if "spanish_formality" in existing:
        op.drop_column("users", "spanish_formality")
