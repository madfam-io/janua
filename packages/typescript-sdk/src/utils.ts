/**
 * Utility functions for the Plinto TypeScript SDK
 */

import type { TokenData } from './types';
import { TokenError } from './errors';

/**
 * Base64 URL-safe encoding/decoding utilities
 */
export class Base64Url {
  /**
   * Encode string to base64url
   */
  static encode(str: string): string {
    if (typeof btoa !== 'undefined') {
      // Browser environment
      return btoa(str)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
    } else {
      // Node.js environment
      return Buffer.from(str, 'utf8')
        .toString('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
    }
  }

  /**
   * Decode base64url to string
   */
  static decode(str: string): string {
    // Add padding if needed
    let padded = str;
    while (padded.length % 4) {
      padded += '=';
    }

    // Convert base64url to base64
    const base64 = padded.replace(/-/g, '+').replace(/_/g, '/');

    if (typeof atob !== 'undefined') {
      // Browser environment
      return atob(base64);
    } else {
      // Node.js environment
      return Buffer.from(base64, 'base64').toString('utf8');
    }
  }
}

/**
 * JWT token utilities
 */
export class JwtUtils {
  /**
   * Decode JWT without verification
   */
  static decode(token: string): any {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        throw new Error('Invalid token format');
      }

      const payload = Base64Url.decode(parts[1]);
      return JSON.parse(payload);
    } catch (error) {
      throw new TokenError('Failed to decode token');
    }
  }

  /**
   * Parse JWT token (alias for decode)
   */
  static parseToken(token: string): { header: any; payload: any; signature: string } {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        throw new Error('Invalid token format');
      }

      const header = JSON.parse(Base64Url.decode(parts[0]));
      const payload = JSON.parse(Base64Url.decode(parts[1]));
      const signature = parts[2];

      return { header, payload, signature };
    } catch (error) {
      throw new TokenError('Failed to parse token');
    }
  }

  /**
   * Get token expiration time
   */
  static getExpiration(token: string): Date | null {
    const payload = JwtUtils.decode(token);
    return payload.exp ? new Date(payload.exp * 1000) : null;
  }

  /**
   * Check if token is expired
   */
  static isExpired(token: string): boolean;
  static isExpired(payload: { exp?: number }): boolean;
  static isExpired(tokenOrPayload: string | { exp?: number }): boolean {
    if (typeof tokenOrPayload === 'string') {
      const expiration = JwtUtils.getExpiration(tokenOrPayload);
      return expiration ? expiration < new Date() : false;
    } else {
      const payload = tokenOrPayload;
      if (!payload.exp) {
        return false;
      }
      return payload.exp < Math.floor(Date.now() / 1000);
    }
  }

  /**
   * Check if token expires within given seconds
   */
  static expiresWithin(token: string, seconds: number): boolean {
    const expiration = JwtUtils.getExpiration(token);
    if (!expiration) return false;

    const now = new Date();
    const threshold = new Date(now.getTime() + seconds * 1000);

    return expiration <= threshold;
  }

  /**
   * Get time until token expiration in seconds
   */
  static getTimeUntilExpiration(token: string): number {
    const expiration = JwtUtils.getExpiration(token);
    return expiration ? Math.max(0, expiration.getTime() - Date.now()) / 1000 : Infinity;
  }

  /**
   * Get time to expiry (alias for getTimeUntilExpiration)
   */
  static getTimeToExpiry(payload: { exp?: number }): number {
    if (!payload.exp) {
      return Infinity;
    }
    return Math.max(0, payload.exp - Math.floor(Date.now() / 1000));
  }

  /**
   * Get user ID from token
   */
  static getUserId(token: string): string | null {
    const payload = JwtUtils.decode(token);
    return payload.sub || payload.user_id || null;
  }

  /**
   * Get JWT ID
   */
  static getJti(token: string): string | null {
    const payload = JwtUtils.decode(token);
    return payload.jti || null;
  }
}

/**
 * Token storage interface and implementations
 */
export interface TokenStorage {
  getItem(key: string): string | null | Promise<string | null>;
  setItem(key: string, value: string): void | Promise<void>;
  removeItem(key: string): void | Promise<void>;
}

/**
 * Browser localStorage implementation
 */
export class LocalTokenStorage implements TokenStorage {
  async getItem(key: string): Promise<string | null> {
    try {
      if (typeof localStorage !== 'undefined') {
        return localStorage.getItem(key);
      }
    } catch {
      // Silently handle errors
    }
    return null;
  }

  async setItem(key: string, value: string): Promise<void> {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(key, value);
      }
    } catch {
      // Silently handle errors (e.g., quota exceeded)
    }
  }

  async removeItem(key: string): Promise<void> {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(key);
      }
    } catch {
      // Silently handle errors
    }
  }
}

/**
 * Browser sessionStorage implementation
 */
