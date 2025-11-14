"""Add performance indexes for auth optimization

Revision ID: 006_performance_indexes
Revises: 005_add_localization_models
Create Date: 2025-11-14 15:45:00.000000

Strategic indexes to optimize authentication and query performance:
- users.email: Login/signup user lookups
- sessions.token: Session validation
- sessions.user_id + is_active: Active session queries
- audit_logs indexes: Compliance and audit trail queries
- Multi-tenant optimizations
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_performance_indexes'
down_revision = '005_add_localization_models'
branch_labels = None
depends_on = None


def upgrade():
    """Add strategic performance indexes"""

    # Users table indexes
    # Primary use: User lookup on login/signup by email
    # Expected improvement: 50-100x faster (full scan → index lookup)
    op.create_index(
        'idx_users_email',
        'users',
        ['email'],
        unique=False
    )

    # Multi-tenant user lookup optimization
    # Primary use: Tenant-scoped user queries
    op.create_index(
        'idx_users_tenant_email',
        'users',
        ['tenant_id', 'email'],
        unique=False
    )

    # Sessions table indexes
    # Primary use: Session validation on every authenticated request
    # Expected improvement: 30-50x faster
    op.create_index(
        'idx_sessions_token',
        'sessions',
        ['token'],
        unique=False
    )

    # Composite index for active session queries
    # Primary use: Get active sessions for a user
    op.create_index(
        'idx_sessions_user_active',
        'sessions',
        ['user_id', 'is_active'],
        unique=False
    )

    # Session expiry queries
    # Primary use: Cleanup expired sessions, session validation
    op.create_index(
        'idx_sessions_expires',
        'sessions',
        ['expires_at'],
        unique=False
    )

    # Audit logs indexes
    # Primary use: Audit trail queries, compliance reports
    # Expected improvement: 100x+ faster for time-range queries
    op.create_index(
        'idx_audit_user_time',
        'audit_logs',
        ['user_id', 'created_at'],
        unique=False,
        postgresql_ops={'created_at': 'DESC'}
    )

    op.create_index(
        'idx_audit_tenant_time',
        'audit_logs',
        ['tenant_id', 'created_at'],
        unique=False,
        postgresql_ops={'created_at': 'DESC'}
    )

    # Event type filtering for security analysis
    # Primary use: Security event monitoring, threat detection
    op.create_index(
        'idx_audit_event_type',
        'audit_logs',
        ['event_type', 'created_at'],
        unique=False,
        postgresql_ops={'created_at': 'DESC'}
    )

    # Organizations table index (if exists)
    # Primary use: Organization lookup
    try:
        op.create_index(
            'idx_organizations_tenant',
            'organizations',
            ['tenant_id'],
            unique=False
        )
    except Exception:
        # Table might not exist in all environments
        pass


def downgrade():
    """Remove performance indexes"""

    # Drop in reverse order
    try:
        op.drop_index('idx_organizations_tenant', table_name='organizations')
    except Exception:
        pass

    op.drop_index('idx_audit_event_type', table_name='audit_logs')
    op.drop_index('idx_audit_tenant_time', table_name='audit_logs')
    op.drop_index('idx_audit_user_time', table_name='audit_logs')
    op.drop_index('idx_sessions_expires', table_name='sessions')
    op.drop_index('idx_sessions_user_active', table_name='sessions')
    op.drop_index('idx_sessions_token', table_name='sessions')
    op.drop_index('idx_users_tenant_email', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
