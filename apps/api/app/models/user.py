"""
User models - backward compatibility module
"""

# Import all user-related models from the main models module
from . import (
    User,
    Session,
    UserStatus,
    Organization,
    OrganizationMember,
    AuditLog,
    ActivityLog
)

# Aliases for backward compatibility
Tenant = Organization  # Tenant is an alias for Organization