/**
 * Plinto React Native SDK
 * Complete authentication solution for React Native apps
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Keychain from 'react-native-keychain';
import { Platform } from 'react-native';
import 'react-native-url-polyfill/auto';

const DEFAULT_BASE_URL = 'https://plinto.dev';

class PlintoClient {
  constructor(config) {
    this.baseURL = config.baseURL || DEFAULT_BASE_URL;
    this.tenantId = config.tenantId;
    this.clientId = config.clientId;
    this.redirectUri = config.redirectUri;
    this.storage = config.storage || AsyncStorage;
    this.secureStorage = config.secureStorage || Keychain;
    
    // Initialize services
    this.auth = new AuthService(this);
    this.users = new UsersService(this);
    this.sessions = new SessionsService(this);
    this.organizations = new OrganizationsService(this);
    
    // Initialize token refresh
    this.initTokenRefresh();
  }

  async request(method, path, data = null, options = {}) {
    const url = `${this.baseURL}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      'X-Tenant-ID': this.tenantId,
      'X-Client-ID': this.clientId,
      'X-Platform': Platform.OS,
      'X-SDK': 'react-native',
      ...options.headers
    };

    // Add auth token if available
    const token = await this.getAccessToken();
    if (token && !options.skipAuth) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      method,
      headers,
      ...options
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json();
        throw new PlintoError(error.message, error.code, error.details);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof PlintoError) {
        throw error;
      }
      throw new PlintoError('Network error', 'NETWORK_ERROR', { original: error.message });
    }
  }

  async getAccessToken() {
    try {
      const tokens = await this.secureStorage.getInternetCredentials('plinto');
      if (tokens) {
        const parsed = JSON.parse(tokens.password);
        return parsed.access_token;
      }
    } catch (error) {
      // Try AsyncStorage as fallback
      return await this.storage.getItem('plinto_access_token');
    }
    return null;
  }

  async setTokens(tokens) {
    try {
      // Store in secure storage
      await this.secureStorage.setInternetCredentials(
        'plinto',
        'tokens',
        JSON.stringify(tokens)
      );
    } catch (error) {
      // Fallback to AsyncStorage
      await this.storage.setItem('plinto_access_token', tokens.access_token);
      await this.storage.setItem('plinto_refresh_token', tokens.refresh_token);
    }
  }

  async clearTokens() {
    try {
      await this.secureStorage.resetInternetCredentials('plinto');
    } catch (error) {
      // Clear from AsyncStorage
      await this.storage.removeItem('plinto_access_token');
      await this.storage.removeItem('plinto_refresh_token');
    }
  }

  initTokenRefresh() {
    // Set up automatic token refresh
    setInterval(async () => {
      try {
        await this.auth.refreshToken();
      } catch (error) {
        console.error('Token refresh failed:', error);
      }
    }, 50 * 60 * 1000); // Refresh every 50 minutes
  }
}

class AuthService {
  constructor(client) {
    this.client = client;
  }

  async signUp({ email, password, firstName, lastName, metadata }) {
    const response = await this.client.request('POST', '/api/v1/auth/signup', {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
      metadata
    });

    if (response.tokens) {
      await this.client.setTokens(response.tokens);
    }

    return response;
  }

  async signIn({ email, password }) {
    const response = await this.client.request('POST', '/api/v1/auth/signin', {
      email,
      password
    });

    if (response.tokens) {
      await this.client.setTokens(response.tokens);
    }

    return response;
  }

  async signOut() {
    try {
      await this.client.request('POST', '/api/v1/auth/signout');
    } finally {
      await this.client.clearTokens();
    }
  }

  async refreshToken() {
    const refreshToken = await this.client.storage.getItem('plinto_refresh_token');
    if (!refreshToken) {
      throw new PlintoError('No refresh token available', 'NO_REFRESH_TOKEN');
    }

    const response = await this.client.request('POST', '/api/v1/auth/refresh', {
      refresh_token: refreshToken
    }, { skipAuth: true });

    await this.client.setTokens(response.tokens);
    return response;
  }

  async requestPasswordReset(email) {
    return await this.client.request('POST', '/api/v1/auth/password/reset', { email });
  }

  async resetPassword(token, newPassword) {
    return await this.client.request('POST', '/api/v1/auth/password/confirm', {
      token,
      password: newPassword
    });
  }

  async verifyEmail(token) {
    return await this.client.request('POST', '/api/v1/auth/verify-email', { token });
  }

  async enableMFA(method = 'totp') {
    return await this.client.request('POST', '/api/v1/auth/mfa/enable', { method });
  }

  async verifyMFA(code, challengeId) {
    return await this.client.request('POST', '/api/v1/auth/mfa/verify', {
      code,
      challenge_id: challengeId
    });
  }

  async disableMFA(password) {
    return await this.client.request('POST', '/api/v1/auth/mfa/disable', { password });
  }

  // OAuth/Social login
  async signInWithProvider(provider) {
    const { authorization_url } = await this.client.request(
      'GET',
      `/api/v1/auth/oauth/${provider}/authorize`,
      null,
      { 
        params: { 
          redirect_uri: this.client.redirectUri,
          client_id: this.client.clientId
        }
      }
    );

    // Open in browser or in-app browser
    return authorization_url;
  }

  async handleOAuthCallback(code, state) {
    const response = await this.client.request('POST', '/api/v1/auth/oauth/callback', {
      code,
      state,
      redirect_uri: this.client.redirectUri
    });

    if (response.tokens) {
      await this.client.setTokens(response.tokens);
    }

    return response;
  }

  // Passkeys/WebAuthn (requires react-native-webauthn)
  async registerPasskey() {
    const options = await this.client.request('POST', '/api/v1/auth/passkeys/register/start');
    
    // Use WebAuthn API
    const credential = await navigator.credentials.create(options);
    
    return await this.client.request('POST', '/api/v1/auth/passkeys/register/complete', {
      credential: credentialToJSON(credential)
    });
  }

  async signInWithPasskey() {
    const options = await this.client.request('POST', '/api/v1/auth/passkeys/authenticate/start');
    
    // Use WebAuthn API
    const assertion = await navigator.credentials.get(options);
    
    const response = await this.client.request('POST', '/api/v1/auth/passkeys/authenticate/complete', {
      assertion: assertionToJSON(assertion)
    });

    if (response.tokens) {
      await this.client.setTokens(response.tokens);
    }

    return response;
  }

  // Biometric authentication
  async enableBiometric() {
    const isSupported = await Keychain.getSupportedBiometryType();
    if (!isSupported) {
      throw new PlintoError('Biometric authentication not supported', 'BIOMETRIC_NOT_SUPPORTED');
    }

    // Store current tokens with biometric protection
    const tokens = await this.client.getTokens();
    await Keychain.setInternetCredentials(
      'plinto-biometric',
      'tokens',
      JSON.stringify(tokens),
      {
        accessControl: Keychain.ACCESS_CONTROL.BIOMETRY_CURRENT,
        authenticatePrompt: 'Authenticate to enable biometric login'
      }
    );

    return { biometryType: isSupported };
  }

  async signInWithBiometric() {
    const result = await Keychain.getInternetCredentials('plinto-biometric', {
      authenticatePrompt: 'Authenticate to sign in'
    });

    if (result) {
      const tokens = JSON.parse(result.password);
      await this.client.setTokens(tokens);
      return { success: true, tokens };
    }

    throw new PlintoError('Biometric authentication failed', 'BIOMETRIC_FAILED');
  }
}

class UsersService {
  constructor(client) {
    this.client = client;
  }

  async getCurrentUser() {
    return await this.client.request('GET', '/api/v1/users/me');
  }

  async updateProfile(updates) {
    return await this.client.request('PUT', '/api/v1/users/me', updates);
  }

  async uploadAvatar(imageUri) {
    const formData = new FormData();
    formData.append('avatar', {
      uri: imageUri,
      type: 'image/jpeg',
      name: 'avatar.jpg'
    });

    return await this.client.request('POST', '/api/v1/users/me/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }

  async changePassword(currentPassword, newPassword) {
    return await this.client.request('PUT', '/api/v1/auth/password/change', {
      current_password: currentPassword,
      new_password: newPassword
    });
  }

  async deleteAccount(password) {
    return await this.client.request('DELETE', '/api/v1/users/me', { password });
  }
}

class SessionsService {
  constructor(client) {
    this.client = client;
  }

  async listSessions() {
    return await this.client.request('GET', '/api/v1/sessions');
  }

  async revokeSession(sessionId) {
    return await this.client.request('DELETE', `/api/v1/sessions/${sessionId}`);
  }

  async revokeAllSessions() {
    return await this.client.request('DELETE', '/api/v1/sessions');
  }

  async getCurrentSession() {
    return await this.client.request('GET', '/api/v1/sessions/current');
  }
}

class OrganizationsService {
  constructor(client) {
    this.client = client;
  }

  async listOrganizations() {
    return await this.client.request('GET', '/api/v1/organizations');
  }

  async createOrganization(data) {
    return await this.client.request('POST', '/api/v1/organizations', data);
  }

  async getOrganization(orgId) {
    return await this.client.request('GET', `/api/v1/organizations/${orgId}`);
  }

  async updateOrganization(orgId, updates) {
    return await this.client.request('PUT', `/api/v1/organizations/${orgId}`, updates);
  }

  async deleteOrganization(orgId) {
    return await this.client.request('DELETE', `/api/v1/organizations/${orgId}`);
  }

  async getMembers(orgId) {
    return await this.client.request('GET', `/api/v1/organizations/${orgId}/members`);
  }

  async inviteMember(orgId, email, role) {
    return await this.client.request('POST', `/api/v1/organizations/${orgId}/invites`, {
      email,
      role
    });
  }

  async removeMember(orgId, userId) {
    return await this.client.request('DELETE', `/api/v1/organizations/${orgId}/members/${userId}`);
  }

  async acceptInvite(inviteToken) {
    return await this.client.request('POST', '/api/v1/organizations/invites/accept', {
      token: inviteToken
    });
  }
}

class PlintoError extends Error {
  constructor(message, code, details = {}) {
    super(message);
    this.name = 'PlintoError';
    this.code = code;
    this.details = details;
  }
}

// Helper functions for WebAuthn
function credentialToJSON(credential) {
  return {
    id: credential.id,
    rawId: arrayBufferToBase64(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: arrayBufferToBase64(credential.response.clientDataJSON),
      attestationObject: arrayBufferToBase64(credential.response.attestationObject)
    }
  };
}

function assertionToJSON(assertion) {
  return {
    id: assertion.id,
    rawId: arrayBufferToBase64(assertion.rawId),
    type: assertion.type,
    response: {
      clientDataJSON: arrayBufferToBase64(assertion.response.clientDataJSON),
      authenticatorData: arrayBufferToBase64(assertion.response.authenticatorData),
      signature: arrayBufferToBase64(assertion.response.signature),
      userHandle: assertion.response.userHandle ? arrayBufferToBase64(assertion.response.userHandle) : null
    }
  };
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

// Export
export default PlintoClient;
export { PlintoError, AuthService, UsersService, SessionsService, OrganizationsService };