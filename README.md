# Plinto - Enterprise Authentication Platform

**Modern, enterprise-grade authentication and user management platform**

[![PyPI version](https://img.shields.io/pypi/v/plinto?style=flat-square)](https://pypi.org/project/plinto/)
[![Python versions](https://img.shields.io/pypi/pyversions/plinto?style=flat-square)](https://pypi.org/project/plinto/)
[![License](https://img.shields.io/pypi/l/plinto?style=flat-square)](https://github.com/madfam-io/plinto/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/plinto?style=flat-square)](https://pypi.org/project/plinto/)

*Enterprise-grade authentication and user management platform for modern applications*

[🚀 **Get Started**](QUICK_START.md) • [📖 **Documentation**](https://docs.plinto.dev) • [🎮 **Try Demo**](#-local-demo) • [💬 **Discord**](https://discord.gg/plinto)

---

## 🎯 **NEW: Local Demo Available**

Experience the complete Plinto platform locally before publishing:

```bash
# Start all services (API + Landing Site + Redis)
./scripts/start-local-demo.sh

# Open in browser
# → Landing Site: http://localhost:3000
# → API Docs: http://localhost:8000/docs
# → Health Check: http://localhost:8000/health

# Run automated validation tests
./scripts/run-demo-tests.sh
```

**What's Included:**
- ✅ Complete authentication API (signup, login, MFA, passkeys)
- ✅ Professional landing site with documentation
- ✅ SSO integration (OIDC Discovery, SAML)
- ✅ Performance optimization (<100ms response times)
- ✅ Comprehensive test validation (all features)

**Quick Links:**
- 📖 **[Quick Start Guide](QUICK_START.md)** - 5-minute setup instructions
- 📋 **[Demo Walkthrough](DEMO_WALKTHROUGH.md)** - Complete 50+ checkpoint validation
- 🏗️ **[Performance Guide](docs/project/WEEK7-8_PERFORMANCE_OPTIMIZATION.md)** - Optimization details

---

## ✨ Quick Start

### Installation

```bash
# Install Plinto
pip install plinto

# Install with all optional dependencies
pip install "plinto[all]"

# Install for development
pip install "plinto[dev]"
```

### Basic Usage

```python
from plinto import create_app, Settings
import uvicorn

# Create FastAPI app with Plinto authentication
app = create_app(
    title="My App",
    description="App powered by Plinto authentication"
)

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### CLI Commands

```bash
# Initialize Plinto configuration
plinto init --database-url postgresql://localhost/myapp

# Start the development server
plinto server --host 0.0.0.0 --port 8000 --reload

# Run database migrations
plinto migrate

# Create an admin user
plinto create-user --email admin@example.com --admin

# Check system health
plinto health

# Show version
plinto version
```

---

## 🏗️ Architecture

Plinto provides a comprehensive authentication platform with:

- **🔐 Multiple Authentication Methods**: JWT, OAuth, SAML, WebAuthn/Passkeys
- **🏢 Multi-tenancy**: Organization-based user management
- **🛡️ Security First**: Rate limiting, security headers, audit logging
- **⚡ High Performance**: Async/await with Redis caching
- **🧩 Modular Design**: Use only what you need

### Core Components

```python
from plinto import (
    # Main application factory
    create_app,
    
    # Configuration
    Settings, get_settings,
    
    # Core services
    AuthService, JWTService, CacheService,
    
    # Models
    User, Organization, Session, AuditLog,
    
    # Exceptions
    AuthenticationError, AuthorizationError, ValidationError
)
```

---

## 🚀 Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, HTTPException
from plinto import AuthService, User, get_settings
from plinto.middleware import apply_middleware_stack

# Create FastAPI app
app = FastAPI(title="My API")

# Apply Plinto middleware stack
apply_middleware_stack(app)

# Dependency for getting current user
async def get_current_user(
    auth_service: AuthService = Depends()
) -> User:
    # Your authentication logic here
    user = await auth_service.get_current_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"message": f"Hello {user.email}!"}
```

### Custom Authentication Service

```python
from plinto import AuthService, JWTService, User
from plinto.exceptions import AuthenticationError

class MyAuthService(AuthService):
    def __init__(self):
        self.jwt_service = JWTService()
    
    async def authenticate_user(self, email: str, password: str) -> User:
        """Custom authentication logic"""
        user = await self.get_user_by_email(email)
        if not user or not self.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")
        
        return user
    
    async def create_access_token(self, user: User) -> str:
        """Create JWT token for user"""
        return await self.jwt_service.create_access_token(
            subject=str(user.id),
            additional_claims={"email": user.email}
        )
```

### Configuration

```python
from plinto import Settings, get_settings
from pydantic import Field

class MySettings(Settings):
    # Extend base Plinto settings
    my_custom_setting: str = Field(default="default_value")
    
    class Config:
        env_prefix = "MY_APP_"

# Use custom settings
settings = MySettings()

# Or use default Plinto settings
settings = get_settings()
```

---

## 🛠️ Advanced Usage

### Custom Middleware Configuration

```python
from plinto.middleware import PlintoMiddlewareConfig, create_plinto_app

# Custom middleware configuration
middleware_config = PlintoMiddlewareConfig(
    enable_rate_limiting=True,
    enable_security_headers=True,
    enable_cors=True,
    custom_cors_origins=["https://myapp.com"],
    custom_allowed_hosts=["myapp.com"]
)

# Create app with custom middleware
app = create_plinto_app(
    title="My App",
    middleware_config=middleware_config
)
```

### Database Models

```python
from plinto.models import User, Organization, UserStatus, OrganizationRole

# Work with Plinto models
async def create_organization_user(email: str, org_id: int):
    user = User(
        email=email,
        status=UserStatus.ACTIVE,
        organization_id=org_id
    )
    
    # Save user to database
    await user.save()
    return user
```

### Caching Integration

```python
from plinto import CacheService

cache = CacheService()

# Cache user data
await cache.set(f"user:{user_id}", user_data, ttl=3600)

# Retrieve cached data
user_data = await cache.get(f"user:{user_id}")
```

---

## 📦 Optional Dependencies

Install additional features as needed:

```bash
# Email providers
pip install "plinto[email]"

# SSO protocols (SAML, OIDC)
pip install "plinto[sso]"

# Development tools
pip install "plinto[dev]"

# Everything
pip install "plinto[all]"
```

### Email Integration

```python
# With email dependencies installed
from plinto.integrations.email import SendGridProvider, PostmarkProvider

# Configure email provider
email_provider = SendGridProvider(api_key="your-sendgrid-key")
```

### SSO Integration

```python
# With SSO dependencies installed
from plinto.integrations.sso import SAMLProvider, OIDCProvider

# Configure SAML SSO
saml_provider = SAMLProvider(
    entity_id="your-entity-id",
    sso_url="https://your-idp.com/sso",
    x509_cert="your-certificate"
)
```

---

## 🧪 Development

### Running Tests

```bash
# Install development dependencies
pip install "plinto[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=plinto --cov-report=html

# Run specific test
pytest tests/test_auth_service.py::TestAuthService::test_authenticate_user
```

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/madfam-io/plinto.git
cd plinto/apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run development server
plinto server --reload
```

### Configuration Files

Create a `.env` file for local development:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/plinto_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Email (optional)
SENDGRID_API_KEY=your-sendgrid-key

# Environment
ENVIRONMENT=development
DEBUG=true
```

---

## 📊 Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["plinto", "server", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  plinto:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/plinto
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: plinto
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection URL |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `JWT_SECRET_KEY` | Yes | - | Secret key for JWT signing |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | No | `30` | JWT token expiration |
| `CORS_ORIGINS` | No | `[]` | Allowed CORS origins |
| `ENVIRONMENT` | No | `production` | Application environment |
| `DEBUG` | No | `false` | Enable debug mode |

---

## 🔒 Security

### Security Features

- **🛡️ Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **⚡ Rate Limiting**: Configurable rate limits per endpoint
- **🔐 Password Security**: Bcrypt hashing with configurable rounds
- **🚨 Audit Logging**: Comprehensive security event logging
- **🎯 JWT Security**: Secure token generation and validation
- **🛡️ CSRF Protection**: Built-in CSRF protection for forms

### Security Best Practices

```python
from plinto import Settings

class ProductionSettings(Settings):
    # Use environment variables for secrets
    JWT_SECRET_KEY: str  # Set via JWT_SECRET_KEY env var
    
    # Security headers
    SECURE_HEADERS: bool = True
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # CORS
    CORS_ORIGINS: list = ["https://yourdomain.com"]
    
    # Database
    DATABASE_URL: str  # Use connection pooling in production
```

### Reporting Security Issues

If you discover a security vulnerability, please send an email to **security@plinto.dev**. Do not create public GitHub issues for security vulnerabilities.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking
- **Pytest** for testing

```bash
# Format code
black .

# Lint code
ruff check .

# Type check
mypy .

# Run tests
pytest
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Database integration with [SQLAlchemy](https://sqlalchemy.org/)
- Async support with [asyncpg](https://github.com/MagicStack/asyncpg)
- Caching with [Redis](https://redis.io/)
- Password hashing with [Passlib](https://passlib.readthedocs.io/)

---

## 📞 Support

- 📖 **Documentation**: [docs.plinto.dev](https://docs.plinto.dev)
- 💬 **Community**: [Discord Server](https://discord.gg/plinto)
- 🐛 **Issues**: [GitHub Issues](https://github.com/madfam-io/plinto/issues)
- 📧 **Email**: [support@plinto.dev](mailto:support@plinto.dev)

---

*Built with ❤️ for developers who want authentication that just works.*