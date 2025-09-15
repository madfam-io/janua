/**
 * Tests for Users suspension and permission operations
 */

import { Users } from '../../users';
import { ValidationError } from '../../errors';
import type { HttpClient } from '../../http-client';

describe('Users - Suspension & Permission Operations', () => {
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

  describe('suspendUser', () => {
    it('should suspend user successfully', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const reason = 'Violation of terms';
      const mockResponse = { message: 'User suspended successfully' };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await users.suspendUser(userId, reason);

      expect(mockHttpClient.post).toHaveBeenCalledWith(`/api/v1/users/${userId}/suspend`, {
        reason
      });
      expect(result).toEqual(mockResponse);
    });

    it('should suspend without reason', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const mockResponse = { message: 'User suspended successfully' };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await users.suspendUser(userId);

      expect(mockHttpClient.post).toHaveBeenCalledWith(`/api/v1/users/${userId}/suspend`, {
        reason: undefined
      });
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for invalid user ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.suspendUser('invalid')).rejects.toThrow(
        new ValidationError('Invalid user ID format')
      );

      delete process.env.NODE_ENV;
    });
  });

  describe('reactivateUser', () => {
    it('should reactivate suspended user', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const mockResponse = { message: 'User reactivated successfully' };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await users.reactivateUser(userId);

      expect(mockHttpClient.post).toHaveBeenCalledWith(`/api/v1/users/${userId}/reactivate`);
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for invalid user ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.reactivateUser('invalid')).rejects.toThrow(
        new ValidationError('Invalid user ID format')
      );

      delete process.env.NODE_ENV;
    });
  });

  describe('suspend (alias)', () => {
    it('should call suspendUser', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const reason = 'Violation of terms';
      const mockResponse = { message: 'User suspended successfully' };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await users.suspend(userId, reason);

      expect(mockHttpClient.post).toHaveBeenCalledWith(`/api/v1/users/${userId}/suspend`, {
        reason
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('unsuspend', () => {
    it('should unsuspend user successfully', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const mockResponse = { message: 'User unsuspended successfully' };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await users.unsuspend(userId);

      expect(mockHttpClient.post).toHaveBeenCalledWith(`/api/v1/users/${userId}/unsuspend`);
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for invalid user ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.unsuspend('invalid')).rejects.toThrow(
        new ValidationError('Invalid user ID format')
      );

      delete process.env.NODE_ENV;
    });
  });

  describe('getPermissions', () => {
    it('should get user permissions successfully', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const mockPermissions = [
        'users.read',
        'users.write',
        'organizations.read'
      ];

      mockHttpClient.get.mockResolvedValue({
        data: { permissions: mockPermissions }
      });

      const result = await users.getPermissions(userId);

      expect(mockHttpClient.get).toHaveBeenCalledWith(`/api/v1/users/${userId}/permissions`);
      expect(result).toEqual(mockPermissions);
    });

    it('should throw error for invalid user ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.getPermissions('invalid')).rejects.toThrow(
        new ValidationError('Invalid user ID format')
      );

      delete process.env.NODE_ENV;
    });
  });

  describe('updatePermissions', () => {
    it('should update user permissions successfully', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const permissions = [
        'users.read',
        'users.write',
        'organizations.read'
      ];

      const mockResponse = {
        success: true,
        permissions
      };

      mockHttpClient.put.mockResolvedValue({ data: mockResponse });

      const result = await users.updatePermissions(userId, permissions);

      expect(mockHttpClient.put).toHaveBeenCalledWith(
        `/api/v1/users/${userId}/permissions`,
        { permissions }
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle empty permissions array', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const permissions: string[] = [];

      const mockResponse = {
        success: true,
        permissions
      };

      mockHttpClient.put.mockResolvedValue({ data: mockResponse });

      const result = await users.updatePermissions(userId, permissions);

      expect(mockHttpClient.put).toHaveBeenCalledWith(
        `/api/v1/users/${userId}/permissions`,
        { permissions }
      );
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for invalid user ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.updatePermissions('invalid', [])).rejects.toThrow(
        new ValidationError('Invalid user ID format')
      );

      delete process.env.NODE_ENV;
    });
  });
});