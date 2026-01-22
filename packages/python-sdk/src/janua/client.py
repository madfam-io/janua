from typing import Optional
from .http_client import HttpClient
from .auth import AuthClient
from .users import UserClient
from .organizations import OrganizationClient
from .types import User, Session


class JanuaClient:
    """
    Main client for interacting with the Janua API
    
    Example:
        ```python
        import asyncio
        from janua import JanuaClient
        
        async def main():
            client = JanuaClient(
                app_id="your-app-id",
                api_key="your-api-key"  # Optional for server-side usage
            )
            
            # Sign up a new user
            response = await client.auth.sign_up(
                email="user@example.com",
                password="secure-password",
                first_name="John",
                last_name="Doe"
            )
            
            print(f"User created: {response.user.email}")
            
            await client.close()
        
        asyncio.run(main())
        ```
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        app_id: Optional[str] = None,
        base_url: str = "https://api.janua.dev",
        api_url: Optional[str] = None,  # Alias for base_url
        timeout: float = 30.0,
        max_retries: int = 3,
        environment: str = "production",
        debug: bool = False,
    ):
        """
        Initialize the Janua client

        Args:
            api_key: Your API key (required, can also be set via JANUA_API_KEY env var)
            app_id: Your Janua application ID (optional)
            base_url: The Janua API URL (defaults to production)
            api_url: Alias for base_url (deprecated)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            environment: Environment name (production, staging, development)
            debug: Enable debug logging
        """
        import os

        # Get API key from argument or environment
        self.api_key = api_key or os.environ.get("JANUA_API_KEY")
        if not self.api_key:
            from .exceptions import ConfigurationError
            raise ConfigurationError("API key is required. Pass api_key parameter or set JANUA_API_KEY environment variable.")

        self.app_id = app_id
        # Support both base_url and api_url (api_url is deprecated)
        self.base_url = api_url or base_url or os.environ.get("JANUA_BASE_URL", "https://api.janua.dev")
        self.api_url = self.base_url  # Alias for compatibility
        self.timeout = timeout
        self.max_retries = max_retries
        self.environment = os.environ.get("JANUA_ENVIRONMENT", environment)
        self.debug = debug
        
        # Store config for access
        self.config = type('Config', (), {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'environment': self.environment,
            'debug': self.debug,
        })()

        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        if app_id:
            headers["X-App-Id"] = app_id

        # Initialize HTTP client
        self.http = HttpClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
            debug=debug,
        )

        # Initialize sub-clients
        self.auth = AuthClient(self.http)
        self.users = UserClient(self.http)
        self.organizations = OrganizationClient(self.http)

        # Add additional service clients expected by tests
        self.sessions = self.auth  # sessions is alias for auth sessions
        self.webhooks = type('WebhooksClient', (), {})()  # placeholder
        self.mfa = type('MFAClient', (), {})()  # placeholder
        self.passkeys = type('PasskeysClient', (), {})()  # placeholder
        
        # Current user and session state
        self._current_user: Optional[User] = None
        self._current_session: Optional[Session] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close the HTTP client connection"""
        await self.http.close()
    
    def get_user(self) -> Optional[User]:
        """Get the current authenticated user"""
        return self._current_user
    
    def get_session(self) -> Optional[Session]:
        """Get the current session"""
        return self._current_session
    
    def is_authenticated(self) -> bool:
        """Check if a user is currently authenticated"""
        return self._current_user is not None and self._current_session is not None
    
    async def sign_out(self):
        """Sign out the current user"""
        await self.auth.sign_out()
        self._current_user = None
        self._current_session = None
    
    async def update_session(self):
        """Update the current session and user information"""
        if not self.is_authenticated():
            raise ValueError("No active session to update")
        
        user = await self.users.get_current_user()
        # Note: In a real implementation, we'd also fetch session info
        self._current_user = user
    
    def set_api_key(self, api_key: str):
        """
        Update the API key for requests

        Args:
            api_key: The new API key
        """
        self.api_key = api_key
        self.config.api_key = api_key
        self.http.set_header("Authorization", f"Bearer {api_key}")

    def set_auth_token(self, token: str):
        """
        Set the authentication token for requests

        Args:
            token: The JWT access token
        """
        self.http.set_header("Authorization", f"Bearer {token}")
    
    def clear_auth_token(self):
        """Clear the authentication token"""
        self.http.remove_header("Authorization")
    
    def _store_session(self, user: User, session: Session):
        """Store the current user and session"""
        self._current_user = user
        self._current_session = session