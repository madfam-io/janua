/**
 * Tests for Users session management operations
 */

import { Users } from '../../users';
import { ValidationError } from '../../errors';
import type { HttpClient } from '../../http-client';

describe('Users - Session Operations', () => {
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

  describe('listSessions', () => {
    it('should list current user sessions', async () => {
      const mockSessions = [
        {
          id: 'session-1',
          user_id: '550e8400-e29b-41d4-a716-446655440000',
          ip_address: '192.168.1.1',
          device: 'Chrome on MacOS',
          created_at: '2023-01-01T00:00:00Z'
        },
        {
          id: 'session-2',
          user_id: '550e8400-e29b-41d4-a716-446655440000',
          ip_address: '192.168.1.2',
          device: 'Safari on iPhone',
          created_at: '2023-01-02T00:00:00Z'
        }
      ];

      const mockResponse = {
        sessions: mockSessions,
        total: 2
      };

      mockHttpClient.get.mockResolvedValue({ data: mockResponse });

      const result = await users.listSessions();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/sessions/', {
        params: undefined
      });
      expect(result.data).toEqual(mockSessions);
      expect(result.total).toEqual(2);
    });

    it('should list sessions with parameters', async () => {
      const params = { active: true };
      const mockResponse = {
        sessions: [],
        total: 0
      };

      mockHttpClient.get.mockResolvedValue({ data: mockResponse });

      const result = await users.listSessions(params);

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/sessions/', {
        params
      });
    });
  });

  describe('getSession', () => {
    it('should get session details', async () => {
      const sessionId = '550e8400-e29b-41d4-a716-446655440000';
      const mockSession = {
        id: sessionId,
        user_id: '550e8400-e29b-41d4-a716-446655440001',
        ip_address: '192.168.1.1',
        device: 'Chrome on MacOS'
      };

      mockHttpClient.get.mockResolvedValue({ data: mockSession });

      const result = await users.getSession(sessionId);

      expect(mockHttpClient.get).toHaveBeenCalledWith(`/api/v1/sessions/${sessionId}`);
      expect(result).toEqual(mockSession);
    });

    it('should throw error for invalid session ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.getSession('invalid')).rejects.toThrow(
        new ValidationError('Invalid session ID format')
      );

      delete process.env.NODE_ENV;
    });
  });

  describe('revokeSession', () => {
    it('should revoke session with single parameter (sessionId)', async () => {
      const sessionId = '550e8400-e29b-41d4-a716-446655440000';
      const mockResponse = { message: 'Session revoked successfully' };

      mockHttpClient.delete.mockResolvedValue({ data: mockResponse });

      const result = await users.revokeSession(sessionId);

      expect(mockHttpClient.delete).toHaveBeenCalledWith(`/api/v1/sessions/${sessionId}`);
      expect(result).toEqual(mockResponse);
    });

    it('should revoke session with userId and sessionId parameters', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const sessionId = '550e8400-e29b-41d4-a716-446655440001';
      const mockResponse = { message: 'Session revoked successfully' };

      mockHttpClient.delete.mockResolvedValue({ data: mockResponse });

      const result = await users.revokeSession(userId, sessionId);

      expect(mockHttpClient.delete).toHaveBeenCalledWith(`/api/v1/users/${userId}/sessions/${sessionId}`);
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for invalid session ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.revokeSession('invalid')).rejects.toThrow(
        new ValidationError('Invalid session ID format')
      );

      delete process.env.NODE_ENV;
    });
  });

  describe('revokeAllSessions', () => {
    it('should revoke all sessions except current', async () => {
      const mockResponse = {
        message: 'All sessions revoked successfully',
        revoked_count: 3
      };

      mockHttpClient.delete.mockResolvedValue({ data: mockResponse });

      const result = await users.revokeAllSessions();

      expect(mockHttpClient.delete).toHaveBeenCalledWith('/api/v1/sessions/');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('refreshSession', () => {
    it('should refresh session expiration', async () => {
      const sessionId = '550e8400-e29b-41d4-a716-446655440000';
      const mockResponse = { message: 'Session refreshed successfully' };

      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await users.refreshSession(sessionId);

      expect(mockHttpClient.post).toHaveBeenCalledWith(`/api/v1/sessions/${sessionId}/refresh`);
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for invalid session ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.refreshSession('invalid')).rejects.toThrow(
        new ValidationError('Invalid session ID format')
      );

      delete process.env.NODE_ENV;
    });
  });

  describe('getRecentActivity', () => {
    it('should get recent session activity with default limit', async () => {
      const mockResponse = {
        activities: [
          {
            session_id: 'session-1',
            activity_type: 'login',
            timestamp: '2023-01-01T00:00:00Z',
            ip_address: '192.168.1.1',
            device: 'Chrome',
            device_type: 'desktop',
            revoked: false
          }
        ],
        total: 1
      };

      mockHttpClient.get.mockResolvedValue({ data: mockResponse });

      const result = await users.getRecentActivity();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/sessions/activity/recent', {
        params: { limit: 10 }
      });
      expect(result).toEqual(mockResponse);
    });

    it('should get recent activity with custom limit', async () => {
      const limit = 5;
      const mockResponse = { activities: [], total: 0 };

      mockHttpClient.get.mockResolvedValue({ data: mockResponse });

      const result = await users.getRecentActivity(limit);

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/sessions/activity/recent', {
        params: { limit }
      });
    });

    it('should throw error for invalid limit', async () => {
      await expect(users.getRecentActivity(0)).rejects.toThrow(
        new ValidationError('Limit must be between 1 and 50')
      );

      await expect(users.getRecentActivity(51)).rejects.toThrow(
        new ValidationError('Limit must be between 1 and 50')
      );
    });
  });

  describe('getSecurityAlerts', () => {
    it('should get security alerts for sessions', async () => {
      const mockResponse = {
        alerts: [
          {
            type: 'suspicious_login',
            severity: 'medium',
            message: 'Login from new location',
            locations: ['New York, NY'],
            session_ids: ['session-1']
          }
        ],
        total: 1
      };

      mockHttpClient.get.mockResolvedValue({ data: mockResponse });

      const result = await users.getSecurityAlerts();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/sessions/security/alerts');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getSessions (alias)', () => {
    it('should get user sessions successfully', async () => {
      const userId = '550e8400-e29b-41d4-a716-446655440000';
      const mockSessions = [
        {
          id: 'session-1',
          user_id: userId,
          ip_address: '192.168.1.1',
          device: 'Chrome on MacOS',
          created_at: '2023-01-01T00:00:00Z'
        }
      ];

      mockHttpClient.get.mockResolvedValue({
        data: { sessions: mockSessions }
      });

      const result = await users.getSessions(userId);

      expect(mockHttpClient.get).toHaveBeenCalledWith(`/api/v1/users/${userId}/sessions`);
      expect(result).toEqual(mockSessions);
    });

    it('should throw error for invalid user ID', async () => {
      process.env.NODE_ENV = 'production';

      await expect(users.getSessions('invalid')).rejects.toThrow(
        new ValidationError('Invalid user ID format')
      );

      delete process.env.NODE_ENV;
    });
  });
});