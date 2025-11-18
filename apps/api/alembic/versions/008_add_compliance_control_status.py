"""add compliance control status and assessment fields

Revision ID: 008
Revises: 007
Create Date: 2025-11-18 15:00:00.000000

This migration adds the 'status', 'last_assessed', and 'assessed_by' fields
to the compliance_controls table.

Critical Fix: Addresses AttributeError in compliance_service_complete.py line 205
where service code sets control.status = ControlStatus.COMPLIANT but field was missing.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status, last_assessed, and assessed_by fields to compliance_controls.

    New fields:
    - status: Control effectiveness status (compliant, non_compliant, effective, etc.)
    - last_assessed: Timestamp of last assessment
    - assessed_by: User ID of assessor
    """
    # Create enum type for ControlStatus
    control_status_enum = sa.Enum(
        "COMPLIANT",
        "NON_COMPLIANT",
        "EFFECTIVE",
        "INEFFECTIVE",
        "NEEDS_IMPROVEMENT",
        "NOT_TESTED",
        "EXCEPTION",
        name="controlstatus",
        create_type=True,
    )

    # Add status column with default NOT_TESTED
    op.add_column("compliance_controls", sa.Column("status", control_status_enum, nullable=True))

    # Add assessment tracking columns
    op.add_column("compliance_controls", sa.Column("last_assessed", sa.DateTime(), nullable=True))
    op.add_column("compliance_controls", sa.Column("assessed_by", sa.UUID(), nullable=True))

    # Backfill existing records with NOT_TESTED status
    op.execute("""
        UPDATE compliance_controls
        SET status = 'NOT_TESTED'
        WHERE status IS NULL
    """)

    # Make status non-nullable after backfill
    op.alter_column("compliance_controls", "status", nullable=False)

    # Create index for status filtering (common query pattern)
    op.create_index(
        "ix_compliance_controls_status", "compliance_controls", ["status"], unique=False
    )

    # Create composite index for common query: organization + framework + status
    op.create_index(
        "ix_compliance_controls_org_framework_status",
        "compliance_controls",
        ["organization_id", "compliance_framework", "status"],
        unique=False,
    )

    # Add foreign key for assessed_by
    op.create_foreign_key(
        "fk_compliance_controls_assessed_by",
        "compliance_controls",
        "users",
        ["assessed_by"],
        ["id"],
    )


def downgrade() -> None:
    """Remove status and assessment tracking fields."""
    # Drop foreign key
    op.drop_constraint(
        "fk_compliance_controls_assessed_by", "compliance_controls", type_="foreignkey"
    )

    # Drop indexes
    op.drop_index("ix_compliance_controls_org_framework_status", table_name="compliance_controls")
    op.drop_index("ix_compliance_controls_status", table_name="compliance_controls")

    # Drop columns
    op.drop_column("compliance_controls", "assessed_by")
    op.drop_column("compliance_controls", "last_assessed")
    op.drop_column("compliance_controls", "status")

    # Drop enum type
    sa.Enum(name="controlstatus").drop(op.get_bind(), checkfirst=True)
