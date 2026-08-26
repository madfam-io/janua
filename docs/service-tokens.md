# Janua Service Tokens (machine-to-machine auth)

Cross-service identity for the RFC 0024 §P4 consolidations:

| Flow | Service client | Scope | Token audience | Resource server |
|---|---|---|---|---|
| Zavlo → Karafiel CFDI bridge (§P4.2) | `zavlo-cfdi-emitter` | `cfdi:issue` | `karafiel-api` | Karafiel API |
| RouteCraft → Dhanam billing (§P4.3) | `routecraft-billing-relay` | `billing:events` | `dhanam-api` | Dhanam API |
| Nauta → Karafiel legal drafts (D3.5) | `nauta-legal-drafts` | `legal:draft`, `legal:client-profile` | `karafiel-api` | Karafiel API |
| Forj → Yantra4D catalog render | `forj-catalog-materializer` | `yantra4d:render` | `yantra4d-api` | Yantra4D render API |

Both migration plans (`zavlo/docs/karafiel-cfdi-migration-plan.md`,
`routecraft/docs/dhanam-payments-migration-plan.md`) are gated on this
decision. This document is the decision record + integration contract.

**Decision**: service-to-service calls authenticate with Janua-issued
OAuth 2.0 `client_credentials` tokens (RFC 6749 §4.4). One confidential
OAuth client per producer→consumer edge, scoped to exactly the capability
that edge needs. Resource servers verify tokens offline via Janua's JWKS
(RS256) or online via RFC 7662 introspection.

Janua's `client_credentials` support (token endpoint, per-client scope
allowlist, introspection, JWKS) **already exists** — see
[`docs/guides/machine-to-machine-authentication-guide.md`](./guides/machine-to-machine-authentication-guide.md)
for the general pattern. This page pins down the concrete service→service
clients (the RFC 0024 §P4 consolidations plus the Forj→Yantra4D catalog
render edge) and how each side integrates.

## Endpoints

Issuer (production): `https://auth.madfam.io`

| Purpose | Endpoint |
|---|---|
| Discovery | `GET /.well-known/openid-configuration` |
| JWKS (public keys) | `GET /.well-known/jwks.json` |
| Token | `POST /api/v1/oauth/token` |
| Introspection (RFC 7662) | `POST /api/v1/oauth/introspect` |
| Client registration (internal) | `POST /api/v1/oauth/clients/register` |

## Service clients

Provisioned by an operator with `apps/api/scripts/seed_service_clients.py`
(or zero-touch via `POST /api/v1/oauth/clients/register` +
`X-Internal-API-Key`). Registration properties:

```jsonc
// zavlo-cfdi-emitter
{
  "name": "zavlo-cfdi-emitter",
  "audience": "karafiel-api",
  "allowed_scopes": ["cfdi:issue"],
  "grant_types": ["client_credentials"],
  "redirect_uris": [],
  "is_confidential": true
}

// routecraft-billing-relay
{
  "name": "routecraft-billing-relay",
  "audience": "dhanam-api",
  "allowed_scopes": ["billing:events"],
  "grant_types": ["client_credentials"],
  "redirect_uris": [],
  "is_confidential": true
}

// forj-catalog-materializer
{
  "name": "forj-catalog-materializer",
  "audience": "yantra4d-api",
  "allowed_scopes": ["yantra4d:render"],
  "grant_types": ["client_credentials"],
  "redirect_uris": [],
  "is_confidential": true
}
```

The `yantra4d:render` scope namespace is what makes Yantra4D emit a
`yantra4d_tier` claim high enough to clear its `pro`-tier GLB export gate
(`yantra4d/apps/api/middleware/auth.py`, `RENDER_SCOPE`). This is the same
render edge `fashion-cabinet/apps/api/body_render.py` already mints against
(`FC_YANTRA4D_CLIENT_ID/SECRET`) — forj's materializer is a second producer
on it, holding `FORJ_YANTRA4D_CLIENT_ID` / `FORJ_YANTRA4D_CLIENT_SECRET`.

