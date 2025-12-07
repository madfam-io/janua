# Development Documentation

> **Complete developer onboarding and workflow documentation for the Janua API**

This section provides comprehensive development documentation covering setup, workflows, testing, and contribution guidelines for developers working on the Janua authentication platform.

## 🎯 Developer Onboarding

### Welcome to Janua Development
Welcome to the Janua API development team! This guide will help you get up and running with the codebase, understand our development workflows, and start contributing effectively.

### Development Philosophy
- **Security First**: Every feature considers security implications
- **Test-Driven Development**: Comprehensive test coverage for reliability
- **Documentation as Code**: Keep documentation current with code changes
- **Code Quality**: Maintain high standards through automated tools
- **Collaboration**: Transparent communication and code review

## 🚀 Quick Start Guide

### Prerequisites

#### System Requirements
- **Python 3.11+** with pip and venv
- **PostgreSQL 14+** for database
- **Redis 6+** for caching and sessions
- **Git** for version control
- **Docker** (optional) for containerized development

#### Development Tools
- **IDE**: VS Code, PyCharm, or similar with Python support
- **Terminal**: Unix-like shell (bash, zsh, fish)
- **Database Client**: pgAdmin, DBeaver, or command-line tools
- **API Client**: Postman, Insomnia, or curl

### Environment Setup

#### 1. Clone Repository
```bash
# Clone the repository
git clone https://github.com/madfam-io/janua.git
cd janua/apps/api

# Create development branch
git checkout -b feature/your-feature-name
```

#### 2. Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Install pre-commit hooks
pre-commit install
```

#### 3. Database Setup
```bash
# Using Docker (recommended)
docker run --name janua-postgres \
  -e POSTGRES_DB=janua \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:14

# Or install PostgreSQL locally and create database
createdb janua
```

#### 4. Redis Setup
```bash
# Using Docker (recommended)
docker run --name janua-redis \
  -p 6379:6379 \
  -d redis:6-alpine

# Or install Redis locally
# On macOS: brew install redis && brew services start redis
# On Ubuntu: sudo apt install redis-server
```

#### 5. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

Example `.env` file:
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
SECRET_KEY=development-secret-key-change-this
JWT_SECRET_KEY=development-jwt-secret-key
JWT_ALGORITHM=HS256

# Features
ENABLE_SIGNUPS=True
ENABLE_MFA=True
ENABLE_ORGANIZATIONS=True
ENABLE_DOCS=True

# Email (optional for development)
EMAIL_ENABLED=False
```

#### 6. Database Migration
```bash
# Run initial migrations
alembic upgrade head

# Verify database setup
python -c "
import asyncio
from app.core.database_manager import init_database, get_database_health

async def test():
    await init_database()
    health = await get_database_health()
    print('Database health:', health)

asyncio.run(test())
"
```

#### 7. Start Development Server
```bash
# Start the API server
uvicorn app.main:app --reload --port 8000

# Test the server
curl http://localhost:8000/health
```

### Verification
If everything is set up correctly, you should see:
- API server running on http://localhost:8000
- API documentation at http://localhost:8000/docs
- Health check returning `{"status": "healthy"}`

## 🏗️ Development Workflow

### Branch Strategy

```
main
├── develop
│   ├── feature/user-management
│   ├── feature/sso-integration
│   └── feature/audit-logging
├── release/v1.2.0
└── hotfix/critical-security-fix
```

