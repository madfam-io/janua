# Plinto Database Schema

This directory contains the complete PostgreSQL database schema for Plinto, implemented using Prisma ORM. The schema supports enterprise-grade multi-tenancy, security, billing, and user management.

## Quick Start

### 1. Environment Setup

Copy the environment template and configure your database:

```bash
cp prisma/env.example .env
```

Update the database connection string and other required environment variables.

### 2. Database Setup

Run the complete database setup (recommended for new installations):

```bash
npm run db:setup
```

This command will:
- Generate and apply migrations
- Set up Row-Level Security (RLS)
- Create performance indexes
- Seed the database with initial data

### 3. Development Workflow

For ongoing development:

```bash
# Generate migration for schema changes
npm run db:migrate

# Apply migrations to production
npm run db:deploy

# Open Prisma Studio (visual database browser)
npm run db:studio

# Reset database (development only)
npm run db:reset
```

## Schema Overview

The database schema is organized into several key modules:

### 🏢 Multi-Tenancy
- **Tenants**: Organization isolation with configurable database strategy
- **Users**: Tenant-scoped user management with MFA support
- **Sessions**: Secure session management with anomaly detection

### 👥 Team Management
- **Teams**: Hierarchical team structure with unlimited nesting
- **TeamMembers**: Role-based team membership
- **TeamInvitations**: Token-based invitation system

### 🔐 Security & RBAC
- **Roles**: Hierarchical role system with custom permissions
- **RoleAssignments**: Flexible role assignment with scope and conditions
- **Policies**: Policy-based access control documents
- **MfaMethod**: Multi-factor authentication methods
- **Passkeys**: WebAuthn/FIDO2 passkey support

### 💳 Payment & Billing
- **PaymentCustomers**: Customer management across multiple providers
- **PaymentMethods**: Multi-provider payment method storage
- **PaymentIntents**: Payment processing with provider abstraction
- **BillingPlans**: Flexible subscription plan management
- **BillingSubscriptions**: Complete subscription lifecycle management

### 📊 Audit & Monitoring
- **AuditLogs**: Comprehensive audit trail with risk scoring
- **SessionAnomalyReports**: Security anomaly detection
- **UsageRecords**: Granular usage tracking for billing

## Key Features

### Multi-Tenancy Support

The schema supports three isolation levels:

1. **Shared**: Single database with Row-Level Security (RLS)
2. **Semi-isolated**: Dedicated schema per tenant
3. **Fully-isolated**: Dedicated database per tenant

```typescript
// Example: Create tenant with isolation level
const tenant = await prisma.tenant.create({
  data: {
    name: "Acme Corp",
    slug: "acme-corp",
    isolation_level: "shared", // or "semi-isolated" or "fully-isolated"
    features: {
      custom_domain: true,
      sso: true,
      advanced_security: true
    }
  }
})
```

### Row-Level Security (RLS)

For shared tenancy, RLS policies ensure data isolation:

```sql
-- Automatic tenant filtering
CREATE POLICY tenant_isolation_users ON users
    FOR ALL TO app_role
    USING (tenant_id = current_setting('app.current_tenant'));
```

### Session Security

Advanced session management with:
- Device fingerprinting
- Geographic anomaly detection
- Velocity-based impossible travel detection
- Refresh token rotation with family tracking

```typescript
// Example: Session with anomaly detection
const session = await sessionManager.createSession({
  user_id: "user_123",
  ip_address: "192.168.1.1",
  user_agent: "Mozilla/5.0...",
  location: {
    country: "US",
    latitude: 37.7749,
    longitude: -122.4194
  }
})
```

### Multi-Provider Payments

Support for multiple payment providers with intelligent routing:

```typescript
// Example: Multi-provider payment setup
const customer = await paymentGateway.createOrUpdateCustomer({
  email: "user@example.com",
  name: "John Doe",
  address: { country: "MX" }, // Routes to Conekta for Mexico
  organization_id: "org_123"
})
```

### Hierarchical RBAC

Flexible role-based access control with:
- Role inheritance
- Scope-based assignments
- Policy-based permissions
- Temporal assignments

```typescript
// Example: Assign role with scope
const assignment = await prisma.roleAssignment.create({
  data: {
    role_id: "admin_role",
    principal_type: "user",
    principal_id: "user_123",
    scope_type: "team",
    scope_id: "team_456",
    conditions: [
      { type: "time_range", start: "09:00", end: "17:00" }
    ]
  }
})
```

