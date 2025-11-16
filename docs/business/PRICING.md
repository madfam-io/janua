# Plinto Pricing & Feature Matrix

**Pricing Philosophy**: All authentication features are free and open source. Paid tiers provide managed hosting, enterprise support, compliance, and scale.

## Pricing Tiers

### 🆓 Community Edition (Open Source)
**Price**: Free forever
**Target**: Individuals, startups, open source projects, self-hosters

#### All Authentication Features Included:
- ✅ **Complete Authentication**
  - Email/password authentication
  - Social login (Google, GitHub, Microsoft, Apple)
  - Magic links (passwordless)
  - User registration and management
  - Password reset and email verification

- ✅ **Multi-Factor Authentication (MFA)** - **ALL TYPES**
  - TOTP (Google Authenticator, Authy)
  - SMS authentication
  - **WebAuthn/Passkeys** (hardware security keys, biometric)
  - Backup codes
  - Device trust

- ✅ **Multi-Tenancy & Organizations**
  - **Unlimited organizations**
  - Team management
  - Role-based access control (RBAC)
  - Custom roles and permissions

- ✅ **Enterprise SSO**
  - **SAML 2.0**
  - **OpenID Connect (OIDC)**
  - Custom identity providers

- ✅ **Developer Tools**
  - REST API
  - SDKs (React, Vue, Next.js, Flutter, Python, Go)
  - Webhooks (unlimited)
  - API keys (unlimited)

- ✅ **Self-Hosting**
  - Full source code access (MIT license)
  - Docker & Kubernetes deployment
  - Complete control over data
  - No vendor lock-in

#### Community Limits:
- **Self-hosted only** (you manage infrastructure)
- Community support (GitHub issues, forum, docs)
- No SLA guarantees
- No managed compliance reports

---

### 💼 Professional (Managed Cloud)
**Price**: $99/month or $990/year (2 months free)
**Target**: Growing businesses who want managed hosting

#### Everything in Community, plus:

- ✅ **Managed Cloud Hosting**
  - No infrastructure management required
  - Automatic updates and patches
  - Multi-region deployment
  - 99.9% uptime SLA

- ✅ **Enhanced Infrastructure**
  - Custom domains with SSL
  - CDN acceleration
  - DDoS protection
  - Automated backups (daily)

- ✅ **Advanced Analytics**
  - User analytics dashboard
  - Authentication metrics
  - Security insights
  - Custom reports

- ✅ **Priority Support**
  - Email support (24h response)
  - Priority bug fixes
  - Migration assistance
  - Slack/Discord support channel

- ✅ **Compliance Assistance**
  - GDPR compliance tools
  - Data export automation
  - 30-day audit log retention
  - Basic compliance reports

#### Professional Limits:
- 10,000 monthly active users (MAU)
- 10 organizations
- 10,000 API requests/hour
- Shared cloud infrastructure

---

### 🏢 Enterprise
**Price**: Custom pricing (contact sales)
**Target**: Large organizations requiring compliance, dedicated infrastructure, SLA

#### Everything in Professional, plus:

- ✅ **Dedicated Infrastructure**
  - **On-premise deployment** (your infrastructure)
  - **Private cloud deployment** (dedicated VPC)
  - Multi-region replication
  - Custom architecture design
  - Custom SLA (up to 99.99%)

- ✅ **Advanced Security & Compliance**
  - **Unlimited audit log retention**
  - SOC 2 Type II reports
  - HIPAA compliance assistance
  - Data residency options (EU, US, APAC)
  - Advanced threat detection
  - Security compliance reports

- ✅ **Advanced Team Management**
  - Unlimited custom roles
  - Fine-grained permissions
  - Attribute-based access control (ABAC)
  - Advanced RBAC policies

- ✅ **White Labeling**
  - Complete UI customization
  - Custom branding
  - Private labeling options
  - Remove Plinto branding

- ✅ **Premium Support**
  - Dedicated account manager
  - 24/7 phone & email support
  - Custom integration support
  - Professional services
  - Training and onboarding

- ✅ **Enterprise Features**
  - Custom rate limits
  - Advanced monitoring and alerts
  - Custom integrations
  - API priority access

#### Enterprise Limits:
- **Unlimited** users
- **Unlimited** organizations
- **Unlimited** API requests
- **Custom** infrastructure and rate limits

---

## Feature Comparison Matrix

