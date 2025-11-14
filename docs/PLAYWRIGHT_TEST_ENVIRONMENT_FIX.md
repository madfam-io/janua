# Playwright Test Environment Fix

**Date**: November 14, 2025
**Issue**: Playwright E2E tests failing with connection refused errors
**Status**: ✅ RESOLVED

---

## Problem Summary

Playwright E2E tests were failing with multiple issues:

### Issue 1: Invalid packageManager Configuration Error
```
error This project's package.json defines "packageManager": "yarn@npm@10.8.2".
However the current global version of Yarn is 1.22.22.
```

### Issue 2: Connection Refused Errors
```
Error: apiRequestContext.get: connect ECONNREFUSED ::1:8000
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000
```

All tests attempting to connect to localhost:8000 (API) and localhost:3000 (frontend) failed because these services were not running.

## Root Causes

### 1. Misconfigured Playwright webServer

The `playwright.config.ts` had a `webServer` configuration that tried to start only the marketing app:

```typescript
webServer: {
  command: 'cd apps/marketing && npm run dev',
  port: 3003,
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
},
```

**Problems**:
- Only started marketing app on port 3003
- Tests expected API on port 8000 and landing on port 3000
- Marketing app uses different package manager setup
- No database or Redis services started
- Incomplete test environment

### 2. Missing Service Orchestration

The project has `docker-compose.test.yml` that provides a complete test environment with:
- API server (port 8000)
- Landing page (port 3000)
- Test app (port 3001)
- Dashboard (port 3002)
- PostgreSQL database
- Redis cache

But the Playwright config wasn't using it.

### 3. Missing Wait Script

The package.json referenced `scripts/wait-for-services.sh` but the script didn't exist.

## Solution

### 1. Updated Playwright Configuration

**File**: `playwright.config.ts`

```typescript
// Before (WRONG)
webServer: {
  command: 'cd apps/marketing && npm run dev',
  port: 3003,
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
},

// After (CORRECT)
// Removed webServer section entirely
// Added comment explaining service management:
// Note: Test environment services are managed by docker-compose.test.yml
// Use npm run test:journeys:setup to start services before running tests
// Use npm run test:journeys:teardown to stop services after tests
```

Also updated baseURL:
```typescript
use: {
  baseURL: 'http://localhost:3000',  // Changed from 3003
  // ...
}
```

### 2. Created Service Wait Script

**File**: `scripts/wait-for-services.sh`

```bash
#!/bin/bash
# Waits for all docker-compose test services to be healthy

Services checked:
- PostgreSQL (port 5432)
- Redis (port 6379)
- API health endpoint (http://localhost:8000/health)
- API ready endpoint (http://localhost:8000/ready)
- Landing page (http://localhost:3000)
- Test app (http://localhost:3001)
- Dashboard (http://localhost:3002)

Features:
- 3-minute maximum wait time
- Health check for each service
- Color-coded output for visibility
- Fails fast if any service doesn't start
```

## Correct Test Workflow

### Running Tests Locally

**Option 1: Full Test Suite** (recommended)
```bash
# Uses package.json script - handles setup & teardown automatically
npm run test:journeys
```

This runs:
1. `docker-compose -f docker-compose.test.yml up -d` - Start all services
2. `bash scripts/wait-for-services.sh` - Wait for services to be healthy
3. `npx playwright test tests/e2e/journeys` - Run tests
4. `docker-compose -f docker-compose.test.yml down -v` - Cleanup

**Option 2: Manual Control** (for development/debugging)
```bash
# 1. Start services
npm run test:journeys:setup

# 2. Run tests (can run multiple times without restarting services)
npx playwright test

# 3. Stop services when done
npm run test:journeys:teardown
```

**Option 3: Headed/Debug Mode**
```bash
# Start services first
npm run test:journeys:setup

# Run with browser visible and debug tools
npm run test:journeys:local

# Or directly with Playwright
npx playwright test --headed --debug

# Cleanup when done
npm run test:journeys:teardown
```

### Running Tests in CI/CD

In GitHub Actions workflows:

```yaml
- name: Start test environment
  run: docker-compose -f docker-compose.test.yml up -d

- name: Wait for services
  run: bash scripts/wait-for-services.sh

- name: Run Playwright tests
  run: npx playwright test --reporter=github

- name: Cleanup test environment
  if: always()
  run: docker-compose -f docker-compose.test.yml down -v
```

## Test Environment Services

The `docker-compose.test.yml` provides:

### Application Services
| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| API | 8000 | http://localhost:8000 | Backend API |
| Landing | 3000 | http://localhost:3000 | Marketing/landing page |
| Test App | 3001 | http://localhost:3001 | SDK integration test app |
| Dashboard | 3002 | http://localhost:3002 | Admin dashboard |

