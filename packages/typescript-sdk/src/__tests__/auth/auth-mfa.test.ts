/**
 * Tests for MFA (Multi-Factor Authentication) operations
 */

import { Auth } from '../../auth';
import { HttpClient } from '../../http-client';
import { TokenManager } from '../../utils';
import { UserStatus } from '../../types';

// Inline fixtures
const userFixtures = {
  validUser: {
    id: '550e8400-e29b-41d4-a716-446655440000',
    email: 'test@example.com',
    email_verified: true,
    first_name: 'Test',
    last_name: 'User',
    status: UserStatus.ACTIVE,
    mfa_enabled: false,
    is_admin: false,
    phone_verified: false,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
    user_metadata: {}
  },
  verifiedUser: {
    id: '550e8400-e29b-41d4-a716-446655440001',
    email: 'verified@example.com',
    email_verified: true,
    first_name: 'Verified',
    last_name: 'User',
    status: UserStatus.ACTIVE,
    mfa_enabled: false,
    is_admin: false,
    phone_verified: true,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
    user_metadata: {}
  }
};

const tokenFixtures = {
  validTokens: {
    access_token: 'valid_access_token',
    refresh_token: 'valid_refresh_token',
    token_type: 'bearer' as const,
    expires_in: 3600
  },
  validAccessToken: 'valid_access_token',
  validRefreshToken: 'valid_refresh_token'
};

