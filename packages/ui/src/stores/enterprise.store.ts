import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

// ============================================================================
// SSO Types
// ============================================================================

export interface SSOProvider {
  id: string
  organization_id: string
  name: string
  provider_type: 'saml' | 'oidc' | 'google' | 'azure' | 'okta'
  enabled: boolean
  jit_enabled: boolean
  default_role?: string
  allowed_domains?: string[]
  created_at: string
  updated_at: string

  // SAML-specific fields
  saml_entity_id?: string
  saml_acs_url?: string
  saml_metadata_url?: string

  // OIDC-specific fields
  oidc_client_id?: string
  oidc_issuer?: string
  oidc_authorization_endpoint?: string
  oidc_token_endpoint?: string
}

export interface SAMLConfig {
  configuration_id: string
  saml_entity_id: string
  saml_acs_url: string
  saml_certificate?: string
  attribute_mapping?: Record<string, string>
  sign_requests?: boolean
  want_assertions_signed?: boolean
  name_id_format?: string
}

export interface SSOTestResult {
  success: boolean
  test_type: string
  results: {
    metadata_valid?: boolean
    certificate_valid?: boolean
    endpoints_reachable?: boolean
    authentication_successful?: boolean
    user_attributes?: Record<string, any>
    errors?: string[]
    warnings?: string[]
  }
  timestamp: string
}

// ============================================================================
// Invitation Types
// ============================================================================

export interface Invitation {
  id: string
  organization_id: string
  email: string
  role: string
  status: 'pending' | 'accepted' | 'expired' | 'revoked'
  message?: string
  invitation_url: string
  expires_at: string
  created_at: string
  updated_at: string
  accepted_at?: string
  inviter_id: string
  inviter_name?: string
}

export interface InvitationStats {
  total: number
  pending: number
  accepted: number
  expired: number
  revoked: number
}

// ============================================================================
// Store State Interface
// ============================================================================

interface EnterpriseState {
  // SSO State
  ssoProviders: SSOProvider[]
  selectedProvider: SSOProvider | null
  ssoLoading: boolean
  ssoError: string | null
  ssoTestResults: Record<string, SSOTestResult> // providerId -> test result

  // Invitations State
  invitations: Invitation[]
  invitationStats: InvitationStats | null
  invitationsLoading: boolean
  invitationsError: string | null
  invitationFilters: {
    status?: 'pending' | 'accepted' | 'expired' | 'revoked'
    search?: string
  }

  // Cache timestamps for invalidation
  ssoLastFetched: number | null
  invitationsLastFetched: number | null

  // SSO Actions
  setSSOProviders: (providers: SSOProvider[]) => void
  addSSOProvider: (provider: SSOProvider) => void
  updateSSOProvider: (id: string, updates: Partial<SSOProvider>) => void
  removeSSOProvider: (id: string) => void
  setSelectedProvider: (provider: SSOProvider | null) => void
  setSSOLoading: (loading: boolean) => void
  setSSOError: (error: string | null) => void
  setSSOTestResult: (providerId: string, result: SSOTestResult) => void
  clearSSOTestResults: () => void

  // SSO Computed/Helper Actions
  getSSOProviderById: (id: string) => SSOProvider | undefined
  getSSOProvidersByType: (type: SSOProvider['provider_type']) => SSOProvider[]
  getEnabledSSOProviders: () => SSOProvider[]

  // Invitations Actions
  setInvitations: (invitations: Invitation[]) => void
  addInvitation: (invitation: Invitation) => void
  updateInvitation: (id: string, updates: Partial<Invitation>) => void
  removeInvitation: (id: string) => void
  setInvitationStats: (stats: InvitationStats) => void
  setInvitationsLoading: (loading: boolean) => void
  setInvitationsError: (error: string | null) => void
  setInvitationFilters: (filters: Partial<EnterpriseState['invitationFilters']>) => void
  clearInvitationFilters: () => void

  // Invitations Computed/Helper Actions
  getInvitationById: (id: string) => Invitation | undefined
  getFilteredInvitations: () => Invitation[]
  getPendingInvitations: () => Invitation[]
  getAcceptedInvitations: () => Invitation[]

  // Cache Management
  invalidateSSOCache: () => void
  invalidateInvitationsCache: () => void
  isSSOCacheValid: (maxAgeMs?: number) => boolean
  isInvitationsCacheValid: (maxAgeMs?: number) => boolean

  // Reset Actions
  resetSSO: () => void
  resetInvitations: () => void
  resetAll: () => void
}

// ============================================================================
// Default State
// ============================================================================

const defaultSSOState = {
  ssoProviders: [],
  selectedProvider: null,
  ssoLoading: false,
  ssoError: null,
  ssoTestResults: {},
  ssoLastFetched: null,
}