### Data Services
| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Test database |
| Redis | 6379 | Cache and sessions |

### Environment Variables
All services run with `ENVIRONMENT=test`:
- Test database credentials
- Test JWT secrets
- Test API keys
- CORS configured for all app ports

## What Tests Expect

### API Integration Tests (`tests-e2e/api-integration.spec.ts`)
Test requests to:
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/ready` - Readiness check
- `http://localhost:8000/.well-known/openid-configuration` - OIDC config
- `http://localhost:8000/.well-known/jwks.json` - JWKS endpoint
- `http://localhost:8000/docs` - API documentation
- `http://localhost:8000/redoc` - ReDoc documentation

### Auth Flow Tests (`tests-e2e/auth-flows.spec.ts`)
Browser automation testing:
- `http://localhost:3000/auth/signup` - User registration
- `http://localhost:3000/auth/login` - User login
- Form interactions and redirects
- Email verification flows

## Why webServer Was Removed

Playwright's `webServer` feature is designed for starting a **single** development server, not complex multi-service environments.

**webServer limitations**:
- Can only start one command
- No service dependency management
- No health checking for multiple services
- Poor cleanup for complex setups
- Not designed for docker-compose orchestration

**Why docker-compose is better**:
- Starts all services (API, frontend, database, Redis) together
- Manages service dependencies (API waits for database)
- Proper health checking for each service
- Clean startup and teardown
- Isolated test environment
- Consistent between local dev and CI

## Troubleshooting

### Tests Still Failing with Connection Refused

1. **Check services are running**:
   ```bash
   docker-compose -f docker-compose.test.yml ps
   ```

2. **Check service health**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:3000
   ```

3. **View service logs**:
   ```bash
   docker-compose -f docker-compose.test.yml logs api
   docker-compose -f docker-compose.test.yml logs landing
   ```

4. **Restart services**:
   ```bash
   docker-compose -f docker-compose.test.yml down -v
   docker-compose -f docker-compose.test.yml up -d
   bash scripts/wait-for-services.sh
   ```

### Services Won't Start

1. **Check for port conflicts**:
   ```bash
   lsof -i :8000  # API port
   lsof -i :3000  # Landing port
   lsof -i :5432  # PostgreSQL port
   lsof -i :6379  # Redis port
   ```

2. **Check Docker resources**:
   ```bash
   docker system df
   docker system prune  # If needed
   ```

3. **Rebuild containers**:
   ```bash
   docker-compose -f docker-compose.test.yml build --no-cache
   docker-compose -f docker-compose.test.yml up -d
   ```

### Wait Script Times Out

If `wait-for-services.sh` times out:

1. **Increase wait time** (edit script):
   ```bash
   MAX_WAIT=300  # 5 minutes instead of 3
   ```

2. **Check individual services**:
   ```bash
   docker-compose -f docker-compose.test.yml logs --tail=50 api
   docker-compose -f docker-compose.test.yml logs --tail=50 postgres
   ```

3. **Database initialization issues**:
   ```bash
   # Remove volumes and restart
   docker-compose -f docker-compose.test.yml down -v
   docker-compose -f docker-compose.test.yml up -d postgres
   # Wait for postgres to be fully ready, then start others
   ```

## Files Modified

1. **playwright.config.ts**
   - Removed `webServer` configuration
   - Updated `baseURL` from 3003 → 3000
   - Added documentation comments

2. **scripts/wait-for-services.sh**
   - Created new script
   - Checks all 7 test services
   - Maximum 3-minute wait time
   - Color-coded output

## Prevention

To prevent similar issues:

1. **Always use docker-compose for E2E tests**
   - Never try to start individual services in Playwright config
   - Use webServer only for simple single-service scenarios

2. **Document test prerequisites**
   - README should explain test environment setup
   - Include quick-start commands

3. **Add pre-test validation**
   - Scripts that check for required services
   - Fail fast with helpful error messages

4. **CI/CD consistency**
   - Use same docker-compose setup locally and in CI
   - Test locally before pushing

## Related Documentation

- [Docker Compose Test Environment](../docker-compose.test.yml)
- [Playwright Configuration](../playwright.config.ts)
- [Package Scripts](../package.json) - See `test:journeys*` scripts

## Verification

After applying fixes:

```bash
# Full test run
npm run test:journeys

# Should see:
# ✅ All services started
# ✅ All services healthy
# ✅ Tests run successfully
# ✅ Clean teardown

# Manual verification
npm run test:journeys:setup
# Visit in browser:
# - http://localhost:8000/health (should return OK)
# - http://localhost:3000 (should show landing page)
# - http://localhost:3001 (should show test app)
# - http://localhost:3002 (should show dashboard)
npm run test:journeys:teardown
```

All tests should now pass when services are properly started with docker-compose.
