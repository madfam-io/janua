/**
 * Main Janua client with complete API surface.
 *
 * Provides strongly-typed access to all Janua authentication and
 * user management endpoints.
 */

import { BaseAPIClient } from './base-client';
import {
  ClientConfig,
  RequestOptions as _RequestOptions,
  SDKDataResponse,
  SDKListResponse,
  SDKSuccessResponse,
  UserProfile,
  TokenResponse
} from '../types/base';

// Specific API types
export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  terms_accepted: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  logo_url?: string;
  website_url?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateOrganizationRequest {
  name: string;
  slug?: string;
  description?: string;
  website_url?: string;
}

export interface MFASetupResponse {
  secret: string;
  qr_code_url: string;
  backup_codes: string[];
}

export interface MFAVerifyRequest {
  code: string;
  backup_code?: boolean;
}

export interface Session {
  id: string;
  user_id: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
  last_activity: string;
  is_current: boolean;
}

export class JanuaClient extends BaseAPIClient {
  constructor(config: Partial<ClientConfig>) {
    super(config);
  }

  // Authentication methods
  public async login(credentials: LoginRequest): Promise<SDKDataResponse<TokenResponse & { user: UserProfile }>> {
    return this.post('/api/v1/auth/login', credentials);
  }

  public async register(registration: RegisterRequest): Promise<SDKDataResponse<{ user: UserProfile; token: TokenResponse }>> {
    return this.post('/api/v1/auth/register', registration);
  }

  public async refreshToken(): Promise<SDKDataResponse<TokenResponse>> {
    return this.post('/api/v1/auth/refresh');
  }

  public async forgotPassword(email: string): Promise<SDKSuccessResponse> {
    return this.post('/api/v1/auth/forgot-password', { email });
  }

  public async resetPassword(token: string, new_password: string): Promise<SDKSuccessResponse> {
    return this.post('/api/v1/auth/reset-password', {
      token,
      new_password
    });
  }

  public async verifyEmail(token: string): Promise<SDKSuccessResponse> {
    return this.post('/api/v1/auth/verify-email', { token });
  }

  public async resendVerification(email: string): Promise<SDKSuccessResponse> {
    return this.post('/api/v1/auth/resend-verification', { email });
  }

  // User management
  public async getCurrentUser(): Promise<SDKDataResponse<UserProfile>> {
    return this.get('/api/v1/users/me');
  }

  public async updateProfile(updates: Partial<Pick<UserProfile, 'name' | 'avatar_url'>>): Promise<SDKDataResponse<UserProfile>> {
    return this.patch('/api/v1/users/me', updates);
  }

  public async changePassword(current_password: string, new_password: string): Promise<SDKSuccessResponse> {
    return this.post('/api/v1/users/me/change-password', {
      current_password,
      new_password
    });
  }

  public async deleteAccount(): Promise<SDKSuccessResponse> {
    return this.delete('/api/v1/users/me');
  }

  // Organization management
  public async getOrganizations(): Promise<SDKListResponse<Organization>> {
    return this.get('/api/v1/organizations');
  }

  public async getOrganization(org_id: string): Promise<SDKDataResponse<Organization>> {
    return this.get(`/api/v1/organizations/${org_id}`);
  }

  public async createOrganization(organization: CreateOrganizationRequest): Promise<SDKDataResponse<Organization>> {
    return this.post('/api/v1/organizations', organization);
  }

  public async updateOrganization(
    org_id: string,
    updates: Partial<CreateOrganizationRequest>
  ): Promise<SDKDataResponse<Organization>> {
    return this.patch(`/api/v1/organizations/${org_id}`, updates);
  }

  public async deleteOrganization(org_id: string): Promise<SDKSuccessResponse> {
    return this.delete(`/api/v1/organizations/${org_id}`);
  }

  // Multi-Factor Authentication
  public async setupMFA(): Promise<SDKDataResponse<MFASetupResponse>> {
    return this.post('/api/v1/mfa/setup');
  }

  public async verifyMFA(verification: MFAVerifyRequest): Promise<SDKSuccessResponse> {
    return this.post('/api/v1/mfa/verify', verification);
  }

  public async disableMFA(password: string): Promise<SDKSuccessResponse> {
    return this.post('/api/v1/mfa/disable', { password });
  }

  public async generateBackupCodes(): Promise<SDKDataResponse<{ backup_codes: string[] }>> {
    return this.post('/api/v1/mfa/backup-codes/generate');
  }

  // Passkey management
  public async registerPasskey(name?: string): Promise<SDKDataResponse<any>> {
    return this.post('/api/v1/passkeys/register', { name });
  }

  public async authenticateWithPasskey(credential: any): Promise<SDKDataResponse<TokenResponse & { user: UserProfile }>> {
    return this.post('/api/v1/passkeys/authenticate', { credential });
  }

  public async getPasskeys(): Promise<SDKListResponse<any>> {
    return this.get('/api/v1/passkeys');
  }

  public async deletePasskey(passkey_id: string): Promise<SDKSuccessResponse> {
    return this.delete(`/api/v1/passkeys/${passkey_id}`);
  }

  // Session management
  public async getSessions(): Promise<SDKListResponse<Session>> {
    return this.get('/api/v1/sessions');
  }

  public async getCurrentSession(): Promise<SDKDataResponse<Session>> {
    return this.get('/api/v1/sessions/current');
  }

  public async revokeSession(session_id: string): Promise<SDKSuccessResponse> {
    return this.delete(`/api/v1/sessions/${session_id}`);
  }

  public async revokeAllSessions(): Promise<SDKSuccessResponse> {
    return this.delete('/api/v1/sessions');
  }

  // OAuth integration
  public async getOAuthProviders(): Promise<SDKListResponse<any>> {
    return this.get('/api/v1/oauth/providers');
  }

  public async initiateOAuth(provider: string, redirect_uri?: string): Promise<SDKDataResponse<{ authorization_url: string }>> {
    return this.post('/api/v1/oauth/authorize', {
      provider,
      redirect_uri
    });
  }

  public async completeOAuth(provider: string, code: string, state?: string): Promise<SDKDataResponse<TokenResponse & { user: UserProfile }>> {
    return this.post('/api/v1/oauth/callback', {
      provider,
      code,
      state
    });
  }

  // Health and status
  public async getHealth(): Promise<SDKDataResponse<any>> {
    return this.get('/api/v1/health');
  }

  public async getStatus(): Promise<SDKDataResponse<any>> {
    return this.get('/api/status');
  }

  // Admin methods (require admin permissions)
  public async getUsers(page: number = 1, size: number = 20): Promise<SDKListResponse<UserProfile>> {
    return this.get('/api/v1/admin/users', {
      query_params: { page, size }
    });
  }

  public async getUser(user_id: string): Promise<SDKDataResponse<UserProfile>> {
    return this.get(`/api/v1/admin/users/${user_id}`);
  }

  public async suspendUser(user_id: string, reason?: string): Promise<SDKSuccessResponse> {
    return this.post(`/api/v1/admin/users/${user_id}/suspend`, { reason });
  }

  public async unsuspendUser(user_id: string): Promise<SDKSuccessResponse> {
    return this.post(`/api/v1/admin/users/${user_id}/unsuspend`);
  }

  public async deleteUser(user_id: string): Promise<SDKSuccessResponse> {
    return this.delete(`/api/v1/admin/users/${user_id}`);
  }
}