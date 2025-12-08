# Janua Test Scripts

Scripts for testing Janua services.

## smoke-test.sh

Production smoke test script that verifies basic functionality of all Janua services.

### Usage

```bash
# Run all smoke tests
./smoke-test.sh

# Verbose output
./smoke-test.sh --verbose

# Stop on first failure
./smoke-test.sh --fail-fast

# Both options
./smoke-test.sh -v -f
```

### Tests Performed

#### API Tests
- Health endpoint (`/health`)
- OpenAPI docs (`/docs`)
- Version endpoint (`/api/v1/`)
- Auth login endpoint validation
- Metrics endpoint (`/metrics`)

#### Frontend Tests
- Dashboard (https://app.janua.dev)
- Admin Panel (https://admin.janua.dev)
- Documentation (https://docs.janua.dev)
- Website (https://janua.dev)

#### Infrastructure Tests
- SSL Certificate validity
- API Response time (< 2000ms)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | https://api.janua.dev | API base URL |
| `APP_URL` | https://app.janua.dev | Dashboard URL |
| `ADMIN_URL` | https://admin.janua.dev | Admin panel URL |
| `DOCS_URL` | https://docs.janua.dev | Documentation URL |
| `WEBSITE_URL` | https://janua.dev | Marketing website URL |
| `TIMEOUT` | 10 | Request timeout in seconds |

### Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed

### Integration with CI/CD

Add to GitHub Actions workflow:

```yaml
- name: Production Smoke Tests
  run: ./scripts/tests/smoke-test.sh
  continue-on-error: false
```

### Local Development

Test against local services:

```bash
API_URL=http://localhost:4100 \
APP_URL=http://localhost:4101 \
ADMIN_URL=http://localhost:4102 \
./smoke-test.sh
```
