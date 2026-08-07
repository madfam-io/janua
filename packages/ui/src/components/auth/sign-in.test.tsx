import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import userEvent from '@testing-library/user-event'
import { SignIn } from './sign-in'

describe('SignIn', () => {
  const mockAfterSignIn = vi.fn()
  const mockOnError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  describe('Rendering', () => {
    it('should render sign-in form with all fields', () => {
      render(<SignIn />)

      expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('should render remember me checkbox when enabled', () => {
      render(<SignIn showRememberMe={true} />)

      expect(screen.getByRole('checkbox', { name: /remember me/i })).toBeInTheDocument()
    })

    it('should not render remember me checkbox when disabled', () => {
      render(<SignIn showRememberMe={false} />)

      expect(screen.queryByRole('checkbox', { name: /remember me/i })).not.toBeInTheDocument()
    })

    it('should render sign-up link when signUpUrl is provided', () => {
      render(<SignIn signUpUrl="/sign-up" />)

      const signUpLink = screen.getByRole('link', { name: /sign up/i })
      expect(signUpLink).toBeInTheDocument()
      expect(signUpLink).toHaveAttribute('href', '/sign-up')
    })

    it('should render custom logo when logoUrl is provided', () => {
      render(<SignIn logoUrl="https://example.com/logo.png" />)

      const logo = screen.getByRole('img', { name: /logo/i })
      expect(logo).toBeInTheDocument()
      expect(logo).toHaveAttribute('src', 'https://example.com/logo.png')
    })

    it('should apply custom className', () => {
      const { container } = render(<SignIn className="custom-class" />)

      expect(container.firstChild).toHaveClass('custom-class')
    })

    it('should render custom header text', () => {
      render(<SignIn headerText="Welcome Back" headerDescription="Enter your details" />)

      expect(screen.getByText('Welcome Back')).toBeInTheDocument()
      expect(screen.getByText('Enter your details')).toBeInTheDocument()
    })
  })

  describe('Social Providers', () => {
    it('should render enabled social providers', () => {
      render(
        <SignIn
          socialProviders={{
            google: true,
            github: true,
            microsoft: false,
            apple: false,
          }}
        />
      )

      expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /github/i })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /microsoft/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /apple/i })).not.toBeInTheDocument()
    })

    it('should call social login handler when provider button is clicked', async () => {
      const user = userEvent.setup()

      // Mock window.location for OAuth redirect
      delete (window as any).location
      window.location = { href: '', origin: 'http://localhost:3000' } as any

      render(<SignIn socialProviders={{ google: true }} />)

      const googleButton = screen.getByRole('button', { name: /google/i })
      await user.click(googleButton)

      // Social login redirects to OAuth URL directly (no fetch call)
      expect(window.location.href).toContain('/api/v1/auth/oauth/google')
      expect(window.location.href).toContain('redirect_url=')
    })
  })

  describe('Form Validation', () => {
    it('should show validation error for empty email', async () => {
      const user = userEvent.setup()
      render(<SignIn />)

      const emailInput = screen.getByRole('textbox', { name: /email/i }) as HTMLInputElement
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      // HTML5 validation - email is required
      expect(emailInput.required).toBe(true)
      await user.click(submitButton)

      // Browser will prevent form submission due to HTML5 validation
      expect(emailInput.validity.valueMissing).toBe(true)
    })

    it('should show validation error for invalid email format', async () => {
      const user = userEvent.setup()
      render(<SignIn />)

      const emailInput = screen.getByRole('textbox', { name: /email/i }) as HTMLInputElement
      await user.type(emailInput, 'invalid-email')

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await user.click(submitButton)

      // HTML5 validation - invalid email format
      expect(emailInput.validity.typeMismatch).toBe(true)
    })

    it('should show validation error for empty password', async () => {
      const user = userEvent.setup()
      render(<SignIn />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      await user.type(emailInput, 'test@example.com')

      const passwordInput = screen.getByLabelText('Password') as HTMLInputElement
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      // HTML5 validation - password is required
      expect(passwordInput.required).toBe(true)
      await user.click(submitButton)

      expect(passwordInput.validity.valueMissing).toBe(true)
    })
  })

  describe('Form Submission', () => {
    it('should submit form with valid credentials', async () => {
      const user = userEvent.setup()
      const mockUser = { id: '1', email: 'test@example.com' }

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ user: mockUser }),
      })

      render(<SignIn afterSignIn={mockAfterSignIn} />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/auth/login',
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
              email: 'test@example.com',
              password: 'password123',
              remember: false,
            }),
          })
        )
      })

      expect(mockAfterSignIn).toHaveBeenCalledWith(mockUser)
    })

    it('awaits an async afterSignIn before navigating (session-bridge contract)', async () => {
      // Regression: the admin's afterSignIn mirrors SDK tokens into an HttpOnly
      // session cookie via a server bridge. If SignIn does not await it, a
      // consumer navigation races the un-awaited bridge and the edge middleware
      // bounces the authenticated user back to /login. This pins that the async
      // callback fully resolves BEFORE the redirect fires.
      const user = userEvent.setup()
      const events: string[] = []
      let resolveBridge: () => void = () => {}
      const bridge = new Promise<void>((r) => {
        resolveBridge = r
      })
      const asyncAfterSignIn = vi.fn(async () => {
        await bridge
        events.push('bridge-done')
      })

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: '1', email: 'test@example.com' } }),
      })

      const hrefSpy = vi.fn()
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: {
          ...window.location,
          set href(v: string) {
            events.push(`redirect:${v}`)
            hrefSpy(v)
          },
        },
      })

      render(<SignIn afterSignIn={asyncAfterSignIn} redirectUrl="/dashboard" />)
      await user.type(screen.getByRole('textbox', { name: /email/i }), 'test@example.com')
      await user.type(screen.getByLabelText('Password'), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => expect(asyncAfterSignIn).toHaveBeenCalled())
      // The redirect must NOT have fired while the bridge is still pending.
      expect(hrefSpy).not.toHaveBeenCalled()

      resolveBridge()
      await waitFor(() => expect(hrefSpy).toHaveBeenCalledWith('/dashboard'))
      // Ordering proof: the bridge resolved before the redirect.
      expect(events).toEqual(['bridge-done', 'redirect:/dashboard'])
    })

    it('should include remember me in submission when checked', async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ user: {} }),
      })

      render(<SignIn showRememberMe={true} />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      const passwordInput = screen.getByLabelText('Password')
      const rememberCheckbox = screen.getByRole('checkbox', { name: /remember me/i })
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(rememberCheckbox)
      await user.click(submitButton)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/auth/login',
          expect.objectContaining({
            body: expect.stringContaining('"remember":true'),
          })
        )
      })
    })

    it('should handle sign-in error', async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' }),
      })

      render(<SignIn onError={mockOnError} />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)

      await waitFor(() => {
        // Error message is displayed in the error div
        expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
      })

      expect(mockOnError).toHaveBeenCalled()
    })

    it('should redirect after successful sign-in when redirectUrl is provided', async () => {
      const user = userEvent.setup()
      delete (window as any).location
      window.location = { href: '' } as any

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ user: {} }),
      })

      render(<SignIn redirectUrl="/dashboard" />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(window.location.href).toBe('/dashboard')
      })
    })

    it('should call onMFARequired when API returns MFA challenge', async () => {
      const user = userEvent.setup()
      const mockOnMFARequired = vi.fn()

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ mfa_required: true, session_id: 'abc123' }),
      })

      render(<SignIn onMFARequired={mockOnMFARequired} />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnMFARequired).toHaveBeenCalledWith(
          expect.objectContaining({ mfa_required: true })
        )
      })
    })
  })

  describe('Loading State', () => {
    it('should show loading state during submission', async () => {
      const user = userEvent.setup()
      // The test decides when the request completes. A 100ms timer here made the
      // loading assertions a race: under load the timer fired before they ran,
      // the button re-enabled, and the test failed while passing in isolation.
      let resolveFetch: (response: unknown) => void = () => {}
      global.fetch = vi.fn().mockImplementation(
        () => new Promise((resolve) => { resolveFetch = resolve })
      )

      render(<SignIn />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      // Button should be disabled and show loading text
      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
      expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument()

      resolveFetch({ ok: true, json: async () => ({ user: {} }) })

      await waitFor(() => {
        expect(submitButton).not.toBeDisabled()
      })
    })

    it('should disable all inputs during loading', async () => {
      const user = userEvent.setup()
      // Stays pending -- the assertion is about the in-flight state, not its end.
      global.fetch = vi.fn().mockImplementation(() => new Promise(() => {}))

      render(<SignIn />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(emailInput).toBeDisabled()
      })
      expect(passwordInput).toBeDisabled()
    })
  })

  describe('Password Visibility', () => {
    it('should toggle password visibility', async () => {
      const user = userEvent.setup()
      render(<SignIn />)

      const passwordInput = screen.getByLabelText('Password') as HTMLInputElement
      // PasswordInput component has an aria-labeled toggle button
      const toggleButton = screen.getByRole('button', { name: /show password/i })

      expect(passwordInput.type).toBe('password')
      expect(toggleButton).toBeInTheDocument()

      await user.click(toggleButton)
      expect(passwordInput.type).toBe('text')

      const hideButton = screen.getByRole('button', { name: /hide password/i })
      await user.click(hideButton)
      expect(passwordInput.type).toBe('password')
    })
  })

  describe('SSO and Advanced Features', () => {
    it('should call onSSODetected when email with domain is blurred', async () => {
      const user = userEvent.setup()
      const mockOnSSODetected = vi.fn()

      render(<SignIn enableSSO={true} onSSODetected={mockOnSSODetected} />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      await user.type(emailInput, 'user@sso-org.com')
      await user.tab() // blur

      expect(mockOnSSODetected).toHaveBeenCalledWith('sso-org.com')
    })

    it('should render passkey button when enabled', () => {
      render(<SignIn enablePasskey={true} />)

      expect(screen.getByRole('button', { name: /passkey/i })).toBeInTheDocument()
    })

    it('should render magic link option when enabled', () => {
      render(<SignIn enableMagicLink={true} />)

      expect(screen.getByText(/email me a sign-in link/i)).toBeInTheDocument()
    })

    it('should render Enterprise SSO button when enableJanuaSSO is true and januaClientId is provided', () => {
      render(<SignIn enableJanuaSSO={true} januaClientId="app-client-id" />)

      expect(screen.getByRole('button', { name: /enterprise sso/i })).toBeInTheDocument()
    })

    // FAIL-LOUD: enableJanuaSSO without a client id must NOT render the button
    // (it would otherwise hit the invalid social path). It logs an error instead.
    it('should NOT render Enterprise SSO button when januaClientId is missing, and logs an error', () => {
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      render(<SignIn enableJanuaSSO={true} />)

      expect(screen.queryByRole('button', { name: /enterprise sso/i })).not.toBeInTheDocument()
      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('januaClientId is missing')
      )

      errorSpy.mockRestore()
    })

    it('should route the Enterprise SSO button through initiateJanuaSSO (OIDC), not initiateOAuth', async () => {
      const user = userEvent.setup()
      const initiateJanuaSSO = vi.fn().mockResolvedValue(undefined)
      const initiateOAuth = vi.fn()
      const januaClient = { auth: { initiateJanuaSSO, initiateOAuth } }

      delete (window as any).location
      window.location = { href: '', origin: 'http://localhost:3000' } as any

      render(
        <SignIn
          enableJanuaSSO={true}
          januaClientId="app-client-id"
          januaRedirectUri="http://localhost:3000/auth/callback"
          januaClient={januaClient}
          socialProviders={{}}
        />
      )

      await user.click(screen.getByRole('button', { name: /enterprise sso/i }))

      expect(initiateJanuaSSO).toHaveBeenCalledWith({
        clientId: 'app-client-id',
        redirectUri: 'http://localhost:3000/auth/callback',
      })
      expect(initiateOAuth).not.toHaveBeenCalled()
    })
  })

  // Zero per-app code: an app that sets NEXT_PUBLIC_JANUA_CLIENT_ID gets a
  // working "Sign in with Janua" button with no prop. Explicit prop overrides
  // the env var; fail-loud still applies when both are absent.
  describe('Janua SSO env-var defaults', () => {
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

    it('renders the Janua button from NEXT_PUBLIC_JANUA_CLIENT_ID when the prop is absent', () => {
      process.env[ENV_CLIENT] = 'env-client-id'

      render(<SignIn enableJanuaSSO={true} socialProviders={{}} />)

      expect(screen.getByRole('button', { name: /enterprise sso/i })).toBeInTheDocument()
    })

    it('lets an explicit januaClientId prop override the env var', async () => {
      const user = userEvent.setup()
      const initiateJanuaSSO = vi.fn().mockResolvedValue(undefined)
      const januaClient = { auth: { initiateJanuaSSO, initiateOAuth: vi.fn() } }
      process.env[ENV_CLIENT] = 'env-client-id'

      delete (window as any).location
      window.location = { href: '', origin: 'http://localhost:3000' } as any

      render(
        <SignIn
          enableJanuaSSO={true}
          januaClientId="prop-client-id"
          januaClient={januaClient}
          socialProviders={{}}
        />
      )

      await user.click(screen.getByRole('button', { name: /enterprise sso/i }))

      expect(initiateJanuaSSO).toHaveBeenCalledWith(
        expect.objectContaining({ clientId: 'prop-client-id' })
      )
    })

    it('uses NEXT_PUBLIC_JANUA_REDIRECT_URI as the default redirect URI', async () => {
      const user = userEvent.setup()
      const initiateJanuaSSO = vi.fn().mockResolvedValue(undefined)
      const januaClient = { auth: { initiateJanuaSSO, initiateOAuth: vi.fn() } }
      process.env[ENV_CLIENT] = 'env-client-id'
      process.env[ENV_REDIRECT] = 'https://env.example.com/auth/callback'

      delete (window as any).location
      window.location = { href: '', origin: 'http://localhost:3000' } as any

      render(<SignIn enableJanuaSSO={true} januaClient={januaClient} socialProviders={{}} />)

      await user.click(screen.getByRole('button', { name: /enterprise sso/i }))

      expect(initiateJanuaSSO).toHaveBeenCalledWith({
        clientId: 'env-client-id',
        redirectUri: 'https://env.example.com/auth/callback',
      })
    })

    it('fails loud (no button + error) when both the prop and the env var are absent', () => {
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      render(<SignIn enableJanuaSSO={true} socialProviders={{}} />)

      expect(screen.queryByRole('button', { name: /enterprise sso/i })).not.toBeInTheDocument()
      expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('januaClientId is missing'))

      errorSpy.mockRestore()
    })
  })

  describe('Legal Links and Footer', () => {
    it('should render terms and privacy links with default URLs', () => {
      render(<SignIn />)

      const termsLink = screen.getByRole('link', { name: /terms of service/i })
      const privacyLink = screen.getByRole('link', { name: /privacy policy/i })

      expect(termsLink).toHaveAttribute('href', '/terms')
      expect(privacyLink).toHaveAttribute('href', '/privacy')
    })

    it('should render custom terms and privacy URLs', () => {
      render(<SignIn termsUrl="https://example.com/terms" privacyUrl="https://example.com/privacy" />)

      const termsLink = screen.getByRole('link', { name: /terms of service/i })
      const privacyLink = screen.getByRole('link', { name: /privacy policy/i })

      expect(termsLink).toHaveAttribute('href', 'https://example.com/terms')
      expect(privacyLink).toHaveAttribute('href', 'https://example.com/privacy')
    })

    it('should render "Powered by Janua" footer', () => {
      render(<SignIn />)

      expect(screen.getByText(/powered by janua/i)).toBeInTheDocument()
    })
  })

  describe('showEmailPassword prop', () => {
    it('should show email/password form by default', () => {
      render(<SignIn />)

      expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('should hide email/password form when showEmailPassword is false', () => {
      render(<SignIn showEmailPassword={false} enableJanuaSSO={true} januaClientId="app-client-id" />)

      expect(screen.queryByRole('textbox', { name: /email/i })).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Password')).not.toBeInTheDocument()
      // SSO button should still be visible
      expect(screen.getByRole('button', { name: /enterprise sso/i })).toBeInTheDocument()
    })

    it('should still render legal links when email/password is hidden', () => {
      render(<SignIn showEmailPassword={false} enableJanuaSSO={true} januaClientId="app-client-id" />)

      expect(screen.getByRole('link', { name: /terms of service/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /privacy policy/i })).toBeInTheDocument()
    })

    it('should not render divider when email/password is hidden', () => {
      render(<SignIn showEmailPassword={false} socialProviders={{ google: true }} />)

      expect(screen.queryByText(/or continue with email/i)).not.toBeInTheDocument()
    })

    // Regression: guards the SSO-only rendering path (showEmailPassword=false +
    // enableJanuaSSO). NOTE: admin.janua.dev itself migrated to email/password
    // (SSO_CRITICAL_PATH Fix 8, PR #445) and no longer uses enableJanuaSSO; this
    // test now covers other ecosystem apps that render the Janua button. A
    // registered januaClientId is required for the button to render (fail-loud).
    it('should hide email/password with an SSO-only prop combo', () => {
      render(
        <SignIn
          enableJanuaSSO={true}
          januaClientId="app-client-id"
          showEmailPassword={false}
          showRememberMe={false}
          socialProviders={{}}
          headerText="Sign in"
          headerDescription="Platform operator access only"
        />
      )

      expect(screen.queryByRole('textbox', { name: /email/i })).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Password')).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /^sign in$/i })).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: /enterprise sso/i })).toBeInTheDocument()
    })

    it('should still render email/password when prop is undefined (default true)', () => {
      // Explicit-undefined is functionally equivalent to omitted; both must default to true.
      render(<SignIn showEmailPassword={undefined} />)

      expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
    })
  })

  describe('Appearance', () => {
    it('should accept appearance prop without error', () => {
      const { container } = render(<SignIn appearance={{ theme: 'dark' }} />)

      expect(container.firstChild).toBeInTheDocument()
    })

    it('should accept custom color variables without error', () => {
      const { container } = render(
        <SignIn
          appearance={{
            variables: {
              colorPrimary: '#ff0000',
              colorBackground: '#000000',
              colorText: '#ffffff',
            },
          }}
        />
      )

      expect(container.firstChild).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have proper form labels', () => {
      render(<SignIn />)

      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
    })

    it('should have proper ARIA attributes on error', async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ message: 'Invalid credentials' }),
      })

      render(<SignIn />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      // Error message is displayed with parsed error message
      await waitFor(() => {
        expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
      })
    })

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup()
      // Disable social providers so we can test email/password form navigation
      render(<SignIn showRememberMe={true} socialProviders={{}} />)

      const emailInput = screen.getByRole('textbox', { name: /email/i })
      await user.tab()

      expect(emailInput).toHaveFocus()

      await user.tab()
      expect(screen.getByLabelText('Password')).toHaveFocus()
    })
  })
})
