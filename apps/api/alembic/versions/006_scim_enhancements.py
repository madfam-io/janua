"""SCIM enhancements - provider, sync logs, resource tracking

Revision ID: 006_scim_enhancements
Revises: 005_add_oauth_client_secrets
Create Date: 2026-01-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006_scim_enhancements"
down_revision = "005_add_oauth_client_secrets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add provider column to scim_configurations
    op.add_column(
        "scim_configurations",
        sa.Column("provider", sa.String(50), nullable=True, server_default="custom"),
    )

    # Add unique constraint on organization_id for scim_configurations
    # This ensures only one SCIM config per organization
    op.create_unique_constraint(
        "uq_scim_configurations_organization_id",
        "scim_configurations",
        ["organization_id"],
    )

    # Add new columns to scim_resources for better tracking
    op.add_column(
        "scim_resources",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "scim_resources",
        sa.Column("raw_attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
    )
    op.add_column(
        "scim_resources",
        sa.Column("sync_status", sa.String(50), nullable=True, server_default="pending"),
    )
    op.add_column(
        "scim_resources",
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
    )

    # Create scim_sync_logs table for audit and debugging
    op.create_table(
        "scim_sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("operation", sa.String(50), nullable=False),  # create, update, delete, patch
        sa.Column("resource_type", sa.String(50), nullable=False),  # User, Group
        sa.Column("scim_id", sa.String(255), nullable=True),
        sa.Column("internal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),  # success, failed, partial
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("idp_request_id", sa.String(255), nullable=True),
        sa.Column("synced_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_scim_sync_logs_organization_id",
        "scim_sync_logs",
        ["organization_id"],
    )
    op.create_index(
        "ix_scim_sync_logs_synced_at",
        "scim_sync_logs",
        ["synced_at"],
    )
    op.create_index(
        "ix_scim_sync_logs_status",
        "scim_sync_logs",
        ["status"],
    )
    op.create_index(
        "ix_scim_resources_sync_status",
        "scim_resources",
        ["sync_status"],
    )
    op.create_index(
        "ix_scim_resources_external_id",
        "scim_resources",
        ["external_id"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_scim_resources_external_id", table_name="scim_resources")
    op.drop_index("ix_scim_resources_sync_status", table_name="scim_resources")
    op.drop_index("ix_scim_sync_logs_status", table_name="scim_sync_logs")
    op.drop_index("ix_scim_sync_logs_synced_at", table_name="scim_sync_logs")
    op.drop_index("ix_scim_sync_logs_organization_id", table_name="scim_sync_logs")

    # Drop scim_sync_logs table
    op.drop_table("scim_sync_logs")

    # Remove columns from scim_resources
    op.drop_column("scim_resources", "last_synced_at")
    op.drop_column("scim_resources", "sync_status")
    op.drop_column("scim_resources", "raw_attributes")
    op.drop_column("scim_resources", "external_id")

    # Remove unique constraint from scim_configurations
    op.drop_constraint("uq_scim_configurations_organization_id", "scim_configurations", type_="unique")

    # Remove provider column from scim_configurations
    op.drop_column("scim_configurations", "provider")
