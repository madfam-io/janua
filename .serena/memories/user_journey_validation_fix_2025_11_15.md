# User Journey Validation Workflow Fix - November 15, 2025

## Issue Resolved

**GitHub Issue #1**: User Journey Validation Failure (OPEN → FIX DEPLOYED)

## Root Cause Analysis

The `validate-user-journeys.yml` workflow was failing because:

1. **Missing Frontend Application**: Workflow only started databases (postgres, redis) and API server (port 8000)
2. **Test Requirements**: All journey tests navigate to `http://localhost:3000` expecting Next.js landing page
3. **Intentional Removal**: Commit bbbb1d9 switched to "databases only" approach, removing frontend startup
4. **Complete Test Failure**: All 3 jobs (validate-journeys, validate-content-alignment, performance-validation) failing

## Solution Implemented

### Changes to `.github/workflows/validate-user-journeys.yml`

Added complete landing page lifecycle to 2 jobs:

#### Job 1: validate-journeys
```yaml
- name: Install landing page dependencies
  run: |
    cd apps/landing
    npm install

- name: Build landing page
  run: |
    cd apps/landing
    npm run build

- name: Start landing page
  run: |
    cd apps/landing
    npm start &
    echo $! > /tmp/landing.pid
    echo "Landing page started in background on port 3000"

- name: Wait for landing page to be ready
  run: |
    echo "Waiting for landing page..."
    timeout 120s bash -c 'until curl -f http://localhost:3000 2>/dev/null; do sleep 2; done'
    echo "Landing page is healthy and ready"

# ... tests run ...

- name: Stop landing page
  if: always()
  run: |
    if [ -f /tmp/landing.pid ]; then
      kill $(cat /tmp/landing.pid) 2>/dev/null || true
    fi
    pkill -f "next start" || true
```

#### Job 2: performance-validation
Same landing page steps added before performance tests.

## Validation

✅ **YAML Syntax**: Validated with `python3 -c "import yaml; yaml.safe_load(...)"`
✅ **Step Order**: Landing page starts after API, cleanup in reverse order
✅ **Error Handling**: All cleanup steps use `if: always()` for resource management
✅ **Process Management**: PID files tracked for graceful shutdown

## Commit Details

**Commit**: 55ec6d9
**Message**: "fix(ci): add landing page to user journey validation workflow"
**Files Changed**: 1 file, +62 insertions

## Expected Outcome

When the workflow runs next (triggered by changes to monitored paths):

1. ✅ Landing page will be available on localhost:3000
2. ✅ Journey tests can navigate and validate marketing claims
3. ✅ Performance tests have complete environment (DB + API + Frontend)
4. ✅ Issue #1 should auto-close or be resolvable

## Workflow Trigger Paths

The workflow runs on push/PR when these paths change:
- `apps/landing/**`
- `apps/api/**`
- `apps/dashboard/**`
- `packages/**`
- `docs/user-journeys/**`
- `tests/e2e/journeys/**`
- `docker-compose.test.yml`

**Note**: The workflow fix itself (`.github/workflows/validate-user-journeys.yml`) is NOT in the trigger paths, so it won't auto-run. Next trigger will be when any of the above paths are modified.

## Testing Recommendation

To verify the fix works:

1. Make a trivial change to `apps/landing/README.md`
2. Commit and push
3. Monitor workflow run at: https://github.com/madfam-org/janua/actions/workflows/validate-user-journeys.yml
4. Verify all jobs pass or fail with meaningful errors (not "page not found")

## Infrastructure Improvements

The fix follows the existing pattern:
- Same approach as API server (background process with PID tracking)
- Health checks with timeouts
- Graceful cleanup with fallback pkill
- Proper error handling with `|| true` to prevent cleanup failures

## Related Files

- `.github/workflows/validate-user-journeys.yml` - Workflow definition
- `apps/landing/package.json` - Landing page build/start scripts
- `tests/e2e/journeys/*.spec.ts` - Journey test files expecting localhost:3000
- `Issue #1` - GitHub issue tracking the validation failure
