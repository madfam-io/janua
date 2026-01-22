/**
 * URL and HTTP utilities
 */

/**
 * List of allowed URL schemes for security validation
 */
const ALLOWED_SCHEMES = ['http:', 'https:'];

/**
 * Validate and sanitize a URL to prevent open redirect and other URL-based attacks.
 * Returns the sanitized URL or null if the URL is invalid/unsafe.
 */
function validateUrl(url: string, allowedHosts?: string[]): string | null {
  if (!url || typeof url !== 'string') return null;

  try {
    const urlObj = new URL(url);

    // Check for allowed schemes only (prevent javascript:, data:, etc.)
    if (!ALLOWED_SCHEMES.includes(urlObj.protocol)) {
      return null;
    }

    // If allowedHosts is provided, verify the hostname matches exactly
    // Using exact match, not substring match to prevent bypass attacks
    if (allowedHosts && allowedHosts.length > 0) {
      const hostname = urlObj.hostname.toLowerCase();
      const isAllowed = allowedHosts.some(host => {
        const allowedHost = host.toLowerCase();
        // Exact match or subdomain match (e.g., api.example.com matches example.com)
        return hostname === allowedHost ||
               hostname.endsWith(`.${allowedHost}`);
      });

      if (!isAllowed) {
        return null;
      }
    }

    return urlObj.toString();
  } catch {
    return null;
  }
}

/**
 * Check if a URL is safe for redirect (same origin or allowed hosts)
 */
function isSafeRedirectUrl(url: string, currentOrigin: string, allowedHosts?: string[]): boolean {
  if (!url || typeof url !== 'string') return false;

  try {
    const urlObj = new URL(url);
    const originObj = new URL(currentOrigin);

    // Check for allowed schemes only
    if (!ALLOWED_SCHEMES.includes(urlObj.protocol)) {
      return false;
    }

    // Same origin is always safe
    if (urlObj.origin === originObj.origin) {
      return true;
    }

    // Check against allowed hosts if provided
    if (allowedHosts && allowedHosts.length > 0) {
      const hostname = urlObj.hostname.toLowerCase();
      return allowedHosts.some(host => {
        const allowedHost = host.toLowerCase();
        return hostname === allowedHost ||
               hostname.endsWith(`.${allowedHost}`);
      });
    }

    return false;
  } catch {
    return false;
  }
}

export class UrlUtils {
  /**
   * Build a URL with path and optional query parameters
   */
  static buildUrl(baseUrl: string, path: string, params?: Record<string, any>): string {
    // Ensure baseUrl doesn't end with slash and path starts with slash
    const cleanBase = baseUrl.replace(/\/$/, '');
    const cleanPath = path.startsWith('/') ? path : `/${path}`;

    let url = `${cleanBase}${cleanPath}`;

    if (params && Object.keys(params).length > 0) {
      const queryString = this.buildQueryString(params);
      url += `?${queryString}`;
    }

    return url;
  }

