import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@/test/test-utils'
import userEvent from '@testing-library/user-event'
import { JanuaSSOLoginButton } from './janua-sso-button'

/**
 * Regression coverage for the SSO-backbone OIDC rewire.
 * The button must use Janua's OIDC provider flow (initiateJanuaSSO) and must
 * fail loud — never silently fall back to the invalid social path.
 */
describe('JanuaSSOLoginButton', () => {
  const makeClient = () => {
    const initiateJanuaSSO = vi.fn().mockResolvedValue(undefined)
    return { initiateJanuaSSO, client: { auth: { initiateJanuaSSO } } }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    delete (window as any).location
    window.location = { href: '', origin: 'http://localhost:3000' } as any
  })

  it('renders the button when januaClientId and a capable client are provided', () => {
    const { client } = makeClient()
    render(<JanuaSSOLoginButton januaClientId="app-client-id" januaClient={client} />)

    expect(screen.getByRole('button', { name: /sign in with janua/i })).toBeInTheDocument()
  })

  it('fails loud (renders nothing + logs) when januaClientId is missing', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { client } = makeClient()

    const { container } = render(<JanuaSSOLoginButton januaClient={client} />)

    expect(container.firstChild).toBeNull()
    expect(errorSpy).toHaveBeenCalledWith(
      expect.stringContaining('requires a januaClientId')
    )
    errorSpy.mockRestore()
  })

  it('fails loud when the client cannot perform the OIDC flow', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    // Legacy/social-only client without initiateJanuaSSO.
    const { container } = render(
      <JanuaSSOLoginButton januaClientId="app-client-id" januaClient={{ auth: { initiateOAuth: vi.fn() } }} />
    )

    expect(container.firstChild).toBeNull()
    expect(errorSpy).toHaveBeenCalledWith(
      expect.stringContaining('initiateJanuaSSO')
    )
    errorSpy.mockRestore()
  })

  it('initiates the OIDC flow with clientId and default redirectUri on click', async () => {
    const user = userEvent.setup()
    const { initiateJanuaSSO, client } = makeClient()

    render(<JanuaSSOLoginButton januaClientId="app-client-id" januaClient={client} />)

    await user.click(screen.getByRole('button', { name: /sign in with janua/i }))

    expect(initiateJanuaSSO).toHaveBeenCalledWith({
      clientId: 'app-client-id',
      redirectUri: 'http://localhost:3000/auth/callback',
    })
  })

  it('uses an explicit redirectUri when provided', async () => {
    const user = userEvent.setup()
    const { initiateJanuaSSO, client } = makeClient()

    render(
      <JanuaSSOLoginButton
        januaClientId="app-client-id"
        redirectUri="https://app.example.com/callback"
        januaClient={client}
      />
    )

    await user.click(screen.getByRole('button', { name: /sign in with janua/i }))

    expect(initiateJanuaSSO).toHaveBeenCalledWith({
      clientId: 'app-client-id',
      redirectUri: 'https://app.example.com/callback',
    })
  })

  // Zero per-app code: NEXT_PUBLIC_JANUA_CLIENT_ID alone renders a working button.
  describe('env-var defaults', () => {
    const ENV_CLIENT = 'NEXT_PUBLIC_JANUA_CLIENT_ID'
    const ENV_REDIRECT = 'NEXT_PUBLIC_JANUA_REDIRECT_URI'
    let savedClient: string | undefined
    let savedRedirect: string | undefined

    beforeEach(() => {
      savedClient = process.env[ENV_CLIENT]
      savedRedirect = process.env[ENV_REDIRECT]
      delete process.env[ENV_CLIENT]
      delete process.env[ENV_REDIRECT]
    })

    afterEach(() => {
      if (savedClient === undefined) delete process.env[ENV_CLIENT]
      else process.env[ENV_CLIENT] = savedClient
      if (savedRedirect === undefined) delete process.env[ENV_REDIRECT]
      else process.env[ENV_REDIRECT] = savedRedirect
    })

    it('renders and initiates using NEXT_PUBLIC_JANUA_CLIENT_ID / _REDIRECT_URI when props are absent', async () => {
      const user = userEvent.setup()
      const { initiateJanuaSSO, client } = makeClient()
      process.env[ENV_CLIENT] = 'env-client-id'
      process.env[ENV_REDIRECT] = 'https://env.example.com/auth/callback'

      render(<JanuaSSOLoginButton januaClient={client} />)

      await user.click(screen.getByRole('button', { name: /sign in with janua/i }))

      expect(initiateJanuaSSO).toHaveBeenCalledWith({
        clientId: 'env-client-id',
        redirectUri: 'https://env.example.com/auth/callback',
      })
    })

    it('lets an explicit januaClientId prop override the env var', async () => {
      const user = userEvent.setup()
      const { initiateJanuaSSO, client } = makeClient()
      process.env[ENV_CLIENT] = 'env-client-id'

      render(<JanuaSSOLoginButton januaClientId="prop-client-id" januaClient={client} />)

      await user.click(screen.getByRole('button', { name: /sign in with janua/i }))

      expect(initiateJanuaSSO).toHaveBeenCalledWith({
        clientId: 'prop-client-id',
        redirectUri: 'http://localhost:3000/auth/callback',
      })
    })

    it('fails loud (renders nothing + logs) when both the prop and the env var are absent', () => {
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const { client } = makeClient()

      const { container } = render(<JanuaSSOLoginButton januaClient={client} />)

      expect(container.firstChild).toBeNull()
      expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('requires a januaClientId'))
      errorSpy.mockRestore()
    })
  })
})