const defaultInvitationsState = {
  invitations: [],
  invitationStats: null,
  invitationsLoading: false,
  invitationsError: null,
  invitationFilters: {},
  invitationsLastFetched: null,
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useEnterpriseStore = create<EnterpriseState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial State
        ...defaultSSOState,
        ...defaultInvitationsState,

        // ====================================================================
        // SSO Actions
        // ====================================================================

        setSSOProviders: (providers) => {
          set(
            {
              ssoProviders: providers,
              ssoLastFetched: Date.now(),
              ssoError: null,
            },
            false,
            'setSSOProviders'
          )
        },

        addSSOProvider: (provider) => {
          set(
            (state) => ({
              ssoProviders: [...state.ssoProviders, provider],
              ssoError: null,
            }),
            false,
            'addSSOProvider'
          )
        },

        updateSSOProvider: (id, updates) => {
          set(
            (state) => ({
              ssoProviders: state.ssoProviders.map((p) =>
                p.id === id ? { ...p, ...updates } : p
              ),
              selectedProvider:
                state.selectedProvider?.id === id
                  ? { ...state.selectedProvider, ...updates }
                  : state.selectedProvider,
              ssoError: null,
            }),
            false,
            'updateSSOProvider'
          )
        },

        removeSSOProvider: (id) => {
          set(
            (state) => ({
              ssoProviders: state.ssoProviders.filter((p) => p.id !== id),
              selectedProvider:
                state.selectedProvider?.id === id ? null : state.selectedProvider,
              ssoError: null,
            }),
            false,
            'removeSSOProvider'
          )
        },

        setSelectedProvider: (provider) => {
          set({ selectedProvider: provider }, false, 'setSelectedProvider')
        },

        setSSOLoading: (loading) => {
          set({ ssoLoading: loading }, false, 'setSSOLoading')
        },

        setSSOError: (error) => {
          set({ ssoError: error, ssoLoading: false }, false, 'setSSOError')
        },

        setSSOTestResult: (providerId, result) => {
          set(
            (state) => ({
              ssoTestResults: {
                ...state.ssoTestResults,
                [providerId]: result,
              },
            }),
            false,
            'setSSOTestResult'
          )
        },

        clearSSOTestResults: () => {
          set({ ssoTestResults: {} }, false, 'clearSSOTestResults')
        },

        // SSO Computed/Helper Actions
        getSSOProviderById: (id) => {
          return get().ssoProviders.find((p) => p.id === id)
        },

        getSSOProvidersByType: (type) => {
          return get().ssoProviders.filter((p) => p.provider_type === type)
        },

        getEnabledSSOProviders: () => {
          return get().ssoProviders.filter((p) => p.enabled)
        },

        // ====================================================================
        // Invitations Actions
        // ====================================================================

        setInvitations: (invitations) => {
          set(
            {
              invitations,
              invitationsLastFetched: Date.now(),
              invitationsError: null,
            },
            false,
            'setInvitations'
          )
        },

        addInvitation: (invitation) => {
          set(
            (state) => ({
              invitations: [invitation, ...state.invitations],
              invitationStats: state.invitationStats
                ? {
                    ...state.invitationStats,
                    total: state.invitationStats.total + 1,
                    pending: state.invitationStats.pending + 1,
                  }
                : null,
              invitationsError: null,
            }),
            false,
            'addInvitation'
          )
        },

        updateInvitation: (id, updates) => {
          set(
            (state) => {
              const oldInvitation = state.invitations.find((i) => i.id === id)
              const newInvitations = state.invitations.map((i) =>
                i.id === id ? { ...i, ...updates } : i
              )

              // Update stats if status changed
              let newStats = state.invitationStats
              if (oldInvitation && updates.status && oldInvitation.status !== updates.status) {
                if (newStats) {
                  newStats = { ...newStats }
                  // Decrement old status
                  if (oldInvitation.status === 'pending') newStats.pending--
                  else if (oldInvitation.status === 'accepted') newStats.accepted--
                  else if (oldInvitation.status === 'expired') newStats.expired--
                  else if (oldInvitation.status === 'revoked') newStats.revoked--

                  // Increment new status
                  if (updates.status === 'pending') newStats.pending++
                  else if (updates.status === 'accepted') newStats.accepted++
                  else if (updates.status === 'expired') newStats.expired++
                  else if (updates.status === 'revoked') newStats.revoked++
                }
              }

              return {
                invitations: newInvitations,
                invitationStats: newStats,
                invitationsError: null,
              }
            },
            false,
            'updateInvitation'
          )
        },

        removeInvitation: (id) => {
          set(
            (state) => {
              const invitation = state.invitations.find((i) => i.id === id)
              const newStats = state.invitationStats
                ? {
                    ...state.invitationStats,
                    total: state.invitationStats.total - 1,
                    [invitation?.status || 'pending']:
                      (state.invitationStats as any)[invitation?.status || 'pending'] - 1,
                  }
                : null

              return {
                invitations: state.invitations.filter((i) => i.id !== id),
                invitationStats: newStats,
                invitationsError: null,
              }
            },
            false,
            'removeInvitation'
          )
        },

        setInvitationStats: (stats) => {
          set({ invitationStats: stats }, false, 'setInvitationStats')
        },

        setInvitationsLoading: (loading) => {
          set({ invitationsLoading: loading }, false, 'setInvitationsLoading')
        },

        setInvitationsError: (error) => {
          set(
            { invitationsError: error, invitationsLoading: false },
            false,
            'setInvitationsError'
          )
        },

        setInvitationFilters: (filters) => {
          set(
            (state) => ({
              invitationFilters: { ...state.invitationFilters, ...filters },
            }),
            false,
            'setInvitationFilters'
          )
        },

        clearInvitationFilters: () => {
          set({ invitationFilters: {} }, false, 'clearInvitationFilters')
        },

        // Invitations Computed/Helper Actions
        getInvitationById: (id) => {
          return get().invitations.find((i) => i.id === id)
        },

        getFilteredInvitations: () => {
          const { invitations, invitationFilters } = get()
          let filtered = [...invitations]

          // Filter by status
          if (invitationFilters.status) {
            filtered = filtered.filter((i) => i.status === invitationFilters.status)
          }

          // Filter by search (email)
          if (invitationFilters.search) {
            const search = invitationFilters.search.toLowerCase()
            filtered = filtered.filter((i) => i.email.toLowerCase().includes(search))
          }

          return filtered
        },

        getPendingInvitations: () => {
          return get().invitations.filter((i) => i.status === 'pending')
        },

        getAcceptedInvitations: () => {
          return get().invitations.filter((i) => i.status === 'accepted')
        },

        // ====================================================================
        // Cache Management
        // ====================================================================

        invalidateSSOCache: () => {
          set({ ssoLastFetched: null }, false, 'invalidateSSOCache')
        },

        invalidateInvitationsCache: () => {
          set({ invitationsLastFetched: null }, false, 'invalidateInvitationsCache')
        },

        isSSOCacheValid: (maxAgeMs = 5 * 60 * 1000) => {
          // Default: 5 minutes
          const { ssoLastFetched } = get()
          if (!ssoLastFetched) return false
          return Date.now() - ssoLastFetched < maxAgeMs
        },

        isInvitationsCacheValid: (maxAgeMs = 5 * 60 * 1000) => {
          // Default: 5 minutes
          const { invitationsLastFetched } = get()
          if (!invitationsLastFetched) return false
          return Date.now() - invitationsLastFetched < maxAgeMs
        },

        // ====================================================================
        // Reset Actions
        // ====================================================================

        resetSSO: () => {
          set(defaultSSOState, false, 'resetSSO')
        },

        resetInvitations: () => {
          set(defaultInvitationsState, false, 'resetInvitations')
        },

        resetAll: () => {
          set(
            { ...defaultSSOState, ...defaultInvitationsState },
            false,
            'resetAll'
          )
        },
      }),
      {
        name: 'plinto-enterprise-store',
        // Only persist non-sensitive data
        partialize: (state) => ({
          invitationFilters: state.invitationFilters,
          selectedProvider: state.selectedProvider,
        }),
      }
    ),
    {
      name: 'Enterprise Store',
      enabled: process.env.NODE_ENV === 'development',
    }
  )
)

// ============================================================================
// Selectors (for better performance and reusability)
// ============================================================================

export const selectSSOProviders = (state: EnterpriseState) => state.ssoProviders
export const selectSelectedProvider = (state: EnterpriseState) => state.selectedProvider
export const selectSSOLoading = (state: EnterpriseState) => state.ssoLoading
export const selectSSOError = (state: EnterpriseState) => state.ssoError
export const selectSSOTestResults = (state: EnterpriseState) => state.ssoTestResults

export const selectInvitations = (state: EnterpriseState) => state.invitations
export const selectInvitationStats = (state: EnterpriseState) => state.invitationStats
export const selectInvitationsLoading = (state: EnterpriseState) => state.invitationsLoading
export const selectInvitationsError = (state: EnterpriseState) => state.invitationsError
export const selectInvitationFilters = (state: EnterpriseState) => state.invitationFilters
export const selectFilteredInvitations = (state: EnterpriseState) =>
  state.getFilteredInvitations()
export const selectPendingInvitations = (state: EnterpriseState) =>
  state.getPendingInvitations()
