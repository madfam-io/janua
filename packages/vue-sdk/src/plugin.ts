import { App, reactive, readonly } from 'vue';
import { PlintoClient } from '@plinto/typescript-sdk';
import type { User, Session, PlintoConfig } from '@plinto/typescript-sdk';

export interface PlintoState {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export interface PlintoPluginOptions extends PlintoConfig {
  onAuthChange?: (user: User | null) => void;
}

const PLINTO_KEY = Symbol('plinto');

class PlintoVue {
  private client: PlintoClient;
  private state: PlintoState;
  private onAuthChange?: (user: User | null) => void;

  constructor(options: PlintoPluginOptions) {
    const { onAuthChange, ...config } = options;
    
    this.client = new PlintoClient(config);
    this.onAuthChange = onAuthChange;
    
    this.state = reactive({
      user: null,
      session: null,
      isLoading: true,
      isAuthenticated: false,
    });

    this.initialize();
  }

  private async initialize() {
    try {
      // Check for OAuth callback parameters in URL
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.has('code') && urlParams.has('state')) {
        const code = urlParams.get('code')!;
        const state = urlParams.get('state')!;
        await this.client.auth.handleOAuthCallback(code, state);
      }

      await this.updateAuthState();
    } catch (error) {
      console.error('Failed to initialize Plinto:', error);
    } finally {
      this.state.isLoading = false;
    }

    // Set up periodic auth state check
    setInterval(async () => {
      const currentUser = await this.client.getCurrentUser();
      if (currentUser !== this.state.user) {
        await this.updateAuthState();
      }
    }, 1000);
  }

  private async updateAuthState() {
    const user = await this.client.getCurrentUser();
    const session = user ? {
      accessToken: await this.client.getAccessToken(),
      refreshToken: await this.client.getRefreshToken()
    } as any : null;
    
    this.state.user = user;
    this.state.session = session;
    this.state.isAuthenticated = !!user && !!session;

    if (this.onAuthChange) {
      this.onAuthChange(user);
    }
  }

  async signIn(email: string, password: string) {
    const response = await this.client.auth.signIn({ email, password });
    this.updateAuthState();
    return response;
  }

  async signUp(data: {
    email: string;
    password: string;
    firstName?: string;
    lastName?: string;
  }) {
    const response = await this.client.auth.signUp(data);
    this.updateAuthState();
    return response;
  }

  async signOut() {
    await this.client.signOut();
    this.state.user = null;
    this.state.session = null;
    this.state.isAuthenticated = false;

    if (this.onAuthChange) {
      this.onAuthChange(null);
    }
  }

  async updateSession() {
    // Refresh the current user and update auth state
    await this.client.auth.getCurrentUser();
    this.updateAuthState();
  }

  getClient() {
    return this.client;
  }

  getState() {
    return readonly(this.state);
  }

  getUser() {
    return this.state.user;
  }

  getSession() {
    return this.state.session;
  }

  isAuthenticated() {
    return this.state.isAuthenticated;
  }
}

export const createPlinto = (options: PlintoPluginOptions) => {
  return {
    install(app: App) {
      const plinto = new PlintoVue(options);
      app.provide(PLINTO_KEY, plinto);
      app.config.globalProperties.$plinto = plinto;
    },
  };
};

export { PLINTO_KEY };
export type { PlintoVue };