| Feature | Community (Self-Hosted) | Professional (Managed) | Enterprise |
|---------|-------------------------|------------------------|------------|
| **Authentication** |
| Email/Password | ✅ | ✅ | ✅ |
| Social Login | ✅ | ✅ | ✅ |
| Magic Links | ✅ | ✅ | ✅ |
| **MFA - ALL TYPES** | ✅ | ✅ | ✅ |
| MFA (TOTP) | ✅ | ✅ | ✅ |
| MFA (SMS) | ✅ | ✅ | ✅ |
| **WebAuthn/Passkeys** | ✅ | ✅ | ✅ |
| **SSO (SAML)** | ✅ | ✅ | ✅ |
| **SSO (OIDC)** | ✅ | ✅ | ✅ |
| **User Management** |
| User Profiles | ✅ | ✅ | ✅ |
| User Search | ✅ | ✅ | ✅ |
| Bulk Operations | ✅ | ✅ | ✅ |
| Custom Attributes | ✅ | ✅ | ✅ |
| **Organizations** |
| Multi-tenancy | ✅ | ✅ | ✅ |
| Team Management | ✅ | ✅ | ✅ |
| Custom Roles | ✅ | ✅ | ✅ |
| ABAC | ✅ | ✅ | ✅ |
| **Security** |
| Rate Limiting | ✅ (self-config) | ✅ | Custom |
| IP Allowlisting | ✅ | ✅ | ✅ |
| Audit Logs | ✅ (self-managed) | 30 days | Unlimited |
| Session Management | ✅ | ✅ | ✅ |
| Device Trust | ✅ | ✅ | ✅ |
| **Compliance** |
| GDPR Tools | ✅ | ✅ | ✅ |
| SOC 2 Reports | ❌ | ❌ | ✅ |
| HIPAA Assistance | ❌ | ❌ | ✅ |
| Data Residency | Self-managed | ❌ | ✅ |
| **Developer Tools** |
| REST API | ✅ | ✅ | ✅ |
| SDKs | ✅ | ✅ | ✅ |
| Webhooks | ✅ (unlimited) | ✅ (unlimited) | ✅ (unlimited) |
| API Keys | ✅ (unlimited) | ✅ (unlimited) | ✅ (unlimited) |
| Rate Limits | Self-managed | 10K/hour | Custom |
| **Infrastructure** |
| **Self-Hosting** | ✅ | ✅ (+ managed) | ✅ (+ dedicated) |
| Cloud Hosting | Self-managed | Shared | Dedicated |
| On-Premise | ✅ | ❌ | ✅ |
| Multi-Region | Self-managed | ✅ | ✅ |
| Custom Domain | Self-config | ✅ | ✅ |
| White Label | ✅ (OSS) | Partial | ✅ |
| **Support & SLA** |
| Documentation | ✅ | ✅ | ✅ |
| Community Forum | ✅ | ✅ | ✅ |
| Email Support | ❌ | 24h | Priority |
| Phone Support | ❌ | ❌ | 24/7 |
| Dedicated Manager | ❌ | ❌ | ✅ |
| SLA | ❌ | 99.9% | Custom (up to 99.99%) |

---

## Add-Ons (Professional & Enterprise)

### 📊 Advanced Analytics
**Price**: $49/month
- Real-time dashboards
- Custom reports
- Data export (CSV, JSON)
- API analytics

### 📧 Email Add-on
**Price**: $29/month per 10,000 emails
- Transactional emails
- Custom templates
- Email analytics
- Dedicated IP

### 💾 Extended Data Retention
**Price**: $99/month per TB
- Extended audit logs
- Long-term user data
- Compliance archives

### 🌍 Additional Regions
**Price**: $199/month per region
- Data residency
- Low-latency access
- Regional compliance

---

## Frequently Asked Questions

### Can I switch plans?
Yes, you can upgrade or downgrade at any time. Upgrades are instant, downgrades take effect at the next billing cycle.

### Is there a free trial for paid plans?
Yes, Professional plan includes a 14-day free trial. Enterprise plans include POC periods.

### What happens if I exceed my limits?
- **Community**: API calls are rate-limited
- **Professional**: Soft limits with notifications
- **Enterprise**: Custom handling based on agreement

### Can I self-host the Community Edition?
Yes, the Community Edition can be self-hosted. See our [deployment guide](./DEPLOYMENT.md).

### Do you offer discounts?
- **Nonprofits**: 50% discount on Professional
- **Education**: 80% discount on Professional
- **Startups**: Special programs available
- **Annual billing**: Save 2 months

### What payment methods do you accept?
- Credit/debit cards (Stripe)
- ACH transfers (Professional+)
- Wire transfers (Enterprise)
- Invoicing (Enterprise)

### How is user count calculated?
Monthly Active Users (MAU) - unique users who authenticate at least once per month.

### Can I get a custom plan?
Yes, contact sales@plinto.dev for custom requirements.

---

## Contact Sales

For Enterprise inquiries or custom requirements:
- 📧 Email: sales@plinto.dev
- 🌐 Website: https://plinto.dev/contact
- 📅 Book a demo: https://plinto.dev/demo

---

## License Terms

- **Community**: MIT License (open source)
- **Professional**: Commercial License
- **Enterprise**: Custom Enterprise Agreement

See [LICENSE](./LICENSE) for Community Edition terms.