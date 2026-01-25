# ADR-003: Multi-Tenancy Strategy

**Status**: Accepted
**Date**: 2024-01-25
**Deciders**: Janua Core Team
**Categories**: Architecture, Data Isolation

## Context

Janua serves multiple organizations (tenants) from a single deployment. We need a multi-tenancy strategy that provides:

1. **Data Isolation**: Tenant A cannot access Tenant B's data
2. **Performance**: Tenant operations don't affect others
3. **Scalability**: Support thousands of organizations
4. **Cost Efficiency**: Single deployment, shared infrastructure
5. **Flexibility**: Different plans with different limits

## Decision

We implement **Organization-based Multi-tenancy** with row-level isolation.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MULTI-TENANCY MODEL                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────┐  ┌───────────────────────────┐
│      Tenant A (Acme)      │  │      Tenant B (Globex)    │
│  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │
│  │ Users: 50           │  │  │  │ Users: 200          │  │
│  │ Plan: Pro           │  │  │  │ Plan: Enterprise    │  │
│  │ Rate Limit: 1000/m  │  │  │  │ Rate Limit: 10000/m │  │
│  └─────────────────────┘  │  │  └─────────────────────┘  │
└───────────────────────────┘  └───────────────────────────┘
            │                              │
            └──────────────┬───────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SHARED API LAYER                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Tenant Context Middleware                                           │    │
│  │  - Extract tenant from JWT claims / X-Tenant-ID header              │    │
│  │  - Set tenant context for request                                    │    │
│  │  - Apply tenant-specific rate limits                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SHARED DATABASE (PostgreSQL)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Row-Level Security                                                  │    │
│  │                                                                      │    │
│  │  users               organization_members     audit_logs             │    │
│  │  ├─ id               ├─ organization_id       ├─ organization_id    │    │
│  │  ├─ email            ├─ user_id               ├─ user_id            │    │
│  │  └─ tenant_id ←─────►└─ role                  └─ action             │    │
│  │                                                                      │    │
│  │  WHERE organization_id = current_tenant()                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. Tenant Context Propagation

Every request carries tenant context:

**From JWT Claims:**
```json
{
  "sub": "usr_abc123",
  "org": "org_xyz789",
  "roles": ["admin"],
  "tenant_id": "org_xyz789"
}
```

**From Request Header (API keys):**
```http
X-Tenant-ID: org_xyz789
```

**Middleware Implementation:**
```python
@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    # Extract tenant from JWT or header
    tenant_id = extract_tenant_id(request)

    # Set context for this request
    tenant_context.set(tenant_id)

    # Set PostgreSQL session variable for RLS
    async with db.begin():
        await db.execute(f"SET app.current_tenant_id = '{tenant_id}'")

    response = await call_next(request)
    return response
```

### 2. Data Isolation Strategy

**Row-Level Security (RLS):**
```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;

-- Policy: Users see only their organization's data
CREATE POLICY org_isolation ON organization_members
  FOR ALL
  USING (organization_id = current_setting('app.current_tenant_id')::uuid);

-- Force RLS for all roles except superuser
ALTER TABLE organization_members FORCE ROW LEVEL SECURITY;
```

**Application-Level Filtering:**
```python
def get_users(db: Session, tenant_id: UUID) -> list[User]:
    return db.query(User).filter(
        OrganizationMember.organization_id == tenant_id,
        OrganizationMember.user_id == User.id
    ).all()
```

### 3. Tenant Hierarchy

```
Organization (Tenant)
├── Owner (User with owner role)
├── Members (Users with various roles)
│   ├── admin
│   ├── member
│   └── viewer
├── Custom Roles
├── Invitations
├── Policies
├── Webhooks
└── Settings
    ├── MFA Requirements
    ├── Password Policy
    ├── Session Timeout
    └── Allowed OAuth Providers
```

### 4. Cross-Tenant User Support

Users can belong to multiple organizations:

```
User (alice@example.com)
├── Organization A: admin
├── Organization B: member
└── Organization C: viewer
```

**Organization Switching:**
1. User authenticates with email/password
2. Token contains list of organizations
3. User selects active organization
4. Subsequent requests scoped to selected org

```json
// JWT payload after org selection
{
  "sub": "usr_abc123",
  "org": "org_selected",
  "orgs": ["org_a", "org_b", "org_c"],
  "role": "admin"
}
```

### 5. Tenant-Specific Rate Limiting

Rate limits applied per-tenant based on plan:

```python
TENANT_LIMITS = {
    "community": 100,    # requests/minute
    "pro": 1000,
    "scale": 5000,
    "enterprise": 10000
}

async def get_tenant_limit(tenant_id: str) -> int:
    plan = await redis.get(f"tenant:plan:{tenant_id}")
    return TENANT_LIMITS.get(plan, 100)
```

### 6. Tenant Provisioning

**Organization Creation Flow:**
1. User creates organization
2. System assigns unique `slug` and `id`
3. Creator becomes `owner`
4. Default settings applied
5. Billing record initialized

```python
async def create_organization(user_id: UUID, name: str) -> Organization:
    org = Organization(
        name=name,
        slug=generate_slug(name),
        owner_id=user_id,
        billing_plan="free",
        settings={
            "mfa_required": False,
            "password_min_length": 8,
            "session_timeout_hours": 24
        }
    )
    db.add(org)

    # Make creator the owner
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user_id,
        role="owner"
    )
    db.add(member)

    await db.commit()
    return org
```

## Alternatives Considered

### Alternative 1: Database-per-Tenant (Rejected)

**Pros:**
- Complete isolation
- Easy compliance (data locality)
- No RLS complexity

**Cons:**
- Connection pool explosion at scale
- Complex migrations
- Higher infrastructure cost

**Decision:** Shared database with RLS provides sufficient isolation at lower cost.

### Alternative 2: Schema-per-Tenant (Rejected)

**Pros:**
- Better isolation than row-level
- Easier backup/restore per tenant

**Cons:**
- Schema migration complexity
- Connection management issues
- PostgreSQL doesn't handle thousands of schemas well

**Decision:** Row-level approach scales better with our expected tenant count.

### Alternative 3: Microservice-per-Tenant (Rejected)

**Pros:**
- Maximum isolation
- Independent scaling
- Custom deployments

**Cons:**
- Massive operational overhead
- Cost prohibitive
- Complexity explosion

**Decision:** Single deployment with tenant isolation is more practical.

## Consequences

### Positive

1. **Cost Efficiency**: Single database, single deployment
2. **Operational Simplicity**: One codebase to maintain
3. **Scalability**: Can support thousands of tenants
4. **Performance**: Shared connection pool, optimized queries
5. **Feature Parity**: All tenants get same features (plan-gated)

### Negative

1. **Noisy Neighbor Risk**: One tenant's heavy usage could affect others
2. **Data Proximity**: All tenant data in same database
3. **Complexity**: RLS and context propagation add code complexity

### Mitigations

1. **Noisy Neighbor**: Per-tenant rate limiting, resource quotas
2. **Data Proximity**: Encryption at rest, strict access controls
3. **Complexity**: Shared utilities, comprehensive testing

## Security Considerations

1. **Query Injection**: All tenant IDs validated as UUIDs
2. **Context Leakage**: Request-scoped context variables
3. **Cross-Tenant Access**: Comprehensive authorization checks
4. **Audit Trail**: All cross-tenant operations logged

## Related Documentation

- [Authentication Flow ADR](./ADR-001_AUTH_FLOW.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [Rate Limiting](/docs/api/RATE_LIMITING.md)
- [Security Guidelines](/docs/security/SECURITY.md)