  /**
   * Build a query string from parameters
   */
  static buildQueryString(params: Record<string, any>): string {
    return Object.entries(params)
      .filter(([_key, value]) => value !== undefined && value !== null)
      .map(([key, value]) => {
        if (Array.isArray(value)) {
          return value.map(v => `${encodeURIComponent(key)}=${encodeURIComponent(v)}`).join('&');
        }
        return `${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
      })
      .join('&');
  }

  /**
   * Parse a query string into an object
   */
  static parseQueryString(queryString: string): Record<string, string | string[]> {
    const params: Record<string, string | string[]> = {};

    if (!queryString) return params;

    // Remove leading ? if present
    const cleanQuery = queryString.startsWith('?') ? queryString.slice(1) : queryString;

    cleanQuery.split('&').forEach(param => {
      const parts = param.split('=').map(decodeURIComponent);
      const key = parts[0];
      const value = parts[1] ?? '';

      if (!key) return;

      if (key in params) {
        // Convert to array if multiple values
        if (Array.isArray(params[key])) {
          (params[key] as string[]).push(value);
        } else {
          params[key] = [params[key] as string, value];
        }
      } else {
        params[key] = value;
      }
    });

    return params;
  }

  /**
   * Join URL paths safely
   */
  static joinPaths(...paths: string[]): string {
    return paths
      .map((path, index) => {
        // Remove leading slash except for first path
        if (index > 0) {
          path = path.replace(/^\/+/, '');
        }
        // Remove trailing slash except for last path
        if (index < paths.length - 1) {
          path = path.replace(/\/+$/, '');
        }
        return path;
      })
      .filter(Boolean)
      .join('/');
  }

  /**
   * Extract domain from URL safely
   * Uses URL parsing instead of substring matching to avoid bypass attacks
   */
  static extractDomain(url: string): string {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname;
    } catch {
      return '';
    }
  }

  /**
   * Check if URL is absolute (starts with http:// or https://)
   */
  static isAbsoluteUrl(url: string): boolean {
    // Use URL parsing for security instead of regex substring matching
    try {
      const urlObj = new URL(url);
      return ALLOWED_SCHEMES.includes(urlObj.protocol);
    } catch {
      return false;
    }
  }

  /**
   * Add or update query parameter in URL
   */
  static setQueryParam(url: string, key: string, value: string): string {
    const urlObj = new URL(url);
    urlObj.searchParams.set(key, value);
    return urlObj.toString();
  }

  /**
   * Remove query parameter from URL
   */
  static removeQueryParam(url: string, key: string): string {
    const urlObj = new URL(url);
    urlObj.searchParams.delete(key);
    return urlObj.toString();
  }

  /**
   * Validate and sanitize a URL for security.
   * Returns the sanitized URL or null if invalid/unsafe.
   *
   * @param url - The URL to validate
   * @param allowedHosts - Optional list of allowed hostnames (exact match or parent domain)
   * @returns Sanitized URL string or null if invalid
   */
  static validateUrl(url: string, allowedHosts?: string[]): string | null {
    return validateUrl(url, allowedHosts);
  }

  /**
   * Check if a URL is safe for redirect (same origin or allowed hosts).
   * Use this to prevent open redirect vulnerabilities.
   *
   * @param url - The redirect URL to check
   * @param currentOrigin - The current page origin (e.g., https://example.com)
   * @param allowedHosts - Optional list of additional allowed hostnames
   * @returns true if the URL is safe for redirect
   */
  static isSafeRedirectUrl(url: string, currentOrigin: string, allowedHosts?: string[]): boolean {
    return isSafeRedirectUrl(url, currentOrigin, allowedHosts);
  }

  /**
   * Check if a hostname matches an allowed pattern.
   * Uses exact matching, not substring matching to prevent bypass attacks.
   *
   * @param hostname - The hostname to check
   * @param allowedHost - The allowed host pattern
   * @returns true if the hostname matches
   */
  static isHostnameAllowed(hostname: string, allowedHost: string): boolean {
    const normalizedHostname = hostname.toLowerCase();
    const normalizedAllowed = allowedHost.toLowerCase();

    // Exact match
    if (normalizedHostname === normalizedAllowed) {
      return true;
    }

    // Subdomain match (e.g., api.example.com matches example.com)
    if (normalizedHostname.endsWith(`.${normalizedAllowed}`)) {
      return true;
    }

    return false;
  }
}

/**
 * HTTP status code utilities
 */
export class HttpStatusUtils {
  /**
   * Check if status code is successful (2xx)
   */
  static isSuccess(status: number): boolean {
    return status >= 200 && status < 300;
  }

  /**
   * Check if status code is redirect (3xx)
   */
  static isRedirect(status: number): boolean {
    return status >= 300 && status < 400;
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
   * Check if status code is error (4xx or 5xx)
   */
  static isError(status: number): boolean {
    return status >= 400;
  }

  /**
   * Get status text for common status codes
   */
  static getStatusText(status: number): string {
    const statusTexts: Record<number, string> = {
      200: 'OK',
      201: 'Created',
      204: 'No Content',
      400: 'Bad Request',
      401: 'Unauthorized',
      403: 'Forbidden',
      404: 'Not Found',
      409: 'Conflict',
      422: 'Unprocessable Entity',
      429: 'Too Many Requests',
      500: 'Internal Server Error',
      502: 'Bad Gateway',
      503: 'Service Unavailable',
      504: 'Gateway Timeout'
    };

    return statusTexts[status] || 'Unknown Status';
  }
}
