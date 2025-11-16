import * as React from 'react'
import { Button } from '../button'
import { cn } from '../../lib/utils'

export interface SSOConfigurationCreate {
  provider: 'saml' | 'oidc'
  saml_metadata_url?: string
  saml_metadata_xml?: string
  saml_sso_url?: string
  saml_slo_url?: string
  saml_certificate?: string
  saml_entity_id?: string
  oidc_issuer?: string
  oidc_client_id?: string
  oidc_client_secret?: string
  oidc_discovery_url?: string
  jit_provisioning?: boolean
  default_role?: string
  attribute_mapping?: Record<string, string>
  allowed_domains?: string[]
}

export interface SSOConfiguration extends SSOConfigurationCreate {
  id: string
  organization_id: string
  status: string
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface SSOProviderFormProps {
  className?: string
  organizationId: string
  configuration?: SSOConfiguration
  onSubmit?: (config: SSOConfigurationCreate) => Promise<SSOConfiguration>
  onCancel?: () => void
  onError?: (error: Error) => void
  plintoClient?: any
  apiUrl?: string
  mode?: 'create' | 'edit'
}

export function SSOProviderForm({
  className,
  organizationId,
  configuration,
  onSubmit,
  onCancel,
  onError,
  plintoClient,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  mode = configuration ? 'edit' : 'create',
}: SSOProviderFormProps) {
  const [provider, setProvider] = React.useState<'saml' | 'oidc'>(
    configuration?.provider || 'saml'
  )
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  // SAML fields
  const [samlMetadataUrl, setSamlMetadataUrl] = React.useState(
    configuration?.saml_metadata_url || ''
  )
  const [samlMetadataXml, setSamlMetadataXml] = React.useState(
    configuration?.saml_metadata_xml || ''
  )
  const [samlSsoUrl, setSamlSsoUrl] = React.useState(configuration?.saml_sso_url || '')
  const [samlSloUrl, setSamlSloUrl] = React.useState(configuration?.saml_slo_url || '')
  const [samlCertificate, setSamlCertificate] = React.useState(
    configuration?.saml_certificate || ''
  )
  const [samlEntityId, setSamlEntityId] = React.useState(configuration?.saml_entity_id || '')

  // OIDC fields
  const [oidcIssuer, setOidcIssuer] = React.useState(configuration?.oidc_issuer || '')
  const [oidcClientId, setOidcClientId] = React.useState(configuration?.oidc_client_id || '')
  const [oidcClientSecret, setOidcClientSecret] = React.useState(
    configuration?.oidc_client_secret || ''
  )
  const [oidcDiscoveryUrl, setOidcDiscoveryUrl] = React.useState(
    configuration?.oidc_discovery_url || ''
  )

  // Common fields
  const [jitProvisioning, setJitProvisioning] = React.useState(
    configuration?.jit_provisioning ?? true
  )
  const [defaultRole, setDefaultRole] = React.useState(configuration?.default_role || 'member')
  const [allowedDomains, setAllowedDomains] = React.useState(
    configuration?.allowed_domains?.join(', ') || ''
  )

  // Handle submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (provider === 'saml') {
      if (!samlMetadataUrl && !samlMetadataXml && !samlSsoUrl) {
        setError('Please provide either Metadata URL, Metadata XML, or SSO URL for SAML')
        return
      }
    } else if (provider === 'oidc') {
      if (!oidcIssuer || !oidcClientId || !oidcClientSecret) {
        setError('OIDC requires Issuer, Client ID, and Client Secret')
        return
      }
    }

    setIsSubmitting(true)

