import * as React from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '../button'
import { Input } from '../input'
import { Label } from '../label'
import { Checkbox } from '../checkbox'
import { parseApiError, formatErrorMessage } from '../../lib/error-messages'
import { AuthCard, type AuthCardLayout } from './auth-card'
import { SocialButton, type SocialProvider } from './social-buttons'
import { AuthDivider } from './divider'
import { PasswordInput } from './password-input'

export interface SignInProps {
  /** Optional custom class name */
  className?: string
  /** Redirect URL after successful sign-in */
  redirectUrl?: string
  /** URL to sign-up page */
  signUpUrl?: string
  /** Callback after successful sign-in. Awaited: return a Promise (e.g. an
   *  HttpOnly session-cookie bridge) to guarantee it completes before any
   *  post-sign-in navigation. */
  afterSignIn?: (user: any) => void | Promise<void>
  /** Callback on error */
  onError?: (error: Error) => void
  /** Theme customization */
  appearance?: {
    theme?: 'light' | 'dark'
    variables?: {
      colorPrimary?: string
      colorBackground?: string
      colorText?: string
    }
  }
  /** Enable/disable social login providers */
  socialProviders?: {
    google?: boolean
    github?: boolean
    microsoft?: boolean
    apple?: boolean
  }
  /** Custom logo URL */
  logoUrl?: string
  /** Show "Remember me" checkbox */
  showRememberMe?: boolean
  /** Janua client instance for API integration */
  januaClient?: any
  /** API URL for direct fetch calls (fallback if no client provided) */
  apiUrl?: string
  /** Layout variant */
  layout?: AuthCardLayout
  /** Show passkey sign-in button */
  enablePasskey?: boolean
  /** Show SSO email domain detection */
  enableSSO?: boolean
  /** Callback when SSO domain is detected */
  onSSODetected?: (domain: string) => void
  /** Show magic link option */
  enableMagicLink?: boolean
  /** Show "Sign in with Janua" button for MADFAM apps */
  enableJanuaSSO?: boolean
  /**
   * Registered Janua OAuth `client_id` for this app. REQUIRED when
   * `enableJanuaSSO` is true — the button uses Janua's OIDC provider flow
   * (`/api/v1/oauth/authorize`), not the social path. Without it the button
   * is not rendered and an error is logged (fail-loud), because there is no
   * safe fallback: routing `janua` through the social OAuth path returns
   * `400 Invalid provider: janua`.
   *
   * Defaults to `process.env.NEXT_PUBLIC_JANUA_CLIENT_ID` when the prop is not
   * passed, so any MADFAM app gets a working button with ZERO code change —
   * it just sets that public env var. An explicit prop overrides the env var.
   * `client_id` is a public (PKCE-protected) identifier, not a secret.
   */
  januaClientId?: string
  /**
   * Redirect URI for the Janua OIDC flow. Defaults to
   * `process.env.NEXT_PUBLIC_JANUA_REDIRECT_URI`, then to `${origin}/auth/callback`.
   */
  januaRedirectUri?: string
  /** Callback when API returns MFA challenge */
  onMFARequired?: (session: any) => void
  /** Custom header text */
  headerText?: string
  /** Custom header description */
  headerDescription?: string
  /** Configurable forgot password URL */
  forgotPasswordUrl?: string
  /** Terms of Service URL */
  termsUrl?: string
  /** Privacy Policy URL */
  privacyUrl?: string
  /** Show email/password form (default true). Set false for SSO-only configs */
  showEmailPassword?: boolean
}

