import type { JanuaAuthConfig } from './types'

/**
 * MADFAM ecosystem preset.
 * Used by Dhanam, Enclii, Tezca, Yantra4D — all MADFAM apps
 * authenticating via Janua SSO.
 */
export const madfamAuthConfig: Partial<JanuaAuthConfig> = {
  branding: {
    themePreset: 'madfam',
    darkMode: 'auto',
  },
  authentication: {
    emailPassword: true,
    magicLink: true,
    passkeys: true,
    socialProviders: {
      google: true,
      github: true,
      microsoft: true,
      apple: true,
    },
    sso: {
      enabled: true,
      autoDetect: true,
    },
    mfa: {
      required: false,
      methods: ['totp', 'sms'],
    },
    enableJanuaSSO: true,
    // `januaClientId` defaults to the per-app PUBLIC env var, so any MADFAM app
    // gets a working "Sign in with Janua" button with ZERO code change — it just
    // sets NEXT_PUBLIC_JANUA_CLIENT_ID (its registered OIDC client_id; a public,
    // PKCE-protected identifier — NOT a secret; see SSO_CRITICAL_PATH Fix 1 / the
    // OIDC-client seed). An explicit `januaClientId` still overrides this. When
    // both the prop and the env var are absent, the "Sign in with Janua" button
    // fails loud (not rendered) rather than hitting the invalid social path.
    januaClientId: process.env.NEXT_PUBLIC_JANUA_CLIENT_ID,
    // Defaults to NEXT_PUBLIC_JANUA_REDIRECT_URI, then to `${origin}/auth/callback`.
    januaRedirectUri: process.env.NEXT_PUBLIC_JANUA_REDIRECT_URI,
  },
  flows: {
    signIn: {
      layout: 'card',
      showRememberMe: true,
    },
    signUp: {
      enabled: true,
      requireEmailVerification: true,
    },
  },
}
