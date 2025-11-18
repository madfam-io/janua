"""Add enterprise features

Revision ID: 003
Revises: 002
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '003'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update Organizations table with enterprise features
    op.add_column('organizations', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()'), index=True))
    op.add_column('organizations', sa.Column('subscription_tier', sa.String(50), server_default='free'))
    op.add_column('organizations', sa.Column('subscription_status', sa.String(50), server_default='trial'))
    op.add_column('organizations', sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organizations', sa.Column('features', postgresql.JSONB(), server_default='{}'))
    op.add_column('organizations', sa.Column('limits', postgresql.JSONB(), server_default='{}'))
    op.add_column('organizations', sa.Column('allowed_domains', postgresql.ARRAY(sa.String), server_default='{}'))
    op.add_column('organizations', sa.Column('ip_allowlist', postgresql.ARRAY(sa.String), server_default='{}'))
    op.add_column('organizations', sa.Column('mfa_required', sa.Boolean(), server_default='false'))
    op.add_column('organizations', sa.Column('sso_enabled', sa.Boolean(), server_default='false'))
    op.add_column('organizations', sa.Column('scim_enabled', sa.Boolean(), server_default='false'))
    op.add_column('organizations', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # Create unique index on tenant_id
    op.create_unique_constraint('uq_organizations_tenant_id', 'organizations', ['tenant_id'])
    op.create_index('idx_org_tenant_id', 'organizations', ['tenant_id'])
    op.create_index('idx_org_domain', 'organizations', ['domain'])

    # Drop old organization_members table and recreate with enhanced features
    op.drop_table('organization_members')

    # Create OrganizationRole table
    op.create_table('organization_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('type', sa.String(50), server_default='custom'),
        sa.Column('parent_role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization_roles.id'), nullable=True),
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('permissions', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('is_system', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint('organization_id', 'name', name='uq_org_role_name'),
        sa.Index('idx_org_role_org', 'organization_id')
    )

    # Create new OrganizationMember table with role support
    op.create_table('organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization_roles.id'), nullable=False),
        sa.Column('custom_permissions', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True)),
        sa.Column('joined_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_org_member'),
        sa.Index('idx_org_member_user', 'user_id'),
        sa.Index('idx_org_member_org', 'organization_id')
    )

    # Create PermissionDefinition table
    op.create_table('permission_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('code', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(50)),
        sa.Column('scope', sa.String(50), server_default='organization'),
        sa.Column('requires', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('includes', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )

    # Create SCIMResource table
    op.create_table('scim_resources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scim_id', sa.String(255), unique=True, nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('internal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True)),
        sa.Column('sync_status', sa.String(50), server_default='synced'),
        sa.Column('raw_attributes', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint('organization_id', 'scim_id', name='uq_org_scim_id'),
        sa.Index('idx_scim_resource_org', 'organization_id'),
        sa.Index('idx_scim_resource_type', 'resource_type')
    )

    # Create AuditLog table with hash chain
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('service_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50)),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('event_data', postgresql.JSONB()),
        sa.Column('changes', postgresql.JSONB()),
        sa.Column('previous_hash', sa.String(64)),
        sa.Column('current_hash', sa.String(64), nullable=False),
        sa.Column('compliance_tags', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('retention_until', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Index('idx_audit_org_created', 'organization_id', 'created_at'),
        sa.Index('idx_audit_user', 'user_id'),
        sa.Index('idx_audit_event_type', 'event_type'),
        sa.Index('idx_audit_resource', 'resource_type', 'resource_id'),
        sa.Index('idx_audit_compliance', 'compliance_tags')
    )

    # Update webhook_endpoints table (already exists, just add missing columns)
    op.add_column('webhook_endpoints', sa.Column('max_retries', sa.Integer(), server_default='3'))
    op.add_column('webhook_endpoints', sa.Column('retry_delay', sa.Integer(), server_default='60'))
    op.add_column('webhook_endpoints', sa.Column('success_count', sa.Integer(), server_default='0'))
    op.add_column('webhook_endpoints', sa.Column('failure_count', sa.Integer(), server_default='0'))
    op.add_column('webhook_endpoints', sa.Column('last_success_at', sa.DateTime(timezone=True)))
    op.add_column('webhook_endpoints', sa.Column('last_failure_at', sa.DateTime(timezone=True)))

    # Update webhook_deliveries table (already exists, just add missing columns)
    op.add_column('webhook_deliveries', sa.Column('status', sa.String(50), server_default='pending'))
    op.add_column('webhook_deliveries', sa.Column('attempts', sa.Integer(), server_default='0'))
    op.add_column('webhook_deliveries', sa.Column('request_headers', postgresql.JSONB()))
    op.add_column('webhook_deliveries', sa.Column('request_body', postgresql.JSONB()))
    op.add_column('webhook_deliveries', sa.Column('response_headers', postgresql.JSONB()))
    op.add_column('webhook_deliveries', sa.Column('scheduled_at', sa.DateTime(timezone=True)))
    op.add_column('webhook_deliveries', sa.Column('next_retry_at', sa.DateTime(timezone=True)))
    op.add_column('webhook_deliveries', sa.Column('error_message', sa.Text()))

    # Create indexes for webhook tables
    op.create_index('idx_webhook_active', 'webhook_endpoints', ['is_active'])
    op.create_index('idx_delivery_endpoint', 'webhook_deliveries', ['webhook_endpoint_id'])
    op.create_index('idx_delivery_status', 'webhook_deliveries', ['status'])
    op.create_index('idx_delivery_scheduled', 'webhook_deliveries', ['scheduled_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_delivery_scheduled', 'webhook_deliveries')
    op.drop_index('idx_delivery_status', 'webhook_deliveries')
    op.drop_index('idx_delivery_endpoint', 'webhook_deliveries')
    op.drop_index('idx_webhook_active', 'webhook_endpoints')

    # Remove columns from webhook tables
    op.drop_column('webhook_deliveries', 'error_message')
    op.drop_column('webhook_deliveries', 'next_retry_at')
    op.drop_column('webhook_deliveries', 'scheduled_at')
    op.drop_column('webhook_deliveries', 'response_headers')
    op.drop_column('webhook_deliveries', 'request_body')
    op.drop_column('webhook_deliveries', 'request_headers')
    op.drop_column('webhook_deliveries', 'attempts')
    op.drop_column('webhook_deliveries', 'status')

    op.drop_column('webhook_endpoints', 'last_failure_at')
    op.drop_column('webhook_endpoints', 'last_success_at')
    op.drop_column('webhook_endpoints', 'failure_count')
    op.drop_column('webhook_endpoints', 'success_count')
    op.drop_column('webhook_endpoints', 'retry_delay')
    op.drop_column('webhook_endpoints', 'max_retries')

    # Drop enterprise tables
    op.drop_table('audit_logs')
    op.drop_table('scim_resources')
    op.drop_table('permission_definitions')
    op.drop_table('organization_members')
    op.drop_table('organization_roles')

    # Recreate simple organization_members table
    op.create_table('organization_members',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('role', sa.String(50), server_default='member'),
        sa.Column('permissions', sa.JSON(), server_default='[]'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'))
    )

    # Remove enterprise columns from organizations
    op.drop_index('idx_org_domain', 'organizations')
    op.drop_index('idx_org_tenant_id', 'organizations')
    op.drop_constraint('uq_organizations_tenant_id', 'organizations')

    op.drop_column('organizations', 'deleted_at')
    op.drop_column('organizations', 'scim_enabled')
    op.drop_column('organizations', 'sso_enabled')
    op.drop_column('organizations', 'mfa_required')
    op.drop_column('organizations', 'ip_allowlist')
    op.drop_column('organizations', 'allowed_domains')
    op.drop_column('organizations', 'limits')
    op.drop_column('organizations', 'features')
    op.drop_column('organizations', 'trial_ends_at')
    op.drop_column('organizations', 'subscription_status')
    op.drop_column('organizations', 'subscription_tier')
    op.drop_column('organizations', 'tenant_id')