The `client_secret` is shown **once** at provisioning. Store it in the
approved secret store (Enclii/Vault) and mount it into the calling
service's runtime environment. Placeholders only in code and docs —
never commit real `jnc_`/`jns_` values.

## How Zavlo / RouteCraft obtain tokens

`POST /api/v1/oauth/token` with `grant_type=client_credentials`. Client
authentication is `client_secret_basic` or `client_secret_post`.

```bash
curl -sS https://auth.madfam.io/api/v1/oauth/token \
  -u "$JANUA_CLIENT_ID:$JANUA_CLIENT_SECRET" \
  -d grant_type=client_credentials \
  -d scope="cfdi:issue"          # routecraft: scope="billing:events"
```

Response:

```json
{
  "access_token": "<RS256 JWT>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": null,
  "scope": "cfdi:issue"
}
```

Rules for callers:

- Tokens live **1 hour** (`expires_in` matches the JWT `exp`). There is no
  refresh token — request a new token when the old one is near expiry.
  Cache the token in memory and re-request ~60s before expiry; do not
  request a fresh token per call (the token endpoint is rate-limited).
- Omitting `scope` grants **all** scopes on the client's allowlist; the
  seeded clients have exactly one scope, so both forms are equivalent.
- Requesting a scope outside the client's allowlist fails closed with
  `400 invalid_scope`.
- Send the token as `Authorization: Bearer <access_token>` on every
  Karafiel/Dhanam call.

TypeScript sketch for `zavlo-backend` (NestJS) / RouteCraft:

```ts
let cached: { token: string; exp: number } | null = null;

async function serviceToken(): Promise<string> {
  if (cached && cached.exp - 60_000 > Date.now()) return cached.token;
  const res = await fetch(`${JANUA_ISSUER}/api/v1/oauth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization:
        "Basic " +
        Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString("base64"),
    },
    body: new URLSearchParams({ grant_type: "client_credentials" }),
  });
  if (!res.ok) throw new Error(`janua token: ${res.status}`);
  const body = await res.json();
  cached = { token: body.access_token, exp: Date.now() + body.expires_in * 1000 };
  return cached.token;
}
```

## Token shape

Service tokens are RS256 JWTs (`kid` in the header, key published at
`/.well-known/jwks.json`) with these claims:

```jsonc
{
  "iss": "https://auth.madfam.io",
  "sub": "service-account:jnc_...",     // stable machine identity
  "aud": "karafiel-api",                // per-client audience
  "exp": 1780000000,                    // iat + 3600
  "iat": 1779996400,
  "jti": "...",
  "type": "access",
  "client_id": "jnc_...",
  "scope": "cfdi:issue",                // space-separated granted scopes
  "token_use": "client_credentials",
  "actor_type": "service_account",
  "roles": ["service_account"],
  "email": "zavlo-cfdi-emitter@service.auth.madfam.io"
}
```

## How Karafiel verifies (offline, JWKS)

Karafiel (FastAPI) verifies without calling Janua on the hot path:

1. Fetch + cache JWKS from `https://auth.madfam.io/.well-known/jwks.json`.
2. Verify signature (RS256), `iss == https://auth.madfam.io`,
   `aud == "karafiel-api"`, and `exp` (PyJWT does all four).
3. Enforce `token_use == "client_credentials"` and that the required
   scope is present in the `scope` claim.

```python
import jwt
from jwt import PyJWKClient

_jwks = PyJWKClient("https://auth.madfam.io/.well-known/jwks.json")

def verify_service_token(token: str, required_scope: str = "cfdi:issue") -> dict:
    key = _jwks.get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        issuer="https://auth.madfam.io",
        audience="karafiel-api",
    )  # raises on bad signature / issuer / audience / expiry
    if claims.get("token_use") != "client_credentials":
        raise PermissionError("not a service token")
    if required_scope not in (claims.get("scope") or "").split():
        raise PermissionError(f"missing scope {required_scope}")
    return claims  # claims["sub"] / claims["client_id"] for audit rows
```

