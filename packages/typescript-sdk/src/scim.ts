/**
 * SCIM 2.0 module for the Janua TypeScript SDK
 *
 * Provides SCIM configuration management for enterprise identity provider integration.
 * Supports Okta, Azure AD, OneLogin, Google Workspace, JumpCloud, and custom IdPs.
 */

import type { HttpClient } from './http-client';
import type { UUID, ISODateString } from './types';
import { ValidationError } from './errors';
import { ValidationUtils } from './utils';

// ========================================
// SCIM Types
// ========================================

export enum SCIMProvider {
  OKTA = 'okta',
  AZURE_AD = 'azure_ad',
  ONELOGIN = 'onelogin',
  GOOGLE_WORKSPACE = 'google_workspace',
  JUMPCLOUD = 'jumpcloud',
  PING_IDENTITY = 'ping_identity',
  CUSTOM = 'custom',
}

export enum SCIMSyncStatus {
  PENDING = 'pending',
  SYNCED = 'synced',
  ERROR = 'error',
}

export interface SCIMConfigCreate {
  provider?: SCIMProvider;
  enabled?: boolean;
  base_url?: string;
  configuration?: Record<string, unknown>;
}

export interface SCIMConfigUpdate {
  provider?: SCIMProvider;
  enabled?: boolean;
  configuration?: Record<string, unknown>;
}

export interface SCIMConfig {
  id: UUID;
  organization_id: UUID;
  provider: SCIMProvider;
  enabled: boolean;
  base_url: string;
  bearer_token_prefix?: string;
  configuration: Record<string, unknown>;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface SCIMTokenResponse {
  bearer_token: string;
  message: string;
}

export interface SCIMSyncLogEntry {
  id: UUID;
  operation: string;
  resource_type: string;
  scim_id?: string;
  internal_id?: UUID;
  status: string;
  error_message?: string;
  error_code?: string;
  synced_at: ISODateString;
}

export interface SCIMSyncStatusResponse {
  enabled: boolean;
  provider?: SCIMProvider;
  total_users: number;
  total_groups: number;
  synced_users: number;
  synced_groups: number;
  pending_users: number;
  pending_groups: number;
  error_users: number;
  error_groups: number;
  last_sync_at?: ISODateString;
  recent_operations: Array<{
    id: string;
    operation: string;
    resource_type: string;
    status: string;
    synced_at?: string;
    error_message?: string;
  }>;
}

export interface SCIMLogsOptions {
  limit?: number;
  offset?: number;
  status?: string;
  resource_type?: string;
}

// ========================================
// SCIM Module Class
// ========================================

export class SCIMModule {
  constructor(private readonly httpClient: HttpClient) {}

  // ========================================
  // Configuration Endpoints
  // ========================================

  /**
   * Create SCIM configuration for an organization.
   * Returns the configuration with a bearer token prefix.
   * Note: The full bearer token is only shown on creation.
   */
  async createConfig(
    organizationId: UUID,
    config: SCIMConfigCreate = {}
  ): Promise<SCIMConfig> {
    ValidationUtils.validateUUID(organizationId, 'organizationId');

    const response = await this.httpClient.post<SCIMConfig>(
      `/api/v1/organizations/${organizationId}/scim/config`,
      config
    );

    return response.data;
  }

  /**
   * Get SCIM configuration for an organization.
   * Returns the configuration without the full bearer token.
   */
  async getConfig(organizationId: UUID): Promise<SCIMConfig> {
    ValidationUtils.validateUUID(organizationId, 'organizationId');

    const response = await this.httpClient.get<SCIMConfig>(
      `/api/v1/organizations/${organizationId}/scim/config`
    );

    return response.data;
  }

  /**
   * Update SCIM configuration for an organization.
   */
  async updateConfig(
    organizationId: UUID,
    config: SCIMConfigUpdate
  ): Promise<SCIMConfig> {
    ValidationUtils.validateUUID(organizationId, 'organizationId');

    const response = await this.httpClient.put<SCIMConfig>(
      `/api/v1/organizations/${organizationId}/scim/config`,
      config
    );

    return response.data;
  }

  /**
   * Delete SCIM configuration for an organization.
   * Warning: This invalidates any configured IdP integrations.
   */
  async deleteConfig(organizationId: UUID): Promise<void> {
    ValidationUtils.validateUUID(organizationId, 'organizationId');

    await this.httpClient.delete(
      `/api/v1/organizations/${organizationId}/scim/config`
    );
  }

