# Week 6 Day 1 - Production API Integration

**Date**: November 16, 2025
**Status**: Infrastructure Complete | Component Updates In Progress
**Objective**: Connect Next.js demo app to production FastAPI backend

---

## 🎯 Implementation Goal

Integrate the Next.js demo application with the production Python FastAPI backend, enabling real end-to-end authentication workflows with database persistence, session management, and email integration.

**Architecture**: Demo App (Next.js) → TypeScript SDK → FastAPI Backend → PostgreSQL + Redis

---

## ✅ Completed Infrastructure

### 1. Backend Services Setup

**PostgreSQL Database** (Docker Container)
- Image: `postgres:15-alpine`
- Port: `5432`
- Database: `plinto_db`
- User: `plinto` / Password: `plinto_dev`
- Status: ✅ Healthy and accepting connections
- Health check: `pg_isready -U plinto` → accepting connections

**Redis Cache** (Docker Container)
- Image: `redis:7-alpine`
- Port: `6379`
- Status: ✅ Healthy and responding to PING
- Health check: `redis-cli ping` → PONG

**FastAPI Backend Server**
- Framework: FastAPI 0.104.1
- Python: 3.11.13
- Port: `8000`
- Status: ✅ Running with hot reload
- Health endpoint: `http://localhost:8000/health` → `{"status":"healthy","version":"0.1.0","environment":"development"}`

**Database Configuration** (`apps/api/.env`)
```env
# Environment
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://plinto:plinto_dev@localhost:5432/plinto_db
DATABASE_POOL_SIZE=20
AUTO_MIGRATE=false

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=development-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS (comma-separated string)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002

# Email (disabled for development)
EMAIL_ENABLED=false
EMAIL_PROVIDER=sendgrid
```

**Backend Initialization Log**:
```
✅ JWT_SECRET_KEY validation passed
✅ Database connection verified
✅ Database manager initialized (environment=development)
✅ Redis cache initialized
✅ Redis initialized successfully
✅ Resource monitoring started (interval: 30s)
✅ Enterprise scalability features initialized successfully
✅ Webhook delivery worker started
🚀 Plinto API started successfully
INFO: Application startup complete.
```

### 2. Frontend Configuration

**Environment Variables** (`apps/demo/.env.local`)
```env
# Plinto API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_PATH=/api/v1

# Frontend Configuration
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_APP_NAME=Plinto Demo

# Feature Flags
NEXT_PUBLIC_ENABLE_AUTH=true
NEXT_PUBLIC_ENABLE_SOCIAL_AUTH=true
NEXT_PUBLIC_ENABLE_MFA=true
NEXT_PUBLIC_ENABLE_PASSKEYS=true

# Development Settings
NODE_ENV=development
```

### 3. Plinto SDK Integration

**SDK Client Configuration** (`apps/demo/lib/plinto-client.ts`)
- Centralized PlintoClient instance
- Token storage: localStorage with key `plinto_auth_token`
- Auto-refresh: enabled (5 minutes before expiration)
- Debug logging: enabled in development
- CORS credentials: include cookies

```typescript
export const plintoClient = new PlintoClient({
  apiUrl: 'http://localhost:8000',
  apiBasePath: '/api/v1',
  debug: true,
  tokenStorage: {
    type: 'localStorage',
    key: 'plinto_auth_token',
  },
  session: {
    autoRefresh: true,
    refreshThreshold: 300,
  },
  credentials: 'include',
})
```

**React Context Provider** (`apps/demo/components/providers/plinto-provider.tsx`)
- Authentication state management via React Context
- User object persistence across app
- Auto-refresh user data on token refresh
- Event listeners for sign-in, sign-out, and token refresh
- Custom hooks: `usePlinto()`, `useAuth()`

**Provider Integration** (`apps/demo/components/providers.tsx`)
- Simplified to wrap PlintoProvider
- Replaces old mock implementation
- Integrated into root layout via existing Providers component

**Root Layout Integration** (`apps/demo/app/layout.tsx`)
- PlintoProvider wraps entire Next.js app via existing Providers
- Available globally throughout application
- Auth state accessible via hooks

---