describe('Auth - MFA Operations', () => {
  let auth: Auth;
  let mockHttpClient: jest.Mocked<HttpClient>;
  let mockTokenManager: jest.Mocked<TokenManager>;
  let mockOnSignIn: jest.Mock;
  let mockOnSignOut: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();

    mockHttpClient = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      patch: jest.fn()
    } as any;

    mockTokenManager = {
      setTokens: jest.fn(),
      clearTokens: jest.fn(),
      getAccessToken: jest.fn(),
      getRefreshToken: jest.fn(),
      hasValidTokens: jest.fn()
    } as any;

    mockOnSignIn = jest.fn();
    mockOnSignOut = jest.fn();

    auth = new Auth(mockHttpClient, mockTokenManager, mockOnSignIn, mockOnSignOut);
  });

  describe('verifyMFA (enrollment confirmation)', () => {
    it('should confirm MFA enrollment with a TOTP code', async () => {
      // verifyMFA finalizes enrollment against POST /api/v1/mfa/verify and
      // returns { message } — it does NOT issue tokens. Token-issuing MFA during
      // sign-in is verifyMfaChallenge (tested below).
      const request = { code: '123456' };
      const mockResponse = { message: 'MFA successfully enabled' };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await auth.verifyMFA(request);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/v1/mfa/verify', request);
      expect(result).toEqual(mockResponse);
    });

    it('should reject a non-6-digit code before calling the API', async () => {
      await expect(auth.verifyMFA({ code: '12' })).rejects.toThrow();
      expect(mockHttpClient.post).not.toHaveBeenCalled();
    });
  });

  describe('verifyMfaChallenge (sign-in second factor)', () => {
    it('should complete the challenge and persist tokens', async () => {
      const mockResponse = {
        user: userFixtures.verifiedUser,
        tokens: tokenFixtures.validTokens
      };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await auth.verifyMfaChallenge('mfa-token-abc', '123456');

      expect(mockHttpClient.post).toHaveBeenCalledWith(
        '/api/v1/mfa/challenge/verify',
        { mfa_token: 'mfa-token-abc', code: '123456' },
        { skipAuth: true }
      );
      expect(mockTokenManager.setTokens).toHaveBeenCalledWith({
        access_token: tokenFixtures.validTokens.access_token,
        refresh_token: tokenFixtures.validTokens.refresh_token,
        expires_at: expect.any(Number)
      });
      expect(mockOnSignIn).toHaveBeenCalled();
      expect(result).toEqual({
        user: mockResponse.user,
        tokens: {
          access_token: tokenFixtures.validTokens.access_token,
          refresh_token: tokenFixtures.validTokens.refresh_token,
          expires_in: tokenFixtures.validTokens.expires_in,
          token_type: tokenFixtures.validTokens.token_type
        }
      });
    });

    it('should require a non-empty mfa_token and code', async () => {
      await expect(auth.verifyMfaChallenge('', '123456')).rejects.toThrow();
      await expect(auth.verifyMfaChallenge('mfa-token', '')).rejects.toThrow();
      expect(mockHttpClient.post).not.toHaveBeenCalled();
    });
  });

  describe('enableMFA', () => {
    it('should begin enrollment with the account password', async () => {
      const password = 'CurrentPassword123!';

      mockHttpClient.post.mockResolvedValue({
        data: {
          secret: 'MFASECRET123',
          qr_code: 'data:image/png;base64,...',
          backup_codes: ['code1', 'code2', 'code3'],
          provisioning_uri: 'otpauth://totp/Janua:test'
        }
      });

      const result = await auth.enableMFA(password);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/v1/mfa/enable', { password });
      expect(result).toEqual({
        secret: 'MFASECRET123',
        qr_code: 'data:image/png;base64,...',
        backup_codes: ['code1', 'code2', 'code3'],
        provisioning_uri: 'otpauth://totp/Janua:test'
      });
    });
  });

  describe('disableMFA', () => {
    it('should disable MFA successfully', async () => {
      const password = 'CurrentPassword123!';

      mockHttpClient.post.mockResolvedValue({
        data: {
          message: 'MFA successfully disabled'
        }
      });

      const result = await auth.disableMFA(password);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/v1/mfa/disable', { password });
      expect(result).toEqual({
        message: 'MFA successfully disabled'
      });
    });

    it('should include an optional code when provided', async () => {
      mockHttpClient.post.mockResolvedValue({ data: { message: 'ok' } });

      await auth.disableMFA('pw', '123456');

      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/v1/mfa/disable', {
        password: 'pw',
        code: '123456'
      });
    });
  });

  describe('getMFAStatus', () => {
    it('should get MFA status successfully', async () => {
      const mockResponse = {
        enabled: true,
        methods: ['totp', 'sms'],
        backup_codes_count: 8
      };

      mockHttpClient.get.mockResolvedValue({
        data: mockResponse
      });

      const result = await auth.getMFAStatus();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/mfa/status');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('regenerateMFABackupCodes', () => {
    it('should regenerate MFA backup codes successfully', async () => {
      const password = 'userpassword123';
      const mockResponse = {
        backup_codes: ['code1', 'code2', 'code3'],
        message: 'Backup codes regenerated successfully'
      };

      mockHttpClient.post.mockResolvedValue({
        data: mockResponse
      });

      const result = await auth.regenerateMFABackupCodes(password);

      // The handler binds `password` as a QUERY parameter, so it is sent via
      // `params`, not the JSON body.
      expect(mockHttpClient.post).toHaveBeenCalledWith(
        '/api/v1/mfa/regenerate-backup-codes',
        undefined,
        { params: { password } }
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('validateMFACode', () => {
    it('should validate MFA code successfully', async () => {
      const code = '123456';
      const mockResponse = { valid: true, message: 'Code is valid' };

      mockHttpClient.post.mockResolvedValue({
        data: mockResponse
      });

      const result = await auth.validateMFACode(code);

      // `code` is a QUERY parameter on the handler, sent via `params`.
      expect(mockHttpClient.post).toHaveBeenCalledWith(
        '/api/v1/mfa/validate-code',
        undefined,
        { params: { code } }
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getMFARecoveryOptions', () => {
    it('should get MFA recovery options successfully', async () => {
      const email = 'user@example.com';
      const mockResponse = {
        options: ['backup_codes', 'sms', 'email'],
        available_methods: ['sms'],
        message: 'Recovery options available'
      };

      mockHttpClient.get.mockResolvedValue({
        data: mockResponse
      });

      const result = await auth.getMFARecoveryOptions(email);

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/mfa/recovery-options?email=user%40example.com', {
        skipAuth: true
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('initiateMFARecovery', () => {
    it('should initiate MFA recovery successfully', async () => {
      const email = 'user@example.com';
      const mockResponse = { message: 'MFA recovery initiated successfully' };

      mockHttpClient.post.mockResolvedValue({
        data: mockResponse
      });

      const result = await auth.initiateMFARecovery(email);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/v1/mfa/initiate-recovery', {
        email: email
      }, { skipAuth: true });
      expect(result).toEqual(mockResponse);
    });
  });
});
