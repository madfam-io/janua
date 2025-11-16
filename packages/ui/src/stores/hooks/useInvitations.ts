import { useCallback } from 'react'
import { useEnterpriseStore } from '../enterprise.store'
import type { Invitation, InvitationStats } from '../enterprise.store'

/**
 * Hook for invitation management with optimistic updates
 *
 * @example
 * ```tsx
 * const { invitations, stats, loading, createInvitation, revokeInvitation } = useInvitations(plintoClient)
 *
 * // Create invitation with optimistic update
 * await createInvitation({
 *   email: 'user@example.com',
 *   role: 'member',
 *   message: 'Welcome!'
 * })
 * ```
 */
export function useInvitations(client?: any) {
  // Selectors
  const invitations = useEnterpriseStore((state) => state.invitations)
  const stats = useEnterpriseStore((state) => state.invitationStats)
  const loading = useEnterpriseStore((state) => state.invitationsLoading)
  const error = useEnterpriseStore((state) => state.invitationsError)
  const filters = useEnterpriseStore((state) => state.invitationFilters)

  // Actions
  const setInvitations = useEnterpriseStore((state) => state.setInvitations)
  const addInvitation = useEnterpriseStore((state) => state.addInvitation)
  const updateInvitation = useEnterpriseStore((state) => state.updateInvitation)
  const removeInvitation = useEnterpriseStore((state) => state.removeInvitation)
  const setInvitationStats = useEnterpriseStore((state) => state.setInvitationStats)
  const setInvitationsLoading = useEnterpriseStore((state) => state.setInvitationsLoading)
  const setInvitationsError = useEnterpriseStore((state) => state.setInvitationsError)
  const setInvitationFilters = useEnterpriseStore((state) => state.setInvitationFilters)
  const clearInvitationFilters = useEnterpriseStore((state) => state.clearInvitationFilters)
  const isCacheValid = useEnterpriseStore((state) => state.isInvitationsCacheValid)
  const invalidateCache = useEnterpriseStore((state) => state.invalidateInvitationsCache)

  // Helper selectors
  const getInvitationById = useEnterpriseStore((state) => state.getInvitationById)
  const getFilteredInvitations = useEnterpriseStore((state) => state.getFilteredInvitations)
  const getPendingInvitations = useEnterpriseStore((state) => state.getPendingInvitations)
  const getAcceptedInvitations = useEnterpriseStore((state) => state.getAcceptedInvitations)

  /**
   * Fetch all invitations for an organization
   * Uses cache if valid, otherwise fetches from API
   */
  const fetchInvitations = useCallback(
    async (organizationId: string, forceRefresh = false) => {
      // Check cache validity
      if (!forceRefresh && isCacheValid()) {
        return invitations
      }

      setInvitationsLoading(true)
      setInvitationsError(null)

      try {
        let response: Invitation[]

        if (client?.invitations?.listInvitations) {
          response = await client.invitations.listInvitations(organizationId)
        } else {
          // Fallback to direct fetch
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/organizations/${organizationId}/invitations`,
            { credentials: 'include' }
          )
          if (!res.ok) throw new Error('Failed to fetch invitations')
          response = await res.json()
        }

        setInvitations(response)
        return response
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to fetch invitations'
        setInvitationsError(errorMsg)
        throw err
      } finally {
        setInvitationsLoading(false)
      }
    },
    [client, invitations, isCacheValid, setInvitationsLoading, setInvitationsError, setInvitations]
  )

  /**
   * Fetch invitation statistics
   */
  const fetchStats = useCallback(
    async (organizationId: string) => {
      try {
        let response: InvitationStats

        if (client?.invitations?.getStats) {
          response = await client.invitations.getStats(organizationId)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/organizations/${organizationId}/invitations/stats`,
            { credentials: 'include' }
          )
          if (!res.ok) throw new Error('Failed to fetch invitation stats')
          response = await res.json()
        }

        setInvitationStats(response)
        return response
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to fetch invitation stats'
        setInvitationsError(errorMsg)
        throw err
      }
    },
    [client, setInvitationStats, setInvitationsError]
  )

  /**
   * Create a new invitation with optimistic update
   */
  const createInvitation = useCallback(
    async (
      organizationId: string,
      data: {
        email: string
        role: string
        message?: string
        expires_in?: number
      }
    ) => {
      setInvitationsLoading(true)
      setInvitationsError(null)

      // Optimistic ID for temporary state
      const tempId = `temp-${Date.now()}`
      const optimisticInvitation: Invitation = {
        id: tempId,
        organization_id: organizationId,
        email: data.email,
        role: data.role,
        status: 'pending',
        message: data.message,
        invitation_url: '', // Will be set by server
        expires_at: new Date(Date.now() + (data.expires_in || 7) * 24 * 60 * 60 * 1000).toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        inviter_id: 'current-user', // Will be set by server
      }

      // Optimistic update
      addInvitation(optimisticInvitation)

      try {
        let response: Invitation

        if (client?.invitations?.createInvitation) {
          response = await client.invitations.createInvitation(organizationId, data)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/organizations/${organizationId}/invitations`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify(data),
            }
          )
          if (!res.ok) throw new Error('Failed to create invitation')
          response = await res.json()
        }

        // Replace optimistic with real data
        removeInvitation(tempId)
        addInvitation(response)
        invalidateCache()

        return response
      } catch (err) {
        // Rollback optimistic update
        removeInvitation(tempId)
        const errorMsg = err instanceof Error ? err.message : 'Failed to create invitation'
        setInvitationsError(errorMsg)
        throw err
      } finally {
        setInvitationsLoading(false)
      }
    },
    [
      client,
      addInvitation,
      removeInvitation,
      setInvitationsLoading,
      setInvitationsError,
      invalidateCache,
    ]
  )

  /**
   * Create bulk invitations
   */
  const createBulkInvitations = useCallback(
    async (
      organizationId: string,
      data: {
        invitations: Array<{ email: string; role?: string; message?: string }>
        default_role?: string
        default_message?: string
        expires_in?: number
      }
    ) => {
      setInvitationsLoading(true)
      setInvitationsError(null)

      try {
        let response: {
          success: boolean
          total: number
          successful: number
          failed: number
          results: Array<{
            email: string
            success: boolean
            invitation_id?: string
            error?: string
          }>
        }

        if (client?.invitations?.createBulkInvitations) {
          response = await client.invitations.createBulkInvitations(organizationId, data)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/organizations/${organizationId}/invitations/bulk`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify(data),
            }
          )
          if (!res.ok) throw new Error('Failed to create bulk invitations')
          response = await res.json()
        }

        // Invalidate cache to fetch fresh data including new invitations
        invalidateCache()
        await fetchInvitations(organizationId, true)
        await fetchStats(organizationId)

        return response
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to create bulk invitations'
        setInvitationsError(errorMsg)
        throw err
      } finally {
        setInvitationsLoading(false)
      }
    },
    [client, fetchInvitations, fetchStats, setInvitationsLoading, setInvitationsError, invalidateCache]
  )

  /**
   * Resend an invitation with optimistic update
   */
  const resendInvitation = useCallback(
    async (invitationId: string) => {
      setInvitationsLoading(true)
      setInvitationsError(null)

      // Store original for rollback
      const original = getInvitationById(invitationId)
      if (!original) {
        setInvitationsError('Invitation not found')
        setInvitationsLoading(false)
        throw new Error('Invitation not found')
      }

      // Optimistic update - update timestamp
      updateInvitation(invitationId, {
        updated_at: new Date().toISOString(),
      })

      try {
        let response: Invitation

        if (client?.invitations?.resendInvitation) {
          response = await client.invitations.resendInvitation(invitationId)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/invitations/${invitationId}/resend`,
            {
              method: 'POST',
              credentials: 'include',
            }
          )
          if (!res.ok) throw new Error('Failed to resend invitation')
          response = await res.json()
        }

        // Update with server response
        updateInvitation(invitationId, response)
        invalidateCache()

        return response
      } catch (err) {
        // Rollback to original
        updateInvitation(invitationId, original)
        const errorMsg = err instanceof Error ? err.message : 'Failed to resend invitation'
        setInvitationsError(errorMsg)
        throw err
      } finally {
        setInvitationsLoading(false)
      }
    },
    [
      client,
      getInvitationById,
      updateInvitation,
      setInvitationsLoading,
      setInvitationsError,
      invalidateCache,
    ]
  )

  /**
   * Revoke an invitation with optimistic update
   */
  const revokeInvitation = useCallback(
    async (invitationId: string) => {
      setInvitationsLoading(true)
      setInvitationsError(null)

      // Store original for rollback
      const original = getInvitationById(invitationId)
      if (!original) {
        setInvitationsError('Invitation not found')
        setInvitationsLoading(false)
        throw new Error('Invitation not found')
      }

      // Optimistic update
      updateInvitation(invitationId, {
        status: 'revoked',
        updated_at: new Date().toISOString(),
      })

      try {
        let response: Invitation

        if (client?.invitations?.revokeInvitation) {
          response = await client.invitations.revokeInvitation(invitationId)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/invitations/${invitationId}/revoke`,
            {
              method: 'POST',
              credentials: 'include',
            }
          )
          if (!res.ok) throw new Error('Failed to revoke invitation')
          response = await res.json()
        }

        // Update with server response
        updateInvitation(invitationId, response)
        invalidateCache()

        return response
      } catch (err) {
        // Rollback to original
        updateInvitation(invitationId, original)
        const errorMsg = err instanceof Error ? err.message : 'Failed to revoke invitation'
        setInvitationsError(errorMsg)
        throw err
      } finally {
        setInvitationsLoading(false)
      }
    },
    [
      client,
      getInvitationById,
      updateInvitation,
      setInvitationsLoading,
      setInvitationsError,
      invalidateCache,
    ]
  )

  /**
   * Delete an invitation with optimistic update
   */
  const deleteInvitation = useCallback(
    async (invitationId: string) => {
      setInvitationsLoading(true)
      setInvitationsError(null)

      // Store original for rollback
      const original = getInvitationById(invitationId)
      if (!original) {
        setInvitationsError('Invitation not found')
        setInvitationsLoading(false)
        throw new Error('Invitation not found')
      }

      // Optimistic delete
      removeInvitation(invitationId)

      try {
        if (client?.invitations?.deleteInvitation) {
          await client.invitations.deleteInvitation(invitationId)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/invitations/${invitationId}`,
            {
              method: 'DELETE',
              credentials: 'include',
            }
          )
          if (!res.ok) throw new Error('Failed to delete invitation')
        }

        invalidateCache()
      } catch (err) {
        // Rollback - add back the deleted invitation
        addInvitation(original)
        const errorMsg = err instanceof Error ? err.message : 'Failed to delete invitation'
        setInvitationsError(errorMsg)
        throw err
      } finally {
        setInvitationsLoading(false)
      }
    },
    [
      client,
      getInvitationById,
      removeInvitation,
      addInvitation,
      setInvitationsLoading,
      setInvitationsError,
      invalidateCache,
    ]
  )

  return {
    // State
    invitations,
    stats,
    loading,
    error,
    filters,

    // Actions
    fetchInvitations,
    fetchStats,
    createInvitation,
    createBulkInvitations,
    resendInvitation,
    revokeInvitation,
    deleteInvitation,
    setFilters: setInvitationFilters,
    clearFilters: clearInvitationFilters,
    invalidateCache,

    // Helpers
    getInvitationById,
    getFilteredInvitations,
    getPendingInvitations,
    getAcceptedInvitations,
  }
}
