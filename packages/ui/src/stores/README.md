# Enterprise State Management

Comprehensive state management for SSO and Invitations features using Zustand with optimistic updates, caching, and persistence.

## Features

- 🚀 **Optimistic Updates**: Instant UI feedback with automatic rollback on errors
- 💾 **Smart Caching**: 5-minute cache with manual invalidation support
- 🔄 **Auto Persistence**: Important state persisted to localStorage
- 📊 **DevTools Integration**: Redux DevTools support in development
- 🎯 **TypeScript**: Full type safety with comprehensive interfaces
- ⚡ **Performance**: Selective re-renders with granular selectors

---

## Installation

```bash
npm install zustand
```

---

## Quick Start

### SSO Management

```tsx
import { useSSO } from '@plinto/ui/stores'
import { PlintoClient } from '@plinto/typescript-sdk'

function SSODashboard() {
  const client = new PlintoClient({ baseURL: 'http://localhost:8000' })
  const {
    providers,
    loading,
    error,
    fetchProviders,
    createProvider,
    updateProvider,
    deleteProvider,
  } = useSSO(client)

  // Fetch providers on mount (with caching)
  useEffect(() => {
    fetchProviders('org-123')
  }, [])

  // Create provider with optimistic update
  const handleCreate = async () => {
    try {
      await createProvider('org-123', {
        name: 'Google Workspace',
        provider_type: 'saml',
        enabled: true,
        jit_enabled: true,
      })
      // UI updates immediately, rolls back on error
    } catch (err) {
      console.error('Failed to create provider:', err)
    }
  }

  return (
    <div>
      {loading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      {providers.map((provider) => (
        <div key={provider.id}>{provider.name}</div>
      ))}
    </div>
  )
}
```

### Invitations Management

```tsx
import { useInvitations } from '@plinto/ui/stores'

function InvitationManager() {
  const {
    invitations,
    stats,
    loading,
    fetchInvitations,
    createInvitation,
    revokeInvitation,
    setFilters,
    getFilteredInvitations,
  } = useInvitations(client)

  // Fetch invitations with stats
  useEffect(() => {
    async function load() {
      await fetchInvitations('org-123')
      await fetchStats('org-123')
    }
    load()
  }, [])

  // Filter invitations
  const handleFilterChange = (status: string) => {
    setFilters({ status: status as any })
  }

  // Get filtered results
  const filtered = getFilteredInvitations()

  return (
    <div>
      <div>Total: {stats?.total}</div>
      <div>Pending: {stats?.pending}</div>

      <select onChange={(e) => handleFilterChange(e.target.value)}>
        <option value="">All</option>
        <option value="pending">Pending</option>
        <option value="accepted">Accepted</option>
      </select>

      {filtered.map((invitation) => (
        <div key={invitation.id}>
          {invitation.email} - {invitation.status}
        </div>
      ))}
    </div>
  )
}
```

---

## API Reference

### `useSSO(client?)`

Hook for SSO provider management with optimistic updates.

#### Returns

```typescript
{
  // State
  providers: SSOProvider[]
  selectedProvider: SSOProvider | null
  loading: boolean
  error: string | null
  testResults: Record<string, SSOTestResult>

  // Actions
  fetchProviders: (orgId: string, forceRefresh?: boolean) => Promise<SSOProvider[]>
  createProvider: (orgId: string, data: Partial<SSOProvider>) => Promise<SSOProvider>
  updateProvider: (id: string, updates: Partial<SSOProvider>) => Promise<SSOProvider>
  deleteProvider: (id: string) => Promise<void>
  testConnection: (id: string, type?: 'metadata' | 'authentication' | 'full') => Promise<SSOTestResult>
  updateSAMLConfig: (id: string, config: Partial<SAMLConfig>) => Promise<SAMLConfig>
  setSelectedProvider: (provider: SSOProvider | null) => void
  invalidateCache: () => void

  // Helpers
  getProviderById: (id: string) => SSOProvider | undefined
  getProvidersByType: (type: SSOProvider['provider_type']) => SSOProvider[]
  getEnabledProviders: () => SSOProvider[]
}
```

#### Usage Examples

**Fetch Providers (with caching)**
```tsx
// First call: fetches from API
await fetchProviders('org-123')

// Second call within 5 min: uses cache
await fetchProviders('org-123')

// Force refresh (bypass cache)
await fetchProviders('org-123', true)
```

**Create Provider (optimistic update)**
```tsx
try {
  const provider = await createProvider('org-123', {
    name: 'Azure AD',
    provider_type: 'saml',
    enabled: true,
    jit_enabled: true,
    default_role: 'member',
  })
  // UI updates immediately, confirmed by server response
  console.log('Created:', provider.id)
} catch (err) {
  // Optimistic update automatically rolled back
  console.error('Failed:', err)
}
```

**Update Provider (optimistic update with rollback)**
```tsx
try {
  await updateProvider('provider-123', {
    enabled: false,
    default_role: 'admin',
  })
  // UI reflects change immediately
} catch (err) {
  // Automatically reverts to original state
}
```

