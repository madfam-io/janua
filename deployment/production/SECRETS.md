# MADFAM Secrets Management

This document provides an overview of secrets management for the MADFAM ecosystem (Janua and Enclii projects).

## Quick Start

```bash
# Check rotation status
./scripts/secrets/manage-secrets.sh status

# List all tracked secrets
./scripts/secrets/manage-secrets.sh list

# Rotate a specific secret
./scripts/secrets/manage-secrets.sh rotate janua-postgres-password

# Run security audit
./scripts/secrets/manage-secrets.sh audit
```

## Key Files

| File | Purpose |
|------|---------|
| `infra/secrets/SECRETS_REGISTRY.yaml` | Central inventory of all secrets |
| `scripts/secrets/manage-secrets.sh` | Main CLI for secrets operations |
| `scripts/secrets/check-rotation-schedule.py` | Rotation status checker |
| `docs/runbooks/secrets/` | Rotation procedures and runbooks |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECRETS MANAGEMENT SYSTEM                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  SECRETS_REGISTRY │───▶│  GitHub Actions   │───▶│  Slack/Issues    │  │
│  │     .yaml         │    │  Weekly Check     │    │  Notifications   │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  manage-secrets   │───▶│  Rotation Scripts │───▶│  Kubernetes      │  │
│  │     .sh CLI       │    │  (DB, JWT, etc)   │    │  Secrets         │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐    ┌──────────────────┐                           │
│  │  Prometheus       │───▶│  Grafana          │                          │
│  │  Metrics          │    │  Dashboard        │                          │
│  └──────────────────┘    └──────────────────┘                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Secrets Inventory Summary

### Janua Project (~30 secrets)

| Category | Count | Policy | Examples |
|----------|-------|--------|----------|
| Database | 3 | Quarterly | PostgreSQL, Redis passwords |
| Authentication | 3 | Annual | JWT keys, session secret |
| OAuth Providers | 8 | Annual | Google, GitHub, Microsoft, Apple, etc. |
| Email | 2 | Annual | SMTP, SendGrid |
| Payment | 3 | Annual | Stripe keys and webhook |
| Infrastructure | 5+ | Various | Cloudflare, GHCR, S3, Sentry |

### Enclii Project (~8 secrets)

| Category | Count | Policy | Examples |
|----------|-------|--------|----------|
| OIDC | 1 | Annual | Janua integration secret |
| Registry | 1 | Annual | GHCR credentials |
| Webhook | 1 | Semi-annual | Webhook signature secret |
| Database | 1 | Quarterly | PostgreSQL password |
| Infrastructure | 2 | Various | Cloudflare, backup keys |

## Rotation Policies

| Policy | Frequency | Applicable To |
|--------|-----------|---------------|
| **Quarterly** | Every 90 days | Database passwords, service accounts |
| **Semi-annual** | Every 180 days | API keys, integration tokens |
| **Annual** | Every 365 days | OAuth secrets, JWT keys, registry creds |
| **On-demand** | As needed | Encryption keys, root credentials |

## Rotation Procedures

### Automated Scripts

| Secret Type | Script | Downtime |
|-------------|--------|----------|
| Database passwords | `rotate-db-password.sh` | Rolling restart |
| JWT keys | `rotate-jwt-keys.sh` | None (24h grace) |

### Manual Procedures (See Runbooks)

| Secret Type | Runbook |
|-------------|---------|
| Google OAuth | `docs/runbooks/secrets/oauth-google-rotation.md` |
| GitHub OAuth | `docs/runbooks/secrets/oauth-github-rotation.md` |
| Stripe keys | `docs/runbooks/secrets/stripe-rotation.md` |
| GHCR credentials | `docs/runbooks/secrets/ghcr-pat-rotation.md` |
| Emergency | `docs/runbooks/secrets/EMERGENCY_ROTATION.md` |

## Automated Reminders

GitHub Actions workflow runs weekly (Mondays 9 AM UTC):
- Checks all secrets against rotation schedule
- Sends Slack notification for upcoming/overdue rotations
- Creates GitHub issues for overdue secrets

**Workflow:** `.github/workflows/secrets-rotation-reminder.yml`

## Monitoring

### Grafana Dashboard

Import `infra/monitoring/dashboards/secrets-rotation.json` to view:
- Overdue secrets count
- Days until rotation by secret
- Rotation history
- Secrets inventory table

### Prometheus Alerts

Deploy `infra/monitoring/alerts/secrets-rotation.yaml` for:
- `SecretRotationOverdue` (critical)
- `SecretRotationDue7Days` (warning)
- `SecretRotationDue14Days` (info)
- `TooManyOverdueSecrets` (critical)

## Cross-Project Coordination

Some secrets are shared between Janua and Enclii:

### JWT Keys
1. Janua owns the JWT signing keys
2. Enclii uses public key for OIDC verification
3. Rotation requires coordination:
   - Rotate Janua keys with 24h grace period
   - Notify Enclii team
   - Enclii sessions continue working during grace period

### GHCR Credentials
1. Single PAT may serve both projects
2. Rotation order: Janua → verify → Enclii → verify → revoke old

## Emergency Procedures

For suspected compromise:

```bash
# View emergency runbook
cat docs/runbooks/secrets/EMERGENCY_ROTATION.md

# Quick reference
./scripts/secrets/manage-secrets.sh emergency --critical
```

**Severity Levels:**
- **CRITICAL** (immediate): JWT keys, DB passwords, payment keys
- **HIGH** (4 hours): OAuth secrets, registry credentials
- **MEDIUM** (24 hours): Monitoring tokens, non-prod secrets

## Adding New Secrets

1. Add entry to `infra/secrets/SECRETS_REGISTRY.yaml`
2. Create runbook in `docs/runbooks/secrets/` if manual rotation
3. Update `manage-secrets.sh` if automated rotation needed
4. Test rotation procedure in staging

Example registry entry:
```yaml
- id: janua-new-secret
  name: NEW_SECRET_NAME
  description: "Purpose of this secret"
  location: k8s/janua-secrets
  environment: production
  policy: annual
  last_rotated: "2026-01-16"
  next_rotation: "2027-01-16"
  owner: infrastructure
  procedure: new-secret-rotation
  dependencies:
    - janua-api
  risk_level: medium
  rotation_downtime: "none"
```

## Best Practices

1. **Never commit secrets** to version control
2. **Use Fine-grained PATs** over Classic tokens
3. **Test rotations in staging** before production
4. **Maintain grace periods** for keys with dependent services
5. **Document all rotations** in the registry
6. **Coordinate cross-project** secrets carefully
7. **Monitor after rotation** for authentication errors

## Troubleshooting

### Common Issues

**"Secret not found in registry"**
- Verify secret ID matches exactly
- Check project name (janua vs enclii)

**"ImagePullBackOff after GHCR rotation"**
- Token may not have `read:packages` permission
- Check if correct repositories are selected

**"JWT validation failed after rotation"**
- 24h grace period may have expired
- Verify new public key is deployed to all services

### Getting Help

- Slack: #infrastructure or #security
- Runbooks: `docs/runbooks/secrets/`
- Registry: `infra/secrets/SECRETS_REGISTRY.yaml`

---

**Last Updated:** 2026-01-16
**Owner:** Infrastructure & Security Teams
