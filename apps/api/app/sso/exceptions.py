"""
SSO Module Exceptions

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from app.core.exceptions instead.

All SSO exceptions now inherit from the unified exception system in app.core.exceptions.
This provides HTTP status codes and consistent error handling across the application.
"""

# Import from unified exception system
from app.core.exceptions import (
    PlintoSSOException as SSOException,
    SSOAuthenticationError as AuthenticationError,
    SSOValidationError as ValidationError,
    SSOConfigurationError as ConfigurationError,
    SSOMetadataError as MetadataError,
    SSOCertificateError as CertificateError,
    SSOProvisioningError as ProvisioningError,
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