#### Branch Types
- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/**: New features and enhancements
- **release/**: Release preparation
- **hotfix/**: Critical production fixes

### Development Process

#### 1. Feature Development
```bash
# Start from develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, commit regularly
git add .
git commit -m "feat: add user profile management

- Add user profile update endpoint
- Implement profile validation
- Add comprehensive tests
- Update API documentation"

# Push branch
git push origin feature/your-feature-name
```

#### 2. Code Quality Checks
```bash
# Run all quality checks before committing
make check

# Or run individually:
black app/ tests/           # Code formatting
isort app/ tests/           # Import sorting
ruff check app/ tests/      # Linting
mypy app/                   # Type checking
bandit -r app/              # Security scan
pytest                      # Run tests
```

#### 3. Pull Request Process
1. **Create PR**: Against develop branch
2. **Description**: Clear description with context
3. **Review**: Wait for team review and approval
4. **CI**: Ensure all checks pass
5. **Merge**: Squash and merge after approval

### Code Quality Standards

#### Code Formatting
```bash
# Format code with Black
black app/ tests/

# Sort imports with isort
isort app/ tests/

# Configuration in pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
```

#### Linting Rules
```bash
# Lint with Ruff
ruff check app/ tests/

# Configuration in pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py311"
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
```

#### Type Checking
```bash
# Type check with mypy
mypy app/

# Configuration in pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

## 🧪 Testing Guidelines

### Test Structure
```
tests/
├── unit/                    # Unit tests
│   ├── test_config.py      # Configuration tests
│   ├── test_models.py      # Model tests
│   ├── test_services.py    # Service tests
│   └── test_utils.py       # Utility tests
├── integration/            # Integration tests
│   ├── test_auth_flow.py   # Authentication flow tests
│   ├── test_api_endpoints.py # API endpoint tests
│   └── test_database.py    # Database integration tests
├── e2e/                    # End-to-end tests
│   ├── test_user_journey.py # Complete user journeys
│   └── test_admin_flow.py  # Admin workflow tests
└── fixtures/               # Test fixtures and factories
    ├── user_factory.py     # User test data
    └── organization_factory.py # Organization test data
```

### Writing Tests

#### Unit Test Example
```python
# tests/unit/test_auth_service.py
import pytest
from unittest.mock import AsyncMock, Mock

from app.services.auth_service import AuthService
from app.models.user import User
from tests.fixtures.user_factory import create_user


class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        return AuthService(
            user_repository=AsyncMock(),
            password_service=Mock(),
            session_service=AsyncMock()
        )

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service):
        # Arrange
        user = create_user(email="test@example.com")
        auth_service.user_repository.get_by_email.return_value = user
        auth_service.password_service.verify.return_value = True

        # Act
        result = await auth_service.authenticate_user("test@example.com", "password")

        # Assert
        assert result == user
        auth_service.user_repository.get_by_email.assert_called_once_with("test@example.com")
        auth_service.password_service.verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, auth_service):
        # Arrange
        user = create_user(email="test@example.com")
        auth_service.user_repository.get_by_email.return_value = user
        auth_service.password_service.verify.return_value = False

        # Act
        result = await auth_service.authenticate_user("test@example.com", "wrong_password")

        # Assert
        assert result is None
```

#### Integration Test Example
```python
# tests/integration/test_auth_endpoints.py
import pytest
from httpx import AsyncClient

from app.main import app


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_signup_success(self, client: AsyncClient):
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "name": "New User"
        }

        # Act
        response = await client.post("/api/v1/auth/signup", json=user_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == user_data["email"]
        assert "access_token" in data["data"]

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self, client: AsyncClient, existing_user):
        # Arrange
        user_data = {
            "email": existing_user.email,
            "password": "SecurePassword123!",
            "name": "Duplicate User"
        }

        # Act
        response = await client.post("/api/v1/auth/signup", json=user_data)

        # Assert
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert "already exists" in data["error"]["message"]
```

### Test Configuration

#### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
asyncio_mode = auto
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
```

#### Test Fixtures
```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.main import app
from app.core.database_manager import get_database_session
from app.models.user import User


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session


@pytest.fixture
async def client():
    """Create a test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_user(db_session, client):
    """Create an authenticated user and return auth headers."""
    user_data = {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "name": "Test User"
    }

    # Create user
    response = await client.post("/api/v1/auth/signup", json=user_data)
    assert response.status_code == 201

    data = response.json()
    token = data["data"]["access_token"]

    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user": data["data"]["user"]
    }
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests only
pytest tests/e2e/                     # E2E tests only

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth_service.py

# Run specific test method
pytest tests/unit/test_auth_service.py::TestAuthService::test_authenticate_user_success

# Run tests matching pattern
pytest -k "test_auth"

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## 🗃️ Database Development

### Database Migrations

#### Creating Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "Add user preferences table"

# Create an empty migration for data changes
alembic revision -m "Migrate user settings data"

# Review the generated migration
cat alembic/versions/<revision_id>_add_user_preferences_table.py
```

#### Migration Best Practices
```python
# Good migration example
def upgrade() -> None:
    # Create table with all constraints
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('ix_user_preferences_user_id', 'user_id')
    )

def downgrade() -> None:
    # Always provide a downgrade path
    op.drop_table('user_preferences')
```

#### Running Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Show migration history
alembic history

# Show current revision
alembic current
```

### Database Models

#### Model Example
```python
# app/models/user_preference.py
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    preferences = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreference(user_id={self.user_id}, category={self.category})>"
```

## 🔧 Development Tools

### Makefile
```makefile
# Makefile for common development tasks

.PHONY: help install test lint format check clean dev

help:			## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:		## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-test.txt
	pre-commit install

test:			## Run tests with coverage
	pytest --cov=app --cov-report=term-missing --cov-report=html

test-fast:		## Run tests without coverage
	pytest

lint:			## Run linting tools
	ruff check app/ tests/
	mypy app/
	bandit -r app/

format:			## Format code
	black app/ tests/
	isort app/ tests/

check:			## Run all quality checks
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test

clean:			## Clean up temporary files
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/

dev:			## Start development server
	uvicorn app.main:app --reload --port 8000

migration:		## Create new migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate:		## Apply migrations
	alembic upgrade head

shell:			## Start Python shell with app context
	python -c "from app.main import app; import asyncio; print('Janua API shell ready')"

docs:			## Generate API documentation
	python scripts/generate_openapi.py

docker-build:		## Build Docker image
	docker build -t janua-api .

docker-run:		## Run Docker container
	docker run -p 8000:8000 janua-api
```

### VS Code Configuration

#### .vscode/settings.json
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": false,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".coverage": true,
        "htmlcov": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.testing.unittestEnabled": false
}
```

#### .vscode/launch.json
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug FastAPI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/uvicorn",
            "args": ["app.main:app", "--reload", "--port", "8000"],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env"
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env"
        }
    ]
}
```

## 📚 Additional Resources

### Documentation
- **[API Documentation](../api/README.md)** - Complete API reference
- **[Architecture Guide](../architecture/README.md)** - System architecture
- **[Security Documentation](../security/README.md)** - Security implementation
- **[Deployment Guide](../deployment/README.md)** - Production deployment

### Development Guides
- **[Getting Started](getting-started.md)** - Detailed setup guide
- **[Testing Guide](testing.md)** - Comprehensive testing documentation
- **[Debugging Guide](debugging.md)** - Debugging tips and techniques
- **[Performance Guide](performance.md)** - Performance optimization
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

### Tools and Resources
- **[Code Style Guide](code-style.md)** - Coding standards and conventions
- **[Git Workflow](git-workflow.md)** - Detailed Git workflow
- **[IDE Setup](ide-setup.md)** - IDE configuration guides
- **[Docker Development](docker-development.md)** - Docker for development

## 🤝 Getting Help

### Team Communication
- **Slack**: #janua-dev channel
- **GitHub Discussions**: [Project Discussions](https://github.com/madfam-io/janua/discussions)
- **Team Meetings**: Daily standups at 9 AM EST

### Getting Unstuck
1. **Check Documentation**: Start with relevant docs section
2. **Search Issues**: Check GitHub issues for similar problems
3. **Ask Team**: Post in Slack channel with context
4. **Create Issue**: Document complex problems for team

### Mentorship Program
New developers are paired with experienced team members for:
- Code review guidance
- Architecture discussions
- Career development
- Best practices sharing

---

<div align="center">

**[⬅️ Documentation Home](../README.md)** • **[🚀 Getting Started](getting-started.md)** • **[🧪 Testing](testing.md)** • **[🐛 Debugging](debugging.md)**

</div>