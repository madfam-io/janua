"""Add oauth_client_secrets table for credential rotation

Revision ID: 005
Revises: 004
Create Date: 2025-01-11

Adds the oauth_client_secrets table to support graceful client secret rotation
with overlap periods where multiple secrets are valid simultaneously.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create oauth_client_secrets table
    op.create_table('oauth_client_secrets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('secret_hash', sa.String(length=255), nullable=False),
        sa.Column('secret_prefix', sa.String(length=20), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['oauth_clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_oauth_client_secrets_client_id'), 'oauth_client_secrets', ['client_id'], unique=False)
    op.create_index(op.f('ix_oauth_client_secrets_is_primary'), 'oauth_client_secrets', ['is_primary'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_oauth_client_secrets_is_primary'), table_name='oauth_client_secrets')
    op.drop_index(op.f('ix_oauth_client_secrets_client_id'), table_name='oauth_client_secrets')
    op.drop_table('oauth_client_secrets')
