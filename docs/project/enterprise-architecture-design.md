# Janua Enterprise Architecture Design

## Overview

Enterprise-grade architecture design with proper separation of concerns, distinct service ports, and microservice-style organization for the Janua identity platform.

## Frontend Applications

### 1. Marketing Site (Port 3000)
- **Location**: `/apps/marketing`
- **URL**: `https://janua.dev`
- **Purpose**: Public website, documentation, pricing, onboarding
- **Tech Stack**: Next.js 14 (Static/SSG), Tailwind CSS, @janua/ui
- **Features**:
  - Landing pages and product information
  - Documentation browser with MDX support
  - Pricing calculator and plan comparison
  - Contact forms and lead capture
  - Blog/content management
  - SEO optimized with static generation

### 2. Application Dashboard (Port 3001)
- **Location**: `/apps/dashboard`
- **URL**: `https://app.janua.dev`
- **Purpose**: Main user application for authenticated users
- **Tech Stack**: Next.js 14 (App Router), @janua/react-sdk, @janua/ui, TanStack Query
- **Features**:
  - User authentication dashboard
  - Organization management and RBAC
  - Identity and session management
  - Passkey/WebAuthn configuration
  - Webhook management and monitoring
  - Audit logs and compliance reporting
  - Team collaboration tools

### 3. Demo Environment (Port 3002)
- **Location**: `/apps/demo`
- **URL**: `https://demo.janua.dev`
- **Purpose**: Interactive product demonstration with mock data
- **Tech Stack**: Next.js 14 (App Router), @janua/react-sdk, @janua/ui, Mock API integration
- **Features**:
  - Sandbox authentication flows
  - Pre-populated demo data and scenarios
  - Interactive feature walkthroughs
  - Performance simulation controls
  - Sales enablement tools
  - No real user data or billing

### 4. Documentation Portal (Port 3003)
- **Location**: `/apps/docs`
- **URL**: `https://docs.janua.dev`
- **Purpose**: Developer documentation and API references
- **Tech Stack**: Next.js 14 (Static), MDX, Algolia Search, @janua/ui
- **Features**:
  - API documentation with OpenAPI integration
  - SDK guides and code examples
  - Integration tutorials and quickstarts
  - Reference documentation
  - Interactive API explorer
  - Community contributions and feedback

### 5. Admin Portal (Port 3004)
- **Location**: `/apps/admin`
- **URL**: `https://admin.janua.dev`
- **Purpose**: Superuser administration and system management
- **Tech Stack**: Next.js 14 (App Router), @janua/react-sdk, @janua/ui, Advanced RBAC
- **Features**:
  - System-wide tenant management
  - Platform monitoring and health dashboards
  - User support and troubleshooting tools
  - Feature flag management
  - System configuration and settings
  - Advanced analytics and reporting
  - Compliance and audit management

### 5. Enhanced Demo Application (Port 3002)
- **Location**: `/apps/demo`
- **URL**: `https://demo.janua.dev`
- **Purpose**: Comprehensive demo with authentication flows and interactive features
- **Tech Stack**: Next.js 14 (App Router), @janua/sdk, @janua/ui, Environment-aware
- **Features**:
  - Interactive product demonstration with mock data
  - Complete authentication flows (sign-in, sign-up, dashboard)
  - Performance simulation controls
  - Environment switching (demo/staging/production)
  - Sales enablement tools
  - Pre-populated demo scenarios
  - WebAuthn/Passkey demonstration
  - MFA setup examples

## Backend Services

### 1. Core API Service (Port 8000)
- **Location**: `/apps/api`
- **URL**: `https://api.janua.dev` (internal: `localhost:8000`)
- **Purpose**: Main authentication and identity API
- **Tech Stack**: FastAPI (Python), PostgreSQL, Redis, custom Janua auth core
- **Features**:
  - Authentication flows (sign-in, sign-up, sign-out)
  - Token issuance and validation
  - User identity management
  - Organization and RBAC endpoints
  - Session management
  - Password reset and email verification
  - WebAuthn/Passkey registration and verification
  - OIDC and OAuth2 provider endpoints