## Database Commands

### Development Commands

```bash
# Complete setup with all features
npm run db:setup

# Migration workflow
npm run db:migrate          # Create and apply migration
npm run db:deploy           # Deploy to production
npm run db:generate         # Generate Prisma client

# Database maintenance
npm run db:seed             # Seed with initial data
npm run db:reset            # Reset database (dev only)
npm run db:studio           # Open visual browser
```

### Advanced Commands

```bash
# Security setup
npm run db:rls              # Set up Row-Level Security

# Performance optimization
npm run db:indexes          # Create performance indexes

# Tenant provisioning
npm run db:tenant -- --tenant=acme-corp  # Provision tenant database
```

## Performance Optimization

### Indexing Strategy

The schema includes comprehensive indexing for:

- **Tenant isolation**: All tenant-scoped queries
- **User activity**: Authentication and session tracking
- **Audit analysis**: Risk assessment and compliance reporting
- **Billing operations**: Usage tracking and invoice generation

### Query Patterns

Common query patterns are optimized with composite indexes:

```sql
-- User session lookups
CREATE INDEX idx_sessions_user_active
ON sessions (user_id, is_active, expires_at DESC)
WHERE is_active = true;

-- Audit log analysis
CREATE INDEX idx_audit_logs_analysis
ON audit_logs (tenant_id, timestamp DESC, action, outcome);
```

### Scalability Features

- **Partitioning-ready**: Audit logs designed for time-based partitioning
- **Read replicas**: Optimized for read-heavy workloads
- **Connection pooling**: Efficient connection management
- **Caching integration**: Redis-compatible session storage

## Security Implementation

### Data Protection

- **Encryption**: Sensitive fields encrypted at application level
- **Password hashing**: Strong bcrypt with configurable rounds
- **API keys**: Stored as hashes with public prefixes
- **Audit integrity**: Checksums for immutable audit records

### Compliance Support

- **GDPR**: Data subject rights and consent tracking
- **SOX**: Immutable audit trails and financial controls
- **HIPAA**: Encryption and access logging
- **PCI DSS**: Payment data isolation and security

### Access Control

- **Row-Level Security**: Automatic tenant isolation
- **Role-based permissions**: Hierarchical RBAC system
- **Policy enforcement**: Attribute-based access control
- **Session security**: Anomaly detection and risk scoring

## Monitoring & Observability

### Audit Logging

Comprehensive audit trail includes:
- User actions and system events
- Risk scoring and compliance flags
- Session correlation and request tracking
- Immutable records with integrity verification

### Performance Monitoring

Built-in support for:
- Query performance tracking
- Connection pool metrics
- Index usage statistics
- Slow query identification

### Security Monitoring

Real-time security features:
- Failed authentication tracking
- Anomaly detection and alerting
- Risk score trending
- Suspicious activity patterns

## Migration Guide

### From Existing Systems

1. **Data Export**: Export existing data to CSV/JSON
2. **Schema Mapping**: Map existing fields to new schema
3. **Data Validation**: Validate and clean data
4. **Bulk Import**: Use Prisma client for efficient imports
5. **Verification**: Verify data integrity and relationships

### Version Upgrades

1. **Backup**: Always backup before migration
2. **Test**: Run migrations on staging environment
3. **Deploy**: Apply migrations with zero downtime strategy
4. **Verify**: Confirm application functionality
5. **Monitor**: Watch for performance impacts

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check DATABASE_URL format
   - Verify PostgreSQL is running
   - Confirm network connectivity

2. **Migration Failures**
   - Review migration SQL for conflicts
   - Check for data constraint violations
   - Ensure sufficient database permissions

3. **Performance Issues**
   - Analyze query execution plans
   - Check index usage statistics
   - Review connection pool settings

### Getting Help

1. Check the [schema design documentation](./schema-design.md)
2. Review Prisma logs for detailed error messages
3. Use `npm run db:studio` to inspect data visually
4. Consult the audit logs for security-related issues

## Contributing

When modifying the schema:

1. **Documentation**: Update this README and schema-design.md
2. **Backward Compatibility**: Ensure migrations are non-breaking
3. **Performance**: Add appropriate indexes for new queries
4. **Security**: Consider tenant isolation and access control
5. **Testing**: Test migrations on sample data

---

For detailed technical documentation, see [schema-design.md](./schema-design.md).