/**
 * Tests for Users avatar operations
 */

import { Users } from '../../users';
import { ValidationError } from '../../errors';
import type { HttpClient } from '../../http-client';

describe('Users - Avatar Operations', () => {
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

  describe('uploadAvatar', () => {
    it('should upload user avatar successfully', async () => {
      const mockFile = new Blob(['test'], { type: 'image/jpeg' });
      Object.defineProperty(mockFile, 'size', { value: 1024 });
      Object.defineProperty(mockFile, 'type', { value: 'image/jpeg' });

      const mockResponse = { profile_image_url: 'https://example.com/avatar.jpg' };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await users.uploadAvatar(mockFile);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/v1/users/me/avatar', expect.any(FormData), {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for oversized file', async () => {
      const mockFile = new Blob(['test'], { type: 'image/jpeg' });
      Object.defineProperty(mockFile, 'size', { value: 6 * 1024 * 1024 }); // 6MB
      Object.defineProperty(mockFile, 'type', { value: 'image/jpeg' });

      await expect(users.uploadAvatar(mockFile)).rejects.toThrow(
        new ValidationError('File size must be less than 5MB')
      );
    });

    it('should throw error for invalid file type', async () => {
      const mockFile = new Blob(['test'], { type: 'text/plain' });
      Object.defineProperty(mockFile, 'size', { value: 1024 });
      Object.defineProperty(mockFile, 'type', { value: 'text/plain' });

      await expect(users.uploadAvatar(mockFile)).rejects.toThrow(
        new ValidationError('Invalid file type. Allowed types: JPEG, PNG, GIF, WebP')
      );
    });

    it('should accept different image formats', async () => {
      const imageTypes = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp'
      ];

      for (const imageType of imageTypes) {
        const mockFile = new Blob(['test'], { type: imageType });
        Object.defineProperty(mockFile, 'size', { value: 1024 });
        Object.defineProperty(mockFile, 'type', { value: imageType });

        const mockResponse = { profile_image_url: 'https://example.com/avatar.jpg' };
        mockHttpClient.post.mockResolvedValue({ data: mockResponse });

        const result = await users.uploadAvatar(mockFile);

        expect(result).toEqual(mockResponse);
      }
    });

    it('should handle file at size limit', async () => {
      const mockFile = new Blob(['test'], { type: 'image/jpeg' });
      Object.defineProperty(mockFile, 'size', { value: 5 * 1024 * 1024 - 1 }); // Just under 5MB
      Object.defineProperty(mockFile, 'type', { value: 'image/jpeg' });

      const mockResponse = { profile_image_url: 'https://example.com/avatar.jpg' };
      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await users.uploadAvatar(mockFile);

      expect(result).toEqual(mockResponse);
    });
  });

  describe('deleteAvatar', () => {
    it('should delete user avatar', async () => {
      const mockResponse = { message: 'Avatar deleted successfully' };

      mockHttpClient.delete.mockResolvedValue({ data: mockResponse });

      const result = await users.deleteAvatar();

      expect(mockHttpClient.delete).toHaveBeenCalledWith('/api/v1/users/me/avatar');
      expect(result).toEqual(mockResponse);
    });

    it('should handle deletion when no avatar exists', async () => {
      const mockResponse = { message: 'No avatar to delete' };

      mockHttpClient.delete.mockResolvedValue({ data: mockResponse });

      const result = await users.deleteAvatar();

      expect(mockHttpClient.delete).toHaveBeenCalledWith('/api/v1/users/me/avatar');
      expect(result).toEqual(mockResponse);
    });
  });
});