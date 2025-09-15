# Plinto Admin

> **Internal superadmin tools** for platform management

**Status:** Active Development · **Domain:** `admin.plinto.dev` · **Port:** 3004

## 📋 Overview

The Plinto Admin panel provides comprehensive administrative tools for platform operators, including user management, system monitoring, security controls, and compliance features. Built with enhanced security measures and restricted access patterns.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Yarn workspace management
- Admin credentials (restricted access)
- VPN/IP allowlist configuration (production)

### Installation

```bash
# From monorepo root
yarn install

# Navigate to admin app
cd apps/admin

# Start development server
yarn dev
```

Admin panel will be available at [http://localhost:3004](http://localhost:3004)

### Environment Setup

Create a `.env.local` file:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ADMIN_API_URL=http://localhost:8000/admin
NEXT_PUBLIC_APP_URL=http://localhost:3004

# Security
NEXT_PUBLIC_REQUIRE_MFA=true
NEXT_PUBLIC_SESSION_TIMEOUT=900000  # 15 minutes
ADMIN_SECRET_KEY=your-admin-secret-key

# Features
NEXT_PUBLIC_ENABLE_IMPERSONATION=true
NEXT_PUBLIC_ENABLE_SYSTEM_CONTROLS=true
NEXT_PUBLIC_ENABLE_AUDIT_LOGS=true

# Monitoring
NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn
NEXT_PUBLIC_DATADOG_RUM_KEY=your-datadog-key
```

## 🏗️ Architecture

### Project Structure

```
apps/admin/
├── app/                     # Next.js 14 App Router
│   ├── (auth)/             # Admin authentication
│   │   ├── login/          # Admin login with MFA
│   │   └── security/       # Security verification
│   ├── (admin)/            # Protected admin routes
│   │   ├── dashboard/      # Admin dashboard
│   │   ├── users/          # User management
│   │   ├── organizations/  # Org management
│   │   ├── security/       # Security center
│   │   ├── compliance/     # Compliance tools
│   │   ├── system/         # System controls
│   │   ├── audit/          # Audit logs
│   │   └── support/        # Support tools
│   ├── api/               # Admin API routes
│   └── layout.tsx         # Root layout with security
├── components/            # Admin components
│   ├── admin/            # Admin-specific UI
│   ├── security/         # Security components
│   └── charts/           # Analytics visualizations
├── lib/                  # Admin utilities
│   ├── auth/            # Admin auth logic
│   ├── security/        # Security utilities
│   ├── audit/           # Audit logging
│   └── permissions/     # RBAC logic
├── middleware.ts        # Security middleware
└── security/           # Security configurations
```

### Security Architecture

```
┌─────────────────────────────────────┐
│         Security Layers             │
├─────────────────────────────────────┤
│  1. IP Allowlist / VPN Required     │
│  2. Admin Authentication + MFA      │
│  3. Role-Based Access Control       │
│  4. Audit Logging (All Actions)     │
│  5. Session Management              │
│  6. CSP & Security Headers          │
└─────────────────────────────────────┘
```

## 🛡️ Security Features

### Authentication & Authorization

#### Multi-Factor Authentication (Required)
```tsx
// Enforced MFA for all admin users
const requireMFA = true;
const mfaMethods = ['totp', 'sms', 'hardware-key'];
```

#### Role-Based Access Control
```tsx
// lib/permissions/roles.ts
export const AdminRoles = {
  SUPER_ADMIN: 'super_admin',     // Full system access
  ADMIN: 'admin',                  // Standard admin access
  SUPPORT: 'support',              // Support team access
  COMPLIANCE: 'compliance',        // Compliance officer access
  SECURITY: 'security',            // Security team access
  READONLY: 'readonly',            // Audit/view only access
};
```

### Security Middleware

```tsx
// middleware.ts
export function middleware(request: NextRequest) {
  // IP allowlist check
  if (!isAllowedIP(request.ip)) {
    return new Response('Unauthorized', { status: 403 });
  }
  
  // Session validation
  if (!validateAdminSession(request)) {
    return NextResponse.redirect('/login');
  }
  
  // Audit logging
  logAdminAction(request);
  
  return NextResponse.next();
}
```

## 🎛️ Features

### Core Administrative Functions

#### 👥 User Management
- View all platform users
- Edit user profiles and permissions
- Suspend/activate accounts
- Reset passwords and MFA
- Impersonate users (with audit)
- Bulk user operations

#### 🏢 Organization Management
- Create/edit organizations
- Manage org subscriptions
- Set org limits and quotas
- Transfer ownership
- Org-level feature flags

#### 🔒 Security Center
- Security dashboard
- Threat detection alerts
- Failed login monitoring
- Suspicious activity tracking
- IP blocking/allowlisting
- Rate limit adjustments

#### 📊 System Monitoring
- Real-time system metrics
- API performance stats
- Database health
- Queue monitoring
- Error tracking
- Resource utilization

#### 📜 Compliance Tools
- GDPR data requests
- Data export/deletion
- Audit log search
- Compliance reports
- Policy enforcement
- Legal hold management

#### 🎯 Support Tools
- User impersonation
- Debug mode toggle
- Feature flag management
- Cache management
- Job queue management
- System announcements

## 🔍 Audit Logging

### Comprehensive Activity Tracking

```tsx
// Every admin action is logged
interface AuditLog {
  id: string;
  adminId: string;
  action: string;
  targetType: 'user' | 'org' | 'system';
  targetId: string;
  changes: Record<string, any>;
  ipAddress: string;
  userAgent: string;
  timestamp: Date;
  sessionId: string;
}
```

### Audit Log Viewer

```tsx
// components/admin/AuditLogViewer.tsx
export function AuditLogViewer() {
  return (
    <DataTable
      columns={auditColumns}
      data={auditLogs}
      searchable
      exportable
      filters={['action', 'admin', 'date']}
    />
  );
}
```

## 📊 Analytics & Monitoring

### Admin Dashboard Metrics

- **System Health**: Service status, uptime, response times
- **User Metrics**: Signups, active users, churn
- **Security Metrics**: Failed logins, threats blocked
- **Business Metrics**: Revenue, subscriptions, usage
- **Performance**: API latency, database queries, cache hit rates

### Real-time Monitoring

```tsx
// Real-time WebSocket connection for live updates
useEffect(() => {
  const ws = new WebSocket('wss://admin.plinto.dev/metrics');
  ws.onmessage = (event) => {
    updateDashboard(JSON.parse(event.data));
  };
}, []);
```

## 🧪 Testing

### Admin-Specific Tests

```bash
# Run admin tests
yarn test

# Security tests
yarn test:security

# Permission tests
yarn test:permissions

# E2E admin flows
yarn test:e2e:admin
```

## 🚢 Deployment

### Production Security Requirements

1. **Infrastructure**
   - Separate hosting environment
   - IP allowlisting configured
   - VPN access required
   - WAF protection enabled

2. **Environment Variables**
   - Rotate admin secrets regularly
   - Use secret management service
   - Separate from main app secrets

3. **Monitoring**
   - Enhanced logging
   - Real-time alerts
   - Anomaly detection
   - Session recording (for audits)

### Deployment Commands

```bash
# Build for production
yarn build

# Security audit before deployment
yarn audit:security

# Deploy to admin environment
yarn deploy:admin
```

## 🔐 Access Control

### Admin User Provisioning

```sql
-- Admin users require manual database provisioning
INSERT INTO admin_users (email, role, mfa_required)
VALUES ('admin@plinto.dev', 'super_admin', true);
```

### Session Management

- Sessions expire after 15 minutes of inactivity
- Concurrent session limit: 1 per admin
- Session recording for audit purposes
- Automatic logout on suspicious activity

## 🚨 Emergency Procedures

### System Controls

- **Emergency Shutdown**: Disable all user access
- **Rate Limit Override**: Adjust limits in real-time
- **Cache Flush**: Clear all caches immediately
- **Queue Pause**: Stop background job processing
- **Maintenance Mode**: Enable system-wide maintenance

### Incident Response

```tsx
// Quick actions for incident response
<EmergencyControls>
  <Button variant="danger" onClick={enableMaintenanceMode}>
    Enable Maintenance Mode
  </Button>
  <Button variant="danger" onClick={flushAllCaches}>
    Flush All Caches
  </Button>
  <Button variant="danger" onClick={pauseJobQueues}>
    Pause Job Queues
  </Button>
</EmergencyControls>
```

## 📈 Performance

### Optimization

- Server-side data fetching for sensitive operations
- Minimal client-side state for security
- Aggressive caching with proper invalidation
- Pagination for large datasets
- Virtual scrolling for long lists

## 🎨 UI Components

### Component Library

The admin panel uses **shadcn/ui** components built on top of **Radix UI** primitives for accessibility and **Tailwind CSS** for styling.

#### Available Components

```
components/ui/
├── alert.tsx         # Alert notifications
├── badge.tsx         # Status badges
├── button.tsx        # Button variants
├── card.tsx          # Card containers
├── input.tsx         # Form inputs
├── label.tsx         # Form labels
├── select.tsx        # Dropdown selects
├── switch.tsx        # Toggle switches
├── tabs.tsx          # Tab navigation
└── [more...]         # Additional components
```

#### Component Usage

```tsx
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function AdminPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>User Management</CardTitle>
      </CardHeader>
      <CardContent>
        <Badge variant="default">Active</Badge>
        <Button variant="destructive">Delete User</Button>
      </CardContent>
    </Card>
  );
}
```

#### Styling System

- **Tailwind CSS**: Utility-first styling
- **CSS Variables**: Theme customization via CSS custom properties
- **Dark Mode**: Built-in dark mode support
- **Responsive**: Mobile-first responsive design
- **Accessibility**: ARIA labels and keyboard navigation

## 🛠️ Development

### Local Development Security

```bash
# Use test admin credentials
ADMIN_EMAIL=admin@test.local
ADMIN_PASSWORD=test-admin-password

# Disable production security for local dev
NEXT_PUBLIC_SKIP_IP_CHECK=true
NEXT_PUBLIC_SKIP_MFA=true
```

### Code Standards

- All admin actions must be audited
- Sensitive data must be redacted in logs
- PII must be encrypted at rest
- Follow principle of least privilege

## 📚 Resources

- [Admin Security Guide](../../docs/security/admin-security.md)
- [Audit Log Specification](../../docs/admin/audit-spec.md)
- [Emergency Response Plan](../../docs/admin/emergency-response.md)
- [Admin Training Materials](../../docs/admin/training.md)

## ⚠️ Important Notes

- **Never** share admin credentials
- **Always** use MFA for admin accounts
- **Audit** all administrative actions
- **Report** suspicious activity immediately
- **Follow** the principle of least privilege

## 🤝 Contributing

Admin panel contributions require additional security review. See [Admin Contributing Guide](../../docs/admin/contributing.md).

## 📄 License

Part of the Plinto platform. See [LICENSE](../../LICENSE) in the root directory.