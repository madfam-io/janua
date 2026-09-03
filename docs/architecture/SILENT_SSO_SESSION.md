# Silent SSO: where the browser session comes from

**Status**: B1, B2 and B6 landed in Janua; B3/B4 are operator steps; B5 lives in
nauta and B7 in crea-map.
**Related**: `ADR-001_AUTH_FLOW.md`, ADR `2026-05-04-selva-unified-sso` (Phase 1
= `prompt=none`, delivered earlier), `docs/guides/SSO_INTEGRATION_GUIDE.md`.

## The problem this closes

Janua has implemented OIDC `prompt=none` at `/authorize` since Phase 1 of the
unified-SSO ADR. It resolves the person from the `janua_access_token` cookie.

That cookie had exactly two writers, both on the hosted password form
(`login_form` and `login_form_mfa` in `apps/api/app/routers/v1/auth.py`, via
`_set_session_cookies`). But the products that actually needed silent SSO — the
MAP (`crea-map.madfam.io`) and the nauta portal, soon `crea-erp.madfam.io` —
sign people in by **magic link**, and their users have no password at all. So no
browser ever held the cookie `/authorize` reads, and `prompt=none` could only
ever answer `login_required`.

Nothing logged an error. The silent path simply never succeeded.

## Order of operations

Each step is useless without the ones before it. This is the order things must
land, not a menu.

| Step | What | Where | State |
|---|---|---|---|
| **B1** | Both magic-link paths set the issuer session cookies | Janua `routers/v1/auth.py` | landed |
| **B2** | `/authorize` accepts every audience Janua mints | Janua `routers/v1/oauth_provider.py` | landed |
| **B6** | First-party clients are pre-consented | Janua `routers/v1/oauth_provider.py` | landed |
| **B3** | `COOKIE_DOMAIN=.madfam.io` so the cookie is readable estate-wide | operator (internal-devops / enclii) | **pending ratification** |
| **B4** | `madfam:silent_auth` on the `crea-map` and nauta OIDC clients | operator (admin API / data) | pending |
| **B5** | nauta sends `prompt=none` and falls back to interactive login | nauta `sso-launch.ts`, `auth.ts` | not started |
| **B7** | The MAP links to `crea-erp` (optionally sends `prompt`) | crea-map | not started |

**B2 is a silent prerequisite of B1.** A magic-link session carries the audience
of the product the link forwards to (`_session_audience_for_redirect`) —
`crea-map`, `nauta-portal` — not the platform `JWT_AUDIENCE`. Before B2,
`/authorize` validated against the platform audience only, so the cookie B1
writes would have been rejected with nothing visibly wrong in the happy path.

### B1 — who writes the cookie

- `GET /api/v1/auth/magic-link/callback`: the browser is on the issuer for this
  hop, which is the one moment Janua can set its own cookie on a magic-link
  login. The redirect still goes to `<destination>?token=<access_token>`; the
  contract products read is unchanged.
- `POST /api/v1/auth/magic-link/verify`: the `SignInResponse` body is unchanged
  — `@madfam/janua-next` and nauta's integration package depend on it — with the
  cookies added on the injected `Response`. When a **server** calls this (which
  is how both products call it today), Node keeps the `Set-Cookie` and drops it;
  the cookie only matters when a browser posts here directly.

An MFA interrupt mints no session and therefore sets no cookie. A destination
the allowlist rejects at redemption returns the HTML page with no cookie.

### B2 — audience tolerance

`get_user_from_cookie_or_header` now verifies through
`_verify_own_access_token`, which retries once with audience verification off
and still requires a usable `aud` claim. Signature, issuer, expiry and token
type stay enforced on both passes. This is the tolerance
`AuthService.verify_token` already had; Janua is the **issuer** reading a token
it minted itself, and audience restriction is a rule for *resource servers*
deciding which tokens to accept.

`JWTManager.verify_token` gained an additive `verify_audience` flag, default
`True`, so every other caller keeps strict validation.

### B6 — pre-consent

Consent exists so a person can refuse a **third party** access to their account.
It communicates nothing when the client is MADFAM itself, and on the silent path
it cannot even be asked: `prompt=none` renders no screen, so a missing consent
row became `consent_required` for a client nobody would have refused.

The predicate is `_is_silent_auth_allowed` itself, not a looser copy — exactly
the clients trusted to authenticate silently are treated as pre-consented, so
widening one can never quietly widen the other. Third-party clients still see
the consent screen.

Consequence: `consent_required` is now unreachable on the silent path by
construction. The branch is kept as defense in depth in case the two predicates
ever diverge.

## Security note: the cookie is readable by JavaScript

`janua_access_token` is set with `httponly=False` on purpose — the browser SDK
reads it to make API calls. `janua_refresh_token` is HttpOnly.

B1 does not change that, and **does not change `COOKIE_DOMAIN`**, which defaults
to `None` (`apps/api/app/config.py`): the cookie is scoped to the issuer host
only. That default is deliberate here.

**B3 must be ratified before it is deployed.** Setting `COOKIE_DOMAIN=.madfam.io`
extends a JS-readable bearer token to every host in the estate; an XSS anywhere
under `madfam.io` would then be able to read a live Janua access token. Options
worth weighing before flipping it:

1. Set `COOKIE_DOMAIN=.madfam.io` as is, accepting the widened blast radius.
2. Mark the wide-domain access cookie HttpOnly and let the browser SDK obtain
   tokens another way (this would break SDK consumers that read the cookie
   directly, so it needs its own migration).
3. Issue a **separate** HttpOnly SSO cookie for the wide domain and leave
   `janua_access_token` host-scoped as it is today. `/authorize` would read the
   SSO cookie; the SDK keeps reading the host-scoped one. This keeps the
   JS-readable token narrow and is the option this note recommends — but it is a
   design decision, not a mechanical change, and it was deliberately not made
   unilaterally.

Silent SSO does **not** work across hosts until one of these is chosen. B1/B2/B6
make the mechanism correct; B3 is what makes it reach.

## Operator steps

- **B3**: set `COOKIE_DOMAIN` in Janua's environment — after ratifying the above.
- **B4**: add `madfam:silent_auth` to `allowed_scopes` on the `crea-map` and
  nauta OIDC clients. Their names ("MAP · Crea Tu Mundo") do not match the
  `selva-office*` / `madfam-*` prefixes, so the scope is the only way they
  qualify — for `prompt=none` and, since B6, for pre-consent.
- **No migration.** B1/B2/B6 add no tables or columns, and promote runs no
  alembic; nothing here waits on a schema change.