    try {
      const configData: SSOConfigurationCreate = {
        provider,
        jit_provisioning: jitProvisioning,
        default_role: defaultRole,
        allowed_domains: allowedDomains
          .split(',')
          .map((d) => d.trim())
          .filter((d) => d.length > 0),
      }

      if (provider === 'saml') {
        if (samlMetadataUrl) configData.saml_metadata_url = samlMetadataUrl
        if (samlMetadataXml) configData.saml_metadata_xml = samlMetadataXml
        if (samlSsoUrl) configData.saml_sso_url = samlSsoUrl
        if (samlSloUrl) configData.saml_slo_url = samlSloUrl
        if (samlCertificate) configData.saml_certificate = samlCertificate
        if (samlEntityId) configData.saml_entity_id = samlEntityId
      } else if (provider === 'oidc') {
        configData.oidc_issuer = oidcIssuer
        configData.oidc_client_id = oidcClientId
        configData.oidc_client_secret = oidcClientSecret
        if (oidcDiscoveryUrl) configData.oidc_discovery_url = oidcDiscoveryUrl
      }

      if (plintoClient) {
        if (mode === 'create') {
          await plintoClient.sso.createConfiguration(organizationId, configData)
        } else {
          await plintoClient.sso.updateConfiguration(organizationId, configData)
        }
      } else if (onSubmit) {
        await onSubmit(configData)
      } else {
        const url =
          mode === 'create'
            ? `${apiUrl}/api/v1/sso/configurations?organization_id=${organizationId}`
            : `${apiUrl}/api/v1/sso/configurations/${organizationId}`

        const res = await fetch(url, {
          method: mode === 'create' ? 'POST' : 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(configData),
        })

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}))
          throw new Error(errorData.detail || 'Failed to save SSO configuration')
        }
      }

      onCancel?.()
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to save SSO configuration')
      setError(error.message)
      onError?.(error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={cn('space-y-6', className)}>
      {/* Error */}
      {error && (
        <div className="p-4 border border-red-200 bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* Provider Selection */}
      {mode === 'create' && (
        <div className="space-y-2">
          <label className="block text-sm font-medium">SSO Provider</label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setProvider('saml')}
              className={cn(
                'p-4 border-2 rounded-lg text-left transition-colors',
                provider === 'saml'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 hover:border-gray-300'
              )}
            >
              <div className="font-semibold">SAML 2.0</div>
              <div className="text-xs text-muted-foreground mt-1">
                Works with Okta, OneLogin, Auth0, and most enterprise IdPs
              </div>
            </button>
            <button
              type="button"
              onClick={() => setProvider('oidc')}
              className={cn(
                'p-4 border-2 rounded-lg text-left transition-colors',
                provider === 'oidc'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 hover:border-gray-300'
              )}
            >
              <div className="font-semibold">OIDC/OAuth2</div>
              <div className="text-xs text-muted-foreground mt-1">
                Works with Google, Azure AD, and modern OAuth providers
              </div>
            </button>
          </div>
        </div>
      )}

      {/* SAML Configuration */}
      {provider === 'saml' && (
        <div className="space-y-4 p-4 border rounded-lg bg-gray-50 dark:bg-gray-900">
          <h4 className="font-semibold">SAML Configuration</h4>

          <div className="space-y-2">
            <label htmlFor="samlMetadataUrl" className="block text-sm font-medium">
              Metadata URL
            </label>
            <input
              id="samlMetadataUrl"
              type="url"
              value={samlMetadataUrl}
              onChange={(e) => setSamlMetadataUrl(e.target.value)}
              placeholder="https://idp.example.com/metadata"
              className="w-full px-3 py-2 border rounded-md"
            />
            <p className="text-xs text-muted-foreground">
              URL to your identity provider's SAML metadata
            </p>
          </div>

          <div className="text-center text-sm text-muted-foreground">OR</div>

          <div className="space-y-2">
            <label htmlFor="samlMetadataXml" className="block text-sm font-medium">
              Metadata XML
            </label>
            <textarea
              id="samlMetadataXml"
              value={samlMetadataXml}
              onChange={(e) => setSamlMetadataXml(e.target.value)}
              placeholder="Paste SAML metadata XML here..."
              rows={4}
              className="w-full px-3 py-2 border rounded-md font-mono text-xs"
            />
          </div>

          <div className="text-center text-sm text-muted-foreground">OR manually configure:</div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="samlSsoUrl" className="block text-sm font-medium">
                SSO URL
              </label>
              <input
                id="samlSsoUrl"
                type="url"
                value={samlSsoUrl}
                onChange={(e) => setSamlSsoUrl(e.target.value)}
                placeholder="https://idp.example.com/sso"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="samlSloUrl" className="block text-sm font-medium">
                SLO URL <span className="text-muted-foreground text-xs">(Optional)</span>
              </label>
              <input
                id="samlSloUrl"
                type="url"
                value={samlSloUrl}
                onChange={(e) => setSamlSloUrl(e.target.value)}
                placeholder="https://idp.example.com/slo"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="samlEntityId" className="block text-sm font-medium">
              Entity ID <span className="text-muted-foreground text-xs">(Optional)</span>
            </label>
            <input
              id="samlEntityId"
              type="text"
              value={samlEntityId}
              onChange={(e) => setSamlEntityId(e.target.value)}
              placeholder="https://idp.example.com"
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="samlCertificate" className="block text-sm font-medium">
              X.509 Certificate <span className="text-muted-foreground text-xs">(Optional)</span>
            </label>
            <textarea
              id="samlCertificate"
              value={samlCertificate}
              onChange={(e) => setSamlCertificate(e.target.value)}
              placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
              rows={4}
              className="w-full px-3 py-2 border rounded-md font-mono text-xs"
            />
          </div>
        </div>
      )}

      {/* OIDC Configuration */}
      {provider === 'oidc' && (
        <div className="space-y-4 p-4 border rounded-lg bg-gray-50 dark:bg-gray-900">
          <h4 className="font-semibold">OIDC Configuration</h4>

          <div className="space-y-2">
            <label htmlFor="oidcIssuer" className="block text-sm font-medium">
              Issuer URL <span className="text-red-500">*</span>
            </label>
            <input
              id="oidcIssuer"
              type="url"
              value={oidcIssuer}
              onChange={(e) => setOidcIssuer(e.target.value)}
              placeholder="https://accounts.google.com"
              required={provider === 'oidc'}
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="oidcClientId" className="block text-sm font-medium">
                Client ID <span className="text-red-500">*</span>
              </label>
              <input
                id="oidcClientId"
                type="text"
                value={oidcClientId}
                onChange={(e) => setOidcClientId(e.target.value)}
                placeholder="your-client-id"
                required={provider === 'oidc'}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="oidcClientSecret" className="block text-sm font-medium">
                Client Secret <span className="text-red-500">*</span>
              </label>
              <input
                id="oidcClientSecret"
                type="password"
                value={oidcClientSecret}
                onChange={(e) => setOidcClientSecret(e.target.value)}
                placeholder="your-client-secret"
                required={provider === 'oidc'}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="oidcDiscoveryUrl" className="block text-sm font-medium">
              Discovery URL <span className="text-muted-foreground text-xs">(Optional)</span>
            </label>
            <input
              id="oidcDiscoveryUrl"
              type="url"
              value={oidcDiscoveryUrl}
              onChange={(e) => setOidcDiscoveryUrl(e.target.value)}
              placeholder="https://accounts.google.com/.well-known/openid-configuration"
              className="w-full px-3 py-2 border rounded-md"
            />
            <p className="text-xs text-muted-foreground">
              Auto-discover OIDC endpoints from well-known URL
            </p>
          </div>
        </div>
      )}

      {/* Common Settings */}
      <div className="space-y-4 p-4 border rounded-lg">
        <h4 className="font-semibold">Common Settings</h4>

        <div className="space-y-2">
          <label htmlFor="defaultRole" className="block text-sm font-medium">
            Default Role
          </label>
          <select
            id="defaultRole"
            value={defaultRole}
            onChange={(e) => setDefaultRole(e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            <option value="viewer">Viewer</option>
            <option value="member">Member</option>
            <option value="admin">Admin</option>
            <option value="owner">Owner</option>
          </select>
          <p className="text-xs text-muted-foreground">
            Role assigned to new users signing in via SSO
          </p>
        </div>

        <div className="flex items-center gap-2">
          <input
            id="jitProvisioning"
            type="checkbox"
            checked={jitProvisioning}
            onChange={(e) => setJitProvisioning(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="jitProvisioning" className="text-sm font-medium cursor-pointer">
            Enable Just-In-Time (JIT) Provisioning
          </label>
        </div>
        <p className="text-xs text-muted-foreground ml-6">
          Automatically create user accounts when they first sign in via SSO
        </p>

        <div className="space-y-2">
          <label htmlFor="allowedDomains" className="block text-sm font-medium">
            Allowed Email Domains <span className="text-muted-foreground text-xs">(Optional)</span>
          </label>
          <input
            id="allowedDomains"
            type="text"
            value={allowedDomains}
            onChange={(e) => setAllowedDomains(e.target.value)}
            placeholder="example.com, company.com"
            className="w-full px-3 py-2 border rounded-md"
          />
          <p className="text-xs text-muted-foreground">
            Comma-separated list. Leave empty to allow all domains.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Button type="submit" disabled={isSubmitting} className="flex-1">
          {isSubmitting ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Saving...
            </>
          ) : mode === 'create' ? (
            'Create SSO Configuration'
          ) : (
            'Update SSO Configuration'
          )}
        </Button>
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  )
}