export function SignIn({
  className,
  redirectUrl,
  signUpUrl,
  afterSignIn,
  onError,
  appearance: _appearance = { theme: 'light' },
  socialProviders = {
    google: true,
    github: true,
    microsoft: false,
    apple: false,
  },
  logoUrl,
  showRememberMe = true,
  januaClient,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  layout = 'card',
  enablePasskey = false,
  enableSSO = false,
  onSSODetected,
  enableMagicLink = false,
  enableJanuaSSO = false,
  // Env defaults (zero per-app code): an app that sets NEXT_PUBLIC_JANUA_CLIENT_ID
  // gets a working "Sign in with Janua" button without passing any prop. An
  // explicit prop still overrides the env var; fail-loud still applies when both
  // the prop and the env var are absent.
  januaClientId = process.env.NEXT_PUBLIC_JANUA_CLIENT_ID,
  januaRedirectUri = process.env.NEXT_PUBLIC_JANUA_REDIRECT_URI,
  onMFARequired,
  headerText = 'Sign in to your account',
  headerDescription = 'Welcome back! Please enter your details',
  forgotPasswordUrl = '/forgot-password',
  termsUrl = '/terms',
  privacyUrl = '/privacy',
  showEmailPassword = true,
}: SignInProps) {
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [remember, setRemember] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  // MFA challenge state. When sign-in returns `mfa_required`, we hold the
  // short-lived `mfa_token` here and render a code-entry step in place of the
  // credentials form. `null` means no challenge is in progress.
  const [mfaToken, setMfaToken] = React.useState<string | null>(null)
  const [mfaCode, setMfaCode] = React.useState('')

  // Finalize a successful sign-in (credentials, MFA, or fetch fallback) by
  // awaiting the consumer's afterSignIn bridge, then navigating. AWAIT matters:
  // consumers use afterSignIn to mirror the SDK's freshly persisted tokens into
  // an HttpOnly session cookie. If we don't await, a consumer that navigates on
  // return races the un-awaited bridge — the edge middleware then sees no cookie
  // and bounces the (authenticated) user back to /login with tokens stranded in
  // localStorage. Awaiting also lets a bridge failure surface through onError
  // instead of becoming a silent unhandled rejection.
  const completeSignIn = React.useCallback(
    async (user: unknown) => {
      await afterSignIn?.(user)
      if (redirectUrl) {
        window.location.href = redirectUrl
      }
    },
    [afterSignIn, redirectUrl]
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      if (januaClient) {
        const response = await januaClient.auth.signIn({
          email,
          password,
          remember,
        })

        // MFA challenge. The API/SDK use snake_case `mfa_required` + `mfa_token`
        // (SignInResponse; apps/api/app/routers/v1/auth.py:451-452). A prior
        // version checked camelCase `mfaRequired`, which never matched, so the
        // MFA step never rendered. If the consumer supplied onMFARequired, defer
        // to it; otherwise render the built-in code-entry step below.
        if (response.mfa_required) {
          if (onMFARequired) {
            onMFARequired(response)
          } else {
            setMfaToken(response.mfa_token ?? null)
            setMfaCode('')
          }
          setIsLoading(false)
          return
        }

        await completeSignIn(response.user)
      } else {
        const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ email, password, remember }),
        })

        // The MFA challenge is a 200 with `mfa_required: true` + `mfa_token`
        // (NOT an error status). Read the body first, then branch on it, before
        // treating a non-OK status as a failure.
        const data = await response.json().catch(() => ({}))

        if (response.ok && data.mfa_required) {
          if (onMFARequired) {
            onMFARequired(data)
          } else {
            setMfaToken(data.mfa_token ?? null)
            setMfaCode('')
          }
          setIsLoading(false)
          return
        }

        if (!response.ok) {
          const actionableError = parseApiError(data, { status: response.status })
          setError(formatErrorMessage(actionableError, true))
          onError?.(new Error(actionableError.message))
          setIsLoading(false)
          return
        }

        await completeSignIn(data.user)
      }
    } catch (err) {
      const actionableError = parseApiError(err, {
        message: err instanceof Error ? err.message : undefined,
      })
      setError(formatErrorMessage(actionableError, true))
      onError?.(new Error(actionableError.message))
    } finally {
      setIsLoading(false)
    }
  }

  // Complete the second factor. Uses the SDK's verifyMfaChallenge when a client
  // is present (it persists tokens and fires onSignIn); otherwise POSTs directly
  // to /api/v1/mfa/challenge/verify for the fetch-fallback path.
  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!mfaToken) return
    setError(null)
    setIsLoading(true)

    try {
      if (januaClient) {
        const result = await januaClient.auth.verifyMfaChallenge(mfaToken, mfaCode)
        setMfaToken(null)
        await completeSignIn(result.user)
      } else {
        const response = await fetch(`${apiUrl}/api/v1/mfa/challenge/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ mfa_token: mfaToken, code: mfaCode }),
        })

        const data = await response.json().catch(() => ({}))
        if (!response.ok) {
          const actionableError = parseApiError(data, { status: response.status })
          setError(formatErrorMessage(actionableError, true))
          onError?.(new Error(actionableError.message))
          setIsLoading(false)
          return
        }
        setMfaToken(null)
        await completeSignIn(data.user)
      }
    } catch (err) {
      const actionableError = parseApiError(err, {
        message: err instanceof Error ? err.message : undefined,
      })
      setError(formatErrorMessage(actionableError, true))
      onError?.(new Error(actionableError.message))
    } finally {
      setIsLoading(false)
    }
  }

  const handleMfaCancel = () => {
    setMfaToken(null)
    setMfaCode('')
    setError(null)
    setPassword('')
  }

  const handleSocialLogin = async (provider: string) => {
    setIsLoading(true)
    try {
      // "Sign in with Janua" uses Janua's OIDC PROVIDER flow, NOT the social
      // OAuth path. `janua` is not a valid social provider, so it must be
      // routed through initiateJanuaSSO with a registered client_id.
      if (provider === 'janua') {
        if (!januaClient) {
          throw new Error('Sign in with Janua requires a januaClient with the OIDC SDK')
        }
        await januaClient.auth.initiateJanuaSSO({
          clientId: januaClientId,
          redirectUri:
            januaRedirectUri ||
            redirectUrl ||
            `${window.location.origin}/auth/callback`,
        })
        return
      }

      if (januaClient) {
        const response = await januaClient.auth.initiateOAuth(provider, {
          redirectUrl: redirectUrl || window.location.origin,
        })
        window.location.href = response.url
      } else {
        const oauthUrl = `${apiUrl}/api/v1/auth/oauth/${provider}?redirect_url=${encodeURIComponent(redirectUrl || window.location.origin)}`
        window.location.href = oauthUrl
      }
    } catch (err) {
      const actionableError = parseApiError(err, {
        message: `${provider} authentication failed`,
      })
      setError(formatErrorMessage(actionableError, true))
      onError?.(new Error(actionableError.message))
      setIsLoading(false)
    }
  }

  // Passkey (WebAuthn) sign-in. Drives the browser assertion ceremony via the
  // SDK's client.signInWithPasskey, which fetches options (with a server session
  // id), calls navigator.credentials.get, and verifies — persisting tokens on
  // success. Requires a januaClient; without one there is no ceremony to run.
  const handlePasskeyLogin = async () => {
    setError(null)
    if (!januaClient) {
      const message =
        'Passkey sign-in requires a configured Janua client. Pass januaClient to <SignIn>.'
      setError(message)
      onError?.(new Error(message))
      return
    }
    if (typeof window === 'undefined' || !window.PublicKeyCredential) {
      const message = 'Passkeys are not supported in this browser.'
      setError(message)
      onError?.(new Error(message))
      return
    }

    setIsLoading(true)
    try {
      // Pass the typed email (if any) so a non-discoverable credential can be
      // matched; empty is fine for discoverable (resident) passkeys.
      const result = await januaClient.signInWithPasskey(email || undefined)
      await completeSignIn(result.user)
    } catch (err) {
      // A user cancelling the OS prompt throws — surface it gently, not as a
      // hard failure banner shape a wrong password would use.
      const actionableError = parseApiError(err, {
        message: err instanceof Error ? err.message : 'Passkey sign-in failed',
      })
      setError(formatErrorMessage(actionableError, true))
      onError?.(new Error(actionableError.message))
    } finally {
      setIsLoading(false)
    }
  }

  // SSO email domain detection
  const handleEmailBlur = React.useCallback(() => {
    if (!enableSSO || !onSSODetected || !email.includes('@')) return
    const domain = email.split('@')[1]
    if (domain) {
      onSSODetected(domain)
    }
  }, [email, enableSSO, onSSODetected])

  const socialProviderList: SocialProvider[] = []
  if (socialProviders.google) socialProviderList.push('google')
  if (socialProviders.github) socialProviderList.push('github')
  if (socialProviders.microsoft) socialProviderList.push('microsoft')
  if (socialProviders.apple) socialProviderList.push('apple')
  // FAIL-LOUD: "Sign in with Janua" requires a registered OIDC client_id.
  // Never silently render a button that would hit the invalid social path
  // (`initiateOAuth('janua')` → 400 "Invalid provider: janua"). If the app
  // asked for the button but gave no client id, log an error and skip it.
  if (enableJanuaSSO) {
    if (januaClientId) {
      socialProviderList.push('janua')
    } else {
      // eslint-disable-next-line no-console
      console.error(
        '[janua/ui] enableJanuaSSO is set but januaClientId is missing. ' +
          'The "Sign in with Janua" button was not rendered. Pass a registered ' +
          'januaClientId (OIDC client_id) to enable it.'
      )
    }
  }

  const hasSocialProviders = socialProviderList.length > 0
  // Default is `true` when the prop is omitted (see destructuring above).
  // `!== false` ensures only an explicit `false` opts out, mirroring how
  // boolean React props are typically handled and matching the prop's JSDoc.
  const renderEmailPassword = showEmailPassword !== false

  const header = (
    <div className="text-center mb-6" style={{ animation: 'janua-fade-in 300ms ease' }}>
      <h2 className="text-2xl font-bold">{headerText}</h2>
      <p className="text-sm text-muted-foreground mt-1">{headerDescription}</p>
    </div>
  )

  const footer = signUpUrl ? (
    <p className="text-center text-sm text-muted-foreground mt-6">
      Don&apos;t have an account?{' '}
      <a href={signUpUrl} className="text-primary hover:underline font-medium">
        Sign up
      </a>
    </p>
  ) : undefined

  // ── MFA challenge step ──
  // Rendered in place of the credentials form once sign-in returns
  // `mfa_required`. It collects the second-factor code and completes the
  // challenge with the held mfa_token. Only shown when the consumer did NOT
  // supply an onMFARequired handler (that handler owns the UX otherwise).
  if (mfaToken) {
    const mfaHeader = (
      <div className="text-center mb-6" style={{ animation: 'janua-fade-in 300ms ease' }}>
        <h2 className="text-2xl font-bold">Two-factor authentication</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Enter the 6-digit code from your authenticator app, or a backup code.
        </p>
      </div>
    )

    return (
      <AuthCard layout={layout} logo={logoUrl} header={mfaHeader} className={className}>
        <form onSubmit={handleMfaSubmit} className="space-y-4">
          {error && (
            <div
              className="bg-destructive/15 text-destructive text-sm p-3 rounded-md"
              style={{ animation: 'janua-slide-up 200ms ease, janua-shake 400ms ease' }}
            >
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="signin-mfa-code">Verification code</Label>
            <Input
              id="signin-mfa-code"
              // inputMode numeric for TOTP, but allow letters/dash for backup codes.
              inputMode="text"
              autoComplete="one-time-code"
              placeholder="123456"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              required
              autoFocus
              disabled={isLoading}
            />
          </div>

          <Button type="submit" className="w-full" disabled={isLoading || !mfaCode.trim()}>
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Verifying...
              </>
            ) : (
              'Verify'
            )}
          </Button>

          <Button
            type="button"
            variant="ghost"
            className="w-full"
            disabled={isLoading}
            onClick={handleMfaCancel}
          >
            Back to sign in
          </Button>
        </form>

        <p className="text-center text-xs text-muted-foreground mt-3 opacity-60">
          Powered by Janua
        </p>
      </AuthCard>
    )
  }

  return (
    <AuthCard layout={layout} logo={logoUrl} header={header} footer={footer} className={className}>
      {/* Social Login Buttons */}
      {hasSocialProviders && (
        <>
          <div className="space-y-2.5 mb-6">
            {socialProviderList.map((provider, i) => (
              <SocialButton
                key={provider}
                provider={provider}
                onClick={() => handleSocialLogin(provider)}
                disabled={isLoading}
                animationIndex={i}
              />
            ))}
          </div>
          {renderEmailPassword && <AuthDivider label="Or continue with email" />}
        </>
      )}

      {/* Email/Password Form */}
      {renderEmailPassword && <form onSubmit={handleSubmit} className="space-y-4">
        {/* Error Message */}
        {error && (
          <div
            className="bg-destructive/15 text-destructive text-sm p-3 rounded-md"
            style={{ animation: 'janua-slide-up 200ms ease, janua-shake 400ms ease' }}
          >
            {error}
          </div>
        )}

        {/* Email Input */}
        <div className="space-y-2">
          <Label htmlFor="signin-email">Email</Label>
          <Input
            id="signin-email"
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={handleEmailBlur}
            required
            disabled={isLoading}
            autoComplete="email"
          />
        </div>

        {/* Password Input */}
        <PasswordInput
          id="signin-password"
          value={password}
          onChange={setPassword}
          disabled={isLoading}
          autoComplete="current-password"
          labelAction={
            <a
              href={forgotPasswordUrl}
              className="text-sm text-primary hover:underline"
              tabIndex={-1}
            >
              Forgot password?
            </a>
          }
        />

        {/* Remember Me */}
        {showRememberMe && (
          <div className="flex items-center gap-2">
            <Checkbox
              id="signin-remember"
              checked={remember}
              onCheckedChange={(checked) => setRemember(checked === true)}
              disabled={isLoading}
            />
            <Label htmlFor="signin-remember" className="text-sm font-normal cursor-pointer">
              Remember me for 30 days
            </Label>
          </div>
        )}

        {/* Submit Button */}
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Signing in...
            </>
          ) : (
            'Sign in'
          )}
        </Button>

        {/* Passkey Button */}
        {enablePasskey && (
          <Button
            type="button"
            variant="outline"
            className="w-full"
            disabled={isLoading}
            onClick={handlePasskeyLogin}
          >
            Sign in with Passkey
          </Button>
        )}

        {/* Magic Link Toggle */}
        {enableMagicLink && (
          <div className="text-center">
            <button
              type="button"
              className="text-sm text-primary hover:underline"
              disabled={isLoading}
              onClick={() => {
                // Magic link handled by MagicLinkForm component in Phase 5
              }}
            >
              Email me a sign-in link
            </button>
          </div>
        )}
      </form>}

      {/* Legal Links */}
      <p className="text-center text-xs text-muted-foreground mt-6">
        By continuing, you agree to the{' '}
        <a href={termsUrl} className="underline hover:text-foreground" target="_blank" rel="noopener noreferrer">
          Terms of Service
        </a>{' '}
        and{' '}
        <a href={privacyUrl} className="underline hover:text-foreground" target="_blank" rel="noopener noreferrer">
          Privacy Policy
        </a>
        .
      </p>

      {/* Powered by Janua */}
      <p className="text-center text-xs text-muted-foreground mt-3 opacity-60">
        Powered by Janua
      </p>
    </AuthCard>
  )
}
