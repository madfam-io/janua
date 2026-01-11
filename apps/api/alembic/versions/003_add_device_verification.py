"""Add device verification tables and fields

Revision ID: 003
Revises: 002
Create Date: 2025-01-11

Adds:
- trusted_devices table for managing user-trusted devices
- device_fingerprint column to sessions table
- is_trusted_device column to sessions table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to sessions table
    op.add_column('sessions', sa.Column('device_fingerprint', sa.String(length=255), nullable=True))
    op.add_column('sessions', sa.Column('is_trusted_device', sa.Boolean(), nullable=True, server_default='false'))

    # Create index on device_fingerprint
    op.create_index(op.f('ix_sessions_device_fingerprint'), 'sessions', ['device_fingerprint'], unique=False)

    # Create trusted_devices table
    op.create_table('trusted_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=False),
        sa.Column('device_name', sa.String(length=255), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('last_ip_address', sa.String(length=50), nullable=True),
        sa.Column('last_location', sa.String(length=255), nullable=True),
        sa.Column('trust_expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_trusted_devices_user_id'), 'trusted_devices', ['user_id'], unique=False)
    op.create_index(op.f('ix_trusted_devices_device_fingerprint'), 'trusted_devices', ['device_fingerprint'], unique=False)

    # Create unique constraint for user_id + device_fingerprint combination
    op.create_unique_constraint(
        'uq_trusted_devices_user_device',
        'trusted_devices',
        ['user_id', 'device_fingerprint']
    )


def downgrade() -> None:
    # Drop trusted_devices table
    op.drop_constraint('uq_trusted_devices_user_device', 'trusted_devices', type_='unique')
    op.drop_index(op.f('ix_trusted_devices_device_fingerprint'), table_name='trusted_devices')
    op.drop_index(op.f('ix_trusted_devices_user_id'), table_name='trusted_devices')
    op.drop_table('trusted_devices')

    # Remove columns from sessions table
    op.drop_index(op.f('ix_sessions_device_fingerprint'), table_name='sessions')
    op.drop_column('sessions', 'is_trusted_device')
    op.drop_column('sessions', 'device_fingerprint')
