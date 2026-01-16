# Secrets Management Scripts

Scripts for managing secret rotation across the MADFAM ecosystem.

## Quick Start

```bash
# Check rotation status
./manage-secrets.sh status

# Rotate a specific secret
./manage-secrets.sh rotate janua-postgres-password

# Run security audit
./manage-secrets.sh audit
```

## Scripts

| Script | Purpose |
|--------|---------|
| `manage-secrets.sh` | Main CLI for all secrets operations |
| `check-rotation-schedule.py` | Parse registry and check rotation dates |
| `rotate-db-password.sh` | Rotate PostgreSQL database passwords |
| `rotate-jwt-keys.sh` | Rotate JWT signing keys with grace period |

## Usage Examples

### Check Status

```bash
# Human-readable format
./manage-secrets.sh status

# JSON output (for CI/CD)
./manage-secrets.sh status --json

# Direct Python script
python3 check-rotation-schedule.py --output text
```

### Rotate Secrets

```bash
# Database password
./manage-secrets.sh rotate janua-postgres-password

# JWT keys
./manage-secrets.sh rotate janua-jwt-private-key

# With dry-run
DRY_RUN=1 ./manage-secrets.sh rotate janua-postgres-password
```

### After Manual Rotation

```bash
# Update registry with new rotation date
./manage-secrets.sh update janua-oauth-google-secret
```

## Prerequisites

- Python 3.x with PyYAML (`pip install pyyaml`)
- kubectl configured with cluster access
- openssl (for key generation)

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SECRETS_REGISTRY_PATH` | Override default registry location |
| `DRY_RUN=1` | Preview actions without making changes |

## Related Documentation

- [SECRETS_REGISTRY.yaml](../../infra/secrets/SECRETS_REGISTRY.yaml) - Central inventory
- [SECRETS.md](../../deployment/production/SECRETS.md) - Overview documentation
- [Runbooks](../../docs/runbooks/secrets/) - Rotation procedures
