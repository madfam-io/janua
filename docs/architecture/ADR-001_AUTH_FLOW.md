# ADR-001: Authentication Flow Design

**Status**: Accepted
**Date**: 2024-01-25
**Deciders**: Janua Core Team
**Categories**: Security, Architecture

## Context

Janua needs a secure, scalable authentication system that supports:
- Email/password authentication
- OAuth/social login (Google, GitHub, Microsoft, etc.)
- Magic links (passwordless)
- Passkeys (WebAuthn/FIDO2)
- Multi-factor authentication (TOTP, SMS)
- Session management across devices
- Enterprise SSO (SAML, OIDC)

The system must balance security with user experience and support both web and mobile clients.

## Decision

We implement a **token-based authentication system** with the following characteristics:

### 1. Token Strategy: RS256 JWT with Refresh Tokens

**Access Tokens:**
- Algorithm: RS256 (RSA with SHA-256)
- Lifetime: 15 minutes
- Claims: `sub` (user_id), `org` (organization_id), `roles`, `jti` (token ID)
- Storage: Memory only (client-side)

**Refresh Tokens:**
- Algorithm: RS256
- Lifetime: 7 days (configurable)
- Stored in: Database (hashed) + httpOnly cookie
- Rotation: Required on each use (token family tracking)

```
┌──────────────────────────────────────────────────────────────────┐
│                    Authentication Flow                            │
└──────────────────────────────────────────────────────────────────┘

    ┌────────┐                    ┌────────┐                ┌─────────┐
    │ Client │                    │  API   │                │ Database│
    └───┬────┘                    └───┬────┘                └────┬────┘
        │                             │                          │
        │ POST /auth/signin           │                          │
        │ {email, password}           │                          │
        │────────────────────────────►│                          │
        │                             │ Verify credentials       │
        │                             │─────────────────────────►│
        │                             │◄─────────────────────────│
        │                             │                          │
        │                             │ Check MFA status         │
        │                             │─────────────────────────►│
        │                             │◄─────────────────────────│
        │                             │                          │
        │  [If MFA enabled]           │                          │
        │◄────────────────────────────│ 200: MFA_REQUIRED        │
        │  {mfa_challenge_id}         │                          │
        │                             │                          │
        │ POST /auth/mfa/verify       │                          │
        │ {challenge_id, code}        │                          │
        │────────────────────────────►│                          │
        │                             │ Verify TOTP              │
        │                             │                          │
        │  200: Tokens                │ Create session           │
        │◄────────────────────────────│─────────────────────────►│
        │  {access_token,             │                          │
        │   refresh_token}            │                          │
        │                             │                          │
```

### 2. Session Management

Sessions are tracked in the database for:
- Multi-device awareness
- Remote session revocation
- Security anomaly detection
- Compliance audit trails

**Session Record:**
```json
{
  "id": "sess_abc123",
  "user_id": "usr_xyz789",
  "access_token_jti": "jti_def456",
  "refresh_token_family": "fam_ghi012",
  "device_fingerprint": "fp_hash",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "is_active": true,
  "expires_at": "2024-02-01T00:00:00Z"
}
```

### 3. Token Family Rotation

To detect refresh token theft, we implement token family tracking:

```
Initial Login:
  family_id = generate_uuid()
  refresh_token = sign({family: family_id, seq: 0})

On Refresh:
  IF token.family != session.family THEN reject
  IF token.seq < session.last_seq THEN
    # Token reuse detected - potential theft
    revoke_entire_family(token.family)
    alert_user()
  ELSE
    new_token = sign({family: token.family, seq: token.seq + 1})
    update_session(last_seq: token.seq + 1)
```

### 4. MFA Implementation

**Supported Methods:**
1. TOTP (Authenticator apps) - Primary
2. SMS OTP - Secondary
3. Backup codes - Recovery

**MFA Challenge Flow:**
1. User provides credentials
2. If MFA enabled, return `MFA_REQUIRED` with challenge ID
3. Client prompts for MFA code
4. User submits code with challenge ID
5. On success, issue tokens

### 5. OAuth Flow

Standard Authorization Code flow with PKCE for public clients:

```
1. Client → /oauth/{provider}/authorize?redirect_uri=...&state=...&code_challenge=...
2. API redirects to provider's authorization endpoint
3. User authenticates with provider
4. Provider redirects to /oauth/{provider}/callback?code=...&state=...
5. API exchanges code for provider tokens
6. API creates/links user account
7. API issues Janua tokens
8. API redirects to client's redirect_uri with tokens
```

### 6. Passkey (WebAuthn) Flow

**Registration:**
1. Client requests registration options
2. API returns WebAuthn registration challenge
3. Browser creates credential with authenticator
4. Client sends attestation to API
5. API verifies and stores public key

**Authentication:**
1. Client requests authentication options
2. API returns WebAuthn authentication challenge
3. Authenticator signs challenge
4. Client sends assertion to API
5. API verifies signature, issues tokens

## Alternatives Considered

### Alternative 1: Opaque Tokens (Rejected)

**Pros:**
- Revocable instantly
- Smaller token size

**Cons:**
- Requires database lookup on every request
- Higher latency
- Single point of failure

**Decision:** JWT with short expiry provides good balance of statelessness and security.

### Alternative 2: HS256 Algorithm (Rejected)

**Pros:**
- Simpler key management
- Faster signing

**Cons:**
- Shared secret between services
- Key rotation more complex
- Cannot provide public key for verification

**Decision:** RS256 allows services to verify tokens without knowing the signing key.

### Alternative 3: Session-only (No Tokens) (Rejected)

**Pros:**
- Simpler mental model
- Instant revocation

**Cons:**
- Requires sticky sessions or session store
- Doesn't scale horizontally well
- Poor mobile/API support

**Decision:** Token-based better supports our multi-client, microservices architecture.

## Consequences

### Positive

1. **Horizontal Scalability**: Stateless token validation allows any API instance to handle requests
2. **Cross-Service Auth**: Other services can verify tokens with public key
3. **Mobile Support**: Tokens work well for mobile apps without cookie limitations
4. **Security**: Short-lived access tokens limit exposure; refresh token rotation detects theft
5. **Flexibility**: Supports multiple auth methods (password, OAuth, passkey, MFA)

### Negative

1. **Token Revocation Delay**: Access tokens valid until expiry (mitigated by 15-minute lifetime)
2. **Complexity**: Token management more complex than simple sessions
3. **Storage**: Refresh tokens require database storage

### Mitigations

1. **Revocation**: Critical operations check token JTI against revocation list in Redis
2. **Complexity**: SDKs abstract token management from application developers
3. **Storage**: Session cleanup job removes expired records

## Security Considerations

1. **Access Token Storage**: Memory only, never localStorage
2. **Refresh Token**: httpOnly cookie with Secure and SameSite=Strict
3. **Token Signing Key**: Rotated quarterly with 2-week overlap
4. **Brute Force Protection**: Rate limiting on auth endpoints
5. **Session Anomaly Detection**: Alert on unusual login patterns

## Related Documentation

- [Rate Limiting](/docs/api/RATE_LIMITING.md)
- [Security Guidelines](/docs/security/SECURITY.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [Multi-tenancy ADR](./ADR-003_MULTITENANCY.md)
