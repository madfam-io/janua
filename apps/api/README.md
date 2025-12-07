# Janua API

> **Enterprise-grade authentication and identity platform** powering secure digital experiences

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-316192.svg?style=flat&logo=postgresql)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-6+-DC382D.svg?style=flat&logo=redis)](https://redis.io)

**Status:** Production Ready · **Architecture:** Async Python · **Coverage:** 50%+ · **Endpoints:** 202

---

## 🎯 Overview

Janua API is a modern, enterprise-grade authentication and identity management platform designed for scale, security, and developer experience. Built with FastAPI and async Python, it provides comprehensive authentication services including JWT tokens, WebAuthn/Passkeys, multi-factor authentication, and enterprise SSO.

### Key Features

- **🔐 Modern Authentication**: JWT with RS256, WebAuthn/Passkeys, MFA
- **🏢 Enterprise Ready**: SSO (SAML/OIDC), SCIM 2.0 provisioning, multi-tenancy, RBAC
- **⚡ High Performance**: Async Python (SQLAlchemy 2.x), Redis caching, connection pooling
- **🛡️ Security First**: OWASP compliance, audit logging, rate limiting, threat detection
- **📊 Production Monitoring**: Health checks, metrics, alerting, APM integration
- **🔧 Developer Experience**: OpenAPI docs, comprehensive testing, 8 SDK packages
- **🌐 Internationalization**: Full i18n support with localization models and APIs
- **🔄 Real-time**: WebSocket support for live updates and notifications

### Architecture Highlights

- **74,569 lines** of production Python code across 222 files
- **202 REST endpoints** with full async/await support
- **100% SQLAlchemy 2.x async** migration complete
- **Multi-language SDKs**: TypeScript, React, Python, Vue, Next.js, Go, Flutter
- **Enterprise features**: SAML, SCIM, RBAC, audit logging, compliance frameworks

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (async/await support)
- **PostgreSQL 14+** (for data persistence)
- **Redis 6+** (for caching and sessions)
- **Docker** (optional, for containerized deployment)

### Development Setup

```bash
# Clone and navigate
git clone <repository-url>
cd apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt  # For development

# Environment configuration
cp .env.example .env
# Edit .env with your settings
```

### Environment Configuration

Create `.env` file with development settings:

```env
# Application
ENVIRONMENT=development
DEBUG=True
BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/janua

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-development-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=RS256

# Features
ENABLE_SIGNUPS=True
ENABLE_MFA=True
ENABLE_ORGANIZATIONS=True
```

### Running the Server

```bash
# Development with auto-reload
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With environment variables
DATABASE_URL=postgresql://... uvicorn app.main:app --reload
```

### Quick Health Check

```bash
# Basic health
curl http://localhost:8000/health

# Infrastructure readiness
curl http://localhost:8000/ready

# API status
curl http://localhost:8000/api/status
```

---

## 📁 Project Structure

```
apps/api/
├── app/                          # Application source code
│   ├── main.py                   # FastAPI application entry point
│   ├── config.py                 # Settings and configuration
│   ├── exceptions.py             # Custom exception classes
│   │
│   ├── routers/v1/              # API endpoint definitions
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── users.py             # User management
│   │   ├── organizations.py     # Multi-tenant organizations
│   │   ├── sessions.py          # Session management
│   │   ├── mfa.py               # Multi-factor authentication
│   │   ├── passkeys.py          # WebAuthn/Passkeys
│   │   ├── sso.py               # Enterprise SSO
│   │   ├── scim.py              # SCIM user provisioning
│   │   ├── compliance.py        # Audit and compliance
│   │   ├── webhooks.py          # Event webhooks
│   │   └── admin.py             # Administrative endpoints
│   │
│   ├── services/                # Business logic layer
│   │   ├── auth_service.py      # Authentication business logic
│   │   ├── jwt_service.py       # JWT token management
│   │   ├── user_service.py      # User management
│   │   ├── organization_service.py # Organization management
│   │   ├── email_service.py     # Email communications
│   │   ├── webhook_service.py   # Webhook management
│   │   └── monitoring.py        # Application monitoring
│   │
│   ├── models/                  # Data models
│   │   ├── user.py              # User data model
│   │   ├── organization.py      # Organization model
│   │   ├── session.py           # Session model
│   │   ├── token.py             # Token model
│   │   ├── webhook.py           # Webhook model
│   │   └── audit.py             # Audit log model
│   │
│   ├── core/                    # Core infrastructure
│   │   ├── database_manager.py  # Database connection management
│   │   ├── redis_manager.py     # Redis connection management
│   │   ├── error_handling.py    # Error handling and middleware
│   │   ├── security.py          # Security utilities
│   │   ├── validation.py        # Data validation
│   │   └── performance.py       # Performance monitoring
│   │
│   └── middleware/              # Custom middleware
│       ├── rate_limit.py        # Rate limiting
│       ├── tenant_context.py    # Multi-tenancy
│       ├── audit_logging.py     # Audit trail
│       └── security_headers.py  # Security headers
│
├── tests/                       # Test suite (58 files)
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   └── fixtures/                # Test fixtures
│
├── docs/                        # Documentation
│   ├── api/                     # API documentation
│   ├── architecture/            # Architecture guides
│   ├── security/                # Security documentation
│   ├── deployment/              # Deployment guides
│   └── development/             # Development guides
│
├── alembic/                     # Database migrations
├── scripts/                     # Utility scripts
├── requirements.txt             # Production dependencies
├── requirements-test.txt        # Testing dependencies
├── docker-compose.yml           # Local development
├── Dockerfile                   # Container configuration
└── pytest.ini                  # Test configuration
```

---

## 🔗 API Documentation

### Core Endpoints

| Category | Endpoint | Description |
|----------|----------|-------------|
| **Health** | `GET /health` | Application health status |
| | `GET /ready` | Infrastructure readiness check |
| **Authentication** | `POST /api/v1/auth/signup` | User registration |
| | `POST /api/v1/auth/signin` | User authentication |
| | `POST /api/v1/auth/refresh` | Token refresh |
| | `GET /api/v1/auth/me` | Current user profile |
| **WebAuthn** | `POST /api/v1/passkeys/register` | Register passkey |
| | `POST /api/v1/passkeys/authenticate` | Authenticate with passkey |
| **Organizations** | `GET /api/v1/organizations` | List organizations |
| | `POST /api/v1/organizations` | Create organization |
| **Enterprise** | `POST /api/v1/sso/saml` | SAML SSO authentication |
| | `GET /api/v1/scim/Users` | SCIM user provisioning |

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs` (development)
- **ReDoc**: `http://localhost:8000/redoc` (development)
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

For comprehensive API documentation, see [API Reference](docs/api/README.md).

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test categories
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests
pytest tests/e2e/                     # End-to-end tests

# Run with verbose output
pytest -v --tb=short

# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Test Coverage

- **Current Coverage**: 78% (target: 90%+)
- **Test Files**: 58 files
- **Test Categories**: Unit, Integration, E2E
- **Mock Support**: External services, database, Redis

### Testing Strategy

- **Unit Tests**: Models, services, utilities
- **Integration Tests**: API endpoints, database operations
- **E2E Tests**: Complete user workflows
- **Performance Tests**: Load testing, benchmark validation

---

## 🏗️ Architecture

### System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Load Balancer │    │   API Gateway   │
│   Applications  │◄──►│   (Railway)     │◄──►│   (Optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 ▼                                 │
┌─────────────────┐    │    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    │
│   Redis Cache   │◄───┼───►│   FastAPI       │    │   Middleware     │    │   Background    │    │
│   Sessions      │    │    │   Application   │◄──►│   Security       │    │   Tasks         │    │
│   Rate Limiting │    │    │   (Async)       │    │   Multi-tenancy  │    │   Webhooks      │    │
└─────────────────┘    │    └─────────────────┘    └──────────────────┘    └─────────────────┘    │
                       │              │                                                           │
                       │              ▼                                                           │
                       │    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
                       │    │   PostgreSQL    │    │   Monitoring    │    │   External      │    │
                       │    │   Database      │    │   Metrics       │    │   Services      │    │
                       │    │   Multi-tenant  │    │   Health Checks │    │   Email, SSO    │    │
                       │    └─────────────────┘    └─────────────────┘    └─────────────────┘    │
                       │                              Janua API Infrastructure                  │
                       └─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Framework**: FastAPI 0.104.1 (async Python web framework)
- **Database**: PostgreSQL 14+ with SQLAlchemy 2.0 (async ORM)
- **Cache**: Redis 6+ (sessions, rate limiting, caching)
- **Authentication**: JWT (RS256), WebAuthn, MFA
- **Validation**: Pydantic 2.11 (data validation and serialization)
- **Testing**: Pytest with async support
- **Deployment**: Docker, Railway, traditional VPS

### Key Design Principles

- **Async-First**: High concurrency with async/await
- **Security by Design**: OWASP compliance, defense in depth
- **Scalable Architecture**: Horizontal scaling, stateless design
- **Developer Experience**: Type safety, comprehensive documentation
- **Production Ready**: Monitoring, logging, error handling

For detailed architecture documentation, see [Architecture Overview](docs/architecture/README.md).

---

## 🔒 Security

### Security Features

- **🔐 Authentication**: JWT with RS256, WebAuthn/Passkeys
- **🛡️ Authorization**: Role-based access control (RBAC)
- **🔒 Password Security**: Bcrypt with configurable rounds
- **⚡ Rate Limiting**: Per-endpoint and global rate limits
- **🔍 Audit Logging**: Comprehensive activity tracking
- **🌐 CORS**: Configurable cross-origin policies
- **📊 Security Headers**: HSTS, CSP, X-Frame-Options

### Compliance

- **OWASP Top 10**: Full compliance implementation
- **SOC 2 Type II**: Control framework alignment
- **GDPR**: Data protection and privacy compliance
- **SCIM 2.0**: Enterprise user provisioning

### Security Configuration

```python
# Password policies
PASSWORD_MIN_LENGTH = 12
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_NUMBERS = True
PASSWORD_REQUIRE_SPECIAL = True

# Rate limiting
RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_PER_HOUR = 1000

# JWT configuration
JWT_ALGORITHM = "RS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
```

For complete security documentation, see [Security Guide](docs/security/README.md).

---

## 🚀 Deployment

### Enclii/Hetzner (Production)

Janua uses self-hosted infrastructure via MADFAM's Enclii DevOps solution on Hetzner bare metal.

```bash
# Deploy via Enclii
enclii deploy --service janua-api

# Or manually via Docker
ssh root@95.217.198.239 'cd /opt/solarpunk/janua && docker-compose -f deployment/production/docker-compose.production.yml up -d janua-api'
```

### Docker (Local/Staging)

```bash
# Build image
docker build -t janua-api .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  janua-api
```

### Environment Variables

**Required for Production:**

```env
ENVIRONMENT=production
BASE_URL=https://api.yourdomain.com
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
SECRET_KEY=<secure-random-key>
JWT_SECRET_KEY=<secure-jwt-key>
```

**Optional Features:**

```env
# Email
EMAIL_ENABLED=true
SENDGRID_API_KEY=<your-sendgrid-key>

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
MONITORING_ENDPOINT=<your-monitoring-url>

# Enterprise Features
ENABLE_SSO=true
ENABLE_SCIM=true
```

For detailed deployment guides, see [Deployment Documentation](docs/deployment/README.md).

---

## 📊 Monitoring

### Health Checks

- **`/health`**: Application health status
- **`/ready`**: Infrastructure connectivity
- **`/metrics`**: Prometheus metrics
- **`/metrics/performance`**: Performance metrics

### Observability

- **Structured Logging**: JSON format with correlation IDs
- **Metrics Collection**: Request rates, response times, error rates
- **Health Monitoring**: Database, Redis, external service connectivity
- **Alerting**: Configurable thresholds and notifications

### Performance Metrics

- **Response Time**: P50, P95, P99 percentiles
- **Throughput**: Requests per second
- **Error Rates**: 4xx and 5xx response rates
- **Resource Usage**: CPU, memory, database connections

---

## 🛠️ Development

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
ruff check app/ tests/
mypy app/

# Security scan
bandit -r app/

# Run all quality checks
make lint
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add user table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Migration history
alembic history
```

### Development Workflow

1. **Setup**: Clone repository, install dependencies
2. **Feature Branch**: Create feature branch from main
3. **Development**: Implement feature with tests
4. **Quality**: Run linting, testing, security checks
5. **Review**: Create pull request for code review
6. **Deploy**: Merge to main triggers deployment

---

## 📚 Documentation

### Available Documentation

- **[API Reference](docs/api/README.md)**: Complete endpoint documentation
- **[Architecture Guide](docs/architecture/README.md)**: System design and patterns
- **[Security Guide](docs/security/README.md)**: Security implementation details
- **[Deployment Guide](docs/deployment/README.md)**: Production deployment
- **[Development Guide](docs/development/README.md)**: Developer onboarding
- **[Contributing Guide](docs/CONTRIBUTING.md)**: Contribution guidelines

### Quick Links

- [Getting Started Guide](docs/development/getting-started.md)
- [Authentication Flows](docs/api/authentication.md)
- [Enterprise Features](docs/api/enterprise.md)
- [Troubleshooting](docs/development/troubleshooting.md)
- [FAQ](docs/FAQ.md)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details on:

- Development setup and workflow
- Code style and quality standards
- Testing requirements
- Pull request process
- Community guidelines

### Quick Start for Contributors

```bash
# Fork and clone
git clone https://github.com/yourusername/janua.git
cd janua/apps/api

# Install development dependencies
pip install -r requirements-test.txt
pre-commit install

# Run tests
pytest

# Submit changes
git checkout -b feature/your-feature
# Make changes, commit, push
# Open pull request
```

---

## 📄 License

This project is licensed under the AGPL-3.0 License - see the [LICENSE](../../LICENSE) file for details.

---

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/madfam-io/janua/issues)
- **Discussions**: [GitHub Discussions](https://github.com/madfam-io/janua/discussions)
- **Email**: [support@janua.dev](mailto:support@janua.dev)

---

<div align="center">

**[🏠 Home](../../README.md)** • **[📖 Docs](docs/)** • **[🔗 API](docs/api/)** • **[🚀 Deploy](docs/deployment/)**

</div>