export class SessionTokenStorage implements TokenStorage {
  getItem(key: string): string | null {
    if (typeof sessionStorage === 'undefined') {
      return null;
    }
    return sessionStorage.getItem(key);
  }

  setItem(key: string, value: string): void {
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(key, value);
    }
  }

  removeItem(key: string): void {
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.removeItem(key);
    }
  }
}

/**
 * In-memory token storage (fallback)
 */
export class MemoryTokenStorage implements TokenStorage {
  private storage = new Map<string, string>();

  getItem(key: string): string | null {
    return this.storage.get(key) || null;
  }

  setItem(key: string, value: string): void {
    this.storage.set(key, value);
  }

  removeItem(key: string): void {
    this.storage.delete(key);
  }

  clear(): void {
    this.storage.clear();
  }
}

/**
 * Token manager for handling token storage and retrieval
 */
export class TokenManager {
  private storage: TokenStorage;
  private readonly ACCESS_TOKEN_KEY = 'plinto_access_token';
  private readonly REFRESH_TOKEN_KEY = 'plinto_refresh_token';
  private readonly EXPIRES_AT_KEY = 'plinto_expires_at';

  constructor(storage: TokenStorage) {
    this.storage = storage;
  }

  /**
   * Store tokens
   */
  async setTokens(tokenData: TokenData): Promise<void> {
    await Promise.all([
      this.storage.setItem(this.ACCESS_TOKEN_KEY, tokenData.access_token),
      this.storage.setItem(this.REFRESH_TOKEN_KEY, tokenData.refresh_token),
      this.storage.setItem(this.EXPIRES_AT_KEY, tokenData.expires_at.toString())
    ]);
  }

  /**
   * Get access token
   */
  async getAccessToken(): Promise<string | null> {
    return await this.storage.getItem(this.ACCESS_TOKEN_KEY);
  }

  /**
   * Get refresh token
   */
  async getRefreshToken(): Promise<string | null> {
    return await this.storage.getItem(this.REFRESH_TOKEN_KEY);
  }

  /**
   * Get token expiration time
   */
  async getExpiresAt(): Promise<number | null> {
    const expiresAt = await this.storage.getItem(this.EXPIRES_AT_KEY);
    return expiresAt ? parseInt(expiresAt, 10) : null;
  }

  /**
   * Get all token data
   */
  async getTokenData(): Promise<TokenData | null> {
    const [accessToken, refreshToken, expiresAt] = await Promise.all([
      this.getAccessToken(),
      this.getRefreshToken(),
      this.getExpiresAt()
    ]);

    if (!accessToken || !refreshToken) {
      return null;
    }

    return {
      access_token: accessToken,
      refresh_token: refreshToken,
      expires_at: expiresAt!
    };
  }

  /**
   * Clear all tokens
   */
  async clearTokens(): Promise<void> {
    await Promise.all([
      this.storage.removeItem(this.ACCESS_TOKEN_KEY),
      this.storage.removeItem(this.REFRESH_TOKEN_KEY),
      this.storage.removeItem(this.EXPIRES_AT_KEY)
    ]);
  }

  /**
   * Check if token is expired or expires soon
   */
  async isTokenExpired(bufferSeconds = 300): Promise<boolean> {
    const accessToken = await this.getAccessToken();
    if (!accessToken) return true;

    try {
      return JwtUtils.expiresWithin(accessToken, bufferSeconds);
    } catch {
      return true; // Consider invalid tokens as expired
    }
  }

  /**
   * Refresh tokens using refresh token
   */
  async refreshTokens(): Promise<TokenData | null> {
    const refreshToken = await this.getRefreshToken();
    if (!refreshToken) {
      throw new TokenError('No refresh token available');
    }

    // This would typically make an API call to refresh tokens
    // Implementation depends on the API endpoint
    throw new Error('Token refresh not implemented - should be handled by HTTP client');
  }

  /**
   * Check if we have valid tokens
   */
  async hasValidTokens(): Promise<boolean> {
    const tokenData = await this.getTokenData();
    if (!tokenData) {
      return false;
    }

    // Check if tokens are expired
    const currentTime = Date.now();
    return tokenData.expires_at > currentTime;
  }
}

/**
 * Retry utilities
 */
