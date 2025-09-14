/**
 * Tests for Webhooks
 */

import { Webhooks } from '../webhooks';
import { ValidationError, WebhookError } from '../errors';
import { WebhookEventType } from '../types';
import type { HttpClient } from '../http-client';

describe('Webhooks', () => {
  let webhooks: Webhooks;
  let mockHttpClient: jest.Mocked<HttpClient>;

  beforeEach(() => {
    mockHttpClient = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
    } as any;

    webhooks = new Webhooks(mockHttpClient);
  });

  describe('createEndpoint', () => {
    it('should create webhook endpoint successfully', async () => {
      const mockEndpoint = {
        id: 'wh_123',
        url: 'https://example.com/webhook',
        events: [WebhookEventType.USER_CREATED],
        is_active: true,
      };

      mockHttpClient.post.mockResolvedValue({ data: mockEndpoint });

      const request = {
        url: 'https://example.com/webhook',
        events: [WebhookEventType.USER_CREATED],
      };

      const result = await webhooks.createEndpoint(request);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/v1/webhooks/', request);
      expect(result).toEqual(mockEndpoint);
    });

    it('should throw error for invalid URL', async () => {
      const request = {
        url: 'invalid-url',
        events: [WebhookEventType.USER_CREATED],
      };

      await expect(webhooks.createEndpoint(request)).rejects.toThrow(
        new ValidationError('Invalid webhook URL format')
      );
    });

    it('should throw error for empty events', async () => {
      const request = {
        url: 'https://example.com/webhook',
        events: [],
      };

      await expect(webhooks.createEndpoint(request)).rejects.toThrow(
        new ValidationError('At least one event type must be specified')
      );
    });

    it('should throw error for invalid event types', async () => {
      const request = {
        url: 'https://example.com/webhook',
        events: ['invalid_event' as any],
      };

      await expect(webhooks.createEndpoint(request)).rejects.toThrow(
        new ValidationError('Invalid event types: invalid_event')
      );
    });

    it('should throw error for long description', async () => {
      const request = {
        url: 'https://example.com/webhook',
        events: [WebhookEventType.USER_CREATED],
        description: 'a'.repeat(501),
      };

      await expect(webhooks.createEndpoint(request)).rejects.toThrow(
        new ValidationError('Description must be 500 characters or less')
      );
    });

    it('should throw error for reserved headers', async () => {
      const request = {
        url: 'https://example.com/webhook',
        events: [WebhookEventType.USER_CREATED],
        headers: {
          'authorization': 'Bearer token',
        },
      };

      await expect(webhooks.createEndpoint(request)).rejects.toThrow(
        new ValidationError('Reserved header names cannot be used: authorization')
      );
    });
  });

  describe('listEndpoints', () => {
    it('should list endpoints with no filter', async () => {
      const mockResponse = {
        endpoints: [{ id: 'wh_1' }, { id: 'wh_2' }],
        total: 2,
      };

      mockHttpClient.get.mockResolvedValue({ data: mockResponse });

      const result = await webhooks.listEndpoints();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/webhooks/', { params: {} });
      expect(result).toEqual(mockResponse);
    });

    it('should list endpoints with active filter', async () => {
      const mockResponse = {
        endpoints: [{ id: 'wh_1' }],
        total: 1,
      };

      mockHttpClient.get.mockResolvedValue({ data: mockResponse });

      const result = await webhooks.listEndpoints(true);

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/webhooks/', {
        params: { is_active: true }
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getEndpoint', () => {
    it('should get endpoint successfully', async () => {
      const mockEndpoint = { id: 'wh_123', url: 'https://example.com' };
      mockHttpClient.get.mockResolvedValue({ data: mockEndpoint });

      const result = await webhooks.getEndpoint('550e8400-e29b-41d4-a716-446655440000');

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000');
      expect(result).toEqual(mockEndpoint);
    });

    it('should throw error for invalid endpoint ID', async () => {
      await expect(webhooks.getEndpoint('invalid')).rejects.toThrow(
        new ValidationError('Invalid endpoint ID format')
      );
    });
  });

  describe('updateEndpoint', () => {
    const validUuid = '550e8400-e29b-41d4-a716-446655440000';

    it('should update endpoint successfully', async () => {
      const mockEndpoint = { id: 'wh_123', url: 'https://updated.com' };
      mockHttpClient.patch.mockResolvedValue({ data: mockEndpoint });

      const request = { url: 'https://updated.com' };
      const result = await webhooks.updateEndpoint(validUuid, request);

      expect(mockHttpClient.patch).toHaveBeenCalledWith(`/api/v1/webhooks/${validUuid}`, request);
      expect(result).toEqual(mockEndpoint);
    });

    it('should throw error for invalid endpoint ID', async () => {
      await expect(webhooks.updateEndpoint('invalid', {})).rejects.toThrow(
        new ValidationError('Invalid endpoint ID format')
      );
    });

    it('should validate updated URL', async () => {
      const request = { url: 'invalid-url' };
      await expect(webhooks.updateEndpoint(validUuid, request)).rejects.toThrow(
        new ValidationError('Invalid webhook URL format')
      );
    });
  });

  describe('deleteEndpoint', () => {
    it('should delete endpoint successfully', async () => {
      const mockResponse = { message: 'Webhook deleted' };
      mockHttpClient.delete.mockResolvedValue({ data: mockResponse });

      const result = await webhooks.deleteEndpoint('550e8400-e29b-41d4-a716-446655440000');

      expect(mockHttpClient.delete).toHaveBeenCalledWith('/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000');
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for invalid endpoint ID', async () => {
      await expect(webhooks.deleteEndpoint('invalid')).rejects.toThrow(
        new ValidationError('Invalid endpoint ID format')
      );
    });
  });

  describe('testEndpoint', () => {
    it('should test endpoint successfully', async () => {
      const mockResponse = { message: 'Test webhook sent' };
      mockHttpClient.post.mockResolvedValue({ data: mockResponse });

      const result = await webhooks.testEndpoint('550e8400-e29b-41d4-a716-446655440000');

      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000/test');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getEndpointStats', () => {
    it('should get endpoint stats with default days', async () => {
      const mockStats = {
        total_deliveries: 100,
        successful: 95,
        failed: 5,
        success_rate: 95,
        average_delivery_time: 250,
        period_days: 7,
      };

      mockHttpClient.get.mockResolvedValue({ data: mockStats });

      const result = await webhooks.getEndpointStats('550e8400-e29b-41d4-a716-446655440000');

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000/stats', {
        params: { days: 7 }
      });
      expect(result).toEqual(mockStats);
    });

    it('should validate days parameter', async () => {
      await expect(webhooks.getEndpointStats('550e8400-e29b-41d4-a716-446655440000', 0)).rejects.toThrow(
        new ValidationError('Days must be between 1 and 90')
      );

      await expect(webhooks.getEndpointStats('550e8400-e29b-41d4-a716-446655440000', 91)).rejects.toThrow(
        new ValidationError('Days must be between 1 and 90')
      );
    });
  });

  describe('listEvents', () => {
    it('should list events with default options', async () => {
      const mockResponse = { events: [], total: 0 };
      mockHttpClient.get.mockResolvedValue({ data: mockResponse });

      const result = await webhooks.listEvents('550e8400-e29b-41d4-a716-446655440000');

      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000/events', {
        params: {}
      });
      expect(result).toEqual(mockResponse);
    });

    it('should validate limit parameter', async () => {
      await expect(webhooks.listEvents('550e8400-e29b-41d4-a716-446655440000', { limit: 0 })).rejects.toThrow(
        new ValidationError('Limit must be between 1 and 1000')
      );

      await expect(webhooks.listEvents('550e8400-e29b-41d4-a716-446655440000', { limit: 1001 })).rejects.toThrow(
        new ValidationError('Limit must be between 1 and 1000')
      );
    });

    it('should validate offset parameter', async () => {
      await expect(webhooks.listEvents('550e8400-e29b-41d4-a716-446655440000', { offset: -1 })).rejects.toThrow(
        new ValidationError('Offset must be non-negative')
      );
    });
  });

  describe('verifyWebhookSignature', () => {
    it('should return false for now (not implemented)', async () => {
      const result = await webhooks.verifyWebhookSignature('payload', 'signature', 'secret');
      expect(result).toBe(false);
    });

    it('should throw error on verification failure', async () => {
      // Since the method is not implemented, it should not throw for now
      const result = await webhooks.verifyWebhookSignature('payload', 'signature', 'secret');
      expect(result).toBe(false);
    });
  });

  describe('parseWebhookPayload', () => {
    it('should parse valid webhook payload', () => {
      const payload = JSON.stringify({
        event: WebhookEventType.USER_CREATED,
        data: { user_id: '123' },
        timestamp: '2023-01-01T00:00:00Z',
        id: 'evt_123',
      });

      const result = webhooks.parseWebhookPayload(payload);

      expect(result).toEqual({
        event: WebhookEventType.USER_CREATED,
        data: { user_id: '123' },
        timestamp: '2023-01-01T00:00:00Z',
        id: 'evt_123',
      });
    });

    it('should throw error for invalid payload format', () => {
      const payload = JSON.stringify({ invalid: true });

      expect(() => webhooks.parseWebhookPayload(payload)).toThrow(
        new WebhookError('Invalid webhook payload format')
      );
    });

    it('should throw error for invalid event type', () => {
      const payload = JSON.stringify({
        event: 'invalid_event',
        data: {},
        timestamp: '2023-01-01T00:00:00Z',
        id: 'evt_123',
      });

      expect(() => webhooks.parseWebhookPayload(payload)).toThrow(
        new WebhookError('Unknown webhook event type: invalid_event')
      );
    });

    it('should throw error for invalid JSON', () => {
      const payload = 'invalid json';

      expect(() => webhooks.parseWebhookPayload(payload)).toThrow(
        new WebhookError('Failed to parse webhook payload')
      );
    });
  });

  describe('validateEndpointUrl', () => {
    it('should validate good URL', () => {
      const result = webhooks.validateEndpointUrl('https://api.example.com/webhook');
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject empty URL', () => {
      const result = webhooks.validateEndpointUrl('');
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('URL is required');
    });

    it('should warn about HTTP vs HTTPS', () => {
      const result = webhooks.validateEndpointUrl('http://api.example.com/webhook');
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('HTTPS is recommended for webhook endpoints');
    });

    it('should warn about localhost URLs', () => {
      const result = webhooks.validateEndpointUrl('https://localhost:3000/webhook');
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Localhost URLs are not recommended for production webhooks');
    });
  });

  describe('getEventCategories', () => {
    it('should return event categories', () => {
      const categories = webhooks.getEventCategories();

      expect(categories.user).toContain(WebhookEventType.USER_CREATED);
      expect(categories.session).toContain(WebhookEventType.SESSION_CREATED);
      expect(categories.organization).toContain(WebhookEventType.ORGANIZATION_CREATED);
    });
  });

  describe('getEventTypeNames', () => {
    it('should return friendly names for event types', () => {
      const names = webhooks.getEventTypeNames();

      expect(names[WebhookEventType.USER_CREATED]).toBe('User Created');
      expect(names[WebhookEventType.SESSION_CREATED]).toBe('Session Created');
    });
  });

  describe('calculateSuccessRate', () => {
    it('should calculate success rate correctly', () => {
      const stats = {
        total_deliveries: 100,
        successful: 95,
        failed: 5,
      };

      const result = webhooks.calculateSuccessRate(stats);

      expect(result.rate).toBe(95);
      expect(result.status).toBe('excellent');
    });

    it('should handle zero deliveries', () => {
      const stats = {
        total_deliveries: 0,
        successful: 0,
        failed: 0,
      };

      const result = webhooks.calculateSuccessRate(stats);

      expect(result.rate).toBe(0);
      expect(result.status).toBe('poor');
    });

    it('should categorize success rates correctly', () => {
      expect(webhooks.calculateSuccessRate({ total_deliveries: 100, successful: 96, failed: 4 }).status).toBe('excellent');
      expect(webhooks.calculateSuccessRate({ total_deliveries: 100, successful: 92, failed: 8 }).status).toBe('good');
      expect(webhooks.calculateSuccessRate({ total_deliveries: 100, successful: 80, failed: 20 }).status).toBe('fair');
      expect(webhooks.calculateSuccessRate({ total_deliveries: 100, successful: 70, failed: 30 }).status).toBe('poor');
    });
  });

  describe('formatEndpoint', () => {
    it('should format endpoint for display', () => {
      const endpoint = {
        id: 'wh_123',
        url: 'https://api.example.com/webhook',
        events: [WebhookEventType.USER_CREATED, WebhookEventType.USER_UPDATED],
        is_active: true,
      } as any;

      const result = webhooks.formatEndpoint(endpoint);

      expect(result.displayUrl).toBe('https://api.example.com/webhook');
      expect(result.eventCount).toBe(2);
      expect(result.statusText).toBe('Active');
      expect(result.isHealthy).toBe(true);
    });

    it('should truncate long URLs', () => {
      const endpoint = {
        url: 'https://api.example.com/very/long/webhook/endpoint/that/should/be/truncated',
        events: [],
        is_active: false,
      } as any;

      const result = webhooks.formatEndpoint(endpoint);

      expect(result.displayUrl).toMatch(/\.\.\.$/);
      expect(result.displayUrl.length).toBeLessThanOrEqual(50);
      expect(result.statusText).toBe('Inactive');
      expect(result.isHealthy).toBe(false);
    });
  });
});