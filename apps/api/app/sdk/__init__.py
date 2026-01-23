"""
SDK support utilities and base classes for Janua API consumption.

This module provides the foundation for generating robust, platform-specific
SDKs that work consistently across TypeScript, Python, Go, Java, and mobile platforms.
"""

from .authentication import (
    AuthenticationFlow,
    TokenManager,
    TokenRefreshStrategy,
)
from .client_base import (
    AuthenticationMethod,
    BaseAPIClient,
    ClientConfig,
    RequestOptions,
    RetryConfig,
)
from .error_handling import (
    APIError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    SDKError,
    ServerError,
    ValidationError,
)
from .response_handlers import (
    BulkOperationHandler,
    PaginationHandler,
    ResponseHandler,
)

__all__ = [
    # Core client classes
    "BaseAPIClient",
    "ClientConfig",
    "AuthenticationMethod",
    "RetryConfig",
    "RequestOptions",
    # Authentication
    "TokenManager",
    "AuthenticationFlow",
    "TokenRefreshStrategy",
    # Error handling
    "SDKError",
    "APIError",
    "ValidationError",
    "AuthenticationError",
    "RateLimitError",
    "ServerError",
    "NetworkError",
    # Response handling
    "ResponseHandler",
    "PaginationHandler",
    "BulkOperationHandler",
]