  /**
   * Rotate the SCIM bearer token.
   * Warning: This invalidates the previous token immediately.
   * The new token is only shown once - store it securely.
   */
  async rotateToken(organizationId: UUID): Promise<SCIMTokenResponse> {
    ValidationUtils.validateUUID(organizationId, 'organizationId');

    const response = await this.httpClient.post<SCIMTokenResponse>(
      `/api/v1/organizations/${organizationId}/scim/config/token`,
      {}
    );

    return response.data;
  }

  // ========================================
  // Status & Monitoring Endpoints
  // ========================================

  /**
   * Get SCIM sync status and statistics for an organization.
   * Shows overview of synced resources and recent operations.
   */
  async getSyncStatus(organizationId: UUID): Promise<SCIMSyncStatusResponse> {
    ValidationUtils.validateUUID(organizationId, 'organizationId');

    const response = await this.httpClient.get<SCIMSyncStatusResponse>(
      `/api/v1/organizations/${organizationId}/scim/status`
    );

    return response.data;
  }

  /**
   * Get SCIM sync operation logs for an organization.
   * Useful for debugging sync issues and auditing provisioning activity.
   */
  async getSyncLogs(
    organizationId: UUID,
    options: SCIMLogsOptions = {}
  ): Promise<SCIMSyncLogEntry[]> {
    ValidationUtils.validateUUID(organizationId, 'organizationId');

    const params = new URLSearchParams();
    if (options.limit !== undefined) params.append('limit', options.limit.toString());
    if (options.offset !== undefined) params.append('offset', options.offset.toString());
    if (options.status) params.append('status', options.status);
    if (options.resource_type) params.append('resource_type', options.resource_type);

    const queryString = params.toString();
    const url = `/api/v1/organizations/${organizationId}/scim/logs${
      queryString ? `?${queryString}` : ''
    }`;

    const response = await this.httpClient.get<SCIMSyncLogEntry[]>(url);

    return response.data;
  }

  // ========================================
  // Convenience Methods
  // ========================================

  /**
   * Enable SCIM for an organization.
   * Shorthand for updateConfig with enabled: true.
   */
  async enable(organizationId: UUID): Promise<SCIMConfig> {
    return this.updateConfig(organizationId, { enabled: true });
  }

  /**
   * Disable SCIM for an organization.
   * Shorthand for updateConfig with enabled: false.
   */
  async disable(organizationId: UUID): Promise<SCIMConfig> {
    return this.updateConfig(organizationId, { enabled: false });
  }

  /**
   * Check if SCIM is enabled for an organization.
   */
  async isEnabled(organizationId: UUID): Promise<boolean> {
    try {
      const config = await this.getConfig(organizationId);
      return config.enabled;
    } catch (error) {
      // If no config exists, SCIM is not enabled
      return false;
    }
  }

  /**
   * Get summary statistics for SCIM sync.
   */
  async getSyncSummary(
    organizationId: UUID
  ): Promise<{
    enabled: boolean;
    provider?: SCIMProvider;
    totalResources: number;
    syncedResources: number;
    pendingResources: number;
    errorResources: number;
    syncHealth: 'healthy' | 'degraded' | 'error' | 'disabled';
  }> {
    const status = await this.getSyncStatus(organizationId);

    const totalResources = status.total_users + status.total_groups;
    const syncedResources = status.synced_users + status.synced_groups;
    const pendingResources = status.pending_users + status.pending_groups;
    const errorResources = status.error_users + status.error_groups;

    let syncHealth: 'healthy' | 'degraded' | 'error' | 'disabled';
    if (!status.enabled) {
      syncHealth = 'disabled';
    } else if (errorResources > 0) {
      syncHealth = errorResources > syncedResources ? 'error' : 'degraded';
    } else if (pendingResources > 0) {
      syncHealth = 'degraded';
    } else {
      syncHealth = 'healthy';
    }

    return {
      enabled: status.enabled,
      provider: status.provider,
      totalResources,
      syncedResources,
      pendingResources,
      errorResources,
      syncHealth,
    };
  }
}

// ========================================
// Factory Function
// ========================================

export function createSCIMModule(httpClient: HttpClient): SCIMModule {
  return new SCIMModule(httpClient);
}
