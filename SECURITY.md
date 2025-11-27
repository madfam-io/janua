# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of Janua seriously. As an OAuth 2.0 / OIDC authentication provider, security is our top priority.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **security@madfam.io**

Include the following information:
- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the issue
- Location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution Target**: Within 30 days for critical issues

### What to Expect

1. **Acknowledgment**: We'll confirm receipt of your report
2. **Assessment**: Our security team will assess the vulnerability
3. **Communication**: We'll keep you informed of our progress
4. **Resolution**: We'll work on a fix and coordinate disclosure
5. **Credit**: With your permission, we'll credit you in the release notes

## Security Best Practices for Janua Users

### Token Security
- Store tokens securely (use httpOnly cookies where possible)
- Implement token rotation
- Use short-lived access tokens with refresh tokens

### OIDC Configuration
- Always validate `iss` (issuer) claims
- Verify `aud` (audience) claims match your client ID
- Check token expiration (`exp` claim)

### Deployment Security
- Always use HTTPS in production
- Configure proper CORS policies
- Enable rate limiting on authentication endpoints
- Use secure session storage (Redis with TLS)

## Security Features

Janua includes the following security features:
- PKCE support for public clients
- Token binding
- Refresh token rotation
- Session management and revocation
- Brute force protection
- Audit logging

## Compliance

Janua is designed to help you meet:
- OAuth 2.0 Security Best Current Practice (RFC 6819)
- OpenID Connect Core 1.0
- OWASP Authentication Guidelines
