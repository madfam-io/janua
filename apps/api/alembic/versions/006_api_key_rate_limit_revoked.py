"""Add rate_limit_per_min, revoked_at, and key_prefix columns to api_keys table.

These columns support the new API key management features:
- rate_limit_per_min: per-key rate limiting (default 60 req/min)
- revoked_at: explicit revocation timestamp (supplements is_active flag)
- key_prefix: visible prefix like "sk_live_ab3f" for key identification

Revision ID: 006_api_key_rate_limit_revoked
Revises: 005_set_tezca_client_audience
Create Date: 2026-04-15

NOTE ON THE REVISION ID: this was "006_add_api_key_rate_limit_and_revoked" --
38 characters. `alembic_version.version_num` is VARCHAR(32), so alembic could
never record this revision: the write failed with StringDataRightTruncation and
rolled the whole upgrade back. It was invisible only because the dangling
down_revision in 004 stopped every upgrade before it got this far. Renaming is
safe precisely because no database can ever have stored it. Keep revision ids
<= 32 characters (enforced by tests/unit/test_alembic_revision_graph.py).
"""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "006_api_key_rate_limit_revoked"
down_revision = "005_set_tezca_client_audience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Each column is added only if absent. Environments that ran
    # `Base.metadata.create_all` (settings.AUTO_MIGRATE) already carry all three
    # while alembic_version reads an older revision; add_column would raise
    # DuplicateColumn and roll the whole chain back. Guarding per column rather
    # than early-returning on the first one means a partially-migrated table
    # still converges. Same idempotency contract as 003/007/009/010/011.
    existing = {c["name"] for c in inspect(bind).get_columns("api_keys")}

    # rate_limit_per_min: per-key rate limiting, with a sensible default
    if "rate_limit_per_min" not in existing:
        op.add_column(
            "api_keys",
            sa.Column("rate_limit_per_min", sa.Integer(), nullable=True, server_default="60"),
        )
    # revoked_at timestamp (nullable -- NULL means not revoked)
    if "revoked_at" not in existing:
        op.add_column(
            "api_keys",
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )
    # key_prefix for visible short prefix (e.g. "sk_live_ab3f")
    if "key_prefix" not in existing:
        op.add_column(
            "api_keys",
            sa.Column("key_prefix", sa.String(length=12), nullable=True),
        )

    # Backfill revoked_at for already-revoked keys (is_active=false). The
    # `revoked_at IS NULL` predicate makes this safe to re-run.
    op.execute(
        "UPDATE api_keys SET revoked_at = updated_at WHERE is_active = false AND revoked_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("api_keys", "key_prefix")
    op.drop_column("api_keys", "revoked_at")
    op.drop_column("api_keys", "rate_limit_per_min")
