# Plinto

> **The secure substrate for identity.** Unify auth, orgs, and policy with edge‑fast verification and full control — all on **plinto.dev**.

**Status:** Private **Alpha** · **Version:** 0.1.0 · **Domain:** `https://plinto.dev`

[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red)](./LICENSE)

**Stack:** Next.js + Vercel Edge + Railway (PostgreSQL) + Cloudflare (R2 + CDN + Turnstile)

---

## 📚 Quick Links

- **[Development Guide](./DEVELOPMENT.md)** - Complete guide for developers
- **[Documentation Hub](./docs/)** - All project documentation
- **[API Reference](./docs/reference/API_SPECIFICATION.md)** - Complete API documentation
- **[Architecture](./docs/architecture/ARCHITECTURE.md)** - System design and decisions
- **[Deployment Guide](./docs/deployment/DEPLOYMENT.md)** - Production deployment instructions

## Contents

* [What is Plinto?](#what-is-plinto)
* [Key Features](#key-features)
* [Quick Start](#quick-start)
* [Project Structure](#project-structure)
* [Development](#development)
* [Testing](#testing)
* [Deployment](#deployment)
* [Security](#security)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)



## What is Plinto?

**Plinto** is an identity platform — a **secure substrate** that provides:

* **Core**: identity, sessions, orgs/tenants, roles, policies, audits, webhooks.
* **Edge**: ultra‑fast verification via Vercel Middleware & Cloudflare Workers with global JWKS caching.
* **Admin**: a dashboard for managing users, orgs, keys, webhooks, and compliance tasks.
* **SDKs**: developer‑first libraries for Next.js/React/Node (alpha), with Vue/Go/Python to follow.

Everything ships from **one domain: `plinto.dev`** during this stage.

---

## Key Features

* **Passkeys (WebAuthn)** and **email/password** out of the box; social logins (G, GH, MS) in parity track.
* **Sessions & tokens** with refresh rotation, replay detection, and per‑tenant signing keys.
* **Orgs/teams/RBAC** + policy evaluation (OPA‑compatible) for route and resource decisions.
* **Edge verification** — p95 target < 50ms with CDN‑cached JWKS.
* **Audits & webhooks** — append‑only audit events; signed webhook deliveries with retries & DLQ.
* **Abuse‑resistant** flows — Turnstile on risky actions, rate limits per IP & tenant.
* **Enterprise track** — SSO (SAML/OIDC), SCIM, region pinning, advanced audit (rolling out).

---

## How it works (at a glance)

```
Browser/App → Cloudflare (WAF/CDN/Turnstile) → Vercel (Next.js) → Railway (Plinto Core API)
                                 ↘ Edge verification (Vercel/Cloudflare) using JWKS from plinto.dev/.well-known
```

* Your app integrates **Plinto SDKs** and uses **edge middleware** to verify sessions.
* Tokens are signed per tenant; verification is local/edge using **JWKS** cached at the CDN.
* Admin tasks live at `/admin`; API is served from `/api/v1/...` under the same domain.

---

## Quick Start

### Prerequisites

- Node.js 18+ and Yarn
- PostgreSQL (via Docker or local)
- Redis (for sessions and caching)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/plinto.git
cd plinto

# Install dependencies
yarn install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development services
yarn dev
```

Services will be available at:
- API: http://localhost:8000
- Admin Panel: http://localhost:3004
- Dashboard: http://localhost:3000
- Documentation: http://localhost:3005

### SDK Installation (for your apps)

#### Next.js App Router

```bash
npm i @plinto/nextjs @plinto/react
# or
pnpm add @plinto/nextjs @plinto/react
```

### 2) Configure environment

Create `.env.local`:

```bash
# Issuer/audience are fixed to plinto.dev in alpha
PLINTO_ISSUER=https://plinto.dev
PLINTO_AUDIENCE=plinto.dev
PLINTO_TENANT_ID=tenant_123            # from Admin → Settings
PLINTO_JWKS_URL=https://plinto.dev/.well-known/jwks.json
```

### 3) Add Edge Middleware

`middleware.ts`

```ts
import { withPlinto } from "@plinto/nextjs/middleware";

export const config = {
  matcher: [
    "/((?!sign-in|sign-up|api|_next|public|favicon.ico|robots.txt).*)",
  ],
};

export default withPlinto({
  audience: process.env.PLINTO_AUDIENCE!,
  issuer: process.env.PLINTO_ISSUER!,
  jwksUrl: process.env.PLINTO_JWKS_URL!,
});
```

### 4) Wrap your app with the provider

`app/layout.tsx`

```tsx
import { PlintoProvider } from "@plinto/nextjs";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <PlintoProvider>{children}</PlintoProvider>
      </body>
    </html>
  );
}
```

### 5) Drop in prebuilt auth UI

`app/sign-in/page.tsx`

```tsx
import { SignIn } from "@plinto/react";
export default function Page() {
  return <SignIn />;
}
```

### 6) Protect a route (server action / route handler)

`app/api/me/route.ts`

```ts
import { getSession } from "@plinto/nextjs/server";

export async function GET() {
  const session = await getSession();
  if (!session) return new Response("Unauthorized", { status: 401 });
  return Response.json({ userId: session.userId, tenantId: session.tenantId });
}
```

---

## Project Structure

```
plinto/
├── apps/                    # Applications
│   ├── api/                # Core API (NestJS) - Port 8000
│   ├── admin/              # Admin Panel (Next.js) - Port 3004
│   ├── dashboard/          # User Dashboard (Next.js) - Port 3000
│   ├── docs/               # Documentation (Docusaurus) - Port 3005
│   ├── marketing/          # Marketing Site (Next.js) - Port 3001
│   └── edge-verify/        # Edge Verification Service
│
├── packages/               # Shared Packages
│   ├── core/              # Core Business Logic
│   ├── database/          # Database Schemas & Migrations
│   ├── ui/                # Shared UI Components (shadcn/ui)
│   ├── typescript-sdk/    # TypeScript/JavaScript SDK
│   ├── react/             # React Components & Hooks
│   ├── python-sdk/        # Python SDK
│   ├── go-sdk/            # Go SDK
│   ├── flutter-sdk/       # Flutter SDK
│   └── react-native-sdk/  # React Native SDK
│
├── docs/                   # Documentation
│   ├── architecture/      # Architecture Decisions
│   ├── deployment/        # Deployment Guides
│   ├── development/       # Development Guides
│   └── enterprise/        # Enterprise Features
│
├── infrastructure/         # Infrastructure as Code
└── DEVELOPMENT.md         # Developer Guide
```

## Development

See [DEVELOPMENT.md](./DEVELOPMENT.md) for the complete development guide.

### Quick Commands

```bash
# Install dependencies
yarn install

# Start all services
yarn dev

# Run tests
yarn test

# Build for production
yarn build

# Type checking
yarn typecheck

# Linting
yarn lint

# Format code
yarn format
```

## Edge Verification Examples

### Vercel Edge Middleware

```ts
import { withPlinto } from "@plinto/nextjs/middleware";
export const config = { matcher: ["/dashboard/:path*"] };
export default withPlinto();
```

### Cloudflare Worker (minimal)

```ts
import { verify } from "@plinto/edge";

export default {
  async fetch(req: Request): Promise<Response> {
    const claims = await verify(req, {
      jwksUrl: "https://plinto.dev/.well-known/jwks.json",
      audience: "plinto.dev",
      issuer: "https://plinto.dev",
    });
    if (!claims) return new Response("Unauthorized", { status: 401 });
    return Response.json({ sub: claims.sub, tid: claims.tid });
  },
};
```

---

## Core API (selected endpoints)

**Base URL:** `https://plinto.dev/api/v1`

### Sign up (email + password)

```bash
curl -X POST https://plinto.dev/api/v1/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "dev@example.com",
    "password": "CorrectHorseBatteryStaple",
    "tenantId": "tenant_123"
  }'
```

### Sign in (password)

```bash
curl -X POST https://plinto.dev/api/v1/auth/signin \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@example.com","password":"••••••••"}'
```

### Start passkey registration

```bash
curl -X POST https://plinto.dev/api/v1/auth/passkeys/register \
  -H 'Authorization: Bearer <sessionToken>'
```

### Verify session (introspection)

```bash
curl "https://plinto.dev/api/v1/sessions/verify" \
  -H "Authorization: Bearer <accessToken>"
```

> Full OpenAPI will be published under `/docs` during alpha.

---

## Testing

```bash
# Run all tests
yarn test

# Run tests with coverage
yarn test:coverage

# Run E2E tests
yarn test:e2e

# Run specific workspace tests
yarn workspace @plinto/api test
yarn workspace @plinto/admin test
```

## Deployment

### Production Deployment

The platform is deployed across multiple providers for optimal performance:

- **Frontend Apps**: Vercel (Next.js apps with edge functions)
- **API**: Railway (NestJS API with PostgreSQL)
- **Storage**: Cloudflare R2 (object storage)
- **CDN**: Cloudflare (global edge caching)
- **Security**: Cloudflare Turnstile (bot protection)

See [Deployment Guide](./docs/deployment/DEPLOYMENT.md) for detailed instructions.

### Environment Variables

**App-side env vars**

* `PLINTO_ISSUER` = `https://plinto.dev`
* `PLINTO_AUDIENCE` = `plinto.dev`
* `PLINTO_TENANT_ID` = your tenant identifier
* `PLINTO_JWKS_URL` = `https://plinto.dev/.well-known/jwks.json`

**Cookie guidance**

* HttpOnly, `SameSite=None; Secure`, domain: `plinto.dev`.

**Caching & keys**

* JWKS is **CDN‑cached**; we rotate keys on a schedule (90d) and on demand. Libraries respect `kid` to fetch fresh keys.

---

## Security

### Security Features

- **Authentication Methods**:
  - Passkeys (WebAuthn) - Primary, most secure
  - Email + Password - With strong password requirements
  - MFA Support - TOTP, SMS, hardware keys
  - Social Login - Google, GitHub, Microsoft (coming soon)

- **Token Security**:
  - JWT with refresh token rotation
  - Replay attack detection
  - Per-tenant signing keys
  - Automatic session invalidation on password change

- **Edge Security**:
  - Global JWKS caching for fast verification
  - Rate limiting per IP and tenant
  - Cloudflare Turnstile for bot protection
  - WAF rules for common attacks

- **Admin Security**:
  - IP allowlisting for admin panel
  - Required MFA for all admin accounts
  - Comprehensive audit logging
  - Session recording for compliance

### Reporting Security Issues

Report vulnerabilities to **[security@plinto.dev](mailto:security@plinto.dev)**

Please **DO NOT** open public issues for security findings. We offer a bug bounty program for responsible disclosure.

---

## Roadmap

### ✅ Completed (Alpha)
- Single-domain deployment on **plinto.dev**
- Passkeys (WebAuthn) + email/password authentication
- Edge verification libraries (Vercel/Cloudflare)
- Admin panel with comprehensive controls
- Multi-tenant architecture with isolation
- Audit logging and compliance features
- Rate limiting and abuse protection
- shadcn/ui component library integration

### 🚧 In Progress
- Social logins (Google, GitHub, Microsoft)
- Webhooks console with retry logic
- Enhanced org/team management UI
- SDK improvements and documentation

### 📋 Planned (Beta)
- SSO (SAML 2.0, OIDC) for enterprise
- SCIM provisioning support
- Advanced audit explorer with export
- Custom roles and permissions builder
- Region pinning and data residency
- White-label customization options
- Compliance certifications (SOC 2, ISO 27001)

### 🔮 Future (GA)
- Multi-region deployment
- Advanced analytics dashboard
- AI-powered security insights
- Passwordless-first experience
- Biometric authentication expansion

Track detailed progress in [Enterprise Features Roadmap](./docs/enterprise/ENTERPRISE_FEATURES_ROADMAP.md)

---

## Contributing

Plinto is in **private alpha**. We welcome contributions from design partners and the MADFAM team.

### How to Contribute

1. **Read the Development Guide**: Start with [DEVELOPMENT.md](./DEVELOPMENT.md)
2. **Check Existing Issues**: Look for open issues or create a new one
3. **Fork and Branch**: Create a feature branch from `develop`
4. **Follow Standards**: Use conventional commits and our code style
5. **Test Thoroughly**: Ensure all tests pass
6. **Submit PR**: Include description and link to issue

### Quick Start for Contributors

```bash
# Clone and setup
git clone https://github.com/your-org/plinto.git
cd plinto
yarn install

# Create feature branch
git checkout -b feature/your-feature

# Make changes and test
yarn dev
yarn test
yarn lint

# Commit with conventional format
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature
```

See [DEVELOPMENT.md](./DEVELOPMENT.md) for complete contribution guidelines.

---

## License

© **Aureo Labs** (a **MADFAM** company). All rights reserved during alpha

Commercial and open‑core options will be announced at GA.
