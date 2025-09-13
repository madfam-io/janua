# Python SDK Quickstart

Get started with Plinto authentication in your Python application in minutes.

## Installation

```bash
pip install plinto
# or
poetry add plinto
```

## Basic Setup

```python
from plinto import PlintoClient

# Initialize the client
client = PlintoClient(
    base_url="https://api.plinto.dev",
    api_key="YOUR_API_KEY",
    tenant_id="YOUR_TENANT_ID"
)
```

## Quick Examples

### Sign Up
```python
try:
    response = client.auth.sign_up(
        email="user@example.com",
        password="SecurePassword123!",
        first_name="John",
        last_name="Doe"
    )
    print(f"Welcome, {response.user.first_name}!")
    # Tokens are automatically stored
except PlintoError as e:
    print(f"Sign up failed: {e.message}")
```

### Sign In
```python
try:
    response = client.auth.sign_in(
        email="user@example.com",
        password="SecurePassword123!"
    )
    print(f"Welcome back, {response.user.first_name}!")
except AuthenticationError as e:
    print("Invalid credentials")
except PlintoError as e:
    print(f"Sign in failed: {e.message}")
```

### Get Current User
```python
user = client.users.get_current_user()
print(f"Logged in as: {user.email}")
```

### Sign Out
```python
client.auth.sign_out()
print("Signed out successfully")
```

## Async Support

```python
import asyncio
from plinto import AsyncPlintoClient

async def main():
    # Initialize async client
    client = AsyncPlintoClient(
        base_url="https://api.plinto.dev",
        api_key="YOUR_API_KEY",
        tenant_id="YOUR_TENANT_ID"
    )
    
    # Async operations
    response = await client.auth.sign_in(
        email="user@example.com",
        password="password"
    )
    print(f"Signed in: {response.user.email}")
    
    # Cleanup
    await client.close()

asyncio.run(main())
```

## Social Authentication

### OAuth Flow
```python
# Get authorization URL
auth_url = client.auth.get_oauth_url(provider="google")
print(f"Redirect user to: {auth_url}")

# Handle callback (in your web framework)
def oauth_callback(request):
    code = request.args.get("code")
    state = request.args.get("state")
    
    if code and state:
        response = client.auth.handle_oauth_callback(code, state)
        print(f"Signed in with OAuth: {response.user.email}")
```

## Multi-Factor Authentication

### Enable MFA
```python
mfa_setup = client.auth.enable_mfa()
print(f"QR Code: {mfa_setup.qr_code}")
print(f"Recovery codes: {', '.join(mfa_setup.recovery_codes)}")
```

### Verify MFA
```python
code = input("Enter your 6-digit code: ")
client.auth.verify_mfa(code)
print("MFA verified successfully")
```

## Session Management

### List Sessions
```python
sessions = client.sessions.list()
for session in sessions:
    print(f"Device: {session.device}, Location: {session.location}")
    print(f"Created: {session.created_at}")
```

### Revoke Session
```python
client.sessions.revoke(session_id="session_123")
print("Session revoked")
```

## Organization Management

### List Organizations
```python
orgs = client.organizations.list()
for org in orgs:
    print(f"{org.name} - Role: {org.role}")
```

### Create Organization
```python
org = client.organizations.create(
    name="My Company",
    description="A great place to work"
)
print(f"Created organization: {org.id}")
```

## Error Handling

```python
from plinto import (
    PlintoError,
    ValidationError,
    AuthenticationError,
    RateLimitError,
    NetworkError
)

try:
    client.auth.sign_in(email=email, password=password)
except ValidationError as e:
    # Handle validation errors
    for violation in e.violations:
        print(f"{violation.field}: {violation.message}")
except AuthenticationError as e:
    # Handle auth errors
    print("Invalid credentials")
except RateLimitError as e:
    # Handle rate limiting
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
except NetworkError as e:
    # Handle network errors
    print("Network error occurred")
except PlintoError as e:
    # Handle other Plinto errors
    print(f"Error {e.code}: {e.message}")
```

## Advanced Configuration

### Custom HTTP Client
```python
import httpx

custom_client = httpx.Client(
    timeout=30.0,
    headers={"User-Agent": "MyApp/1.0"}
)

client = PlintoClient(
    base_url="https://api.plinto.dev",
    api_key="YOUR_API_KEY",
    tenant_id="YOUR_TENANT_ID",
    http_client=custom_client
)
```

### Retry Configuration
```python
from plinto import RetryConfig

client = PlintoClient(
    base_url="https://api.plinto.dev",
    api_key="YOUR_API_KEY",
    tenant_id="YOUR_TENANT_ID",
    retry_config=RetryConfig(
        max_retries=3,
        backoff_factor=2,
        retry_statuses=[500, 502, 503, 504]
    )
)
```

## Django Integration

### Settings
```python
# settings.py
PLINTO_CONFIG = {
    'BASE_URL': 'https://api.plinto.dev',
    'API_KEY': os.environ.get('PLINTO_API_KEY'),
    'TENANT_ID': os.environ.get('PLINTO_TENANT_ID'),
}
```

