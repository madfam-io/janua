import * as React from 'react'
import { JanuaSSOButton as JanuaSSOButtonBase } from './social-buttons'

export interface JanuaSSOButtonProps {
  /**
   * Registered Janua OAuth `client_id` for this app (REQUIRED).
   * The button uses Janua's OIDC provider flow (`/api/v1/oauth/authorize`);
   * without a client id there is no valid entrypoint, so the button renders
   * nothing and logs an error (fail-loud).
   */
  januaClientId?: string
  /** OIDC redirect URI — defaults to `${origin}/auth/callback` */
  redirectUri?: string
  /** Janua SDK client instance (must expose `auth.initiateJanuaSSO`) */
  januaClient?: any
  disabled?: boolean
  className?: string
}

/**
 * "Sign in with Janua" button for MADFAM ecosystem apps.
 *
 * Initiates the OIDC authorization-code + PKCE flow against Janua as the
 * identity provider (`GET /api/v1/oauth/authorize`). This is DISTINCT from the
 * social OAuth path: `janua` is not a valid social provider, so the old
 * `initiateOAuth('janua')` call returned `400 "Invalid provider: janua"`.
 *
 * Fail-loud: if `januaClientId` is missing, or the SDK client can't perform the
 * OIDC flow, the button is not rendered and an error is logged. It never falls
 * back to the invalid social path.
 */
export function JanuaSSOLoginButton({
  januaClientId,
  redirectUri,
  januaClient,
  disabled,
  className,
}: JanuaSSOButtonProps) {
  const [isLoading, setIsLoading] = React.useState(false)

  if (!januaClientId) {
    // eslint-disable-next-line no-console
    console.error(
      '[janua/ui] JanuaSSOLoginButton requires a januaClientId (registered OIDC ' +
        'client_id). Button not rendered.'
    )
    return null
  }

  if (!januaClient || !januaClient.auth || typeof januaClient.auth.initiateJanuaSSO !== 'function') {
    // eslint-disable-next-line no-console
    console.error(
      '[janua/ui] JanuaSSOLoginButton requires a januaClient whose auth module ' +
        'implements initiateJanuaSSO (@janua/typescript-sdk >= OIDC rewire). ' +
        'Button not rendered.'
    )
    return null
  }

  const handleClick = async () => {
    setIsLoading(true)
    try {
      await januaClient.auth.initiateJanuaSSO({
        clientId: januaClientId,
        redirectUri: redirectUri || `${window.location.origin}/auth/callback`,
      })
      // On success the browser navigates away; nothing else to do.
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[janua/ui] Sign in with Janua failed to initiate:', err)
      setIsLoading(false)
    }
  }

  return (
    <JanuaSSOButtonBase
      onClick={handleClick}
      disabled={disabled || isLoading}
      className={className}
      label={isLoading ? 'Redirecting...' : 'Sign in with Janua'}
    />
  )
}
