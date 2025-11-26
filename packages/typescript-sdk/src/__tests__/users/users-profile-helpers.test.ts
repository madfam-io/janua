/**
 * Tests for Users profile helper functions
 */

import { Users } from '../../users';
import type { HttpClient } from '../../http-client';

describe('Users - Profile Helper Functions', () => {
  let users: Users;
  let mockHttpClient: jest.Mocked<HttpClient>;

  beforeEach(() => {
    mockHttpClient = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
    } as any;

    users = new Users(mockHttpClient);
  });

  describe('getDisplayName', () => {
    it('should return display_name if available', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        display_name: 'Display Name',
        first_name: 'First',
        last_name: 'Last',
        username: 'username'
      } as any;

      const result = users.getDisplayName(user);
      expect(result).toBe('Display Name');
    });

    it('should return first and last name combined', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        first_name: 'First',
        last_name: 'Last'
      } as any;

      const result = users.getDisplayName(user);
      expect(result).toBe('First Last');
    });

    it('should return first name only', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        first_name: 'First'
      } as any;

      const result = users.getDisplayName(user);
      expect(result).toBe('First');
    });

    it('should return username', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        username: 'testuser'
      } as any;

      const result = users.getDisplayName(user);
      expect(result).toBe('testuser');
    });

    it('should return email as fallback', () => {
      const user = {
        id: '1',
        email: 'test@example.com'
      } as any;

      const result = users.getDisplayName(user);
      expect(result).toBe('test@example.com');
    });

    it('should handle empty strings', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        display_name: '',
        first_name: '',
        last_name: '',
        username: ''
      } as any;

      const result = users.getDisplayName(user);
      expect(result).toBe('test@example.com');
    });
  });

  describe('getInitials', () => {
    it('should return initials from first and last name', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        first_name: 'First',
        last_name: 'Last'
      } as any;

      const result = users.getInitials(user);
      expect(result).toBe('FL');
    });

    it('should return first two letters of first name', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        first_name: 'FirstName'
      } as any;

      const result = users.getInitials(user);
      expect(result).toBe('FI');
    });

    it('should return first two letters of username', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        username: 'testuser'
      } as any;

      const result = users.getInitials(user);
      expect(result).toBe('TE');
    });

    it('should return first two letters of email', () => {
      const user = {
        id: '1',
        email: 'test@example.com'
      } as any;

      const result = users.getInitials(user);
      expect(result).toBe('TE');
    });

    it('should handle single character names', () => {
      const user = {
        id: '1',
        email: 'a@example.com',
        first_name: 'A'
      } as any;

      const result = users.getInitials(user);
      expect(result).toBe('A');
    });

    it('should handle empty strings', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        first_name: '',
        last_name: '',
        username: ''
      } as any;

      const result = users.getInitials(user);
      expect(result).toBe('TE');
    });
  });

  describe('isProfileComplete', () => {
    it('should return true for complete profile', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: true,
        first_name: 'First',
        last_name: 'Last',
        timezone: 'America/New_York'
      } as any;

      const result = users.isProfileComplete(user);
      expect(result).toBe(true);
    });

    it('should return false for incomplete profile', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: false,
        first_name: 'First'
      } as any;

      const result = users.isProfileComplete(user);
      expect(result).toBe(false);
    });

    it('should return false for missing email verification', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: false,
        first_name: 'First',
        last_name: 'Last',
        timezone: 'America/New_York'
      } as any;

      const result = users.isProfileComplete(user);
      expect(result).toBe(false);
    });

    it('should return false for missing timezone', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: true,
        first_name: 'First',
        last_name: 'Last'
      } as any;

      const result = users.isProfileComplete(user);
      expect(result).toBe(false);
    });
  });

  describe('getProfileCompletionPercentage', () => {
    it('should calculate profile completion percentage', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: true,
        first_name: 'First',
        last_name: 'Last',
        display_name: 'Display',
        bio: 'Bio text',
        timezone: 'America/New_York',
        profile_image_url: 'https://example.com/avatar.jpg'
      } as any;

      const result = users.getProfileCompletionPercentage(user);
      expect(result).toBe(100);
    });

    it('should handle partial completion', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: true,
        first_name: 'First',
        last_name: '',
        display_name: null,
        bio: undefined,
        timezone: 'America/New_York',
        profile_image_url: ''
      } as any;

      // 3 out of 7 fields completed: email_verified, first_name, timezone
      const result = users.getProfileCompletionPercentage(user);
      expect(result).toBe(43); // Math.round((3/7) * 100)
    });

    it('should handle completely empty profile', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: false
      } as any;

      const result = users.getProfileCompletionPercentage(user);
      expect(result).toBe(0);
    });

    it('should handle all fields with empty strings', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: false,
        first_name: '',
        last_name: '',
        display_name: '',
        bio: '',
        timezone: '',
        profile_image_url: ''
      } as any;

      const result = users.getProfileCompletionPercentage(user);
      expect(result).toBe(0);
    });
  });

  describe('getMissingProfileFields', () => {
    it('should return empty array for complete profile', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: true,
        first_name: 'First',
        last_name: 'Last',
        timezone: 'America/New_York'
      } as any;

      const result = users.getMissingProfileFields(user);
      expect(result).toEqual([]);
    });

    it('should return missing required fields', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: false,
        first_name: '',
        last_name: 'Last'
      } as any;

      const result = users.getMissingProfileFields(user);
      expect(result).toEqual(['Email verification', 'First name', 'Timezone']);
    });

    it('should return all missing fields', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: false
      } as any;

      const result = users.getMissingProfileFields(user);
      expect(result).toEqual(['Email verification', 'First name', 'Last name', 'Timezone']);
    });
  });

  describe('formatUser', () => {
    it('should format user with all computed fields', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: true,
        first_name: 'First',
        last_name: 'Last',
        timezone: 'America/New_York'
      } as any;

      const result = users.formatUser(user);

      expect(result.displayName).toBe('First Last');
      expect(result.initials).toBe('FL');
      expect(result.profileComplete).toBe(true);
      expect(result.completionPercentage).toBe(57); // 4 out of 7 fields
      expect(result.missingFields).toEqual([]);
    });

    it('should include original user data', () => {
      const user = {
        id: '1',
        email: 'test@example.com',
        email_verified: true,
        first_name: 'First',
        last_name: 'Last',
        timezone: 'America/New_York',
        custom_field: 'custom_value'
      } as any;

      const result = users.formatUser(user) as typeof user & { displayName: string; initials: string; profileComplete: boolean; completionPercentage: number; missingFields: string[] };

      expect(result.id).toBe('1');
      expect(result.email).toBe('test@example.com');
      expect((result as Record<string, unknown>).custom_field).toBe('custom_value');
    });
  });

  describe('Backward Compatibility Aliases', () => {
    describe('getById (alias)', () => {
      it('should call getUserById', async () => {
        const userId = '550e8400-e29b-41d4-a716-446655440000';
        const mockUser = {
          id: userId,
          email: 'test@example.com',
          first_name: 'Test',
          last_name: 'User'
        };

        mockHttpClient.get.mockResolvedValue({ data: mockUser });

        const result = await users.getById(userId);

        expect(mockHttpClient.get).toHaveBeenCalledWith(`/api/v1/users/${userId}`);
        expect(result).toEqual(mockUser);
      });
    });

    describe('list (alias)', () => {
      it('should list users with default parameters', async () => {
        const mockResponse = {
          users: [{ id: '1', email: 'user1@example.com' }],
          total: 1,
          page: 1,
          limit: 20
        };

        mockHttpClient.get.mockResolvedValue({ data: mockResponse });

        const result = await users.list();

        expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/users', {
          params: {}
        });
        expect(result).toEqual(mockResponse);
      });
    });
  });
});
