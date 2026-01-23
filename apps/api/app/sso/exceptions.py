"""
SSO Module Exceptions

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from app.core.exceptions instead.

All SSO exceptions now inherit from the unified exception system in app.core.exceptions.
This provides HTTP status codes and consistent error handling across the application.
"""

# Import from unified exception system
from app.core.exceptions import (
    JanuaSSOException as SSOException,
)
from app.core.exceptions import (
    SSOAuthenticationError as AuthenticationError,
)
from app.core.exceptions import (
    SSOCertificateError as CertificateError,
)
from app.core.exceptions import (
    SSOConfigurationError as ConfigurationError,
)
from app.core.exceptions import (
    SSOMetadataError as MetadataError,
)
from app.core.exceptions import (
    SSOProvisioningError as ProvisioningError,
)
from app.core.exceptions import (
    SSOValidationError as ValidationError,
)

# Re-export for backward compatibility
__all__ = [
    "SSOException",
    "AuthenticationError",
    "ValidationError",
    "ConfigurationError",
    "MetadataError",
    "CertificateError",
    "ProvisioningError",
]