Karafiel's CFDI billing bridge guards `POST` envelope ingestion with
`required_scope="cfdi:issue"` and attributes the envelope to
`claims["client_id"]` alongside the existing `source: "zavlo.*"`
discriminator and idempotency key.

Scope map on the Karafiel side:

- `cfdi:issue` — Zavlo's CFDI envelope ingestion (above).
- `legal:draft` — creates and compiles service-agreement drafts and reads
  generated-document metadata.
- `legal:client-profile` — creates and updates the calling client's **own**
  legal-entity profile (`ClientProfile`) at `/api/v1/legal/clients`
  (`POST`/`PUT`/`PATCH`/`GET`; `DELETE` is refused). Karafiel PR #148.

`legal:draft` and `legal:client-profile` are **independent**: neither
implies the other, and Karafiel enforces each separately on its own routes.
A `legal:client-profile` token grants no access to drafts or generated
documents, and a `legal:draft` token cannot write a client profile.
`nauta-legal-drafts` is allowlisted for both because Nauta's
`engagement.provision` needs both capabilities; each token still carries
only the scopes that request asked for (omitting `scope` grants both).

## How Dhanam verifies (offline, JWKS)

Dhanam (NestJS) uses the same pattern via `passport-jwt` + `jwks-rsa`
(mirrors `zavlo-backend/src/modules/janua/janua-jwt.strategy.ts`):

```ts
import { passportJwtSecret } from "jwks-rsa";
import { ExtractJwt, Strategy } from "passport-jwt";

export class JanuaServiceJwtStrategy extends PassportStrategy(Strategy, "janua-service") {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      algorithms: ["RS256"],
      issuer: "https://auth.madfam.io",
      audience: "dhanam-api",
      secretOrKeyProvider: passportJwtSecret({
        jwksUri: "https://auth.madfam.io/.well-known/jwks.json",
        cache: true,
        rateLimit: true,
      }),
    });
  }

  validate(claims: Record<string, unknown>) {
    if (claims.token_use !== "client_credentials") throw new UnauthorizedException();
    const scopes = String(claims.scope ?? "").split(" ");
    if (!scopes.includes("billing:events")) throw new ForbiddenException();
    return claims; // claims.sub === "service-account:jnc_..."
  }
}
```

Scope map on the Dhanam side:

- `billing:events` — RouteCraft's signed `payment.succeeded` /
  attribution emission to `POST /v1/billing/madfam-events` and the
  delegated `POST /v1/billing/checkout` call. The existing HMAC envelope
  signature (`t=<ts>,v1=<hex>`) stays as content integrity on the event
  body; the Bearer token is the caller *identity*.

## Alternative: introspection (RFC 7662)

Resource servers that prefer online checks (or need immediate-revocation
semantics) can call introspection instead of JWKS verification:

```bash
curl -sS https://auth.madfam.io/api/v1/oauth/introspect \
  -u "$RESOURCE_CLIENT_ID:$RESOURCE_CLIENT_SECRET" \
  -d token="$ACCESS_TOKEN"
# => {"active": true, "sub": "service-account:jnc_...",
#     "client_id": "jnc_...", "scope": "cfdi:issue", "exp": ..., "iat": ...}
```

Expired or otherwise invalid tokens return `{"active": false}`.
Introspection itself requires client authentication (the resource
server's own Janua client credentials).

## Rotation & operations

- Rotate secrets via Janua's OAuth client secret-rotation endpoint;
  `CLIENT_SECRET_ROTATION_ENABLED` gives a dual-secret grace window so
  callers roll without downtime.
- One client per edge: do not reuse `zavlo-cfdi-emitter` for anything but
  Zavlo→Karafiel, nor `routecraft-billing-relay` for anything but
  RouteCraft→Dhanam. New edges get new clients with their own scopes.
- Widening a client's `allowed_scopes` is an operator action on the Janua
  side (seed script re-run or admin API) and must be reflected here.
