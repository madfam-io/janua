"""Add guest_invites table for guest access link management.

Revision ID: 004_add_guest_invites
Revises: 003
Create Date: 2026-03-15

NOTE ON down_revision: migrations 000-003 use bare numeric revision ids
('000'..'003'); 004 onwards use `NNN_slug` ids. This file originally pointed at
"003_add_product_tiers" -- the *filename stem* of 003, not its revision id,
which is '003'. That dangling parent made every alembic command (history,
heads, current, stamp, upgrade) raise KeyError: '003_add_product_tiers', so no
migration from 004 onwards could ever be applied. Keep this pointing at '003'.
"""

import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004_add_guest_invites"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guest_invites",
        sa.Column("id", sa.Uuid(), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(255), unique=True, nullable=False),
        sa.Column("label", sa.String(255), server_default=""),
        sa.Column("max_uses", sa.Integer(), server_default="0"),
        sa.Column("use_count", sa.Integer(), server_default="0"),
        sa.Column("guest_ttl_hours", sa.Integer(), server_default="4"),
        sa.Column("room_id", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked", sa.Boolean(), server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_guest_invites_token", "guest_invites", ["token"], unique=True)
    op.create_index(
        "ix_guest_invites_org_id", "guest_invites", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_guest_invites_org_id")
    op.drop_index("ix_guest_invites_token")
    op.drop_table("guest_invites")
