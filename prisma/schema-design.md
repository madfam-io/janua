# Database Schema Design Documentation

## Overview

This PostgreSQL schema is designed to support a comprehensive multi-tenant SaaS platform with advanced security, billing, and user management features. The schema implements the requirements analyzed from the existing services in `packages/core/src/services/`.

## Key Design Decisions

### 1. Multi-Tenancy Strategy

**Approach**: Hybrid tenant isolation with configurable levels
- **Shared**: Single database with `tenant_id` columns (Row-Level Security)
- **Semi-isolated**: Dedicated schemas per tenant within shared database
- **Fully-isolated**: Dedicated databases per tenant

**Implementation**:
```sql
-- Tenant model includes isolation configuration
model Tenant {
  isolation_level       String   @default("shared") // shared, semi-isolated, fully-isolated
  database_host         String?
  database_port         Int?
  database_name         String?
  database_schema       String?
}
```

**Benefits**:
- Flexible isolation based on customer tier
- Cost-effective for small tenants (shared)
- Enhanced security for enterprise customers (isolated)
- Seamless migration between isolation levels

### 2. User Management & Authentication

**Multi-Factor Authentication**:
- Separate `MfaMethod` model supports multiple MFA types per user
- Flexible TOTP, SMS, email, WebAuthn, and hardware token support
- Backup and recovery codes stored securely

**WebAuthn/Passkeys**:
- Full WebAuthn support with credential tracking
- Device type classification and backup status
- Counter tracking for replay attack prevention

**Session Management**:
- Comprehensive session tracking with device fingerprinting
- Refresh token rotation with family tracking
- Anomaly detection capabilities built into the schema

### 3. Role-Based Access Control (RBAC)

**Hierarchical Roles**:
```sql
model Role {
  parent_role_id   String?
  parent_role      Role?    @relation("RoleHierarchy", fields: [parent_role_id], references: [id])
  child_roles      Role[]   @relation("RoleHierarchy")
}
```

**Flexible Permissions**:
- JSON-stored permissions with conditions
- Scope-based assignments (organization, team, project, resource)
- Policy documents for complex authorization rules

**Assignment Tracking**:
- Temporal assignments with expiration
- Comprehensive audit trail
- Support for users, teams, and service accounts

### 4. Team Management

**Hierarchical Teams**:
- Self-referencing relationship for team hierarchies
- Unlimited nesting depth support
- Efficient querying with proper indexing

**Flexible Membership**:
- Role-based team membership
- Custom permissions per member
- Invitation system with token-based acceptance

### 5. Payment & Billing

**Multi-Provider Support**:
```sql
model PaymentCustomer {
  stripe_customer_id  String?
  conekta_customer_id String?
  fungies_customer_id String?
}
```

**Subscription Management**:
- Full subscription lifecycle support
- Trial management
- Proration and quantity changes
- Discount and coupon support

**Usage Tracking**:
- Granular usage recording
- Aggregation-friendly design
- Billing alert system

### 6. Audit & Compliance

**Comprehensive Audit Trail**:
- Every significant action logged
- Risk scoring and compliance flags
- Session and request correlation
- Immutable audit records

**Performance Optimized**:
- Composite indexes for common query patterns
- Partitioning-ready design (by timestamp)
- Efficient storage of JSON details

### 7. Security Features

**Session Security**:
- Device fingerprinting
- Anomaly detection data structures
- Geographic and velocity tracking
- Risk-based authentication flags

**Data Protection**:
- Sensitive data identified and properly typed
- Foreign key constraints for data integrity
- Cascade deletes for tenant isolation
- Soft delete capabilities where needed

## Performance Considerations

### 1. Indexing Strategy

**Primary Indexes**:
- All foreign keys indexed
- Timestamp columns for audit and session tables
- Status and state columns for filtering

**Composite Indexes**:
```sql
@@index([tenant_id, timestamp])    -- Tenant-scoped queries
@@index([user_id, created_at])     -- User activity tracking
@@index([resource_type, outcome])  -- Audit analysis
```

### 2. Query Optimization

**Tenant Isolation**:
- All tenant-scoped queries include `tenant_id` in WHERE clause
- Composite indexes start with `tenant_id` for isolation

**Audit Log Partitioning**:
- Ready for PostgreSQL partitioning by timestamp
- Indexes support both recent and historical data access

### 3. Data Types

**Optimized Storage**:
- `BigInt` for counters that may overflow
- `Float` for calculated values like risk scores
- `Json` for flexible metadata and configuration
- Proper string lengths based on actual usage

## Scalability Features

### 1. Horizontal Scaling

**Tenant Sharding**:
- Schema supports distributing tenants across databases
- Configuration stored in tenant record
- Application-level routing supported

### 2. Read Replicas

**Query Distribution**:
- Audit logs optimized for read-heavy workloads
- Session data can be cached/replicated
- Billing data separated for reporting

### 3. Archival Strategy

**Data Lifecycle**:
- Audit logs can be archived by date
- Session data has natural expiration
- Usage records support time-based retention

## Security Implementation

### 1. Row-Level Security (RLS)

**Tenant Isolation**:
```sql
-- Example RLS policy for shared tenancy
CREATE POLICY tenant_isolation ON users
    FOR ALL TO app_role
    USING (tenant_id = current_setting('app.current_tenant'));
```

### 2. Data Encryption

**Sensitive Fields**:
- MFA secrets encrypted at application level
- Password hashes use strong algorithms
- API keys stored as hashes with prefixes

### 3. Audit Compliance

**Immutable Logs**:
- Audit logs use checksums for integrity verification
- No UPDATE permissions on audit tables
- Proper retention and archival policies

## Migration Considerations

### 1. Zero-Downtime Deployments

**Schema Evolution**:
- Nullable columns for gradual rollouts
- Backward-compatible changes
- Feature flags for new functionality

### 2. Data Migration

**Tenant Onboarding**:
- Bulk import capabilities
- Data validation and cleanup
- Rollback procedures

### 3. Performance Testing

**Load Testing**:
- Index effectiveness under load
- Query performance optimization
- Connection pooling considerations

## Monitoring & Observability

### 1. Performance Metrics

**Query Performance**:
- Slow query identification
- Index usage statistics
- Connection pool metrics

### 2. Security Monitoring

**Anomaly Detection**:
- Failed authentication tracking
- Unusual access patterns
- Risk score trending

### 3. Business Metrics

**Usage Analytics**:
- Feature adoption tracking
- Billing metric calculations
- User engagement patterns

## Compliance Support

### 1. GDPR Compliance

**Data Subject Rights**:
- User data identification and export
- Right to erasure implementation
- Consent tracking capabilities

### 2. SOX Compliance

**Financial Controls**:
- Immutable audit trails
- Billing data integrity
- Access control documentation

### 3. HIPAA Compliance

**Data Security**:
- Encryption at rest and in transit
- Access logging and monitoring
- Data retention policies

## Future Enhancements

### 1. Advanced Features

**Machine Learning**:
- Risk scoring improvements
- Anomaly detection enhancement
- Usage prediction models

### 2. Integration Capabilities

**Third-party Systems**:
- SSO provider support
- External audit systems
- Business intelligence tools

### 3. Performance Optimizations

**Caching Strategies**:
- Redis integration for sessions
- Materialized views for reporting
- Event sourcing for audit logs

This schema provides a solid foundation for a production-ready multi-tenant SaaS platform with enterprise-grade security, compliance, and scalability features.