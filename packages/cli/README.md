# Janua CLI

> **Local Development Environment Management** for Janua and MADFAM ecosystem

**Version:** 0.1.0 | **Language:** Go 1.21+ | **Status:** Development

## Overview

The Janua CLI (`enclii local`) provides orchestration for local MADFAM development environments. It manages shared infrastructure (PostgreSQL, Redis, MinIO) and coordinates all ecosystem services to mirror production topology.

**Note:** The CLI is distributed as part of the Enclii platform tools but directly manages Janua services.

## Installation

```bash
# Install via Go
go install github.com/madfam/enclii/packages/cli@latest

# Verify installation
enclii --version
```

## Commands

### `enclii local up`

Start the complete local development environment.

```bash
# Start everything (infrastructure + all services)
enclii local up

# Start only infrastructure (PostgreSQL, Redis, MinIO, MailHog)
enclii local up infra

# Start specific services
enclii local up janua              # Janua only
enclii local up janua enclii       # Multiple services

# Skip infrastructure (if already running)
enclii local up --skip-infra
```

**What gets started:**

| Phase | Service | Port |
|-------|---------|------|
| Infrastructure | PostgreSQL | 5432 |
| Infrastructure | Redis | 6379 |
| Infrastructure | MinIO | 9000/9001 |
| Infrastructure | MailHog | 8025 |
| Janua | API | 4100 |
| Janua | Dashboard | 4101 |
| Janua | Admin | 4102 |
| Janua | Docs | 4103 |
| Janua | Website | 4104 |

### `enclii local down`

Stop all services and infrastructure.

```bash
# Stop everything
enclii local down

# Stop services but keep infrastructure running
enclii local down --keep-infra
```

### `enclii local status`

Check the health of all local services.

```bash
enclii local status
```

**Output:**
```
Infrastructure:
  ✓ PostgreSQL: running
  ✓ Redis: running
  ✓ MinIO: running
  ✓ MailHog: running

Janua Services:
  ✓ Janua API: 200
  ✓ Dashboard: 200
  ✓ Admin: 200
  ✓ Docs: 200
  ✓ Website: 200
```

### `enclii local logs`

View logs from infrastructure containers.

```bash
# View all logs
enclii local logs

# View specific service
enclii local logs postgres

# Follow logs in real-time
enclii local logs -f
enclii local logs -f redis
```

### `enclii local infra`

Start only the shared infrastructure.

```bash
enclii local infra
```

**Connection details provided:**
- PostgreSQL: `postgres://madfam:madfam_dev_password@localhost:5432`
- Redis: `redis://:redis_dev_password@localhost:6379`
- MinIO: `http://localhost:9000` (admin/minioadmin)
- MailHog: `http://localhost:8025`

## Port Allocation

Janua follows the [MADFAM Port Allocation Standard](https://github.com/madfam-org/solarpunk-foundry/blob/main/docs/PORT_ALLOCATION.md):

| Service | Port | Description |
|---------|------|-------------|
| **Janua Block (4100-4199)** | | |
| API | 4100 | FastAPI backend |
| Dashboard | 4101 | User management UI |
| Admin | 4102 | Platform admin UI |
| Docs | 4103 | Documentation site |
| Website | 4104 | Marketing/landing |
| Demo | 4105 | Demo application |
| Email Worker | 4110 | Background email |
| WebSocket | 4120 | Real-time events |
| Metrics | 4190 | Prometheus metrics |
| **Shared Infrastructure** | | |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache/sessions |
| MinIO | 9000/9001 | Object storage |
| MailHog | 8025 | Email testing |

## Prerequisites

- **Go 1.21+** for CLI installation
- **Docker & Docker Compose** for infrastructure
- **Python 3.11+** for Janua API
- **Node.js 18+ & pnpm** for frontend apps

## Configuration

### Environment Variables

The CLI uses sensible defaults but can be configured:

```bash
# Database credentials (defaults)
DATABASE_URL=postgresql://janua:janua_dev@localhost:5432/janua_dev
REDIS_URL=redis://:redis_dev_password@localhost:6379/0

# Admin bootstrap
ADMIN_BOOTSTRAP_PASSWORD='YourSecurePassword'
ADMIN_BOOTSTRAP_EMAIL='admin@janua.dev'
```

### Directory Structure

The CLI expects standard labspace structure:

```
~/labspace/
├── solarpunk-foundry/    # Shared infrastructure
│   └── ops/local/
│       └── docker-compose.shared.yml
├── janua/                # Janua repository
│   └── apps/
│       ├── api/          # Python API
│       ├── dashboard/    # Next.js dashboard
│       ├── admin/        # Next.js admin
│       └── ...
└── enclii/               # Enclii repository
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -ti:4100

# Kill process
kill -9 $(lsof -ti:4100)

# Or use down command
enclii local down
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker exec madfam-postgres-shared pg_isready -U madfam

# Check Redis is running
docker exec madfam-redis-shared redis-cli -a redis_dev_password ping
```

### Infrastructure Won't Start

```bash
# Check Docker daemon
docker info

# Check existing containers
docker ps -a | grep madfam

# Remove stale containers
docker rm -f madfam-postgres-shared madfam-redis-shared madfam-minio madfam-mailhog
```

### Migration Failures

```bash
# Run migrations manually
cd apps/api
source .venv/bin/activate
DATABASE_URL=postgresql://janua:janua_dev@localhost:5432/janua_dev alembic upgrade head
```

## Development Workflow

### First-Time Setup

```bash
# 1. Start infrastructure
enclii local infra

# 2. Setup Python environment
cd ~/labspace/janua/apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Start all services
enclii local up
```

### Daily Development

```bash
# Start your day
enclii local up

# Check status anytime
enclii local status

# View API logs
enclii local logs -f

# End your day
enclii local down --keep-infra  # Keep DB for next time
```

### Full Reset

```bash
# Stop everything
enclii local down

# Remove all Docker volumes (WARNING: deletes data)
docker volume rm madfam_postgres_data madfam_redis_data madfam_minio_data

# Fresh start
enclii local up
```

## Related Documentation

- [Quick Start Guide](/docs/guides/QUICK_START.md)
- [Local Demo Guide](/docs/guides/LOCAL_DEMO_GUIDE.md)
- [API Documentation](/apps/api/docs/api/)
- [Troubleshooting Guide](/docs/guides/TROUBLESHOOTING_GUIDE.md)
- [Port Allocation Standard](https://github.com/madfam-org/solarpunk-foundry/blob/main/docs/PORT_ALLOCATION.md)

## License

Part of the Janua platform. See [LICENSE](../../LICENSE) for details.
