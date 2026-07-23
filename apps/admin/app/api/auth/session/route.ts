import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { createRemoteJWKSet, jwtVerify, type JWTPayload } from 'jose'

/**
 * Janua Admin — Session Cookie Bridge
 *
 * The browser-side <SignIn> component (and SSO callback) stores access /
 * refresh tokens in localStorage via the Janua SDK. The admin middleware,
 * however, gates protected routes on three HttpOnly cookies it reads from
 * `request.cookies`:
 *
 *   - janua_access_token  → bearer used for upstream API calls
 *   - janua_admin_email   → checked against the email domain allowlist
 *   - janua_admin_roles   → comma-separated role list parsed by middleware
 *
 * Setting HttpOnly cookies from JS in the browser is impossible by design,
 * so this route handler accepts the freshly-issued sign-in payload and
 * sets the three cookies server-side. The client invokes POST after a
 * successful sign-in (from the `afterSignIn` callback) and DELETE on
 * logout.
 *
 * SECURITY — why the token is verified here:
 *   The middleware makes its allow/deny decision on `janua_admin_email` and
 *   `janua_admin_roles`. If those were trusted straight from the POST body,
 *   anyone able to reach this route could mint cookies claiming
 *   `email=ops@madfam.io, roles=superadmin` and pass the edge gate without a
 *   valid session. So we verify the access token's RS256 signature against
 *   Janua's JWKS and derive email + roles from the *verified* claims,
 *   ignoring whatever the client body asserts for them. Verification is
 *   fail-closed: an unsigned/forged/expired token yields 401 and no cookies.
 *
 *   Signature + expiry are the security-critical checks (a forged token
 *   cannot be signed by Janua's private key). Audience/issuer are
 *   intentionally NOT pinned here — the console accepts tokens for its own
 *   per-client audience, and the upstream data plane independently enforces
 *   audience on every API call.
 *
 * Cookie flags:
 *   - HttpOnly  — JS cannot read the access token (mitigates XSS exfil)
 *   - Secure    — only sent over TLS in production
 *   - SameSite=Lax — protects against CSRF on top-level navigations while
 *     still allowing the dashboard SSO redirect flow to land properly
 *   - path '/'  — middleware runs on every protected route
 */

interface SessionPayload {
  access_token: string
  refresh_token?: string
  // email / roles / expires_at may be present in the body for backwards
  // compatibility, but they are NOT trusted — the authoritative values come
  // from the verified token claims below.
  email?: string
  roles?: string[] | string
  expires_at?: number | string
}

const ONE_DAY_SECONDS = 60 * 60 * 24

/**
 * Janua JWKS endpoint. Defaults to the public API's well-known path; operators
 * can override with JANUA_JWKS_URL for private/self-hosted deployments.
 */
function jwksUrl(): string {
  if (process.env.JANUA_JWKS_URL) return process.env.JANUA_JWKS_URL
  const apiBase = process.env.NEXT_PUBLIC_JANUA_API_URL || 'https://api.janua.dev'
  return `${apiBase.replace(/\/$/, '')}/.well-known/jwks.json`
}

// Module-scoped remote key set: jose caches the fetched keys internally with a
// cooldown, so we build it once per JWKS URL rather than per request.
let jwks: ReturnType<typeof createRemoteJWKSet> | null = null
let jwksSource = ''
function getJwks(): ReturnType<typeof createRemoteJWKSet> {
  const url = jwksUrl()
  if (!jwks || jwksSource !== url) {
    jwks = createRemoteJWKSet(new URL(url))
    jwksSource = url
  }
  return jwks
}

/**
 * Verify the RS256 signature and expiry of a Janua access token and return its
 * claims. Throws if the token is malformed, unsigned, tampered, or expired.
 */
async function verifyAccessToken(token: string): Promise<JWTPayload> {
  const { payload } = await jwtVerify(token, getJwks(), { clockTolerance: 30 })
  return payload
}

function normalizeRoles(roles: unknown): string {
  if (!roles) return ''
  if (Array.isArray(roles)) return roles.map((r) => String(r).trim()).filter(Boolean).join(',')
  return String(roles).trim()
}

function deriveMaxAge(expiresAt: number | string | undefined): number {
  if (expiresAt === undefined || expiresAt === null) return ONE_DAY_SECONDS
  const expiresMs = typeof expiresAt === 'string' ? Date.parse(expiresAt) : Number(expiresAt) * 1000
  if (!Number.isFinite(expiresMs)) return ONE_DAY_SECONDS
  const seconds = Math.floor((expiresMs - Date.now()) / 1000)
  if (seconds <= 0) return ONE_DAY_SECONDS
  // Cap at 30 days to avoid unbounded sessions.
  return Math.min(seconds, ONE_DAY_SECONDS * 30)
}

export async function POST(request: NextRequest) {
  let payload: SessionPayload
  try {
    payload = (await request.json()) as SessionPayload
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const accessToken = typeof payload.access_token === 'string' ? payload.access_token.trim() : ''
  if (!accessToken) {
    return NextResponse.json({ error: 'access_token is required' }, { status: 400 })
  }

  // Fail-closed: derive the trusted identity from the token's own claims, not
  // from the client-supplied body. A forged or expired token gets no cookies.
  let claims: JWTPayload
  try {
    claims = await verifyAccessToken(accessToken)
  } catch {
    return NextResponse.json(
      { error: 'Invalid or expired access token' },
      { status: 401 }
    )
  }

  const email = typeof claims.email === 'string' ? claims.email.trim() : ''
  if (!email) {
    return NextResponse.json(
      { error: 'Access token is missing an email claim' },
      { status: 401 }
    )
  }
  let roles = normalizeRoles(claims.roles)
  // Parity with the client-side session bootstrap (login/page.tsx): when the
  // verified token carries is_admin but no materialized roles yet, treat it as
  // the 'admin' role so the middleware allow-list behaves identically. This is
  // still derived from a VERIFIED claim, not the request body.
  if (!roles && claims.is_admin === true) {
    roles = 'admin'
  }
  // Prefer the token's own exp; fall back to the (advisory) body expires_at.
  const maxAge = deriveMaxAge(
    typeof claims.exp === 'number' ? claims.exp : payload.expires_at
  )
  const isProd = process.env.NODE_ENV === 'production'

  const cookieStore = await cookies()
  const baseOptions = {
    httpOnly: true,
    secure: isProd,
    sameSite: 'lax' as const,
    path: '/',
    maxAge,
  }

  cookieStore.set('janua_access_token', accessToken, baseOptions)
  cookieStore.set('janua_admin_email', email, baseOptions)
  cookieStore.set('janua_admin_roles', roles, baseOptions)

  if (payload.refresh_token && typeof payload.refresh_token === 'string') {
    cookieStore.set('janua_refresh_token', payload.refresh_token, {
      ...baseOptions,
      // Refresh tokens get a longer life, capped at 30 days.
      maxAge: ONE_DAY_SECONDS * 30,
    })
  }

  return NextResponse.json({ ok: true }, { status: 200 })
}

export async function DELETE() {
  const cookieStore = await cookies()
  const isProd = process.env.NODE_ENV === 'production'
  const expireOptions = {
    httpOnly: true,
    secure: isProd,
    sameSite: 'lax' as const,
    path: '/',
    maxAge: 0,
  }

  cookieStore.set('janua_access_token', '', expireOptions)
  cookieStore.set('janua_admin_email', '', expireOptions)
  cookieStore.set('janua_admin_roles', '', expireOptions)
  cookieStore.set('janua_refresh_token', '', expireOptions)

  return NextResponse.json({ ok: true }, { status: 200 })
}
