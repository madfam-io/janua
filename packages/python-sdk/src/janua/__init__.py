"""
Janua Python SDK
Official Python SDK for Janua - Modern authentication and user management platform
"""

from .client import JanuaClient
from .auth import AuthClient
from .users import UserClient
from .organizations import OrganizationClient
from .types import (
    User,
    Session,
    AuthTokens,
    SignUpRequest,
    SignInRequest,
    SignInResponse,
    SignUpResponse,
    UpdateUserRequest,
    OrganizationInfo,
    OrganizationMembership,
    JanuaError as JanuaErrorModel,  # Renamed to avoid conflict with exception
)
from .exceptions import (
    JanuaError,
    JanuaAPIError,
    ConfigurationError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

__version__ = "0.1.0"

__all__ = [
    "JanuaClient",
    "create_client",
    "AuthClient",
    "UserClient",
    "OrganizationClient",
    "User",
    "Session",
    "AuthTokens",
    "SignUpRequest",
    "SignInRequest",
    "SignInResponse",
    "SignUpResponse",
    "UpdateUserRequest",
    "OrganizationInfo",
    "OrganizationMembership",
    "JanuaError",
    "JanuaAPIError",
    "ConfigurationError",
    "AuthenticationError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
]


def create_client(**kwargs) -> JanuaClient:
    """
    Convenience function to create a JanuaClient instance.

    Args:
        **kwargs: Arguments to pass to JanuaClient constructor

    Returns:
        JanuaClient instance
    """
    return JanuaClient(**kwargs)