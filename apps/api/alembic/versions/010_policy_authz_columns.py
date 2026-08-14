"""Add the authorization columns `policies` was always read and written with.

`app/routers/v1/policies.py` and `app/services/policy_engine.py` have referenced
`effect`, `priority`, `enabled`, `version`, `target_type`, `target_id`,
`resource_type`, `resource_pattern`, `actions`, `conditions` and `expires_at`
since they were written. None of them existed: alembic 000_init created
`policies` with only (id, name, description, rules, organization_id, created_at,
updated_at) and the SQLAlchemy model matched that. Every create/list/get/update
/delete therefore raised before reaching the database, so the table stayed empty
(verified 0 rows in production on 2026-08-13 before this migration was written).

Because the table is empty everywhere, the new NOT NULL columns can take server
defaults without a backfill step.

`IF NOT EXISTS` keeps this idempotent against environments that ran
`Base.metadata.create_all` instead of migrations (the test suite does).

Revision ID: 010_policy_authz_columns
Revises: 009_add_legacy_webhook_events
"""

from alembic import op

revision = "010_policy_authz_columns"
down_revision = "009_add_legacy_webhook_events"
branch_labels = None
depends_on = None


# (column, DDL type + constraints)
_COLUMNS = [
    ("effect", "varchar(20) NOT NULL DEFAULT 'allow'"),
    ("priority", "integer NOT NULL DEFAULT 0"),
    ("enabled", "boolean NOT NULL DEFAULT true"),
    ("version", "integer NOT NULL DEFAULT 1"),
    ("target_type", "varchar(50)"),
    ("target_id", "varchar(255)"),
    ("resource_type", "varchar(255)"),
    ("resource_pattern", "varchar(500)"),
    ("actions", "jsonb DEFAULT '[]'::jsonb"),
    ("conditions", "jsonb DEFAULT '{}'::jsonb"),
    ("expires_at", "timestamp"),
]


def upgrade() -> None:
    for name, ddl in _COLUMNS:
        op.execute(f"ALTER TABLE policies ADD COLUMN IF NOT EXISTS {name} {ddl}")

    # The engine's hot path filters enabled policies within one organization.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policies_organization_id_enabled "
        "ON policies (organization_id, enabled)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policies_target_type_target_id "
        "ON policies (target_type, target_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_policies_target_type_target_id")
    op.execute("DROP INDEX IF EXISTS ix_policies_organization_id_enabled")
    for name, _ in reversed(_COLUMNS):
        op.execute(f"ALTER TABLE policies DROP COLUMN IF EXISTS {name}")
