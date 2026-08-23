/**
 * Multi-Factor Authentication Service
 * Handles MFA setup, verification, and recovery
 */

import type { HttpClient } from '../http-client';
import type {
  AuthResponse,
  MFAEnableResponse,
  MFAVerifyRequest,
  MFAStatusResponse,
  MFABackupCodesResponse,
  User
} from '../types';
import { TokenManager } from '../utils';

export class MFAService {
  constructor(
    private http: HttpClient,
    private tokenManager: TokenManager,
    private onSignIn?: (data?: { user: User }) => void
  ) {}

  /**
   * Get MFA status for current user.
   *
   * NOTE: the Janua MFA router is mounted at `/api/v1/mfa`, NOT `/api/v1/auth/mfa`
   * (apps/api/app/main.py:1076). The endpoints below use the correct prefix; the
   * prior `/auth/mfa/...` paths 404'd.
   */
  async getMFAStatus(): Promise<MFAStatusResponse> {
    const response = await this.http.get<MFAStatusResponse>('/api/v1/mfa/status');
    return response.data;
  }

  /**
   * Begin MFA enrollment for the signed-in user. Requires the account password.
   * Targets `POST /api/v1/mfa/enable` (mfa.py:236), body `{ password }`.
   */
  async enableMFA(password: string): Promise<MFAEnableResponse> {
    const response = await this.http.post<MFAEnableResponse>('/api/v1/mfa/enable', { password });
    return response.data;
  }

  /**
   * Confirm MFA enrollment with a TOTP code. Targets `POST /api/v1/mfa/verify`
   * (mfa.py:291); returns `{ message }` and does NOT issue tokens. To complete a
   * second factor during sign-in, use {@link verifyMfaChallenge} instead.
   */
  async verifyMFA(request: MFAVerifyRequest): Promise<{ message: string }> {
    const response = await this.http.post<{ message: string }>('/api/v1/mfa/verify', request);
    return response.data;
  }

  /**
   * Complete an MFA challenge during sign-in and obtain session tokens.
   * Targets `POST /api/v1/mfa/challenge/verify` (mfa.py:565), which returns the
   * SignInResponse shape `{ user, tokens }`.
   */
  async verifyMfaChallenge(mfaToken: string, code: string): Promise<AuthResponse> {
    const response = await this.http.post<{
      user: User;
      tokens?: { access_token: string; refresh_token: string; expires_in: number; token_type: 'bearer' };
      access_token?: string;
      refresh_token?: string;
      expires_in?: number;
      token_type?: 'bearer';
    }>('/api/v1/mfa/challenge/verify', { mfa_token: mfaToken, code }, { skipAuth: true });

    const tokens = response.data.tokens || {
      access_token: response.data.access_token!,
      refresh_token: response.data.refresh_token!,
      expires_in: response.data.expires_in!,
      token_type: response.data.token_type || 'bearer'
    };

    if (tokens.access_token && tokens.refresh_token) {
      await this.tokenManager.setTokens({
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        expires_at: Date.now() + (tokens.expires_in * 1000)
      });
    }

    if (this.onSignIn) {
      this.onSignIn({ user: response.data.user });
    }

    return { user: response.data.user, tokens };
  }

  /**
   * Disable MFA for current user. Targets `POST /api/v1/mfa/disable` (mfa.py:321).
   */
  async disableMFA(password: string, code?: string): Promise<{ message: string }> {
    const body: { password: string; code?: string } = { password };
    if (code) body.code = code;
    const response = await this.http.post<{ message: string }>('/api/v1/mfa/disable', body);
    return response.data;
  }

  /**
   * Regenerate MFA backup codes. Targets
   * `POST /api/v1/mfa/regenerate-backup-codes` (mfa.py:363). The handler binds
   * `password` as a QUERY parameter, so it is sent via `params`.
   */
  async regenerateMFABackupCodes(password: string): Promise<MFABackupCodesResponse> {
    const response = await this.http.post<MFABackupCodesResponse>(
      '/api/v1/mfa/regenerate-backup-codes',
      undefined,
      { params: { password } }
    );
    return response.data;
  }

  /**
   * Validate an MFA code without completing sign-in. Targets
   * `POST /api/v1/mfa/validate-code` (mfa.py:400). `code` is a QUERY parameter.
   */
  async validateMFACode(code: string): Promise<{ valid: boolean; message: string }> {
    const response = await this.http.post<{ valid: boolean; message: string }>(
      '/api/v1/mfa/validate-code',
      undefined,
      { params: { code } }
    );
    return response.data;
  }

  /**
   * Get MFA recovery options for a user. Targets
   * `GET /api/v1/mfa/recovery-options?email=...` (mfa.py:435).
   */
  async getMFARecoveryOptions(email: string): Promise<{
    recovery_available: boolean;
    methods?: { backup_codes: boolean; email_recovery: boolean };
  }> {
    const response = await this.http.get<{
      recovery_available: boolean;
      methods?: { backup_codes: boolean; email_recovery: boolean };
    }>(`/api/v1/mfa/recovery-options?email=${encodeURIComponent(email)}`, { skipAuth: true });
    return response.data;
  }

  /**
   * Initiate MFA recovery process. Targets
   * `POST /api/v1/mfa/initiate-recovery` (mfa.py:475); `email` is a QUERY param.
   */
  async initiateMFARecovery(email: string): Promise<{ message: string }> {
    const response = await this.http.post<{ message: string }>(
      '/api/v1/mfa/initiate-recovery',
      undefined,
      { params: { email }, skipAuth: true }
    );
    return response.data;
  }
}