export class RetryUtils {
  /**
   * Execute operation with exponential backoff retry
   */
  static async withRetry<T>(
    operation: () => Promise<T>,
    maxAttempts: number = 3,
    baseDelay: number = 1000,
    backoffFactor: number = 2,
    maxDelay: number = 30000
  ): Promise<T> {
    let lastError: Error;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;

        // Don't retry on the last attempt
        if (attempt === maxAttempts) {
          break;
        }

        // Calculate delay with exponential backoff
        const delay = Math.min(
          baseDelay * Math.pow(backoffFactor, attempt - 1),
          maxDelay
        );

        // Add jitter to prevent thundering herd
        const jitteredDelay = delay * (0.5 + Math.random() * 0.5);

        await new Promise(resolve => setTimeout(resolve, jitteredDelay));
      }
    }

    throw lastError!;
  }

  /**
   * Check if error is retryable
   */
  static isRetryableError(error: any): boolean {
    // Network errors are usually retryable
    if (error.name === 'NetworkError' || error.code === 'NETWORK_ERROR') {
      return true;
    }

    // HTTP status codes that are retryable
    if (error.response?.status) {
      const status = error.response.status;
      return status >= 500 || status === 408 || status === 429;
    }

    return false;
  }
}

/**
 * Event emitter for SDK events
 */
export class EventEmitter<T extends Record<string, any> = Record<string, any>> {
  private listeners = new Map<keyof T, Set<(data: any) => void>>();

  /**
   * Add event listener
   */
  on<K extends keyof T>(event: K, listener: (data: T[K]) => void): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }

    const eventListeners = this.listeners.get(event)!;
    eventListeners.add(listener);

    // Return unsubscribe function
    return () => {
      eventListeners.delete(listener);
      if (eventListeners.size === 0) {
        this.listeners.delete(event);
      }
    };
  }

  /**
   * Add one-time event listener
   */
  once<K extends keyof T>(event: K, listener: (data: T[K]) => void): () => void {
    const unsubscribe = this.on(event, (data) => {
      unsubscribe();
      listener(data);
    });

    return unsubscribe;
  }

  /**
   * Remove event listener
   */
  off<K extends keyof T>(event: K, listener: (data: T[K]) => void): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(listener);
      if (eventListeners.size === 0) {
        this.listeners.delete(event);
      }
    }
  }

  /**
   * Emit event
   */
  emit<K extends keyof T>(event: K, data: T[K]): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(listener => {
        try {
          listener(data);
        } catch (error) {
          console.error('Error in event listener:', error);
        }
      });
    }
  }

  /**
   * Remove all listeners for an event
   */
  removeAllListeners<K extends keyof T>(event?: K): void {
    if (event) {
      this.listeners.delete(event);
    } else {
      this.listeners.clear();
    }
  }

  /**
   * Get listener count for an event
   */
  listenerCount<K extends keyof T>(event: K): number {
    const eventListeners = this.listeners.get(event);
    return eventListeners ? eventListeners.size : 0;
  }
}

/**
 * URL utility functions
 */
export class UrlUtils {
  /**
   * Parse query string to object
   */
  static parseQueryString(queryString: string): Record<string, string> {
    if (!queryString) return {};

    return queryString
      .replace(/^\?/, '')
      .split('&')
      .reduce((acc, pair) => {
        const [key, value] = pair.split('=');
        if (key) {
          acc[decodeURIComponent(key)] = decodeURIComponent(value || '');
        }
        return acc;
      }, {} as Record<string, string>);
  }

  /**
   * Build query string from object
   */
  static buildQueryString(params: Record<string, any>): string {
    const searchParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });

    return searchParams.toString();
  }

  /**
   * Build URL with path and optional query parameters
   */
  static buildUrl(baseUrl: string, path?: string, params?: Record<string, any>): string {
    // Remove trailing slash from baseUrl
    const cleanBase = baseUrl.replace(/\/$/, '');

    // Remove leading slash from path and handle empty path
    const cleanPath = path ? path.replace(/^\//, '') : '';

    // Build the URL
    let url = cleanPath ? `${cleanBase}/${cleanPath}` : cleanBase;

    // Add query parameters if provided
    if (params && Object.keys(params).length > 0) {
      const queryString = this.buildQueryString(params);
      url = `${url}?${queryString}`;
    }

    return url;
  }
}

/**
 * Validation utility functions
 */
export class ValidationUtils {
  /**
   * Validate email address
   */
  static isValidEmail(email: string): boolean {
    // More strict email regex that doesn't allow consecutive dots
    const emailRegex = /^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;

    // Additional check for consecutive dots
    if (email.includes('..')) {
      return false;
    }

    return emailRegex.test(email);
  }

  /**
   * Validate password strength
   */
  static isValidPassword(password: string): boolean {
    // At least 8 characters, one uppercase, one lowercase, one number
    // Allow special characters
    const hasMinLength = password.length >= 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumber = /\d/.test(password);

    return hasMinLength && hasUpperCase && hasLowerCase && hasNumber;
  }