## 📊 Current Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Next.js Demo App                      │
│                  (localhost:3000)                       │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │         PlintoProvider (React Context)        │    │
│  │  - Auth state management                      │    │
│  │  - User object persistence                     │    │
│  │  - Auto token refresh                          │    │
│  │  - Event listeners (signIn, signOut, refresh)  │    │
│  └───────────────────────────────────────────────┘    │
│                        │                                │
│  ┌───────────────────────────────────────────────┐    │
│  │      Plinto SDK Client (TypeScript)           │    │
│  │  - HTTP client with token management          │    │
│  │  - Auth module (signUp, signIn, signOut)      │    │
│  │  - Users, Sessions, Organizations modules      │    │
│  └───────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                           │
                           │ HTTP/JSON
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                       │
│                  (localhost:8000)                       │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │         Auth Router (/api/v1/auth/*)          │    │
│  │  - POST /signup                                │    │
│  │  - POST /signin                                │    │
│  │  - POST /refresh                               │    │
│  │  - POST /password/forgot                       │    │
│  │  - POST /password/reset                        │    │
│  │  - POST /email/verify                          │    │
│  │  - POST /magic-link                            │    │
│  │  - MFA, OAuth, Passkey endpoints               │    │
│  └───────────────────────────────────────────────┘    │
│                        │                                │
│  ┌─────────────────┐  │  ┌──────────────────────┐     │
│  │   PostgreSQL    │◄─┼─►│       Redis          │     │
│  │  (port 5432)    │  │  │    (port 6379)       │     │
│  │  - User data    │  │  │  - Sessions          │     │
│  │  - Sessions     │  │  │  - Rate limiting     │     │
│  │  - Organizations│  │  │  - Cache             │     │
│  └─────────────────┘  │  └──────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Next Steps (In Progress)

### 4. Update Auth Components to Use Real API

**Components to Update**:
1. `SignIn` → Use `plintoClient.auth.signIn()`
2. `SignUp` → Use `plintoClient.auth.signUp()`
3. `PasswordReset` → Use `plintoClient.auth.resetPassword()`
4. `EmailVerification` → Use `plintoClient.auth.verifyEmail()`
5. `MFASetup` → Use `plintoClient.auth.setupMFA()`
6. `PhoneVerification` → Use `plintoClient.auth.verifyPhone()`
7. `PasskeySetup` → Use `plintoClient.auth.registerPasskey()`

**Pattern for Component Updates**:
```typescript
// Before (mock implementation)
const handleSubmit = async (data) => {
  const response = await fetch('/api/auth/signin', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  // ... mock logic
}

// After (real API via SDK)
import { usePlinto } from '@/components/providers/plinto-provider'

const { client } = usePlinto()

const handleSubmit = async (data) => {
  try {
    const response = await client.auth.signIn({
      email: data.email,
      password: data.password,
      remember: data.rememberMe,
    })
    // Handle success - user is now authenticated
    // SDK automatically stores tokens and updates auth state
  } catch (error) {
    // Handle error - display to user
  }
}
```

### 5. Test Authentication Flows

**Test Scenarios**:
- ✅ Backend health check (completed)
- ⏳ Sign-up flow with email verification
- ⏳ Sign-in flow with remember me
- ⏳ Password reset flow
- ⏳ MFA setup and verification
- ⏳ Social OAuth providers
- ⏳ Passkey registration and authentication

### 6. Update E2E Tests

**E2E Test Updates Required**:
- Remove mock/simulation functions
- Use real API endpoints and database
- Add database cleanup between tests
- Update test fixtures for real backend responses
- Verify token persistence and refresh

### 7. Documentation

**Documentation to Create**:
- ✅ API integration architecture (this document)
- ⏳ SDK usage guide for components
- ⏳ Testing strategy for real backend
- ⏳ Deployment guide for production

---

## 📈 Progress Metrics

### Infrastructure Setup
```
✅ PostgreSQL: Healthy and running
✅ Redis: Healthy and running
✅ FastAPI Backend: Running on port 8000
✅ Environment Configuration: Complete
✅ SDK Integration: Complete
✅ React Context Provider: Complete
```

### Component Updates
```
⏳ Auth Components: 0/14 updated
⏳ API Integration: 0/14 components
⏳ E2E Tests: 0/49 tests updated
```

### Testing
```
⏳ Sign-up Flow: Not tested
⏳ Sign-in Flow: Not tested
⏳ Password Reset: Not tested
⏳ MFA Flow: Not tested
⏳ OAuth Flow: Not tested
⏳ Passkey Flow: Not tested
```

---

## 🛠️ Technical Details

### Backend API Endpoints

**Authentication Endpoints** (`/api/v1/auth/*`):
```
POST /api/v1/auth/signup
POST /api/v1/auth/signin
POST /api/v1/auth/refresh
POST /api/v1/auth/signout
POST /api/v1/auth/password/forgot
POST /api/v1/auth/password/reset
POST /api/v1/auth/email/verify
POST /api/v1/auth/magic-link
POST /api/v1/auth/mfa/setup
POST /api/v1/auth/mfa/verify
POST /api/v1/auth/oauth/{provider}
POST /api/v1/auth/passkey/register
POST /api/v1/auth/passkey/authenticate
```

### TypeScript SDK API

**Auth Module Methods**:
```typescript
// User authentication
auth.signUp(request: SignUpRequest): Promise<AuthResponse>
auth.signIn(request: SignInRequest): Promise<AuthResponse>
auth.signOut(): Promise<void>
auth.refreshToken(request?: RefreshTokenRequest): Promise<TokenResponse>
auth.getCurrentUser(): Promise<User | null>

// Password management
auth.forgotPassword(request: ForgotPasswordRequest): Promise<{ message: string }>
auth.resetPassword(token: string, newPassword: string): Promise<{ message: string }>

// Email verification
auth.verifyEmail(token: string): Promise<{ message: string }>

// MFA
auth.setupMFA(type: 'totp' | 'sms'): Promise<MFASetupResponse>
auth.verifyMFA(code: string): Promise<{ success: boolean }>

// OAuth
auth.initiateOAuth(provider: string): Promise<{ url: string }>

// Passkeys
auth.registerPasskey(request: PasskeyRegisterRequest): Promise<PasskeyResponse>
auth.authenticatePasskey(request: PasskeyAuthRequest): Promise<AuthResponse>
```

### React Hooks

**Available Hooks**:
```typescript
// Full Plinto client access
const { client, user, isAuthenticated, isLoading, refreshUser } = usePlinto()

// Auth-specific hook
const { user, isAuthenticated, isLoading, refreshUser } = useAuth()
```

---

## 🔍 Files Modified

### Backend Configuration
- `apps/api/.env` - Database and Redis configuration
- `apps/api/docker-compose.yml` - Already existed (no changes)

### Frontend Configuration
- `apps/demo/.env.local` - API URL and feature flags
- `apps/demo/lib/plinto-client.ts` - **NEW** - SDK client configuration
- `apps/demo/components/providers/plinto-provider.tsx` - **NEW** - React Context provider
- `apps/demo/components/providers.tsx` - Updated to use PlintoProvider

### Infrastructure
- Docker containers: PostgreSQL and Redis running
- FastAPI server: Running with hot reload

---

## 🎯 Success Criteria

### Phase 1: Infrastructure ✅ COMPLETE
- [x] PostgreSQL running and healthy
- [x] Redis running and healthy
- [x] FastAPI backend running and responding
- [x] Environment variables configured
- [x] SDK integrated into Next.js app
- [x] React Context provider created

### Phase 2: Component Integration ⏳ IN PROGRESS
- [ ] Update SignIn component
- [ ] Update SignUp component
- [ ] Update PasswordReset component
- [ ] Update EmailVerification component
- [ ] Update MFA components
- [ ] Update OAuth components
- [ ] Update Passkey components

### Phase 3: Testing ⏳ PENDING
- [ ] Sign-up flow tested
- [ ] Sign-in flow tested
- [ ] Password reset flow tested
- [ ] MFA flow tested
- [ ] OAuth flow tested
- [ ] Passkey flow tested
- [ ] E2E tests updated

### Phase 4: Documentation ⏳ PENDING
- [x] API integration architecture documented
- [ ] SDK usage guide created
- [ ] Component update guide created
- [ ] Testing strategy documented
- [ ] Deployment guide created

---

## 💡 Key Learnings

### Environment Configuration
- Backend Settings class requires specific variable names (not arbitrary)
- EMAIL_PROVIDER must match pattern `^(sendgrid|ses|smtp)$`
- CORS_ORIGINS is a comma-separated string, not JSON array in .env
- Database URL needs `postgresql+asyncpg://` for async SQLAlchemy

### Docker Services
- Alembic migrations reference missing migration 002
- Can run backend without migrations initially
- PostgreSQL and Redis both have health checks configured
- Images pulled: `postgres:15-alpine`, `redis:7-alpine`

### SDK Integration
- PlintoClient supports multiple configuration options
- Token storage can be localStorage, sessionStorage, or memory
- Auto-refresh prevents token expiration issues
- Event emitters allow reactive auth state updates

### Next.js Integration
- Client components required for React Context providers
- Root layout integration via existing Providers component
- Environment variables prefixed with `NEXT_PUBLIC_` are client-accessible

---

## 🚀 Next Session Plan

1. **Update SignIn Component** (30 min)
   - Replace mock fetch with `plintoClient.auth.signIn()`
   - Handle success and error states
   - Test sign-in flow end-to-end

2. **Update SignUp Component** (30 min)
   - Replace mock implementation with `plintoClient.auth.signUp()`
   - Handle email verification redirect
   - Test sign-up flow end-to-end

3. **Update PasswordReset Component** (20 min)
   - Implement forgot password flow
   - Implement reset password flow
   - Test password reset end-to-end

4. **Test Complete Authentication Journey** (30 min)
   - Sign up → verify email → sign in → access protected route
   - Verify session persistence
   - Test token refresh

5. **Update E2E Tests** (40 min)
   - Remove mock functions
   - Add real API integration
   - Add database cleanup

6. **Document Complete Integration** (30 min)
   - Update README with API integration status
   - Create SDK usage guide
   - Document deployment requirements

---

**Total Session Time**: ~3 hours
**Status**: Infrastructure complete, component updates ready to begin
**Blockers**: None - all services running and healthy