**Test SSO Connection**
```tsx
const result = await testConnection('provider-123', 'full')

if (result.success) {
  console.log('Test passed!')
  console.log('User attributes:', result.results.user_attributes)
} else {
  console.error('Test failed:', result.results.errors)
}
```

**Filter Providers**
```tsx
// Get all SAML providers
const samlProviders = getProvidersByType('saml')

// Get enabled providers only
const enabled = getEnabledProviders()

// Get specific provider
const provider = getProviderById('provider-123')
```

---

### `useInvitations(client?)`

Hook for invitation management with optimistic updates and filtering.

#### Returns

```typescript
{
  // State
  invitations: Invitation[]
  stats: InvitationStats | null
  loading: boolean
  error: string | null
  filters: { status?: string; search?: string }

  // Actions
  fetchInvitations: (orgId: string, forceRefresh?: boolean) => Promise<Invitation[]>
  fetchStats: (orgId: string) => Promise<InvitationStats>
  createInvitation: (orgId: string, data: InvitationCreate) => Promise<Invitation>
  createBulkInvitations: (orgId: string, data: BulkInvitationCreate) => Promise<BulkInvitationResponse>
  resendInvitation: (id: string) => Promise<Invitation>
  revokeInvitation: (id: string) => Promise<Invitation>
  deleteInvitation: (id: string) => Promise<void>
  setFilters: (filters: { status?: string; search?: string }) => void
  clearFilters: () => void
  invalidateCache: () => void

  // Helpers
  getInvitationById: (id: string) => Invitation | undefined
  getFilteredInvitations: () => Invitation[]
  getPendingInvitations: () => Invitation[]
  getAcceptedInvitations: () => Invitation[]
}
```

#### Usage Examples

**Create Invitation**
```tsx
const invitation = await createInvitation('org-123', {
  email: 'user@example.com',
  role: 'member',
  message: 'Welcome to our team!',
  expires_in: 7, // days
})

console.log('Invitation URL:', invitation.invitation_url)
```

**Bulk Invitations**
```tsx
const result = await createBulkInvitations('org-123', {
  invitations: [
    { email: 'user1@example.com', role: 'member' },
    { email: 'user2@example.com', role: 'admin' },
    { email: 'user3@example.com' }, // uses default_role
  ],
  default_role: 'member',
  default_message: 'Welcome!',
  expires_in: 14,
})

console.log(`${result.successful}/${result.total} invitations sent`)
console.log('Failures:', result.results.filter(r => !r.success))
```

**Resend Invitation**
```tsx
await resendInvitation('invitation-123')
// Email re-sent, updated_at timestamp refreshed
```

**Revoke Invitation**
```tsx
await revokeInvitation('invitation-123')
// Status changes to 'revoked', can't be accepted
```

**Filter Invitations**
```tsx
// Filter by status
setFilters({ status: 'pending' })

// Filter by email search
setFilters({ search: 'john' })

// Combine filters
setFilters({ status: 'accepted', search: '@company.com' })

// Get filtered results
const filtered = getFilteredInvitations()

// Clear all filters
clearFilters()
```

**Get Statistics**
```tsx
await fetchStats('org-123')

console.log('Total:', stats.total)
console.log('Pending:', stats.pending)
console.log('Accepted:', stats.accepted)
console.log('Expired:', stats.expired)
```

---

## Direct Store Access

For advanced use cases, access the store directly:

```tsx
import { useEnterpriseStore } from '@plinto/ui/stores'

function AdvancedComponent() {
  // Use selectors for optimal performance
  const providers = useEnterpriseStore((state) => state.ssoProviders)
  const addProvider = useEnterpriseStore((state) => state.addSSOProvider)

  // Or use pre-defined selectors
  const { selectSSOProviders, selectInvitations } = useEnterpriseStore

  return <div>...</div>
}
```

---

## Caching Strategy

### Default Cache Duration
- **SSO Providers**: 5 minutes
- **Invitations**: 5 minutes

### Cache Validation
```tsx
const { isCacheValid, invalidateCache, fetchProviders } = useSSO()

// Check if cache is valid (default: 5 minutes)
if (isCacheValid()) {
  console.log('Using cached data')
} else {
  console.log('Cache expired, fetching fresh data')
}

// Check with custom duration (10 minutes)
if (isCacheValid(10 * 60 * 1000)) {
  console.log('Cache valid for 10 minutes')
}

// Force cache invalidation
invalidateCache()
await fetchProviders('org-123', true) // Force refresh
```

---

## Optimistic Updates

### How It Works

1. **Immediate UI Update**: State updates instantly with temporary/optimistic data
2. **API Call**: Real request sent to server
3. **Success**: Optimistic data replaced with server response
4. **Failure**: Automatic rollback to original state

### Example Flow