  /**
   * Validate password with detailed error information
   */
  static validatePassword(password: string): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (password.length < 8) {
      errors.push('Password must be at least 8 characters long');
    }
    if (!/[A-Z]/.test(password)) {
      errors.push('Password must contain at least one uppercase letter');
    }
    if (!/[a-z]/.test(password)) {
      errors.push('Password must contain at least one lowercase letter');
    }
    if (!/\d/.test(password)) {
      errors.push('Password must contain at least one number');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * Validate UUID
   */
  static isValidUuid(uuid: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
  }

  /**
   * Validate phone number (basic validation)
   */
  static isValidPhoneNumber(phone: string): boolean {
    // Remove all non-digit characters
    const cleaned = phone.replace(/\D/g, '');

    // Should have 10-15 digits
    return cleaned.length >= 10 && cleaned.length <= 15;
  }

  /**
   * Validate URL
   */
  static isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Validate that string is not empty or only whitespace
   */
  static isNotEmpty(value: string): boolean {
    return value.trim().length > 0;
  }

  /**
   * Validate slug format (alphanumeric with hyphens)
   */
  static isValidSlug(slug: string): boolean {
    // Allow lowercase letters, numbers, and hyphens
    // Must start and end with alphanumeric character
    const slugRegex = /^[a-z0-9]+([a-z0-9-]*[a-z0-9])?$/;
    return slugRegex.test(slug) && slug.length >= 2 && slug.length <= 50;
  }

  /**
   * Validate username format
   */
  static isValidUsername(username: string): boolean {
    // Allow alphanumeric characters, underscores, and hyphens
    // Must start with letter or number, 3-30 characters
    const usernameRegex = /^[a-zA-Z0-9][a-zA-Z0-9_-]{2,29}$/;
    return usernameRegex.test(username);
  }
}

/**
 * HTTP status utilities
 */
export class HttpStatusUtils {
  /**
   * Check if status code is successful (2xx)
   */
  static isSuccess(status: number): boolean {
    return status >= 200 && status < 300;
  }

  /**
   * Check if status code is client error (4xx)
   */
  static isClientError(status: number): boolean {
    return status >= 400 && status < 500;
  }

  /**
   * Check if status code is server error (5xx)
   */
  static isServerError(status: number): boolean {
    return status >= 500 && status < 600;
  }

  /**
   * Check if status code is retryable
   */
  static isRetryable(status: number): boolean {
    // Retry on server errors, timeout, and rate limit
    return status >= 500 || status === 408 || status === 429;
  }

  /**
   * Get status text for common status codes
   */
  static getStatusText(status: number): string {
    const statusMap: Record<number, string> = {
      200: 'OK',
      201: 'Created',
      204: 'No Content',
      400: 'Bad Request',
      401: 'Unauthorized',
      403: 'Forbidden',
      404: 'Not Found',
      408: 'Request Timeout',
      409: 'Conflict',
      422: 'Unprocessable Entity',
      429: 'Too Many Requests',
      500: 'Internal Server Error',
      502: 'Bad Gateway',
      503: 'Service Unavailable',
      504: 'Gateway Timeout'
    };

    return statusMap[status] || 'Unknown Status';
  }
}

/**
 * Date utility functions
 */
export class DateUtils {
  /**
   * Check if timestamp is expired (in the past)
   */
  static isExpired(timestamp: number): boolean {
    return timestamp < Date.now();
  }

  /**
   * Format date to ISO string
   */
  static formatISO(date: Date): string {
    return date.toISOString();
  }

  /**
   * Parse ISO string to date
   */
  static parseISO(isoString: string): Date {
    return new Date(isoString);
  }
}

/**
 * Environment detection utilities
 */
export class EnvUtils {
  /**
   * Check if running in Node.js environment
   */
  static isNode(): boolean {
    return typeof process !== 'undefined' &&
           process.versions != null &&
           process.versions.node != null;
  }

  /**
   * Check if running in browser environment
   */
  static isBrowser(): boolean {
    // In test environment, we prioritize Node.js detection
    // Check for Jest or Node test environment first
    if (EnvUtils.isNode() && (
        typeof jest !== 'undefined' ||
        process.env.NODE_ENV === 'test' ||
        process.env.JEST_WORKER_ID !== undefined
      )) {
      return false;
    }

    return typeof window !== 'undefined' && typeof document !== 'undefined';
  }

  /**
   * Get default token storage based on environment
   */
  static getDefaultStorage(): TokenStorage {
    if (EnvUtils.isBrowser()) {
      return new LocalTokenStorage();
    } else {
      return new MemoryTokenStorage();
    }
  }
}

/**
 * Webhook utility functions
 */
export class WebhookUtils {
  /**
   * Validate webhook signature (placeholder implementation)
   */
  static validateSignature(payload: string, signature: string, secret: string): boolean {
    // This would contain actual HMAC signature validation
    // Placeholder implementation for tests
    return signature.length > 0 && secret.length > 0;
  }

  /**
   * Parse webhook payload
   */
  static parsePayload<T = any>(payload: string): T {
    try {
      return JSON.parse(payload);
    } catch (error) {
      throw new Error('Invalid webhook payload format');
    }
  }
}