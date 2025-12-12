import { inject, computed, ComputedRef } from 'vue';
import { JANUA_KEY, JanuaVue } from './plugin';
import type { User, Session } from '@janua/typescript-sdk';

export function useJanua(): JanuaVue {
  const janua = inject<JanuaVue>(JANUA_KEY);
  
  if (!janua) {
    throw new Error('Janua plugin not installed. Make sure to call app.use(createJanua(...))');
  }

  return janua;
}

export function useAuth() {
  const janua = useJanua();
  const client = janua.getClient();
  const state = janua.getState();

  return {
    auth: client.auth,
    user: computed(() => state.user),
    session: computed(() => state.session),
    isAuthenticated: computed(() => state.isAuthenticated),
    isLoading: computed(() => state.isLoading),
    signIn: janua.signIn.bind(janua),
    signUp: janua.signUp.bind(janua),
    signOut: janua.signOut.bind(janua),
    updateSession: janua.updateSession.bind(janua),
  };
}

export function useUser() {
  const janua = useJanua();
  const client = janua.getClient();
  const state = janua.getState();

  const updateUser = async (data: any) => {
    const updatedUser = await client.users.updateCurrentUser(data);
    await janua.updateSession();
    return updatedUser;
  };

  return {
    user: computed(() => state.user as User | null),
    isLoading: computed(() => state.isLoading),
    updateUser,
  };
}

export function useSession(): {
  session: ComputedRef<Session | null>;
  refreshSession: () => Promise<void>;
  revokeSession: (sessionId: string) => Promise<void>;
} {
  const janua = useJanua();
  const client = janua.getClient();
  const state = janua.getState();

  const refreshSession = async () => {
    await janua.updateSession();
  };

  const revokeSession = async (sessionId: string) => {
    await client.users.revokeSession(sessionId);
    if (state.session?.id === sessionId) {
      await janua.signOut();
    }
  };

  return {
    session: computed(() => state.session),
    refreshSession,
    revokeSession,
  };
}

export function useOrganizations() {
  const janua = useJanua();
  const client = janua.getClient();
  
  return client.organizations;
}

export function useSignIn() {
  const janua = useJanua();
  const state = janua.getState();

  return {
    signIn: janua.signIn.bind(janua),
    isLoading: computed(() => state.isLoading),
  };
}

export function useSignUp() {
  const janua = useJanua();
  const state = janua.getState();

  return {
    signUp: janua.signUp.bind(janua),
    isLoading: computed(() => state.isLoading),
  };
}

export function useSignOut() {
  const janua = useJanua();
  
  return {
    signOut: janua.signOut.bind(janua),
  };
}

export function useMagicLink() {
  const janua = useJanua();
  const client = janua.getClient();

  const sendMagicLink = async (email: string, redirectUrl?: string) => {
    await client.auth.sendMagicLink({ email, redirect_url: redirectUrl });
  };

  const signInWithMagicLink = async (token: string) => {
    const response = await client.auth.verifyMagicLink(token);
    await janua.updateSession();
    return response;
  };

  return {
    sendMagicLink,
    signInWithMagicLink,
  };
}

export function useOAuth() {
  const janua = useJanua();
  const client = janua.getClient();

  const getOAuthUrl = async (
    provider: any,
    redirectUrl?: string
  ) => {
    return client.auth.initiateOAuth(provider as any, { redirect_uri: redirectUrl || window.location.origin + '/auth/callback' });
  };

  const handleOAuthCallback = async (code: string, state: string) => {
    const response = await client.auth.handleOAuthCallback(code, state);
    await janua.updateSession();
    return response;
  };

  return {
    getOAuthUrl,
    handleOAuthCallback,
  };
}

export function usePasskeys() {
  const janua = useJanua();
  const client = janua.getClient();

  const registerPasskey = async (options?: any) => {
    const registrationOptions = await client.auth.getPasskeyRegistrationOptions();
    // In a real implementation, you would use the WebAuthn API here
    // const credential = await navigator.credentials.create(registrationOptions);
    // await client.auth.completePasskeyRegistration(credential);
    return registrationOptions;
  };

  const authenticateWithPasskey = async () => {
    const authOptions = await client.auth.getPasskeyAuthenticationOptions();
    // In a real implementation, you would use the WebAuthn API here
    // const credential = await navigator.credentials.get(authOptions);
    // const response = await client.auth.completePasskeyAuthentication(credential);
    // await janua.updateSession();
    return authOptions;
  };

  return {
    registerPasskey,
    authenticateWithPasskey,
  };
}

export function useMFA() {
  const janua = useJanua();
  const client = janua.getClient();

  const enableMFA = async (type: 'totp' | 'sms') => {
    return client.auth.enableMFA(type);
  };

  const confirmMFA = async (code: string) => {
    await client.auth.verifyMFA({ code });
    await janua.updateSession();
  };

  const disableMFA = async (password: string) => {
    await client.auth.disableMFA(password);
    await janua.updateSession();
  };

  const verifyMFA = async (code: string) => {
    const tokens = await client.auth.verifyMFA({ code });
    await janua.updateSession();
    return tokens;
  };

  return {
    enableMFA,
    confirmMFA,
    disableMFA,
    verifyMFA,
  };
}