### Middleware
```python
# middleware.py
from django.utils.functional import SimpleLazyObject
from plinto import PlintoClient

def get_plinto_user(request):
    if not hasattr(request, '_cached_plinto_user'):
        client = PlintoClient(**settings.PLINTO_CONFIG)
        try:
            request._cached_plinto_user = client.users.get_current_user()
        except:
            request._cached_plinto_user = None
    return request._cached_plinto_user

class PlintoAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.plinto_user = SimpleLazyObject(
            lambda: get_plinto_user(request)
        )
        return self.get_response(request)
```

### View Decorator
```python
# decorators.py
from functools import wraps
from django.http import HttpResponseForbidden

def plinto_login_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.plinto_user:
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)
    return wrapped_view

# Usage
@plinto_login_required
def protected_view(request):
    return JsonResponse({'user': request.plinto_user.email})
```

## Flask Integration

### Extension
```python
# flask_plinto.py
from flask import g, current_app
from plinto import PlintoClient

class Plinto:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        app.config.setdefault('PLINTO_BASE_URL', 'https://api.plinto.dev')
        app.teardown_appcontext(self.teardown)
    
    def teardown(self, exception):
        client = g.pop('plinto_client', None)
        if client is not None:
            client.close()
    
    @property
    def client(self):
        if 'plinto_client' not in g:
            g.plinto_client = PlintoClient(
                base_url=current_app.config['PLINTO_BASE_URL'],
                api_key=current_app.config['PLINTO_API_KEY'],
                tenant_id=current_app.config['PLINTO_TENANT_ID']
            )
        return g.plinto_client

# Usage
from flask import Flask
plinto = Plinto()

app = Flask(__name__)
app.config.from_object('config')
plinto.init_app(app)

@app.route('/profile')
def profile():
    user = plinto.client.users.get_current_user()
    return jsonify(user.to_dict())
```

## FastAPI Integration

### Dependency Injection
```python
# dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from plinto import PlintoClient

security = HTTPBearer()

def get_plinto_client():
    return PlintoClient(
        base_url="https://api.plinto.dev",
        api_key=os.environ.get("PLINTO_API_KEY"),
        tenant_id=os.environ.get("PLINTO_TENANT_ID")
    )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    client: PlintoClient = Depends(get_plinto_client)
):
    try:
        return client.users.get_current_user(token=credentials.credentials)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Usage
from fastapi import FastAPI, Depends

app = FastAPI()

@app.get("/profile")
async def profile(user = Depends(get_current_user)):
    return {"email": user.email, "name": user.first_name}
```

## Testing

### Mocking
```python
from unittest.mock import Mock, patch
from plinto import PlintoClient

def test_sign_in():
    # Mock the client
    mock_client = Mock(spec=PlintoClient)
    mock_response = Mock()
    mock_response.user.email = "test@example.com"
    mock_client.auth.sign_in.return_value = mock_response
    
    # Test
    result = mock_client.auth.sign_in(
        email="test@example.com",
        password="password"
    )
    
    assert result.user.email == "test@example.com"
    mock_client.auth.sign_in.assert_called_once()

# Using pytest fixtures
import pytest

@pytest.fixture
def plinto_client():
    with patch('plinto.PlintoClient') as mock:
        yield mock.return_value

def test_get_user(plinto_client):
    plinto_client.users.get_current_user.return_value = Mock(
        email="test@example.com"
    )
    
    user = plinto_client.users.get_current_user()
    assert user.email == "test@example.com"
```

## Logging

```python
import logging
from plinto import PlintoClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

client = PlintoClient(
    base_url="https://api.plinto.dev",
    api_key="YOUR_API_KEY",
    tenant_id="YOUR_TENANT_ID",
    debug=True  # Enable debug mode
)
```

## Best Practices

1. **Environment Variables**: Store credentials in environment variables
   ```python
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   
   client = PlintoClient(
       base_url=os.getenv("PLINTO_BASE_URL"),
       api_key=os.getenv("PLINTO_API_KEY"),
       tenant_id=os.getenv("PLINTO_TENANT_ID")
   )
   ```

2. **Connection Pooling**: Reuse client instances
   ```python
   # singleton.py
   _client = None
   
   def get_client():
       global _client
       if _client is None:
           _client = PlintoClient(...)
       return _client
   ```

3. **Error Recovery**: Implement proper error handling
   ```python
   def safe_api_call(func, *args, **kwargs):
       max_retries = 3
       for attempt in range(max_retries):
           try:
               return func(*args, **kwargs)
           except NetworkError:
               if attempt == max_retries - 1:
                   raise
               time.sleep(2 ** attempt)
   ```

## Next Steps

- [Full Python API Reference](/docs/api/python)
- [Django Integration Guide](/docs/guides/django)
- [Flask Integration Guide](/docs/guides/flask)
- [FastAPI Integration Guide](/docs/guides/fastapi)

## Support

- 📖 [Documentation](https://docs.plinto.dev)
- 🐍 [Python Examples](https://github.com/plinto/python-examples)
- 💬 [Community Forum](https://community.plinto.dev)
- 📧 [Support](mailto:support@plinto.dev)