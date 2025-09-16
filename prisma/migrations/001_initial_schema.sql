-- Initial schema migration for Plinto multi-tenant platform
-- This migration creates all the core tables and indexes

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Create custom types
CREATE TYPE tenant_isolation_level AS ENUM ('shared', 'semi-isolated', 'fully-isolated');
CREATE TYPE tenant_status AS ENUM ('active', 'suspended', 'deleted');
CREATE TYPE user_status AS ENUM ('active', 'suspended', 'pending_verification', 'deleted');
CREATE TYPE mfa_method AS ENUM ('totp', 'sms', 'email', 'webauthn', 'hardware_token');
CREATE TYPE payment_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded');
CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'past_due', 'trialing', 'paused');
CREATE TYPE billing_interval AS ENUM ('month', 'year', 'week', 'day');
CREATE TYPE audit_risk_level AS ENUM ('low', 'medium', 'high', 'critical');

-- Create RLS policies function
CREATE OR REPLACE FUNCTION get_current_tenant_id() RETURNS TEXT AS $$
BEGIN
  RETURN current_setting('app.current_tenant_id', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Main tables creation (Prisma will handle this, but this is for reference)
-- The actual table creation will be done by Prisma generate and migrate

-- Create indexes for performance
-- These will be added after Prisma creates the base tables

-- Performance indexes for tenant queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_slug ON "Tenant" (slug);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_domain ON "Tenant" (domain) WHERE domain IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_status ON "Tenant" (status);

-- User performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_email ON "User" (email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_tenant_status ON "User" (tenant_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_created_at ON "User" (created_at);

-- Session performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_token ON "Session" (token);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_user_active ON "Session" (user_id, expires_at) WHERE revoked_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_device ON "Session" (device_fingerprint);

-- Team and role indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_team_tenant ON "Team" (tenant_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_team_parent ON "Team" (parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_role_assignment_user ON "RoleAssignment" (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_role_assignment_scope ON "RoleAssignment" (scope_type, scope_id);

-- Payment and billing indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payment_tenant_status ON "Payment" (tenant_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payment_provider ON "Payment" (provider, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subscription_tenant_status ON "Subscription" (tenant_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_tenant_due ON "Invoice" (tenant_id, due_date);

-- Audit and monitoring indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_tenant_timestamp ON "AuditLog" (tenant_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_user_action ON "AuditLog" (user_id, action);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_risk_level ON "AuditLog" (risk_level);

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_tenant_email ON "User" (tenant_id, email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_user_expires ON "Session" (user_id, expires_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payment_tenant_created ON "Payment" (tenant_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_team_tenant_status ON "Team" (tenant_id, status);

-- Text search indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_name_search ON "Tenant" USING gin(name gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_name_search ON "User" USING gin((first_name || ' ' || last_name) gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_team_name_search ON "Team" USING gin(name gin_trgm_ops);

-- Row Level Security (RLS) setup for shared tenancy
ALTER TABLE "Tenant" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "User" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Team" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Session" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "RoleAssignment" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Payment" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Subscription" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Invoice" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "AuditLog" ENABLE ROW LEVEL SECURITY;

-- RLS policies for tenant isolation
CREATE POLICY tenant_isolation_policy ON "User"
  FOR ALL USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_policy ON "Team"
  FOR ALL USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_policy ON "Session"
  FOR ALL USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_policy ON "RoleAssignment"
  FOR ALL USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_policy ON "Payment"
  FOR ALL USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_policy ON "Subscription"
  FOR ALL USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_policy ON "Invoice"
  FOR ALL USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_policy ON "AuditLog"
  FOR ALL USING (tenant_id = get_current_tenant_id());

-- Functions for trigger-based audit logging
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO "AuditLog" (
      tenant_id, user_id, action, resource_type, resource_id,
      old_values, new_values, ip_address, user_agent, risk_level
    ) VALUES (
      NEW.tenant_id,
      current_setting('app.current_user_id', true)::TEXT,
      'CREATE',
      TG_TABLE_NAME,
      NEW.id,
      '{}',
      to_jsonb(NEW),
      current_setting('app.current_ip', true),
      current_setting('app.current_user_agent', true),
      'low'
    );
    RETURN NEW;
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO "AuditLog" (
      tenant_id, user_id, action, resource_type, resource_id,
      old_values, new_values, ip_address, user_agent, risk_level
    ) VALUES (
      NEW.tenant_id,
      current_setting('app.current_user_id', true)::TEXT,
      'UPDATE',
      TG_TABLE_NAME,
      NEW.id,
      to_jsonb(OLD),
      to_jsonb(NEW),
      current_setting('app.current_ip', true),
      current_setting('app.current_user_agent', true),
      'medium'
    );
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO "AuditLog" (
      tenant_id, user_id, action, resource_type, resource_id,
      old_values, new_values, ip_address, user_agent, risk_level
    ) VALUES (
      OLD.tenant_id,
      current_setting('app.current_user_id', true)::TEXT,
      'DELETE',
      TG_TABLE_NAME,
      OLD.id,
      to_jsonb(OLD),
      '{}',
      current_setting('app.current_ip', true),
      current_setting('app.current_user_agent', true),
      'high'
    );
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to key tables
CREATE TRIGGER audit_user_trigger
  AFTER INSERT OR UPDATE OR DELETE ON "User"
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_payment_trigger
  AFTER INSERT OR UPDATE OR DELETE ON "Payment"
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_subscription_trigger
  AFTER INSERT OR UPDATE OR DELETE ON "Subscription"
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Partitioning setup for audit logs (for future scaling)
CREATE OR REPLACE FUNCTION create_monthly_audit_partition(start_date DATE)
RETURNS VOID AS $$
DECLARE
  table_name TEXT;
  end_date DATE;
BEGIN
  table_name := 'AuditLog_' || TO_CHAR(start_date, 'YYYY_MM');
  end_date := start_date + INTERVAL '1 month';

  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS %I PARTITION OF "AuditLog"
     FOR VALUES FROM (%L) TO (%L)',
    table_name, start_date, end_date
  );

  EXECUTE format(
    'CREATE INDEX IF NOT EXISTS %I ON %I (tenant_id, created_at)',
    'idx_' || table_name || '_tenant_created', table_name
  );
END;
$$ LANGUAGE plpgsql;

-- Create current month partition
SELECT create_monthly_audit_partition(DATE_TRUNC('month', CURRENT_DATE));

-- Setup automatic partition creation
CREATE OR REPLACE FUNCTION create_next_month_partition()
RETURNS VOID AS $$
BEGIN
  PERFORM create_monthly_audit_partition(
    DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')
  );
END;
$$ LANGUAGE plpgsql;

-- Create extension for pg_cron if available (for automatic partition management)
-- This would typically be done by DBA in production
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('create-audit-partitions', '0 0 1 * *', 'SELECT create_next_month_partition();');

COMMIT;