### 2. Auth Service (Port 8001)
- **Location**: `/apps/auth-service`
- **URL**: Internal service (`localhost:8001`)
- **Purpose**: Specialized authentication microservice
- **Tech Stack**: FastAPI (Python), Redis, JWT handling
- **Features**:
  - Token introspection and validation
  - Session state management
  - Rate limiting and abuse protection
  - MFA orchestration
  - Account security monitoring
  - Audit event generation

### 3. Edge Verification Workers
- **Location**: `/apps/edge-verify`
- **URL**: Deployed to Cloudflare Workers at edge locations
- **Purpose**: High-performance token verification at edge
- **Tech Stack**: TypeScript, Cloudflare Workers, KV storage
- **Features**:
  - JWT signature verification with cached JWKS
  - Sub-50ms token validation
  - Rate limiting with Durable Objects
  - Geographic routing and compliance
  - Real-time blacklist checking

### 4. Mock API Service (Port 8002)
- **Location**: `/packages/mock-api`
- **URL**: Development only (`localhost:8002`)
- **Purpose**: Development and demo API simulation
- **Tech Stack**: Express.js (TypeScript), In-memory database
- **Features**:
  - All Core API endpoints with mock responses
  - Realistic data generation and scenarios
  - Configurable latency simulation
  - Demo-specific features and workflows
  - No persistent data storage

### 5. Webhook Service (Port 8003)
- **Location**: `/apps/webhook-service`
- **URL**: Internal service (`localhost:8003`)
- **Purpose**: Event delivery and webhook management
- **Tech Stack**: FastAPI (Python), PostgreSQL, Redis Queue
- **Features**:
  - Event subscription management
  - Reliable webhook delivery with retry logic
  - HMAC signature generation and validation
  - Event filtering and transformation
  - Delivery monitoring and analytics

## Shared Packages

### 1. UI Component Library (`@janua/ui`)
- **Location**: `/packages/ui`
- **Purpose**: Shared design system and React components
- **Features**: Buttons, forms, modals, tables, navigation, theming

### 2. React SDK (`@janua/react-sdk`)
- **Location**: `/packages/react`
- **Purpose**: React hooks and components for Janua integration
- **Features**: Authentication hooks, session management, protected routes

### 3. Core SDK (`@janua/sdk`)
- **Location**: `/packages/sdk`
- **Purpose**: Framework-agnostic JavaScript/TypeScript client
- **Features**: API client, token management, authentication flows

### 4. Edge SDK (`@janua/edge`)
- **Location**: `/packages/edge`
- **Purpose**: Edge runtime token verification utilities
- **Features**: JWT validation, middleware helpers, performance optimization

## Port Allocation Strategy

### Development Environment
```yaml
Frontend Applications:
  marketing: 3000
  dashboard: 3001  
  demo: 3002 (enhanced with auth flows)
  docs: 3003
  admin: 3004

Backend Services:
  core-api: 8000
  auth-service: 8001
  mock-api: 8002
  webhook-service: 8003

Infrastructure:
  postgres: 5432
  redis: 6379
  mailhog: 1025, 8025
```

### Production Environment
```yaml
Frontend Applications:
  marketing: janua.dev (Vercel)
  dashboard: app.janua.dev (Vercel)
  demo: demo.janua.dev (Vercel)
  docs: docs.janua.dev (Vercel)
  admin: admin.janua.dev (Vercel)

Backend Services:
  core-api: api.janua.dev (Railway)
  auth-service: auth.janua.dev (Railway)
  edge-verify: Cloudflare Workers (Global Edge)
  webhook-service: webhooks.janua.dev (Railway)
```

## Development Workflow

### 1. Environment Setup
```bash
# Install dependencies
yarn install

# Start all services in development
yarn dev:all

# Start specific service
yarn workspace @janua/marketing dev
yarn workspace @janua/api dev
```

