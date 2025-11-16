import { useCallback } from 'react'
import { useEnterpriseStore } from '../enterprise.store'
import type { SSOProvider, SAMLConfig, SSOTestResult } from '../enterprise.store'

/**
 * Hook for SSO provider management with optimistic updates
 *
 * @example
 * ```tsx
 * const { providers, loading, error, createProvider, updateProvider } = useSSO(plintoClient)
 *
 * // Create provider with optimistic update
 * await createProvider({
 *   name: 'Google Workspace',
 *   provider_type: 'saml',
 *   enabled: true
 * })
 * ```
 */
export function useSSO(client?: any) {
  // Selectors
  const providers = useEnterpriseStore((state) => state.ssoProviders)
  const selectedProvider = useEnterpriseStore((state) => state.selectedProvider)
  const loading = useEnterpriseStore((state) => state.ssoLoading)
  const error = useEnterpriseStore((state) => state.ssoError)
  const testResults = useEnterpriseStore((state) => state.ssoTestResults)

  // Actions
  const setSSOProviders = useEnterpriseStore((state) => state.setSSOProviders)
  const addSSOProvider = useEnterpriseStore((state) => state.addSSOProvider)
  const updateSSOProvider = useEnterpriseStore((state) => state.updateSSOProvider)
  const removeSSOProvider = useEnterpriseStore((state) => state.removeSSOProvider)
  const setSelectedProvider = useEnterpriseStore((state) => state.setSelectedProvider)
  const setSSOLoading = useEnterpriseStore((state) => state.setSSOLoading)
  const setSSOError = useEnterpriseStore((state) => state.setSSOError)
  const setSSOTestResult = useEnterpriseStore((state) => state.setSSOTestResult)
  const isCacheValid = useEnterpriseStore((state) => state.isSSOCacheValid)
  const invalidateCache = useEnterpriseStore((state) => state.invalidateSSOCache)

  // Helper selectors
  const getProviderById = useEnterpriseStore((state) => state.getSSOProviderById)
  const getProvidersByType = useEnterpriseStore((state) => state.getSSOProvidersByType)
  const getEnabledProviders = useEnterpriseStore((state) => state.getEnabledSSOProviders)

  /**
   * Fetch all SSO providers for an organization
   * Uses cache if valid, otherwise fetches from API
   */
  const fetchProviders = useCallback(
    async (organizationId: string, forceRefresh = false) => {
      // Check cache validity
      if (!forceRefresh && isCacheValid()) {
        return providers
      }

      setSSOLoading(true)
      setSSOError(null)

      try {
        let response: SSOProvider[]

        if (client?.sso?.listProviders) {
          response = await client.sso.listProviders(organizationId)
        } else {
          // Fallback to direct fetch
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/organizations/${organizationId}/sso/providers`,
            { credentials: 'include' }
          )
          if (!res.ok) throw new Error('Failed to fetch SSO providers')
          response = await res.json()
        }

        setSSOProviders(response)
        return response
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to fetch SSO providers'
        setSSOError(errorMsg)
        throw err
      } finally {
        setSSOLoading(false)
      }
    },
    [client, providers, isCacheValid, setSSOLoading, setSSOError, setSSOProviders]
  )

  /**
   * Create a new SSO provider with optimistic update
   */
  const createProvider = useCallback(
    async (organizationId: string, data: Partial<SSOProvider>) => {
      setSSOLoading(true)
      setSSOError(null)

      // Optimistic ID for temporary state
      const tempId = `temp-${Date.now()}`
      const optimisticProvider: SSOProvider = {
        id: tempId,
        organization_id: organizationId,
        name: data.name || '',
        provider_type: data.provider_type || 'saml',
        enabled: data.enabled ?? false,
        jit_enabled: data.jit_enabled ?? false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        ...data,
      }

      // Optimistic update
      addSSOProvider(optimisticProvider)

      try {
        let response: SSOProvider

        if (client?.sso?.createProvider) {
          response = await client.sso.createProvider(organizationId, data)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/organizations/${organizationId}/sso/providers`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify(data),
            }
          )
          if (!res.ok) throw new Error('Failed to create SSO provider')
          response = await res.json()
        }

        // Replace optimistic with real data
        removeSSOProvider(tempId)
        addSSOProvider(response)
        invalidateCache()

        return response
      } catch (err) {
        // Rollback optimistic update
        removeSSOProvider(tempId)
        const errorMsg = err instanceof Error ? err.message : 'Failed to create SSO provider'
        setSSOError(errorMsg)
        throw err
      } finally {
        setSSOLoading(false)
      }
    },
    [client, addSSOProvider, removeSSOProvider, setSSOLoading, setSSOError, invalidateCache]
  )

  /**
   * Update an existing SSO provider with optimistic update
   */
  const updateProvider = useCallback(
    async (providerId: string, updates: Partial<SSOProvider>) => {
      setSSOLoading(true)
      setSSOError(null)

      // Store original for rollback
      const original = getProviderById(providerId)
      if (!original) {
        setSSOError('Provider not found')
        setSSOLoading(false)
        throw new Error('Provider not found')
      }

      // Optimistic update
      updateSSOProvider(providerId, updates)

      try {
        let response: SSOProvider

        if (client?.sso?.updateProvider) {
          response = await client.sso.updateProvider(providerId, updates)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/sso/providers/${providerId}`,
            {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify(updates),
            }
          )
          if (!res.ok) throw new Error('Failed to update SSO provider')
          response = await res.json()
        }

        // Update with server response
        updateSSOProvider(providerId, response)
        invalidateCache()

        return response
      } catch (err) {
        // Rollback to original
        updateSSOProvider(providerId, original)
        const errorMsg = err instanceof Error ? err.message : 'Failed to update SSO provider'
        setSSOError(errorMsg)
        throw err
      } finally {
        setSSOLoading(false)
      }
    },
    [client, getProviderById, updateSSOProvider, setSSOLoading, setSSOError, invalidateCache]
  )

  /**
   * Delete an SSO provider with optimistic update
   */
  const deleteProvider = useCallback(
    async (providerId: string) => {
      setSSOLoading(true)
      setSSOError(null)

      // Store original for rollback
      const original = getProviderById(providerId)
      if (!original) {
        setSSOError('Provider not found')
        setSSOLoading(false)
        throw new Error('Provider not found')
      }

      // Optimistic delete
      removeSSOProvider(providerId)

      try {
        if (client?.sso?.deleteProvider) {
          await client.sso.deleteProvider(providerId)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/sso/providers/${providerId}`,
            {
              method: 'DELETE',
              credentials: 'include',
            }
          )
          if (!res.ok) throw new Error('Failed to delete SSO provider')
        }

        invalidateCache()
      } catch (err) {
        // Rollback - add back the deleted provider
        addSSOProvider(original)
        const errorMsg = err instanceof Error ? err.message : 'Failed to delete SSO provider'
        setSSOError(errorMsg)
        throw err
      } finally {
        setSSOLoading(false)
      }
    },
    [
      client,
      getProviderById,
      removeSSOProvider,
      addSSOProvider,
      setSSOLoading,
      setSSOError,
      invalidateCache,
    ]
  )

  /**
   * Test SSO connection and store results
   */
  const testConnection = useCallback(
    async (
      providerId: string,
      testType: 'metadata' | 'authentication' | 'full' = 'full'
    ) => {
      setSSOLoading(true)
      setSSOError(null)

      try {
        let response: SSOTestResult

        if (client?.sso?.testConfiguration) {
          response = await client.sso.testConfiguration(providerId, { test_type: testType })
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/sso/providers/${providerId}/test`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ test_type: testType }),
            }
          )
          if (!res.ok) throw new Error('Failed to test SSO connection')
          response = await res.json()
        }

        setSSOTestResult(providerId, response)
        return response
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to test SSO connection'
        setSSOError(errorMsg)
        throw err
      } finally {
        setSSOLoading(false)
      }
    },
    [client, setSSOLoading, setSSOError, setSSOTestResult]
  )

  /**
   * Update SAML configuration
   */
  const updateSAMLConfig = useCallback(
    async (providerId: string, config: Partial<SAMLConfig>) => {
      setSSOLoading(true)
      setSSOError(null)

      try {
        let response: SAMLConfig

        if (client?.sso?.updateConfiguration) {
          response = await client.sso.updateConfiguration(providerId, config)
        } else {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/sso/providers/${providerId}/saml/config`,
            {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify(config),
            }
          )
          if (!res.ok) throw new Error('Failed to update SAML configuration')
          response = await res.json()
        }

        // Update provider with new SAML details
        updateSSOProvider(providerId, {
          saml_entity_id: config.saml_entity_id,
          saml_acs_url: config.saml_acs_url,
        })
        invalidateCache()

        return response
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to update SAML configuration'
        setSSOError(errorMsg)
        throw err
      } finally {
        setSSOLoading(false)
      }
    },
    [client, updateSSOProvider, setSSOLoading, setSSOError, invalidateCache]
  )

  return {
    // State
    providers,
    selectedProvider,
    loading,
    error,
    testResults,

    // Actions
    fetchProviders,
    createProvider,
    updateProvider,
    deleteProvider,
    testConnection,
    updateSAMLConfig,
    setSelectedProvider,
    invalidateCache,

    // Helpers
    getProviderById,
    getProvidersByType,
    getEnabledProviders,
  }
}
