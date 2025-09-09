# Plinto Project Structure

## Overview
Plinto is a secure identity platform with edge-fast verification, currently in private alpha. The project is structured as a multi-app system with shared design components.

## Project Layout

```
plinto/
├── marketing/          # Marketing site (plinto.dev)
├── dashboard/          # User dashboard (app.plinto.dev)
├── admin/             # Admin portal (admin.plinto.dev)
├── api/               # FastAPI backend (api.plinto.dev)
├── edge-verify/       # Edge verification workers
├── docs/              # Documentation
└── packages/          # Shared packages
    └── ui/            # Unified design system
```

## Applications

### Marketing Site (`marketing/`)
- **URL**: https://plinto.dev
- **Stack**: Next.js 14, Tailwind CSS
- **Port**: 3000
- **Purpose**: Public-facing marketing site, documentation, pricing

### Dashboard (`dashboard/`)
- **URL**: https://app.plinto.dev
- **Stack**: Next.js 14, Tailwind CSS, @plinto/ui
- **Port**: 3001
- **Purpose**: User dashboard for identity management
- **Features**:
  - Identity management
  - Session tracking
  - Organization management
  - API keys & webhooks
  - Audit logs

### Admin Portal (`admin/`)
- **URL**: https://admin.plinto.dev
- **Stack**: Next.js 14, Tailwind CSS, @plinto/ui
- **Port**: 3002
- **Purpose**: Internal superadmin portal
- **Features**:
  - Tenant management
  - Infrastructure monitoring
  - Billing & subscriptions
  - Security monitoring
  - System health

### API Backend (`api/`)
- **URL**: https://api.plinto.dev
- **Stack**: FastAPI, PostgreSQL, Redis
- **Port**: 8000
- **Purpose**: Core authentication and identity API
- **Endpoints**:
  - `/api/v1/auth/*` - Authentication flows
  - `/api/v1/sessions/*` - Session management
  - `/api/v1/orgs/*` - Organization management
  - `/.well-known/jwks.json` - JWKS endpoint
  - `/.well-known/openid-configuration` - OIDC metadata

## Shared Components

### UI Design System (`packages/ui/`)
Unified design system shared across all frontend applications:
- **Theme**: Brand colors (primary blue #3b82f6)
- **Components**: Button, Card, Input, Badge, Dialog, Toast, Tabs
- **Utilities**: Consistent spacing, typography, shadows

## Development Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (or use Docker)
- Redis (or use Docker)

### Quick Start

1. **Setup local domains**:
```bash
sudo ./dev-setup.sh
```

2. **Start all services**:
```bash
# Start API with Docker
cd api && docker-compose up -d && cd ..

# Start frontend apps
cd marketing && yarn dev &
cd dashboard && yarn dev &
cd admin && yarn dev &
```

3. **Access applications**:
- Marketing: http://localhost:3000
- Dashboard: http://localhost:3001
- Admin: http://localhost:3002
- API: http://localhost:8000

### Subdomain Routing (Local)
For local subdomain routing, use the provided `nginx.conf`:
```bash
nginx -c $(pwd)/nginx.conf
```

Then access via:
- http://plinto.local
- http://app.plinto.local
- http://admin.plinto.local
- http://api.plinto.local

## Deployment

### Frontend Apps (Vercel)
All frontend apps deploy to Vercel with automatic subdomain routing:
- `plinto.dev` → Marketing
- `app.plinto.dev` → Dashboard
- `admin.plinto.dev` → Admin

### API Backend (Railway)
The FastAPI backend deploys to Railway with:
- PostgreSQL database
- Redis for sessions/caching
- Auto-scaling configuration

### CI/CD
GitHub Actions workflow (`deploy.yml`) handles:
- Automated testing
- Build verification
- Production deployment
- Environment variable management

## Security

- **Authentication**: JWT-based with short-lived access tokens
- **Primary Auth**: WebAuthn/Passkeys preferred
- **Rate Limiting**: Redis-based per-endpoint limits
- **CORS**: Strict origin validation
- **Headers**: Security headers on all responses
- **Audit**: Comprehensive audit logging

## Current Status

✅ **Completed**:
- Unified design system created
- Admin portal built with full functionality
- API backend structure with FastAPI
- Subdomain routing configured
- Deployment configurations ready

⏳ **Pending**:
- Align marketing site with design system
- Update dashboard to use shared UI components
- Complete API implementation
- Production deployment

## Next Steps

1. Complete UI alignment across all frontends
2. Implement core API functionality
3. Add WebAuthn/Passkeys support
4. Deploy to production environment
5. Enable RBAC and tenant isolation