### 2. Service Communication
- **Frontend → Backend**: Direct HTTP calls to service ports
- **Backend → Backend**: Internal service communication via localhost
- **Frontend → Edge**: Direct calls to deployed edge workers

### 3. Shared Configuration
- Environment variables managed per service with shared base config
- Feature flags controlled through environment configuration
- Service discovery through well-defined port allocation

## Deployment Architecture

### 1. Vercel (Frontend Applications)
```yaml
marketing:
  domain: janua.dev
  build: apps/marketing
  
dashboard:
  domain: app.janua.dev
  build: apps/dashboard
  
demo:
  domain: demo.janua.dev
  build: apps/demo
  
docs:
  domain: docs.janua.dev
  build: apps/docs
  
admin:
  domain: admin.janua.dev
  build: apps/admin
```

### 2. Railway (Backend Services)
```yaml
core-api:
  domain: api.janua.dev
  dockerfile: apps/api/Dockerfile
  
auth-service:
  domain: auth.janua.dev
  dockerfile: apps/auth-service/Dockerfile
  
webhook-service:
  domain: webhooks.janua.dev
  dockerfile: apps/webhook-service/Dockerfile
```

### 3. Cloudflare (Edge Services)
```yaml
edge-verify:
  workers: apps/edge-verify
  domains: 
    - janua.dev/api/v1/verify/*
    - "*.janua.dev/api/v1/verify/*"
```

## Security Architecture

### 1. Authentication Flow
1. **User Authentication**: Frontend → Core API (port 8000)
2. **Token Validation**: Frontend → Edge Workers (Cloudflare)
3. **Session Management**: Auth Service (port 8001) ← → Core API
4. **Audit Logging**: All services → Webhook Service (port 8003)

### 2. Network Security
- **HTTPS Everywhere**: All external communication encrypted
- **Internal Services**: Localhost communication between backend services
- **Rate Limiting**: Per-service rate limiting with shared Redis
- **CORS Configuration**: Strict origin controls per environment

### 3. Data Protection
- **Tenant Isolation**: Per-tenant encryption keys and data separation
- **Audit Trail**: Immutable event logging with hash chains
- **Compliance**: GDPR/CCPA data handling with retention policies

## Monitoring and Observability

### 1. Application Monitoring
- **Frontend**: Vercel Analytics + Sentry error tracking
- **Backend**: Prometheus metrics + Grafana dashboards
- **Edge**: Cloudflare Analytics + custom metrics

### 2. Health Checks
- **Service Health**: `/health` endpoints on all backend services
- **Database Health**: Connection pool monitoring
- **Cache Health**: Redis connectivity and performance metrics

### 3. Performance Monitoring
- **Response Times**: p95 < 50ms for edge verification
- **Uptime**: 99.95% SLO across all services
- **Error Rates**: < 0.1% error rate target

## Migration Strategy

### Phase 1: Foundation (Week 1-2)
1. ✅ Create new app structure with proper port allocation
2. ✅ Set up shared packages and build system
3. ⏳ Implement basic service communication

### Phase 2: Service Separation (Week 3-4)
1. Extract auth-service from core API
2. Create dedicated admin portal
3. Set up webhook service infrastructure

### Phase 3: Production Deployment (Week 5-6)
1. Configure Vercel deployments with custom domains
2. Set up Railway services with proper networking
3. Deploy Cloudflare Workers for edge verification

### Phase 4: Optimization (Week 7-8)
1. Performance tuning and monitoring setup
2. Security hardening and penetration testing
3. Load testing and scalability validation

## Next Steps

1. **Complete Backend Services Design**: Finish auth-service and webhook-service specifications
2. **Create Deployment Configuration**: Set up Vercel, Railway, and Cloudflare configurations
3. **Implement Architectural Changes**: Restructure existing code to match new architecture
4. **Set Up Monitoring**: Implement health checks and observability across all services
5. **Security Review**: Conduct comprehensive security assessment of new architecture