```tsx
// Initial state: providers = []

// 1. User clicks "Create Provider"
await createProvider('org-123', { name: 'Google', ... })

// 2. Immediate optimistic update
// providers = [{ id: 'temp-123', name: 'Google', ... }]
// UI shows provider instantly

// 3a. If success:
// providers = [{ id: 'provider-456', name: 'Google', ... }]
// Temporary ID replaced with real ID

// 3b. If failure:
// providers = []
// Rolled back to original state
// Error message shown to user
```

### Benefits

- **Instant Feedback**: No waiting for server responses
- **Better UX**: Feels fast and responsive
- **Safe**: Automatic rollback prevents inconsistent state
- **Transparent**: Users don't notice rollbacks on errors

---

## Persistence

### What's Persisted

Only non-sensitive UI state is persisted to localStorage:

- Selected SSO provider
- Invitation filters (status, search)

### What's NOT Persisted

- Provider lists (refetched on app load)
- Invitation lists (refetched on app load)
- Loading states
- Error messages
- Test results

### Custom Persistence

```tsx
import { useEnterpriseStore } from '@plinto/ui/stores'

// Clear persisted state
localStorage.removeItem('plinto-enterprise-store')

// Access persisted state
const persisted = localStorage.getItem('plinto-enterprise-store')
console.log(JSON.parse(persisted))
```

---

## TypeScript Types

### SSOProvider
```typescript
interface SSOProvider {
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

  // SAML-specific
  saml_entity_id?: string
  saml_acs_url?: string
  saml_metadata_url?: string

  // OIDC-specific
  oidc_client_id?: string
  oidc_issuer?: string
  oidc_authorization_endpoint?: string
  oidc_token_endpoint?: string
}
```

### Invitation
```typescript
interface Invitation {
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
```

### InvitationStats
```typescript
interface InvitationStats {
  total: number
  pending: number
  accepted: number
  expired: number
  revoked: number
}
```

---

## Best Practices

### 1. Use Hooks, Not Direct Store Access
```tsx
// ✅ Recommended
const { providers, createProvider } = useSSO(client)

// ❌ Avoid (unless you need advanced control)
const providers = useEnterpriseStore((state) => state.ssoProviders)
```

### 2. Handle Errors Properly
```tsx
try {
  await createProvider('org-123', data)
  toast.success('Provider created')
} catch (err) {
  // Optimistic update already rolled back
  toast.error(err.message)
  // Log for debugging
  console.error('Provider creation failed:', err)
}
```

### 3. Leverage Caching
```tsx
// Don't refetch unnecessarily
useEffect(() => {
  // Only fetches if cache expired
  fetchProviders('org-123')
}, [])

// Force refresh only when needed
const handleRefresh = () => {
  fetchProviders('org-123', true)
}
```

### 4. Use Filters for Performance
```tsx
// ✅ Filter in store (efficient)
setFilters({ status: 'pending' })
const filtered = getFilteredInvitations()

// ❌ Filter in component (less efficient)
const filtered = invitations.filter(i => i.status === 'pending')
```

### 5. Clean Up on Unmount
```tsx
useEffect(() => {
  fetchProviders('org-123')

  return () => {
    // Optional: clear filters on unmount
    clearFilters()
  }
}, [])
```

---

## Troubleshooting

### Cache Not Working
```tsx
// Check cache validity
const isValid = isCacheValid()
console.log('Cache valid:', isValid)

// Check last fetched timestamp
const store = useEnterpriseStore.getState()
console.log('Last fetched:', new Date(store.ssoLastFetched))

// Force invalidate
invalidateCache()
```

### Optimistic Update Not Rolling Back
```tsx
// Ensure you're catching errors
try {
  await createProvider(...)
} catch (err) {
  // Error caught = rollback triggered
  console.error(err)
}
```

### DevTools Not Showing
```tsx
// Only enabled in development
console.log('NODE_ENV:', process.env.NODE_ENV)

// Install Redux DevTools browser extension
// https://github.com/reduxjs/redux-devtools
```

### State Not Persisting
```tsx
// Check localStorage
console.log(localStorage.getItem('plinto-enterprise-store'))

// Only selected provider and filters are persisted
// Full data lists are NOT persisted (security/freshness)
```

---

## Migration Guide

### From Local State to Store

**Before:**
```tsx
function Component() {
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchProviders()
  }, [])

  const fetchProviders = async () => {
    setLoading(true)
    const data = await api.getProviders()
    setProviders(data)
    setLoading(false)
  }
}
```

**After:**
```tsx
function Component() {
  const { providers, loading, fetchProviders } = useSSO(client)

  useEffect(() => {
    fetchProviders('org-123')
  }, [])

  // That's it! Caching, loading, error handling all included
}
```

---

## Performance Tips

1. **Use Selectors**: Only subscribe to needed state slices
2. **Leverage Caching**: Avoid unnecessary API calls
3. **Filter in Store**: Use built-in filter functions
4. **Batch Updates**: Multiple updates in single action
5. **Invalidate Strategically**: Only when data actually changes

---

## License

MIT
