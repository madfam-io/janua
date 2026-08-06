/**
 * @jest-environment node
 */

import { POST, DELETE } from './route'
import { jwtVerify } from 'jose'

// Capture every cookies().set() call so we can assert flags.
type CookieCall = {
  name: string
  value: string
  options: {
    httpOnly?: boolean
    secure?: boolean
    sameSite?: 'lax' | 'strict' | 'none'
    path?: string
    maxAge?: number
  }
}

const cookieCalls: CookieCall[] = []

jest.mock('next/headers', () => ({
  cookies: jest.fn(async () => ({
    set: (name: string, value: string, options: CookieCall['options']) => {
      cookieCalls.push({ name, value, options })
    },
  })),
}))

jest.mock('next/server', () => {
  class FakeNextResponse {
    body: unknown
    status: number
    constructor(body: unknown, init?: { status?: number }) {
      this.body = body
      this.status = init?.status ?? 200
    }
    static json(body: unknown, init?: { status?: number }) {
      return new FakeNextResponse(body, init)
    }
  }
  return { NextResponse: FakeNextResponse }
})

// Stub jose so tests never hit a network JWKS. `jwtVerify` is the seam: the
// route trusts ONLY what this returns, never the request body's email/roles.
jest.mock('jose', () => ({
  createRemoteJWKSet: jest.fn(() => jest.fn()),
  jwtVerify: jest.fn(),
}))

const mockJwtVerify = jwtVerify as unknown as jest.Mock

/** Make jwtVerify resolve with the given verified claims. */
function verifiedClaims(claims: Record<string, unknown>) {
  mockJwtVerify.mockResolvedValueOnce({ payload: claims, protectedHeader: { alg: 'RS256' } })
}

/** Make jwtVerify reject as if the token were forged/expired. */
function rejectVerification(message = 'signature verification failed') {
  mockJwtVerify.mockRejectedValueOnce(new Error(message))
}

function makeRequest(body: unknown, opts: { malformed?: boolean } = {}): any {
  return {
    json: jest.fn(async () => {
      if (opts.malformed) throw new Error('invalid json')
      return body
    }),
  }
}

