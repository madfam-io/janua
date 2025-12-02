# Secrets Management Guide

Best practices for managing secrets in Janua production deployments.

---

## Overview

Janua requires several secrets for production operation. This guide covers secure handling, storage, and rotation of these secrets.

---

## Required Secrets

### Database

| Secret | Description | Rotation |
|--------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Quarterly |
| `POSTGRES_PASSWORD` | Database user password | Quarterly |
| `REDIS_PASSWORD` | Redis authentication | Quarterly |

### Authentication

| Secret | Description | Rotation |
|--------|-------------|----------|
| `JWT_SECRET_KEY` | JWT signing key (HS256) | Annually |
| `JWT_PRIVATE_KEY` | JWT private key (RS256) | Annually |
| `SECRET_KEY` | Application secret | Annually |
| `SESSION_SECRET` | Session encryption key | Annually |

### External Services

| Secret | Description | Rotation |
|--------|-------------|----------|
| `RESEND_API_KEY` | Email service API key | As needed |
| `SENDGRID_API_KEY` | SendGrid API key | As needed |
| `SENTRY_DSN` | Error tracking DSN | Never (static) |
| `INTERNAL_API_KEY` | Service-to-service auth | Quarterly |

### OAuth Providers

| Secret | Description | Rotation |
|--------|-------------|----------|
| `OAUTH_GOOGLE_CLIENT_SECRET` | Google OAuth | Annually |
| `OAUTH_GITHUB_CLIENT_SECRET` | GitHub OAuth | Annually |
| `OAUTH_MICROSOFT_CLIENT_SECRET` | Microsoft OAuth | Annually |

---

## Storage Options

### Option 1: Environment Files (Development Only)

```bash
# .env.production (gitignored)
DATABASE_URL=postgresql://user:pass@host:5432/janua
JWT_SECRET_KEY=your-secret-key
```

**Warning:** Never commit `.env` files to version control.

### Option 2: Docker Secrets (Recommended for Self-Hosted)

```bash
# Create secrets
echo "your-db-password" | docker secret create postgres_password -
echo "your-jwt-secret" | docker secret create jwt_secret -

# Use in docker-compose
services:
  janua-api:
    secrets:
      - postgres_password
      - jwt_secret

secrets:
  postgres_password:
    external: true
  jwt_secret:
    external: true
```

### Option 3: HashiCorp Vault (Enterprise)

```bash
# Store secrets
vault kv put secret/janua/db password=xxx
vault kv put secret/janua/jwt secret=xxx

# Retrieve in application
vault kv get -field=password secret/janua/db
```

### Option 4: Cloud Provider Secrets

**AWS Secrets Manager:**
```bash
aws secretsmanager create-secret \
  --name janua/production/db \
  --secret-string '{"password":"xxx"}'
```

**Google Secret Manager:**
```bash
gcloud secrets create janua-db-password \
  --data-file=- <<< "your-password"
```

---

## Current Production Setup

For the Hetzner bare metal server, secrets are managed via:

1. **Environment file**: `/opt/solarpunk/janua/.env.production`
2. **Docker environment**: Passed via `--env-file` flag
3. **Systemd**: Environment variables in service files

### Setup on Server

```bash
# SSH to server
ssh -i ~/.ssh/id_ed25519 root@95.217.198.239

# Create/edit production environment
cd /opt/solarpunk/janua
nano .env.production

# Set restrictive permissions
chmod 600 .env.production
chown root:root .env.production
```

### Environment File Template

```bash
# /opt/solarpunk/janua/.env.production
# DO NOT COMMIT THIS FILE

# Database
DATABASE_URL=postgresql://janua:CHANGE_ME@localhost:5432/janua
REDIS_URL=redis://:CHANGE_ME@localhost:6379/0

# Security
JWT_SECRET_KEY=CHANGE_ME_32_CHARS_MIN
SECRET_KEY=CHANGE_ME_32_CHARS_MIN

# Email
RESEND_API_KEY=re_CHANGE_ME

# Internal
INTERNAL_API_KEY=CHANGE_ME
```

---

## Rotation Procedures

### Database Password Rotation

```bash
# 1. Generate new password
NEW_PASS=$(openssl rand -base64 32)

# 2. Update PostgreSQL
docker exec janua-postgres psql -U postgres -c \
  "ALTER USER janua PASSWORD '$NEW_PASS';"

# 3. Update .env.production
sed -i "s/DATABASE_URL=.*/DATABASE_URL=postgresql:\/\/janua:$NEW_PASS@localhost:5432\/janua/" \
  /opt/solarpunk/janua/.env.production

# 4. Restart services
docker restart janua-api
```

### JWT Secret Rotation

```bash
# 1. Generate new secret
NEW_SECRET=$(openssl rand -base64 64)

# 2. Update .env.production
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$NEW_SECRET/" \
  /opt/solarpunk/janua/.env.production

# 3. Restart API (existing sessions will be invalidated)
docker restart janua-api
```

---

## Security Checklist

- [ ] All secrets are at least 32 characters
- [ ] `.env.production` has `600` permissions
- [ ] No secrets in docker-compose.yml (use env_file)
- [ ] No secrets in git history
- [ ] Secrets rotated on schedule
- [ ] Backup of secrets stored securely offline
- [ ] Access to secrets is logged

---

## Generating Secure Secrets

```bash
# 32-character secret
openssl rand -base64 32

# 64-character secret
openssl rand -base64 64

# Hex secret (for specific requirements)
openssl rand -hex 32

# URL-safe secret
openssl rand -base64 32 | tr '+/' '-_'
```

---

## Emergency Response

If secrets are compromised:

1. **Immediately** rotate the compromised secret
2. **Audit** access logs for unauthorized use
3. **Invalidate** all sessions (restart API with new JWT secret)
4. **Notify** affected users if data was accessed
5. **Document** the incident and remediation

---

## References

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [HashiCorp Vault](https://www.vaultproject.io/)
