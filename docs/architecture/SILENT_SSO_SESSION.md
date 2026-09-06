# Silent SSO: where the browser session comes from

**Status**: B1, B2, B6 and R1 landed in Janua; B3/B4 are operator steps; B5 lives
in nauta and B7 in crea-map. **R1 chose option 3 of the security note below** —
a separate HttpOnly estate cookie, `janua_sso`; see "R1 — the `janua_sso` estate
cookie".
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
| **R1** | `janua_sso`: an HttpOnly estate cookie the SDK can relay to the browser | Janua `auth/sso_cookie.py`, `routers/v1/auth.py`, `routers/v1/oauth_provider.py` | landed |
| **R1s** | `@madfam/janua-next` relays `janua_sso` (and its deletion) | madfam-js `@madfam/janua-next@0.2.0` | landed |
| **R1n** | nauta adds the same relay | nauta | in flight |

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

**Option 3 was ratified and is what shipped** — the cookie is `janua_sso`; see
"R1 — the `janua_sso` estate cookie" below. `janua_access_token` is unchanged.

Silent SSO does **not** work across hosts until one of these is chosen. B1/B2/B6
make the mechanism correct; B3 is what makes it reach.

## R1 — the `janua_sso` estate cookie

### What B1 could not reach

B1 made all four session-establishing paths call `_set_session_cookies`. That is
correct, and it is not enough. The MAP and the nauta ERP portal exchange the
magic link **server-to-server**: their Next process calls
`POST /api/v1/auth/magic-link/verify` and reads the JSON. Node keeps the
`Set-Cookie` headers on that fetch response and drops them. Nothing ever reaches
a browser, so a person signed into the MAP was still asked for a second email at
`crea-erp.madfam.io`.

`@madfam/janua-next@0.2.0` closes the gap by relaying, **byte for byte**, any
`Set-Cookie` line whose cookie is named exactly `janua_sso` and whose `Domain`
covers the app's public host, appending it to the 303 it returns to the browser
after the verify exchange. It relays the `Max-Age=0` deletion from
`POST /api/v1/auth/logout` the same way. nauta adds the same relay (R1n). R1 is
the Janua half: minting what the relay carries.

### Why a separate cookie (option 3, ratified)

The security note above listed three ways to make silent SSO reach across hosts
and recommended the third. R1 implements it. `janua_access_token` stays exactly
as it is — host-scoped by default, JS-readable because the browser SDK reads it
— and the estate-wide cookie is a new, HttpOnly one that no script can read and
that is useless as a bearer credential. Widening the access cookie (option 1)
would have put a live bearer token within reach of an XSS on any host under
`madfam.io`; option 2 would have broken every SDK consumer that reads the cookie.

### The cookie

```
janua_sso=<signed reference>; Path=/; Domain=.madfam.io; HttpOnly; Secure; SameSite=Lax; Max-Age=604800
```

- **HttpOnly** — it is readable on every host in the estate, so no script
  anywhere in the estate may read it.
- **Secure**, **SameSite=Lax** — Lax because every silent hop arrives as a
  top-level GET navigation to `/authorize`, which Lax sends.
- **`Domain`** is `settings.COOKIE_DOMAIN` when set, host-only otherwise. **The
  relay refuses a host-only cookie**, so estate SSO requires
  `COOKIE_DOMAIN=.madfam.io` (B3 — already set in prod). Without it Janua still
  emits the cookie and it still works on the issuer host; it just does not
  travel, and the estate silently keeps two sessions.
- **`Max-Age`** is the refresh-session lifetime
  (`JWT_REFRESH_TOKEN_EXPIRE_DAYS`), because the row it references expires then.

### Value, and why it is revocable without a migration

The value is a signed JWT carrying `sub` and `sid` — the id of the `sessions`
row `AuthService.create_session` already writes — with `type: "sso_session"`.

That type is the security boundary. Every bearer path in Janua verifies
`token_type="access"` (`get_current_user`, and `_verify_own_access_token` on the
`/authorize` seam), so the cookie's value presented as `Authorization: Bearer …`
fails verification everywhere. It is a **session reference**, not a credential.

