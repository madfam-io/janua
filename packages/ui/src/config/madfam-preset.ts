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
    // NOTE: `januaClientId` is intentionally NOT set here — it is per-app and
    // must be supplied by each consuming app (its registered OIDC client_id,
    // see SSO_CRITICAL_PATH Fix 1). Without it, the "Sign in with Janua" button
    // fails loud (not rendered) rather than hitting the invalid social path.
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
