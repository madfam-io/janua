# Quarantined Tests

This directory contains test files that are temporarily excluded from CI due to
implementation drift during refactoring. These tests reference outdated method
signatures, classes, or APIs that no longer exist in the current codebase.

## Why Quarantine Instead of Delete?

1. **Preserve test logic** - Many tests contain valuable test cases and edge cases
2. **Restoration potential** - Tests can be updated to match current implementations
3. **Historical context** - Tests document what was previously tested
4. **Cleaner CI** - Reduces 46+ `--ignore` flags to a single directory ignore

## Quarantine Date

**Quarantined**: January 2025 (Test Coverage Audit)

## File Count by Category

| Category | Count | Priority to Restore |
|----------|-------|---------------------|
| Services | 21 | P0 - High value test coverage |
| Routers | 6 | P1 - API endpoint coverage |
| Root | 12 | P2 - Mixed priority |
| Core | 3 | P1 - Core utilities |
| Middleware | 2 | P1 - Rate limiting tests |
| Models | 1 | P0 - Data model tests |
| Auth | 1 | P1 - Auth router tests |

## Restoration Process

To restore a quarantined test file:

1. Read the current service/module implementation
2. Identify signature changes since test was written
3. Update test mocks, fixtures, and assertions
4. Run locally to verify: `pytest tests/quarantine/services/test_file.py -v`
5. Move file back to appropriate `tests/unit/` directory
6. Verify CI passes

## Priority Restoration Order

### P0 - Critical (Restore First)
- `services/test_auth_service_comprehensive.py` - Core auth functionality
- `services/test_jwt_service_enhanced.py` - JWT token handling
- `models/test_user.py` - User model validation

### P1 - High (Week 1-2)
- `services/test_billing_service_comprehensive.py` - Billing logic
- `services/test_monitoring_service.py` - Observability
- `middleware/test_rate_limit.py` - Rate limiting
- `core/test_redis.py` - Cache layer

### P2 - Medium (Week 3-4)
- `services/test_compliance_service_comprehensive.py` - Compliance
- `routers/test_auth_router_comprehensive.py` - Auth endpoints
- Remaining services and routers

## Common Issues

Most tests fail due to:
- Method signature changes (new required parameters)
- Class renames or relocations
- Removed deprecated methods
- Changed return types or response schemas
- Updated dependency injection patterns

## Do Not

- Delete files from quarantine without team approval
- Move files back to `tests/unit/` without fixing them first
- Ignore quarantine failures if you accidentally run them