Resolution re-reads the `sessions` row on **every** use and refuses it when the
row is revoked (`revoked = True`, which `/signout` and `invalidate_user_sessions`
set), deactivated (`is_active = False`, which `revoke_token_family` sets on
refresh-token theft detection), past `expires_at`, or owned by a non-active user.
That is what makes the cookie revocable — and it means every revocation path
Janua already has revokes this cookie too, for free. **No new table, no new
column, no alembic revision**, which matters while production is frozen behind
the migration-drift guard.

Refresh rotation mutates `refresh_token_jti` on that same row and leaves
`session.id` alone, so a rotation does not invalidate the cookie and nothing has
to be re-issued on the `/authorize` response.

### Where it is accepted — and where it is not

`janua_sso` is read in exactly one function,
`get_user_from_cookie_or_header` (`routers/v1/oauth_provider.py`), whose only
callers are `GET /authorize` and its consent continuation `POST /consent`. It is
**not** accepted at `/api/v1/auth/me` or any other API — those use
`get_current_user`, which never reads it, and the token-type gate would refuse it
anyway. A unit test pins both the reader count and the caller set, so widening
the acceptance scope has to be a deliberate edit rather than a side effect.

Within `/authorize` the cookie authenticates the person for **both** `prompt=none`
and the interactive flow — a valid estate session skipping the login page is what
SSO means. It resolves *who* the person is and never *whether they may proceed*:
email verification, MFA and third-party consent are enforced exactly as before.

### Logout

Deleting the cookie is the cosmetic half; a copy taken before logout must stop
working. Both `POST /api/v1/auth/logout` (and `/signout`) and the OIDC
`end_session` endpoint therefore **revoke the `sessions` row** the cookie
references and **then** delete the cookie with the same `Domain` and `Path` it was
set with — a deletion differing on either attribute addresses a different cookie
and leaves the live one in place. The cookie's signature is verified before
anything is revoked, so a forged value cannot end someone else's session.

### Which paths emit it, and which deliberately do not

The cookie is emitted from `_set_session_cookies`, so all four paths that
establish a **browser** session get it: `login_form`, `login_form_mfa`,
`magic_link_callback` and `verify_magic_link` (`routers/v1/auth.py`). The other
session-minting paths were reviewed and deliberately excluded:

| Path | Why not |
|---|---|
| `POST /auth/signin` (`app/auth/router.py`) | JSON API returning `TokenResponse`. Its cookies are the legacy `access_token` / `refresh_token` names, which `/authorize` does not read — it establishes no `/authorize`-visible session today, with or without R1. |
| `POST /mfa/challenge/verify` (`routers/v1/mfa.py`) | JSON API returning tokens in the body; sets **no** cookies at all, not even `janua_access_token`. Nothing to be estate-wide about. |
| Social OAuth callback (`routers/v1/oauth.py`) | Calls `AuthService.create_user_session`, **which does not exist anywhere in the codebase** — that path raises `AttributeError` the moment a social provider is configured. It is masked in production only because the social-provider env vars are unset (`/auth/oauth/providers` returns `[]`). Fixing it is out of R1's scope and tracked separately; when it is fixed it should emit `janua_sso` (and the `janua_*` cookie pair) too. |

Each of these becomes a one-line change (`user=` / `session=` on the helper, or
`set_sso_cookie`) if it later becomes a real browser-session door.

### A failed exchange sets nothing

An invalid or expired magic link, a wrong password, an MFA interrupt, or a
destination the allowlist rejects at redemption all emit no `janua_sso` — there
is no session, so there is nothing to reference.

## Operator steps

- **B3**: set `COOKIE_DOMAIN` in Janua's environment — after ratifying the above.
- **B4**: add `madfam:silent_auth` to `allowed_scopes` on the `crea-map` and
  nauta OIDC clients. Their names ("MAP · Crea Tu Mundo") do not match the
  `selva-office*` / `madfam-*` prefixes, so the scope is the only way they
  qualify — for `prompt=none` and, since B6, for pre-consent.
- **R1**: nothing beyond B3. `COOKIE_DOMAIN=.madfam.io` is the single
  prerequisite for `janua_sso` to travel, and it is already set in production.
  Without it the cookie is emitted host-only, the relay refuses it, and the
  estate keeps two sessions — working, but not shared.
- **No migration.** B1/B2/B6 and R1 add no tables or columns, and promote runs no
  alembic; nothing here waits on a schema change. R1 deliberately reuses the
  existing `sessions` row rather than adding storage, because production is
  frozen behind the migration-drift guard.