describe('POST /api/auth/session', () => {
  beforeEach(() => {
    cookieCalls.length = 0
    mockJwtVerify.mockReset()
    delete (process.env as any).NODE_ENV
  })

  it('sets HttpOnly, Lax, path=/ cookies from VERIFIED token claims', async () => {
    ;(process.env as any).NODE_ENV = 'production'
    const exp = Math.floor(Date.now() / 1000) + 3600
    verifiedClaims({ email: 'ops@janua.dev', roles: ['superadmin', 'admin'], exp })

    const res: any = await POST(
      makeRequest({
        access_token: 'jwt-abc',
        refresh_token: 'refresh-xyz',
      })
    )

    expect(res.status).toBe(200)
    expect(res.body).toEqual({ ok: true })

    const byName = Object.fromEntries(cookieCalls.map((c) => [c.name, c]))

    expect(byName.janua_access_token.value).toBe('jwt-abc')
    expect(byName.janua_access_token.options).toMatchObject({
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
      path: '/',
    })
    expect(byName.janua_access_token.options.maxAge).toBeGreaterThan(0)
    expect(byName.janua_access_token.options.maxAge).toBeLessThanOrEqual(3600)

    expect(byName.janua_admin_email.value).toBe('ops@janua.dev')
    expect(byName.janua_admin_roles.value).toBe('superadmin,admin')
    expect(byName.janua_refresh_token.value).toBe('refresh-xyz')
    expect(byName.janua_refresh_token.options.httpOnly).toBe(true)
  })

  it('IGNORES spoofed email/roles in the body — trusts only the verified token', async () => {
    verifiedClaims({ email: 'realuser@janua.dev', roles: ['viewer'], exp: Math.floor(Date.now() / 1000) + 3600 })

    const res: any = await POST(
      makeRequest({
        access_token: 'jwt-abc',
        // Attacker-supplied escalation attempt — must be discarded.
        email: 'attacker@evil.example',
        roles: ['superadmin'],
      })
    )

    expect(res.status).toBe(200)
    const byName = Object.fromEntries(cookieCalls.map((c) => [c.name, c]))
    expect(byName.janua_admin_email.value).toBe('realuser@janua.dev')
    expect(byName.janua_admin_roles.value).toBe('viewer')
  })

  it('rejects a forged/expired token with 401 and sets no cookies (fail-closed)', async () => {
    rejectVerification()

    const res: any = await POST(
      makeRequest({
        access_token: 'forged',
        email: 'ops@janua.dev',
        roles: ['superadmin'],
      })
    )

    expect(res.status).toBe(401)
    expect(cookieCalls).toHaveLength(0)
  })

  it('rejects a verified token missing an email claim with 401', async () => {
    verifiedClaims({ roles: ['admin'], exp: Math.floor(Date.now() / 1000) + 3600 })

    const res: any = await POST(makeRequest({ access_token: 'jwt-no-email' }))
    expect(res.status).toBe(401)
    expect(cookieCalls).toHaveLength(0)
  })

  it('marks Secure=false outside production so dev http://localhost works', async () => {
    ;(process.env as any).NODE_ENV = 'development'
    verifiedClaims({ email: 'ops@janua.dev', roles: ['admin'], exp: Math.floor(Date.now() / 1000) + 3600 })

    await POST(makeRequest({ access_token: 'jwt-abc' }))

    const access = cookieCalls.find((c) => c.name === 'janua_access_token')!
    expect(access.options.secure).toBe(false)
    expect(access.options.httpOnly).toBe(true)
    expect(access.options.sameSite).toBe('lax')
  })

  it('normalizes an array roles claim into a comma-separated cookie', async () => {
    verifiedClaims({ email: 'ops@janua.dev', roles: [' superadmin ', 'admin', ''], exp: Math.floor(Date.now() / 1000) + 3600 })

    await POST(makeRequest({ access_token: 'jwt' }))

    const roles = cookieCalls.find((c) => c.name === 'janua_admin_roles')!
    expect(roles.value).toBe('superadmin,admin')
  })

  it('falls back to the admin role when the verified token is is_admin with empty roles', async () => {
    verifiedClaims({ email: 'ops@janua.dev', roles: [], is_admin: true, exp: Math.floor(Date.now() / 1000) + 3600 })

    await POST(makeRequest({ access_token: 'jwt' }))

    const roles = cookieCalls.find((c) => c.name === 'janua_admin_roles')!
    expect(roles.value).toBe('admin')
  })

  it('does NOT invent an admin role when is_admin is absent/false', async () => {
    verifiedClaims({ email: 'ops@janua.dev', roles: [], is_admin: false, exp: Math.floor(Date.now() / 1000) + 3600 })

    await POST(makeRequest({ access_token: 'jwt' }))

    const roles = cookieCalls.find((c) => c.name === 'janua_admin_roles')!
    expect(roles.value).toBe('')
  })

  it('omits the refresh-token cookie when no refresh_token is supplied', async () => {
    verifiedClaims({ email: 'ops@janua.dev', roles: ['admin'], exp: Math.floor(Date.now() / 1000) + 3600 })

    await POST(makeRequest({ access_token: 'jwt' }))

    expect(cookieCalls.find((c) => c.name === 'janua_refresh_token')).toBeUndefined()
  })

  it('rejects requests missing access_token with 400 (before any verification)', async () => {
    const res: any = await POST(makeRequest({ email: 'ops@janua.dev', roles: ['admin'] }))
    expect(res.status).toBe(400)
    expect(cookieCalls).toHaveLength(0)
    expect(mockJwtVerify).not.toHaveBeenCalled()
  })

  it('rejects malformed JSON bodies with 400', async () => {
    const res: any = await POST(makeRequest(undefined, { malformed: true }))
    expect(res.status).toBe(400)
    expect(cookieCalls).toHaveLength(0)
  })

  it('falls back to a 1-day maxAge when the token has no exp', async () => {
    verifiedClaims({ email: 'ops@janua.dev', roles: ['admin'] })

    await POST(makeRequest({ access_token: 'jwt' }))

    const access = cookieCalls.find((c) => c.name === 'janua_access_token')!
    expect(access.options.maxAge).toBe(60 * 60 * 24)
  })
})

describe('DELETE /api/auth/session', () => {
  beforeEach(() => {
    cookieCalls.length = 0
  })

  it('expires all four admin cookies with maxAge=0 and HttpOnly=true', async () => {
    const res: any = await DELETE()
    expect(res.status).toBe(200)
    expect(res.body).toEqual({ ok: true })

    const names = cookieCalls.map((c) => c.name).sort()
    expect(names).toEqual(
      [
        'janua_access_token',
        'janua_admin_email',
        'janua_admin_roles',
        'janua_refresh_token',
      ].sort()
    )

    for (const call of cookieCalls) {
      expect(call.value).toBe('')
      expect(call.options.maxAge).toBe(0)
      expect(call.options.httpOnly).toBe(true)
      expect(call.options.sameSite).toBe('lax')
      expect(call.options.path).toBe('/')
    }
  })
})
