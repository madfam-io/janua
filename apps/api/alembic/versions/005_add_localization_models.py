"""Add localization models

Revision ID: 005
Revises: 004
Create Date: 2025-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create locales table
    op.create_table('locales',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('code', sa.String(10), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('native_name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_rtl', sa.Boolean(), server_default='false'),
        sa.Column('translation_progress', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )

    # Create indexes for locales
    op.create_index('idx_locales_code', 'locales', ['code'])
    op.create_index('idx_locales_active', 'locales', ['is_active'])

    # Create translation_keys table
    op.create_table('translation_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('key', sa.String(255), nullable=False, unique=True),
        sa.Column('default_value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )

    # Create indexes for translation_keys
    op.create_index('idx_translation_keys_key', 'translation_keys', ['key'])
    op.create_index('idx_translation_keys_category', 'translation_keys', ['category'])

    # Create translations table
    op.create_table('translations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('translation_key_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('translation_keys.id', ondelete='CASCADE'), nullable=False),
        sa.Column('locale_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('locales.id', ondelete='CASCADE'), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('is_approved', sa.Boolean(), server_default='false'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )

    # Create indexes for translations
    op.create_index('idx_translations_key_locale', 'translations', ['translation_key_id', 'locale_id'])
    op.create_index('idx_translations_locale', 'translations', ['locale_id'])
    op.create_index('idx_translations_approved', 'translations', ['is_approved'])

    # Create unique constraint for translation_key_id + locale_id combination
    op.create_unique_constraint('uq_translation_key_locale', 'translations',
                                ['translation_key_id', 'locale_id'])

    # Insert default English (US) locale
    op.execute("""
        INSERT INTO locales (id, code, name, native_name, is_active, is_rtl, translation_progress)
        VALUES (gen_random_uuid(), 'en-US', 'English (US)', 'English (United States)', true, false, 100)
    """)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('translations')
    op.drop_table('translation_keys')
    op.drop_table('locales')
