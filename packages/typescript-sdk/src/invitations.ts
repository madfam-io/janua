/**
 * Invitations module for the Plinto TypeScript SDK
 *
 * Provides organization invitation management capabilities.
 */

import type { HttpClient } from './http-client';
import type { UUID, ISODateString } from './types';
import { ValidationError } from './errors';
import { ValidationUtils } from './utils';

// Invitation Types

export enum InvitationStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  EXPIRED = 'expired',
  REVOKED = 'revoked'
}

export interface InvitationCreate {
  organization_id: UUID;
  email: string;
  role?: string; // 'owner' | 'admin' | 'member' | 'viewer'
  message?: string;
  expires_in?: number; // days (1-30)
}

export interface InvitationUpdate {
  role?: string;
  message?: string;
  expires_at?: ISODateString;
}

export interface Invitation {
  id: UUID;
  organization_id: UUID;
  email: string;
  role: string;
  status: InvitationStatus;
  invited_by: UUID;
  message?: string;
  expires_at: ISODateString;
  created_at: ISODateString;
  invite_url: string;
  email_sent: boolean;
}

export interface InvitationListParams {
  organization_id?: UUID;
  status?: InvitationStatus;
  email?: string;
  skip?: number;
  limit?: number;
}

export interface InvitationListResponse {
  invitations: Invitation[];
  total: number;
  pending_count: number;
  accepted_count: number;
  expired_count: number;
}

export interface InvitationAcceptRequest {
  token: string;
  user_id?: UUID; // If user already exists
  // For new user registration
  name?: string;
  password?: string;
}

export interface InvitationAcceptResponse {
  success: boolean;
  user_id: UUID;
  organization_id: UUID;
  message: string;
  is_new_user: boolean;
}

export interface InvitationValidateResponse {
  valid: boolean;
  reason?: string;
  email?: string;
  organization_id?: UUID;
  organization_name?: string;
  role?: string;
  expires_at?: ISODateString;
  message?: string;
}

export interface BulkInvitationCreate {
  organization_id: UUID;
  emails: string[];
  role?: string;
  message?: string;
  expires_in?: number; // days
}

export interface BulkInvitationResponse {
  successful: Invitation[];
  failed: Array<{ email: string; error: string }>;
  total_sent: number;
  total_failed: number;
}

/**
 * Invitation management operations
 */
export class Invitations {
  constructor(private http: HttpClient) {}

  /**
   * Create a new invitation
   *
   * @param invitation - Invitation details
   * @returns Created invitation
   */
  async createInvitation(invitation: InvitationCreate): Promise<Invitation> {
    // Validate organization ID
    if (!ValidationUtils.isValidUuid(invitation.organization_id)) {
      throw new ValidationError('Invalid organization ID format');
    }

    // Validate email
    if (!ValidationUtils.isValidEmail(invitation.email)) {
      throw new ValidationError('Invalid email format');
    }

    // Validate role
    if (invitation.role && !['owner', 'admin', 'member', 'viewer'].includes(invitation.role)) {
      throw new ValidationError('Invalid role. Must be owner, admin, member, or viewer');
    }

    // Validate message length
    if (invitation.message && invitation.message.length > 500) {
      throw new ValidationError('Message must be 500 characters or less');
    }

    // Validate expires_in
    if (invitation.expires_in !== undefined) {
      if (invitation.expires_in < 1 || invitation.expires_in > 30) {
        throw new ValidationError('Expiration must be between 1 and 30 days');
      }
    }

    const response = await this.http.post<Invitation>('/api/v1/invitations', invitation);
    return response.data;
  }

  /**
   * Create multiple invitations at once
   *
   * @param bulkInvitation - Bulk invitation details
   * @returns Result with successful and failed invitations
   */
  async createBulkInvitations(bulkInvitation: BulkInvitationCreate): Promise<BulkInvitationResponse> {
    // Validate organization ID
    if (!ValidationUtils.isValidUuid(bulkInvitation.organization_id)) {
      throw new ValidationError('Invalid organization ID format');
    }

    // Validate emails
    if (!bulkInvitation.emails || bulkInvitation.emails.length === 0) {
      throw new ValidationError('At least one email is required');
    }

    if (bulkInvitation.emails.length > 100) {
      throw new ValidationError('Maximum 100 emails allowed per bulk invitation');
    }

    for (const email of bulkInvitation.emails) {
      if (!ValidationUtils.isValidEmail(email)) {
        throw new ValidationError(`Invalid email format: ${email}`);
      }
    }

    // Validate role
    if (bulkInvitation.role && !['owner', 'admin', 'member', 'viewer'].includes(bulkInvitation.role)) {
      throw new ValidationError('Invalid role. Must be owner, admin, member, or viewer');
    }

    // Validate message length
    if (bulkInvitation.message && bulkInvitation.message.length > 500) {
      throw new ValidationError('Message must be 500 characters or less');
    }

    // Validate expires_in
    if (bulkInvitation.expires_in !== undefined) {
      if (bulkInvitation.expires_in < 1 || bulkInvitation.expires_in > 30) {
        throw new ValidationError('Expiration must be between 1 and 30 days');
      }
    }

    const response = await this.http.post<BulkInvitationResponse>(
      '/api/v1/invitations/bulk',
      bulkInvitation
    );
    return response.data;
  }

