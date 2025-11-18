"""add organization member status field

Revision ID: 007
Revises: 006
Create Date: 2025-11-18 14:30:00.000000

This migration adds the 'status' field to the organization_members table.
The field is used by RBAC service to filter active organization members.

Critical Fix: Addresses AttributeError in rbac_service.py line 161 where
service code checks OrganizationMember.status == 'active' but field was missing.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status field to organization_members table.

    Default value: 'active'
    Possible values: 'active', 'inactive', 'pending', 'removed'
    """
    # Add status column with default value
    op.add_column(
        "organization_members",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
    )

    # Create index for performance (status is commonly filtered)
    op.create_index(
        "ix_organization_members_status", "organization_members", ["status"], unique=False
    )

    # Create composite index for common query pattern in rbac_service.py
    # Query pattern: WHERE user_id = ? AND organization_id = ? AND status = 'active'
    op.create_index(
        "ix_organization_members_user_org_status",
        "organization_members",
        ["user_id", "organization_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove status field and associated indexes."""
    # Drop indexes first
    op.drop_index("ix_organization_members_user_org_status", table_name="organization_members")
    op.drop_index("ix_organization_members_status", table_name="organization_members")

    # Drop column
    op.drop_column("organization_members", "status")
