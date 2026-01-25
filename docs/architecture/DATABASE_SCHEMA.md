# Database Schema Documentation

> **Entity-Relationship Diagram and model documentation** for Janua's PostgreSQL database

## Overview

Janua uses PostgreSQL as its primary database, with SQLAlchemy 2.0 ORM for data access. The schema is designed for multi-tenancy with organization-based data isolation.

**Database**: PostgreSQL 14+
**ORM**: SQLAlchemy 2.0 (async)
**Migrations**: Alembic

## Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AUTHENTICATION DOMAIN                           │
└─────────────────────────────────────────────────────────────────────────────┘

                                  ┌──────────────┐
                                  │    users     │
                                  ├──────────────┤
                                  │ id (PK)      │
                                  │ email        │
                                  │ password_hash│
                                  │ tenant_id    │
                 ┌───────────────►│ mfa_enabled  │◄───────────────┐
                 │                │ mfa_secret   │                │
                 │                │ status       │                │
                 │                │ created_at   │                │
                 │                └──────┬───────┘                │
                 │                       │                        │
        ┌────────┴────────┐     ┌───────┴───────┐     ┌──────────┴──────────┐
        │                 │     │               │     │                     │
   ┌────▼────┐      ┌─────▼─────┐      ┌───────▼───────┐      ┌────────────▼─────┐
   │sessions │      │oauth_accts│      │   passkeys    │      │email_verifications│
   ├─────────┤      ├───────────┤      ├───────────────┤      ├──────────────────┤
   │id (PK)  │      │id (PK)    │      │id (PK)        │      │id (PK)           │
   │user_id  │      │user_id    │      │user_id        │      │user_id           │
   │token    │      │provider   │      │credential_id  │      │token             │
   │ip_addr  │      │prov_user  │      │public_key     │      │expires_at        │
   │expires  │      │access_tok │      │sign_count     │      │verified_at       │
   └─────────┘      └───────────┘      └───────────────┘      └──────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            ORGANIZATION DOMAIN                               │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │  organizations   │
                              ├──────────────────┤
                              │ id (PK)          │
                              │ name             │
                              │ slug             │
                              │ owner_id (FK)    │──────────► users.id
                              │ billing_plan     │
                              │ settings (JSONB) │
                              └────────┬─────────┘
                                       │
         ┌─────────────────┬───────────┼───────────┬─────────────────┐
         │                 │           │           │                 │
    ┌────▼────┐     ┌──────▼──────┐ ┌──▼───┐ ┌─────▼─────┐   ┌───────▼───────┐
    │ members │     │ invitations │ │roles │ │ policies  │   │   webhooks    │
    ├─────────┤     ├─────────────┤ ├──────┤ ├───────────┤   ├───────────────┤
    │id       │     │id           │ │id    │ │id         │   │id             │
    │org_id   │     │org_id       │ │org_id│ │org_id     │   │org_id         │
    │user_id  │     │email        │ │name  │ │name       │   │url            │
    │role     │     │role         │ │perms │ │rules      │   │events (JSONB) │
    │status   │     │token        │ │      │ │           │   │secret         │
    └─────────┘     │expires_at   │ └──────┘ └───────────┘   └───────────────┘
                    └─────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              BILLING DOMAIN                                  │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
    │     plans      │     │ subscriptions  │     │   invoices     │
    ├────────────────┤     ├────────────────┤     ├────────────────┤
    │ id (PK)        │◄────│ plan_id (FK)   │     │ id (PK)        │
    │ name           │     │ id (PK)        │     │ subscription_id│
    │ price_monthly  │     │ org_id (FK)    │────►│ org_id (FK)    │
    │ price_yearly   │     │ status         │     │ amount         │
    │ features       │     │ current_period │     │ status         │
    └────────────────┘     └────────────────┘     │ due_date       │
                                                  └────────┬───────┘
                                                           │
                                                    ┌──────▼───────┐
                                                    │   payments   │
                                                    ├──────────────┤
                                                    │ id (PK)      │
                                                    │ invoice_id   │
                                                    │ amount       │
                                                    │ status       │
                                                    └──────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                               AUDIT DOMAIN                                   │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
    │  audit_logs    │     │ activity_logs  │     │  notifications │
    ├────────────────┤     ├────────────────┤     ├────────────────┤
    │ id (PK)        │     │ id (PK)        │     │ id (PK)        │
    │ user_id (FK)   │     │ user_id (FK)   │     │ user_id (FK)   │
    │ action         │     │ action         │     │ org_id (FK)    │
    │ resource_type  │     │ resource_type  │     │ title          │
    │ resource_id    │     │ ip_address     │     │ message        │
    │ ip_address     │     │ user_agent     │     │ is_read        │
    │ details        │     │ created_at     │     │ created_at     │
    └────────────────┘     └────────────────┘     └────────────────┘
