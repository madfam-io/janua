# Plinto Documentation Hub

> **Complete documentation for the Plinto identity platform**

## 🚀 Quick Start

- **[Development Guide](../DEVELOPMENT.md)** - Complete guide for developers
- **[Troubleshooting Guide](./TROUBLESHOOTING.md)** - Solutions for common issues
- **[API Reference](./reference/API_SPECIFICATION.md)** - Complete API documentation

## 📚 Documentation Structure

### Development
- **[Development Guide](../DEVELOPMENT.md)** - Setup, workflow, and best practices
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Common issues and solutions
- **[Testing Strategy](./technical/testing-strategy.md)** - Testing approach and coverage
- **[Code Style Guide](./development/code-style.md)** - Coding standards and conventions

### Architecture
- **[System Architecture](./architecture/ARCHITECTURE.md)** - Overall system design
- **[API Structure](./architecture/API_STRUCTURE.md)** - API design and patterns
- **[Database Design](./technical/DATABASE_DESIGN.md)** - Schema and data model
- **[Subdomain Architecture](./architecture/SUBDOMAIN_ARCHITECTURE.md)** - Multi-tenant design

### Deployment
- **[Deployment Guide](./deployment/DEPLOYMENT.md)** - Production deployment
- **[Vercel Setup](./deployment/VERCEL_SETUP.md)** - Frontend deployment
- **[Railway Deployment](./operations/RAILWAY_DEPLOYMENT.md)** - API deployment
- **[Monitoring Setup](./deployment/MONITORING_SETUP.md)** - Observability configuration

### Enterprise Features
- **[Enterprise Roadmap](./enterprise/ENTERPRISE_FEATURES_ROADMAP.md)** - Enterprise feature plans
- **[SSO Integration](./enterprise/sso-integration-guide.md)** - SAML/OIDC setup
- **[Admin Portal](./enterprise/admin-portal-guide.md)** - Admin panel features
- **[Audit & Compliance](./enterprise/audit-compliance-guide.md)** - Compliance features
- **[White Label](./enterprise/white-label-branding.md)** - Customization options

### Operations
- **[Production Readiness](./operations/PRODUCTION_READINESS_REPORT.md)** - Production checklist
- **[Incident Response](./operations/INCIDENT_RESPONSE_PLAYBOOK.md)** - Incident handling
- **[Monitoring Guide](./operations/README.md)** - Operational monitoring

### API & SDKs
- **[API Specification](./reference/API_SPECIFICATION.md)** - OpenAPI specification
- **[Public Documentation Portal](../apps/docs/README.md)** - User-facing docs at docs.plinto.dev

#### Available SDKs (in packages/)
- **[TypeScript SDK](../packages/typescript-sdk/)** - JavaScript/TypeScript SDK
- **[React SDK](../packages/react/)** - React components and hooks
- **[Python SDK](../packages/python-sdk/)** - Python client library
- **[Go SDK](../packages/go-sdk/)** - Go client library
- **[React Native SDK](../packages/react-native-sdk/)** - Mobile SDK
- **[Next.js SDK](../packages/nextjs-sdk/)** - Next.js integration
- **[Vue SDK](../packages/vue-sdk/)** - Vue.js integration
- **[Flutter SDK](../packages/flutter-sdk/)** - Flutter mobile SDK

### User Documentation
For quick start guides and tutorials, see the **[Public Documentation](https://docs.plinto.dev)** or run locally:
```bash
cd apps/docs && yarn dev
```

### Reports & Analysis
- **[Security Assessment](./SECURITY_ASSESSMENT_REPORT.md)** - Security audit results
- **[Test Coverage](./testing/TEST_COVERAGE_REPORT.md)** - Testing metrics
- **[Codebase Metrics](./reports/CODEBASE_METRICS.md)** - Code quality metrics
- **[Production Status](./production/PRODUCTION_STATUS_REPORT.md)** - Production readiness

## 🔍 Finding Information

### By Role

#### For Developers
1. Start with [Development Guide](../DEVELOPMENT.md)
2. Review [Architecture](./architecture/ARCHITECTURE.md)
3. Check [API Reference](./reference/API_SPECIFICATION.md)
4. Use [Troubleshooting Guide](./TROUBLESHOOTING.md) when stuck

#### For DevOps/SRE
1. Review [Deployment Guide](./deployment/DEPLOYMENT.md)
2. Set up [Monitoring](./deployment/MONITORING_SETUP.md)
3. Prepare [Incident Response](./operations/INCIDENT_RESPONSE_PLAYBOOK.md)
4. Check [Production Readiness](./operations/PRODUCTION_READINESS_REPORT.md)

#### For Product/Business
1. Review [Enterprise Features](./enterprise/ENTERPRISE_FEATURES_ROADMAP.md)
2. Understand [Business Development](./business/BIZ_DEV.md)
3. Check [Production Status](./production/PRODUCTION_STATUS_REPORT.md)

#### For Security Teams
1. Review [Security Assessment](./SECURITY_ASSESSMENT_REPORT.md)
2. Check [Audit & Compliance](./enterprise/audit-compliance-guide.md)
3. Understand [Zero Trust Architecture](./enterprise/zero-trust-architecture.md)

## 📝 Documentation Standards

### File Naming
- Use UPPERCASE for important documents (README.md, CONTRIBUTING.md)
- Use kebab-case for guides (quick-start-guide.md)
- Use descriptive names that indicate content

### Content Structure
1. **Title**: Clear, descriptive H1
2. **Description**: Brief overview blockquote
3. **Table of Contents**: For documents > 500 words
4. **Sections**: Logical grouping with H2/H3
5. **Code Examples**: Practical, runnable examples
6. **Troubleshooting**: Common issues and solutions

### Markdown Standards
- Use GitHub Flavored Markdown
- Include syntax highlighting for code blocks
- Use tables for structured data
- Add diagrams where helpful (Mermaid supported)

## 🤝 Contributing to Docs

### How to Contribute
1. Find an area that needs documentation
2. Follow our documentation standards
3. Submit a PR with your changes
4. Tag relevant reviewers

### Priority Areas
- SDK usage examples
- Integration tutorials
- Troubleshooting scenarios
- Architecture decisions
- Performance optimization

## 📊 Documentation Coverage

| Area | Coverage | Status |
|------|----------|--------|
| API Reference | 95% | ✅ Complete |
| Architecture | 90% | ✅ Complete |
| Development | 85% | ✅ Complete |
| Deployment | 90% | ✅ Complete |
| SDKs | 70% | 🚧 In Progress |
| Troubleshooting | 85% | ✅ Complete |
| Enterprise | 80% | ✅ Complete |
| Operations | 85% | ✅ Complete |

## 🔗 External Resources

- **[Next.js Documentation](https://nextjs.org/docs)** - Framework documentation
- **[NestJS Documentation](https://docs.nestjs.com)** - API framework
- **[Turborepo Documentation](https://turbo.build/repo/docs)** - Monorepo management
- **[Radix UI Documentation](https://www.radix-ui.com/docs)** - UI components
- **[WebAuthn Guide](https://webauthn.guide)** - Passkey implementation

## 📞 Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **Discord**: Community support and discussions
- **Email**: dev-support@plinto.dev
- **Documentation Issues**: Open an issue with `docs` label

---

*Last updated: January 2025*