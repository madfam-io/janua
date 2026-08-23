<!-- 2026-08-23 MFA/passkey completeness audit + implementation status + remaining plan.
Audit by a read-only research agent (every claim file:line-cited). SHIPPED so far:
PR #556 (backup-code hashing), #557 (passkey ceremony fixes), #558 (MFA enforcement,
staged behind a default-off flag). Remaining P1-P3 captured as a ready-to-execute
backlog at the top. Enforcement flag MFA_ENFORCE_ON_LOGIN stays OFF until the P1 UIs land. -->

# MFA / Passkeys — audit, status, and remaining plan (2026-08-23)

## Status: what shipped in this pass (all lock-out-safe, on live prod)

| PR | Scope | Lock-out risk |
|---|---|---|
| **#556** | Backup codes hashed at rest (were plaintext) + one shared verify-and-consume path; fixes disable() ignoring the `used` flag. Backward-compatible with legacy plaintext. | None (pure fix) |
| **#557** | Passkey ceremonies: registration challenge now read from Redis (was unreadable → always failed); auth challenge read server-side by session_id (was client-supplied → replay hole); RP config uses WEBAUTHN_RP_ID/ORIGIN (was localhost in prod); clone detection; MAX_PASSKEYS enforced. | None (no passkey login UI/caller exists yet) |
| **#558** | MFA **enforcement** on all four login paths (OAuth form, OAuth /authorize, both magic-link), via one shared gate, behind new flag **MFA_ENFORCE_ON_LOGIN (default FALSE)**. | None while flag off (behavior identical to today) |

**The flag stays OFF** until the P1 UIs below ship — turning it on before then would lock users out (enabling MFA today already locks dashboard users out because the dashboard login ignores the mfa_required response — that's P1 #1).

## Remaining backlog (P1 → P3), ready to execute

### P1 — functional; REQUIRED before flipping MFA_ENFORCE_ON_LOGIN
1. **MFA-challenge UI + SDK.** `@janua/typescript-sdk` `signIn` must surface `mfa_required`/`mfa_token` (today it swallows them) and gain a `verifyMfaChallenge(mfa_token, code)` method hitting `POST /api/v1/mfa/challenge/verify`. Then `apps/dashboard/lib/auth.tsx` `login()` and `apps/dashboard/app/login/page.tsx` must render a code-entry step on `mfa_required`. Also fix the stale SDK MFA methods (`setupMFA`→`/mfa/enable` with password; backup-codes path→`/mfa/regenerate-backup-codes`). (medium)
2. **Passkey LOGIN UI + flow.** No caller exists for `/authenticate/options`→`navigator.credentials.get`→`/authenticate/verify` (now `session_id`-based). Build it in the dashboard + hosted login. Add SDK passkey methods. (medium)
3. **Hosted OAuth login page MFA step.** `login_form` now returns an interstitial on MFA-required; give it a real challenge screen so OAuth/OIDC logins (every downstream app) can complete the second factor. (medium)

### P2 — policy / hardening (declared in models, not wired)
4. **Per-org "require MFA" policy** → consume `AUTH_REQUIRE_MFA` (system_settings) / `policy_engine.mfa_required` in the login gate so admins can force MFA per org/role (would extend `mfa_required_for` to also require *enrollment*). (large)
5. **Trusted-device / remember-this-device** using the existing `TrustedDevice` model + `Session.is_trusted_device` to skip MFA for a configured window. (medium)
6. **Step-up / re-auth** for sensitive ops (MFA-based, not just password re-prompt). (medium)

### P3 — coverage & polish
7. **Restore quarantined MFA/passkey tests to CI** (`tests/quarantine/…`, currently `--ignore`d in pytest.ini) after updating them to current signatures; add enforcement tests for every login path so the P0 bypasses can't regress. (medium)
8. **SMS / email OTP** (`mfa.py` "not implemented" markers) — only if wanted. (large)
9. **`ENABLE_MFA`** gates nothing today (main.py capabilities dict only) — decide whether it should gate the router/enforcement or drop it. (small)

---

---

## Full audit

The complete file:line-cited audit (TOTP lifecycle, passkey ceremonies, enforcement gap, policy/step-up/trusted-device, tests, SDK/consumer side, and the 20-item prioritized gap list) is preserved in the session record and summarized by the backlog above. PRs #556/#557/#558 close the entire P0 set; the P1-P3 backlog above is the remaining work.
