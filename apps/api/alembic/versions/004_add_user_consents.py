"""Add user_consents table for OAuth consent management

Revision ID: 004
Revises: 003
Create Date: 2025-01-11

Adds the user_consents table to store OAuth client consent grants.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_consents table
    op.create_table('user_consents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.String(length=255), nullable=False),
        sa.Column('scopes', postgresql.JSONB(), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_user_consents_user_id'), 'user_consents', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_consents_client_id'), 'user_consents', ['client_id'], unique=False)

    # Create unique constraint for user_id + client_id combination
    op.create_unique_constraint(
        'uq_user_consents_user_client',
        'user_consents',
        ['user_id', 'client_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_user_consents_user_client', 'user_consents', type_='unique')
    op.drop_index(op.f('ix_user_consents_client_id'), table_name='user_consents')
    op.drop_index(op.f('ix_user_consents_user_id'), table_name='user_consents')
    op.drop_table('user_consents')