```

## Core Tables

### users

Primary user identity table.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | User email address |
| `email_verified` | BOOLEAN | DEFAULT FALSE | Email verification status |
| `password_hash` | VARCHAR(255) | | Bcrypt password hash |
| `status` | ENUM | DEFAULT 'active' | active, inactive, suspended, pending, deleted |
| `first_name` | VARCHAR(255) | | User's first name |
| `last_name` | VARCHAR(255) | | User's last name |
| `username` | VARCHAR(50) | UNIQUE | Optional username |
| `phone` | VARCHAR(50) | | Phone number |
| `avatar_url` | VARCHAR(500) | | Profile image URL |
| `tenant_id` | UUID | INDEX | Multi-tenancy support |
| `mfa_enabled` | BOOLEAN | DEFAULT FALSE | MFA activation status |
| `mfa_secret` | VARCHAR(255) | | TOTP secret (encrypted) |
| `mfa_backup_codes` | JSONB | DEFAULT [] | Hashed backup codes |
| `failed_login_attempts` | INTEGER | DEFAULT 0 | Lockout counter |
| `locked_until` | TIMESTAMP | | Lockout expiration |
| `is_admin` | BOOLEAN | DEFAULT FALSE | System admin flag |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `users_email_idx` (email) - Login lookups
- `users_tenant_id_idx` (tenant_id) - Multi-tenant queries

### sessions

Active user sessions with device tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Session identifier |
| `user_id` | UUID | FK(users.id), NOT NULL | Owning user |
| `token` | TEXT | UNIQUE, NOT NULL | Session token |
| `refresh_token` | TEXT | UNIQUE | Refresh token |
| `access_token_jti` | VARCHAR(255) | UNIQUE | JWT token ID |
| `ip_address` | VARCHAR(50) | | Client IP |
| `user_agent` | TEXT | | Browser/client info |
| `device_name` | VARCHAR(255) | | Device identifier |
| `device_fingerprint` | VARCHAR(255) | INDEX | Unique device hash |
| `is_active` | BOOLEAN | DEFAULT TRUE | Session status |
| `revoked` | BOOLEAN | DEFAULT FALSE | Revocation flag |
| `revoked_at` | TIMESTAMP | | Revocation time |
| `expires_at` | TIMESTAMP | NOT NULL | Session expiration |
| `last_activity` | TIMESTAMP | DEFAULT NOW() | Last request time |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time |

### organizations

Multi-tenant organization container.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Organization identifier |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `slug` | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | URL-safe identifier |
| `owner_id` | UUID | FK(users.id) | Organization owner |
| `billing_plan` | VARCHAR(100) | DEFAULT 'free' | Current plan |
| `billing_email` | VARCHAR(255) | | Billing contact |
| `billing_customer_id` | VARCHAR(255) | INDEX | External billing ID |
| `logo_url` | VARCHAR(500) | | Organization logo |
| `description` | TEXT | | Organization description |
| `settings` | JSONB | DEFAULT {} | Organization settings |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update |

### organization_members

User-organization membership with roles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Membership identifier |
| `organization_id` | UUID | FK(organizations.id), NOT NULL | Organization |
| `user_id` | UUID | FK(users.id), NOT NULL | User |
| `role` | VARCHAR(50) | DEFAULT 'member' | owner, admin, member, viewer |
| `status` | VARCHAR(50) | DEFAULT 'active' | Membership status |
| `joined_at` | TIMESTAMP | DEFAULT NOW() | Join date |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation |

**Unique Constraint:** `(organization_id, user_id)`

### oauth_accounts

Linked OAuth provider accounts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Account identifier |
| `user_id` | UUID | FK(users.id), NOT NULL | Owning user |
| `provider` | ENUM | NOT NULL | google, github, microsoft, etc. |
| `provider_user_id` | VARCHAR(255) | NOT NULL | Provider's user ID |
| `provider_email` | VARCHAR(255) | | Email from provider |
| `access_token` | TEXT | | OAuth access token |
| `refresh_token` | TEXT | | OAuth refresh token |
| `token_expires_at` | TIMESTAMP | | Token expiration |
| `provider_data` | JSONB | DEFAULT {} | Provider-specific data |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Link creation |

**Unique Constraint:** `(provider, provider_user_id)`

### passkeys

WebAuthn/FIDO2 credentials.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Passkey identifier |
| `user_id` | UUID | FK(users.id), NOT NULL | Owning user |
| `credential_id` | VARCHAR(500) | UNIQUE, NOT NULL | WebAuthn credential ID |
| `public_key` | TEXT | NOT NULL | COSE public key |
| `sign_count` | INTEGER | DEFAULT 0 | Signature counter |
| `name` | VARCHAR(100) | | User-given name |
| `authenticator_attachment` | VARCHAR(50) | | platform or cross-platform |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Registration time |
| `last_used_at` | TIMESTAMP | | Last authentication |

### audit_logs

Compliance and security audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Log entry identifier |
| `user_id` | UUID | FK(users.id) | Acting user |
| `action` | VARCHAR(100) | NOT NULL | Action performed |
| `resource_type` | VARCHAR(100) | | Type of resource |
| `resource_id` | UUID | | Resource identifier |
| `details` | JSONB | DEFAULT {} | Action details |
| `ip_address` | INET | | Client IP address |
| `user_agent` | TEXT | | Client user agent |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Event timestamp |

**Indexes:**
- `audit_logs_user_id_idx` (user_id)
- `audit_logs_created_at_idx` (created_at)
- `audit_logs_action_idx` (action)

## Relationships

### User-Centric Relationships

```
User (1) ──────< Session (*)         # User has many sessions
User (1) ──────< OAuthAccount (*)    # User can link multiple OAuth providers
User (1) ──────< Passkey (*)         # User can register multiple passkeys
User (1) ──────< OrganizationMember (*) # User belongs to many organizations
User (1) ──────< AuditLog (*)        # User's activity is logged
```

### Organization-Centric Relationships

```
Organization (1) ──────< OrganizationMember (*) # Org has many members
Organization (1) ──────< Invitation (*)         # Org has pending invitations
Organization (1) ──────< Role (*)               # Org defines custom roles
Organization (1) ──────< Policy (*)             # Org has access policies
Organization (1) ──────< Webhook (*)            # Org configures webhooks
Organization (1) ─────── User (owner)           # Org has one owner
```

## Key Design Patterns

### Multi-Tenancy

All tenant-scoped tables include `organization_id` or `tenant_id`:

```sql
-- Row-level security pattern
CREATE POLICY org_isolation ON organization_members
  FOR ALL
  USING (organization_id = current_setting('app.current_org_id')::uuid);
```

### Soft Deletes

User accounts use status-based soft deletion:

```sql
-- Instead of DELETE
UPDATE users SET status = 'deleted', updated_at = NOW() WHERE id = ?;
```

### Audit Trail

All sensitive operations are logged:

```sql
INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address)
VALUES (?, 'user.password_changed', 'user', ?, '{}', ?);
```

### Token Family Rotation

Sessions use token families to detect token theft:

```sql
-- On refresh, check family and rotate
SELECT * FROM sessions WHERE refresh_token_family = ? AND NOT revoked;
-- If token reused after rotation, revoke entire family
UPDATE sessions SET revoked = true WHERE refresh_token_family = ?;
```

## Migration Commands

```bash
# Create new migration
cd apps/api
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current revision
alembic current

# View migration history
alembic history --verbose
```

## Connection Configuration

```python
# apps/api/app/config.py
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/janua"

# Connection pool settings
POOL_SIZE = 20
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30
POOL_RECYCLE = 1800
```

## Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [API Endpoints Reference](/apps/api/docs/api/endpoints-reference.md)
- [Multi-Tenancy ADR](./ADR-003_MULTITENANCY.md)
- [Performance Tuning](/docs/guides/PERFORMANCE_TUNING_GUIDE.md)