  /**
   * List invitations with optional filtering
   *
   * @param params - Filter and pagination parameters
   * @returns Paginated invitation list with counts
   */
  async listInvitations(params?: InvitationListParams): Promise<InvitationListResponse> {
    // Validate organization ID if provided
    if (params?.organization_id && !ValidationUtils.isValidUuid(params.organization_id)) {
      throw new ValidationError('Invalid organization ID format');
    }

    // Validate status if provided
    if (params?.status && !Object.values(InvitationStatus).includes(params.status)) {
      throw new ValidationError('Invalid invitation status');
    }

    // Validate pagination
    if (params?.skip !== undefined && params.skip < 0) {
      throw new ValidationError('Skip must be non-negative');
    }

    if (params?.limit !== undefined) {
      if (params.limit < 1 || params.limit > 1000) {
        throw new ValidationError('Limit must be between 1 and 1000');
      }
    }

    // Build query string
    const queryParams = new URLSearchParams();
    if (params?.organization_id) queryParams.append('organization_id', params.organization_id);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.email) queryParams.append('email', params.email);
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

    const queryString = queryParams.toString();
    const url = queryString ? `/api/v1/invitations?${queryString}` : '/api/v1/invitations';

    const response = await this.http.get<InvitationListResponse>(url);
    return response.data;
  }

  /**
   * Get a specific invitation by ID
   *
   * @param invitationId - Invitation ID
   * @returns Invitation details
   */
  async getInvitation(invitationId: UUID): Promise<Invitation> {
    if (!ValidationUtils.isValidUuid(invitationId)) {
      throw new ValidationError('Invalid invitation ID format');
    }

    const response = await this.http.get<Invitation>(`/api/v1/invitations/${invitationId}`);
    return response.data;
  }

  /**
   * Update a pending invitation
   *
   * @param invitationId - Invitation ID
   * @param update - Fields to update
   * @returns Updated invitation
   */
  async updateInvitation(invitationId: UUID, update: InvitationUpdate): Promise<Invitation> {
    if (!ValidationUtils.isValidUuid(invitationId)) {
      throw new ValidationError('Invalid invitation ID format');
    }

    // Validate role if provided
    if (update.role && !['owner', 'admin', 'member', 'viewer'].includes(update.role)) {
      throw new ValidationError('Invalid role. Must be owner, admin, member, or viewer');
    }

    // Validate message length if provided
    if (update.message && update.message.length > 500) {
      throw new ValidationError('Message must be 500 characters or less');
    }

    const response = await this.http.patch<Invitation>(
      `/api/v1/invitations/${invitationId}`,
      update
    );
    return response.data;
  }

  /**
   * Resend an invitation email
   *
   * @param invitationId - Invitation ID
   * @returns Updated invitation
   */
  async resendInvitation(invitationId: UUID): Promise<Invitation> {
    if (!ValidationUtils.isValidUuid(invitationId)) {
      throw new ValidationError('Invalid invitation ID format');
    }

    const response = await this.http.post<Invitation>(
      `/api/v1/invitations/${invitationId}/resend`,
      {}
    );
    return response.data;
  }

  /**
   * Revoke (cancel) a pending invitation
   *
   * @param invitationId - Invitation ID
   */
  async revokeInvitation(invitationId: UUID): Promise<void> {
    if (!ValidationUtils.isValidUuid(invitationId)) {
      throw new ValidationError('Invalid invitation ID format');
    }

    await this.http.delete(`/api/v1/invitations/${invitationId}`);
  }

  /**
   * Accept an invitation using the token
   *
   * @param request - Accept request with token and optional user info
   * @returns Acceptance result
   */
  async acceptInvitation(request: InvitationAcceptRequest): Promise<InvitationAcceptResponse> {
    if (!request.token || request.token.trim().length === 0) {
      throw new ValidationError('Invitation token is required');
    }

    // Validate user_id if provided
    if (request.user_id && !ValidationUtils.isValidUuid(request.user_id)) {
      throw new ValidationError('Invalid user ID format');
    }

    // Validate new user registration if provided
    if (request.password && !request.user_id) {
      if (!request.name || request.name.trim().length === 0) {
        throw new ValidationError('Name is required for new user registration');
      }

      if (request.name.length > 255) {
        throw new ValidationError('Name must be 255 characters or less');
      }

      const passwordValidation = ValidationUtils.validatePassword(request.password);
      if (!passwordValidation.isValid) {
        throw new ValidationError(
          'Password validation failed',
          passwordValidation.errors.map(err => ({ field: 'password', message: err }))
        );
      }
    }

    const response = await this.http.post<InvitationAcceptResponse>(
      '/api/v1/invitations/accept',
      request
    );
    return response.data;
  }

  /**
   * Validate an invitation token
   *
   * @param token - Invitation token
   * @returns Validation result with invitation details
   */
  async validateToken(token: string): Promise<InvitationValidateResponse> {
    if (!token || token.trim().length === 0) {
      throw new ValidationError('Invitation token is required');
    }

    const response = await this.http.get<InvitationValidateResponse>(
      `/api/v1/invitations/validate/${token}`
    );
    return response.data;
  }

  /**
   * Clean up expired invitations (admin only)
   *
   * @returns Count of invitations marked as expired
   */
  async cleanupExpiredInvitations(): Promise<{ message: string; count: number }> {
    const response = await this.http.post<{ message: string; count: number }>(
      '/api/v1/invitations/cleanup',
      {}
    );
    return response.data;
  }
}
