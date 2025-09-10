# Plinto Project Context

**Generated:** 2025-09-09  
**Project:** Plinto - Secure substrate for identity  
**Status:** Private alpha  
**Repository:** Clean (main branch)

## 🎯 Project Overview

Plinto is a comprehensive identity platform providing secure authentication, session management, and organization control with edge-fast verification. The platform ships from a single domain (plinto.dev) during alpha.

### Core Features
- **Identity & Auth**: Passkeys (WebAuthn), email/password, social logins (planned)
- **Sessions & Tokens**: Refresh rotation, replay detection, per-tenant signing keys
- **Organizations**: Teams, RBAC, policy evaluation (OPA-compatible)
- **Edge Verification**: P95 target < 50ms with CDN-cached JWKS
- **Security**: Turnstile protection, rate limiting, audit logs, webhooks

## 🏗️ Architecture

### Tech Stack
- **Frontend**: Next.js 14, React 18, TypeScript, TailwindCSS
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Alembic
- **Infrastructure**: Vercel (frontend), Railway (backend), Cloudflare (CDN/WAF)
- **Build System**: Turbo, Yarn workspaces
- **Testing**: Jest (22% coverage), Playwright (E2E)

### Project Structure
```
plinto/
├── apps/               # Application workspaces
│   ├── admin/         # Admin panel (port 3004)
│   ├── api/           # FastAPI backend (port 8000)
│   ├── dashboard/     # User dashboard (port 3001)
│   ├── demo/          # Demo application (port 3002)
│   ├── docs/          # Documentation site (port 3003)
│   ├── edge-verify/   # Edge verification service
│   └── marketing/     # Marketing site (port 3003)
├── packages/          # Shared packages
│   ├── config/        # Shared configuration
│   ├── core/          # Core business logic
│   ├── database/      # Database utilities
│   ├── mock-api/      # Mock API for testing
│   ├── monitoring/    # Monitoring utilities
│   ├── react/         # React components/hooks
│   ├── sdk/           # Core SDK
│   ├── sdk-js/        # JavaScript SDK
│   └── ui/            # UI component library
├── docs/              # Documentation
├── tests/             # Global test suites
├── deployment/        # Deployment configs
└── scripts/           # Build and utility scripts
```

## 📊 Key Metrics

### Code Quality
- **Test Coverage**: 22% overall (target: 80%)
- **Type Safety**: Full TypeScript/Python typing
- **Linting**: ESLint + Prettier (frontend), Black + Ruff (backend)
- **CI/CD**: GitHub Actions with automated testing

### Performance Targets
- **Edge Verification**: < 50ms P95
- **API Response**: < 200ms P95
- **Frontend Load**: < 2s (FCP)
- **Database Queries**: < 100ms P95

## 🚀 Development Workflow

### Quick Commands
```bash
# Development
yarn dev              # Start all services
yarn dev:frontend     # Frontend only
yarn dev:backend      # Backend only (Docker)
yarn dev:api         # API hot reload

# Testing
yarn test            # Run all tests with coverage
yarn test:unit       # Unit tests only
yarn test:e2e        # E2E tests (Playwright)

# Quality
yarn lint            # Lint all workspaces
yarn typecheck       # TypeScript validation
yarn build           # Production build

# Database
yarn db:migrate      # Run migrations
yarn db:reset        # Reset database
```

### Environment Setup
- **Node.js**: >= 18.0.0
- **Python**: 3.11+
- **Docker**: Required for backend development
- **PostgreSQL**: Via Docker or Railway

## 🔐 Security Considerations

### Authentication Flow
1. Browser → Cloudflare (WAF/Turnstile)
2. → Vercel (Next.js middleware)
3. → Railway (Plinto Core API)
4. Edge verification using cached JWKS

### Key Security Features
- **WebAuthn/Passkeys**: Passwordless authentication
- **JWT with rotation**: Secure token management
- **Rate limiting**: Per IP and tenant
- **Audit logging**: Append-only events
- **Webhook signatures**: Secure event delivery

## 📝 Recent Updates

### Completed
- ✅ Comprehensive test infrastructure (22% coverage)
- ✅ API deployment issue resolution
- ✅ Documentation structure established
- ✅ Monorepo optimization with Turbo

### In Progress
- 🔄 Increasing test coverage to 80%
- 🔄 Production deployment preparation
- 🔄 SSO/SAML implementation
- 🔄 Performance optimization

## 🎯 Current Focus Areas

1. **Test Coverage**: Expand from 22% to 80%
2. **Production Readiness**: Complete deployment checklists
3. **Documentation**: Fill missing README files
4. **Performance**: Achieve edge verification targets
5. **Security**: Complete security audit items

## 🔗 Key Resources

- **Main Domain**: https://plinto.dev
- **API**: https://api.plinto.dev
- **Dashboard**: https://app.plinto.dev
- **Admin**: https://admin.plinto.dev
- **Docs**: https://docs.plinto.dev
- **GitHub**: https://github.com/aureolabs/plinto

## 📚 Documentation Map

- [Project Index](./docs/PROJECT_INDEX.md) - Complete documentation structure
- [System Architecture](./docs/architecture/system-overview.md)
- [API Reference](./docs/api/overview.md)
- [Testing Strategy](./docs/technical/testing-strategy.md)
- [Deployment Guides](./docs/deployment/)

## 🏃 Next Steps

1. Review existing test coverage reports in `/coverage`
2. Check deployment configurations in `/deployment`
3. Explore API implementation in `/apps/api`
4. Review frontend applications in `/apps/*`
5. Examine shared packages in `/packages/*`

---

*Context loaded successfully. Ready for development tasks.*