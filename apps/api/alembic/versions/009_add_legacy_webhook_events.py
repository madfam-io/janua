"""Add legacy_webhook_events table.

The LegacyWebhookEvent model (app/models/__init__.py) shipped without any
migration, so environments that only ran migrations never had the table.
In prod (alembic at 002) every fully-valid signup 503'd: the user row
committed, then the event-log INSERT poisoned the session and the next
commit blew up with UndefinedTableError (2026-08-02 incident; hand-DDL
hotfix applied the same day). IF NOT EXISTS keeps this idempotent against
environments that received that hotfix or ran metadata.create_all.

Revision ID: 009_add_legacy_webhook_events
Revises: 008_connected_accounts
"""

from alembic import op

revision = "009_add_legacy_webhook_events"
down_revision = "008_connected_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS legacy_webhook_events (
            id uuid PRIMARY KEY,
            type varchar(255) NOT NULL,
            data jsonb DEFAULT '{}'::jsonb,
            user_id uuid REFERENCES users(id),
            organization_id uuid REFERENCES organizations(id),
            created_at timestamp
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS legacy_webhook_events")
