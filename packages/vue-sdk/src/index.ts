// Re-export everything from @plinto/typescript-sdk
export * from '@plinto/typescript-sdk';

// Plugin
export { createPlinto, PLINTO_KEY } from './plugin';
export type { PlintoState, PlintoPluginOptions, PlintoVue } from './plugin';

// Composables
export {
  usePlinto,
  useAuth,
  useUser,
  useSession,
  useOrganizations,
  useSignIn,
  useSignUp,
  useSignOut,
  useMagicLink,
  useOAuth,
  usePasskeys,
  useMFA,
} from './composables';