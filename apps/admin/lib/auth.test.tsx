/**
 * Regression tests for the admin login handoff (bounce-to-/login production bug).
 *
 * Root cause: AuthProvider subscribed to SDK event names that were never
 * emitted ('signIn'/'signOut'/'tokenRefreshed' — declared in SdkEventMap as
 * backward-compat aliases, but no emit site fired them). A successful sign-in
 * via the shared <SignIn> component therefore never reached React state:
 * isAuthenticated stayed false and the home page guard bounced the user back
 * to /login even though the SDK held valid tokens in localStorage and the
 * /api/auth/session bridge had just set valid HttpOnly middleware cookies.
 */
import React from 'react'
import { render, screen, act, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './auth'

jest.mock('./janua-client', () => {
  const listeners: Record<string, Array<(data: unknown) => void>> = {}
  const client = {
    on: jest.fn((event: string, cb: (data: unknown) => void) => {
      ;(listeners[event] = listeners[event] || []).push(cb)
      return () => {
        listeners[event] = (listeners[event] || []).filter((fn) => fn !== cb)
      }
    }),
    off: jest.fn((event: string, cb: (data: unknown) => void) => {
      listeners[event] = (listeners[event] || []).filter((fn) => fn !== cb)
    }),
    auth: {
      getCurrentUser: jest.fn(),
      signIn: jest.fn(),
      signOut: jest.fn(),
    },
    __listeners: listeners,
    __emit: (event: string, data: unknown) => {
      ;(listeners[event] || []).forEach((fn) => fn(data))
    },
  }
  return { __esModule: true, januaClient: client, default: client }
})

const { januaClient: mockClient } = jest.requireMock('./janua-client') as {
  januaClient: {
    on: jest.Mock
    off: jest.Mock
    auth: { getCurrentUser: jest.Mock; signIn: jest.Mock; signOut: jest.Mock }
    __listeners: Record<string, Array<(data: unknown) => void>>
    __emit: (event: string, data: unknown) => void
  }
}

const adminUser = {
  id: 'user-1',
  email: 'ops@madfam.io',
  roles: ['admin'],
}

function Probe() {
  const { user, isAuthenticated, isLoading } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="email">{user?.email ?? 'none'}</span>
    </div>
  )
}

async function renderProvider() {
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  )
  await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
}

beforeEach(() => {
  jest.clearAllMocks()
  for (const key of Object.keys(mockClient.__listeners)) {
    delete mockClient.__listeners[key]
  }
  // Match the unauthenticated /login load: SDK has no tokens, so
  // getCurrentUser fails ("No refresh token available" in production).
  mockClient.auth.getCurrentUser.mockRejectedValue(new Error('No refresh token available'))
  window.localStorage.clear()
  jest.spyOn(console, 'error').mockImplementation(() => undefined)
})

afterEach(() => {
  ;(console.error as jest.Mock).mockRestore?.()
})

describe('AuthProvider SDK event contract', () => {
  it('subscribes to the canonical SDK event names (not the never-emitted aliases)', async () => {
    await renderProvider()

    const subscribed = mockClient.on.mock.calls.map((call: unknown[]) => call[0])
    expect(subscribed).toEqual(
      expect.arrayContaining(['auth:signedIn', 'auth:signedOut', 'token:refreshed'])
    )
    // The old names were never emitted by the SDK; subscribing to them is the bug.
    expect(subscribed).not.toContain('signIn')
    expect(subscribed).not.toContain('signOut')
    expect(subscribed).not.toContain('tokenRefreshed')
  })

  it('becomes authenticated when the SDK emits auth:signedIn after a component sign-in', async () => {
    await renderProvider()
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false')

    await act(async () => {
      mockClient.__emit('auth:signedIn', { user: adminUser })
    })

    expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    expect(screen.getByTestId('email')).toHaveTextContent('ops@madfam.io')
  })

  it('hydrates from /auth/me when a signedIn payload carries no usable user', async () => {
    await renderProvider()
    mockClient.auth.getCurrentUser.mockResolvedValue(adminUser)

    await act(async () => {
      mockClient.__emit('auth:signedIn', { user: {} })
    })

    await waitFor(() => expect(screen.getByTestId('authenticated')).toHaveTextContent('true'))
    expect(screen.getByTestId('email')).toHaveTextContent('ops@madfam.io')
    expect(mockClient.auth.getCurrentUser).toHaveBeenCalledTimes(2) // init + hydration
  })

  it('clears the user when the SDK emits auth:signedOut', async () => {
    await renderProvider()
    await act(async () => {
      mockClient.__emit('auth:signedIn', { user: adminUser })
    })
    expect(screen.getByTestId('authenticated')).toHaveTextContent('true')

    await act(async () => {
      mockClient.__emit('auth:signedOut', {})
    })

    expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
    expect(screen.getByTestId('email')).toHaveTextContent('none')
  })

  it('re-fetches the user when the SDK emits token:refreshed', async () => {
    await renderProvider()
    mockClient.auth.getCurrentUser.mockResolvedValue(adminUser)

    await act(async () => {
      mockClient.__emit('token:refreshed', {
        tokens: { access_token: 'a', refresh_token: 'r', expires_in: 900, token_type: 'bearer' },
      })
    })

    await waitFor(() => expect(screen.getByTestId('authenticated')).toHaveTextContent('true'))
  })
})
