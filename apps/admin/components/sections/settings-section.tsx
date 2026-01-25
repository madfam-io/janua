'use client'

import { useState, useEffect } from 'react'
import { adminAPI } from '@/lib/admin-api'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.janua.dev'

// Types
interface Alert {
  alert_id: string
  rule_id: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  status: string
  title: string
  description: string
  metric_value: number
  threshold_value: number
  triggered_at: string
  acknowledged_at: string | null
  acknowledged_by: string | null
  context: Record<string, unknown>
  notifications_sent: number
}

interface AlertRule {
  rule_id: string
  name: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  metric_name: string
  threshold_value: number
  comparison_operator: string
  evaluation_window: number
  trigger_count: number
  cooldown_period: number
  enabled: boolean
  channels: string[]
  conditions: Record<string, unknown>
  metadata: Record<string, unknown>
}

interface NotificationChannel {
  channel_id: string
  channel_type: 'email' | 'webhook' | 'slack' | 'pagerduty'
  name: string
  config: Record<string, string>
  enabled: boolean
  rate_limit: number | null
}

interface ApiKey {
  id: string
  name: string
  key_prefix: string
  scopes: string[]
  created_at: string
  last_used_at: string | null
  expires_at: string | null
  is_active: boolean
}

interface BrandingConfig {
  id: string
  organization_id: string
  branding_level: string
  is_enabled: boolean
  company_name: string | null
  company_logo_url: string | null
  primary_color: string
  secondary_color: string
  accent_color: string
  created_at: string
  updated_at: string
}

// Sub-tab type
type SettingsTab = 'general' | 'alerts' | 'api-keys' | 'branding'

function getAuthHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('janua_access_token') : null
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  }
}

// Severity badge colors
const severityColors = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  low: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
}

// General Settings Sub-section
function GeneralSettings() {
  const [maintenanceMode, setMaintenanceMode] = useState(false)
  const [saving, setSaving] = useState(false)

  const handleMaintenanceToggle = async () => {
    setSaving(true)
    try {
      await adminAPI.setMaintenanceMode(!maintenanceMode)
      setMaintenanceMode(!maintenanceMode)
    } catch {
      alert('Failed to update maintenance mode')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-card border-border rounded-lg border p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-foreground font-medium">Maintenance Mode</h4>
              <p className="text-muted-foreground text-sm">Temporarily disable access to the platform</p>
            </div>
            <button
              onClick={handleMaintenanceToggle}
              disabled={saving}
              className={`rounded-lg px-4 py-2 ${
                maintenanceMode
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              } disabled:opacity-50`}
            >
              {saving ? 'Saving...' : maintenanceMode ? 'Disable' : 'Enable'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Alerts Settings Sub-section
function AlertsSettings() {
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([])
  const [alertRules, setAlertRules] = useState<AlertRule[]>([])
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAlertData()
  }, [])

  const fetchAlertData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch active alerts
      const alertsRes = await fetch(`${API_URL}/api/v1/alerts/active`, {
        headers: getAuthHeaders(),
      })
      if (alertsRes.ok) {
        const data = await alertsRes.json()
        setActiveAlerts(Array.isArray(data) ? data : [])
      }

      // Fetch alert rules
      const rulesRes = await fetch(`${API_URL}/api/v1/alerts/rules`, {
        headers: getAuthHeaders(),
      })
      if (rulesRes.ok) {
        const data = await rulesRes.json()
        setAlertRules(Array.isArray(data) ? data : [])
      }

      // Fetch notification channels
      const channelsRes = await fetch(`${API_URL}/api/v1/alerts/channels`, {
        headers: getAuthHeaders(),
      })
      if (channelsRes.ok) {
        const data = await channelsRes.json()
        setChannels(Array.isArray(data) ? data : [])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alert data')
    } finally {
      setLoading(false)
    }
  }

  const handleAcknowledge = async (alertId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: getAuthHeaders(),
      })
      if (!res.ok) throw new Error('Failed to acknowledge')
      fetchAlertData()
    } catch {
      alert('Failed to acknowledge alert')
    }
  }

  const handleResolve = async (alertId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: getAuthHeaders(),
      })
      if (!res.ok) throw new Error('Failed to resolve')
      fetchAlertData()
    } catch {
      alert('Failed to resolve alert')
    }
  }

  const handleToggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/alerts/rules/${ruleId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ enabled }),
      })
      if (!res.ok) throw new Error('Failed to update rule')
      fetchAlertData()
    } catch {
      alert('Failed to update rule')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading alerts...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-destructive/10 text-destructive rounded-lg p-4">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Active Alerts */}
      <div className="bg-card border-border rounded-lg border p-6">
        <div className="mb-4 flex items-center justify-between">
          <h4 className="text-foreground font-medium">Active Alerts</h4>
          <span className="bg-destructive/10 text-destructive rounded-full px-2 py-1 text-xs font-medium">
            {activeAlerts.length}
          </span>
        </div>
        {activeAlerts.length === 0 ? (
          <p className="text-muted-foreground text-sm">No active alerts</p>
        ) : (
          <div className="space-y-3">
            {activeAlerts.map((alert) => (
              <div key={alert.alert_id} className="flex items-start justify-between rounded-lg border p-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{alert.title}</span>
                    <span className={`rounded px-2 py-0.5 text-xs ${severityColors[alert.severity]}`}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-muted-foreground mt-1 text-sm">{alert.description}</p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    {new Date(alert.triggered_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  {!alert.acknowledged_at && (
                    <button
                      onClick={() => handleAcknowledge(alert.alert_id)}
                      className="bg-muted hover:bg-muted/80 rounded px-3 py-1 text-sm"
                    >
                      Acknowledge
                    </button>
                  )}
                  <button
                    onClick={() => handleResolve(alert.alert_id)}
                    className="bg-primary text-primary-foreground hover:bg-primary/90 rounded px-3 py-1 text-sm"
                  >
                    Resolve
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Alert Rules */}
      <div className="bg-card border-border rounded-lg border p-6">
        <h4 className="text-foreground mb-4 font-medium">Alert Rules</h4>
        {alertRules.length === 0 ? (
          <p className="text-muted-foreground text-sm">No alert rules configured</p>
        ) : (
          <div className="space-y-3">
            {alertRules.map((rule) => (
              <div key={rule.rule_id} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{rule.name}</span>
                    <span className={`rounded px-2 py-0.5 text-xs ${severityColors[rule.severity]}`}>
                      {rule.severity}
                    </span>
                    <span className={`rounded px-2 py-0.5 text-xs ${rule.enabled ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-gray-100 text-gray-800'}`}>
                      {rule.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </div>
                  <p className="text-muted-foreground mt-1 text-sm">{rule.description}</p>
                </div>
                <button
                  onClick={() => handleToggleRule(rule.rule_id, !rule.enabled)}
                  className="bg-muted hover:bg-muted/80 rounded px-3 py-1 text-sm"
                >
                  {rule.enabled ? 'Disable' : 'Enable'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Notification Channels */}
      <div className="bg-card border-border rounded-lg border p-6">
        <h4 className="text-foreground mb-4 font-medium">Notification Channels</h4>
        {channels.length === 0 ? (
          <p className="text-muted-foreground text-sm">No notification channels configured</p>
        ) : (
          <div className="space-y-3">
            {channels.map((channel) => (
              <div key={channel.channel_id} className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-3">
                  <span className="bg-muted rounded px-2 py-1 text-xs uppercase">{channel.channel_type}</span>
                  <span className="font-medium">{channel.name}</span>
                  <span className={`rounded px-2 py-0.5 text-xs ${channel.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {channel.enabled ? 'Active' : 'Disabled'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// API Keys Settings Sub-section
function ApiKeysSettings() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchApiKeys()
  }, [])

  const fetchApiKeys = async () => {
    try {
      setLoading(true)
      setError(null)

      const res = await fetch(`${API_URL}/api/v1/api-keys`, {
        headers: getAuthHeaders(),
      })

      if (res.status === 404) {
        setApiKeys([])
      } else if (!res.ok) {
        throw new Error('Failed to fetch API keys')
      } else {
        const data = await res.json()
        setApiKeys(Array.isArray(data) ? data : data.items || [])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load API keys')
    } finally {
      setLoading(false)
    }
  }

  const handleRevokeKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return

    try {
      const res = await fetch(`${API_URL}/api/v1/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      if (!res.ok) throw new Error('Failed to revoke key')
      fetchApiKeys()
    } catch {
      alert('Failed to revoke API key')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading API keys...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-destructive/10 text-destructive rounded-lg p-4">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-card border-border rounded-lg border p-6">
        <div className="mb-4 flex items-center justify-between">
          <h4 className="text-foreground font-medium">Platform API Keys</h4>
          <span className="text-muted-foreground text-sm">{apiKeys.length} keys</span>
        </div>
        {apiKeys.length === 0 ? (
          <p className="text-muted-foreground text-sm">No API keys found</p>
        ) : (
          <div className="space-y-3">
            {apiKeys.map((key) => (
              <div key={key.id} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{key.name}</span>
                    <span className={`rounded px-2 py-0.5 text-xs ${key.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {key.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <p className="text-muted-foreground mt-1 font-mono text-sm">{key.key_prefix}...</p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    Created: {new Date(key.created_at).toLocaleDateString()}
                    {key.last_used_at && ` | Last used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {key.scopes.map((scope) => (
                      <span key={scope} className="bg-muted rounded px-2 py-0.5 text-xs">
                        {scope}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() => handleRevokeKey(key.id)}
                  className="text-destructive hover:bg-destructive/10 rounded px-3 py-1 text-sm"
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Security Info */}
      <div className="bg-card border-border rounded-lg border p-6">
        <h4 className="text-foreground mb-2 font-medium">API Key Security</h4>
        <ul className="text-muted-foreground space-y-2 text-sm">
          <li>API keys provide programmatic access to the Janua platform</li>
          <li>Keys should be stored securely and never exposed in client-side code</li>
          <li>Rotate keys periodically and revoke any compromised keys immediately</li>
          <li>Monitor the &quot;last used&quot; timestamps to detect unauthorized access</li>
        </ul>
      </div>
    </div>
  )
}

// Branding Settings Sub-section
function BrandingSettings() {
  const [configs, setConfigs] = useState<BrandingConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchBrandingConfigs()
  }, [])

  const fetchBrandingConfigs = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch all white-label configurations (admin view)
      const res = await fetch(`${API_URL}/api/v1/white-label/configurations`, {
        headers: getAuthHeaders(),
      })

      if (res.status === 404) {
        setConfigs([])
      } else if (!res.ok) {
        throw new Error('Failed to fetch branding configurations')
      } else {
        const data = await res.json()
        setConfigs(Array.isArray(data) ? data : data.items || [])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load branding configurations')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleBranding = async (configId: string, enabled: boolean) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/white-label/configurations/${configId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ is_enabled: enabled }),
      })
      if (!res.ok) throw new Error('Failed to update')
      fetchBrandingConfigs()
    } catch {
      alert('Failed to update branding configuration')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading branding settings...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-destructive/10 text-destructive rounded-lg p-4">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-card border-border rounded-lg border p-6">
        <div className="mb-4 flex items-center justify-between">
          <h4 className="text-foreground font-medium">White-Label Configurations</h4>
          <span className="text-muted-foreground text-sm">{configs.length} organizations</span>
        </div>
        {configs.length === 0 ? (
          <p className="text-muted-foreground text-sm">No branding configurations found</p>
        ) : (
          <div className="space-y-3">
            {configs.map((config) => (
              <div key={config.id} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{config.company_name || 'Unnamed Organization'}</span>
                    <span className={`rounded px-2 py-0.5 text-xs ${config.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {config.is_enabled ? 'Active' : 'Disabled'}
                    </span>
                    <span className="bg-muted rounded px-2 py-0.5 text-xs">{config.branding_level}</span>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-muted-foreground text-xs">Colors:</span>
                    <div
                      className="size-4 rounded border"
                      style={{ backgroundColor: config.primary_color }}
                      title={`Primary: ${config.primary_color}`}
                    />
                    <div
                      className="size-4 rounded border"
                      style={{ backgroundColor: config.secondary_color }}
                      title={`Secondary: ${config.secondary_color}`}
                    />
                    <div
                      className="size-4 rounded border"
                      style={{ backgroundColor: config.accent_color }}
                      title={`Accent: ${config.accent_color}`}
                    />
                  </div>
                  <p className="text-muted-foreground mt-1 text-xs">
                    Updated: {new Date(config.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => handleToggleBranding(config.id, !config.is_enabled)}
                  className="bg-muted hover:bg-muted/80 rounded px-3 py-1 text-sm"
                >
                  {config.is_enabled ? 'Disable' : 'Enable'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Branding Info */}
      <div className="bg-card border-border rounded-lg border p-6">
        <h4 className="text-foreground mb-2 font-medium">White-Label Features</h4>
        <ul className="text-muted-foreground space-y-2 text-sm">
          <li><strong>Basic:</strong> Custom logo and company name</li>
          <li><strong>Standard:</strong> Custom colors, fonts, and styling</li>
          <li><strong>Enterprise:</strong> Custom domains, CSS injection, and full theming</li>
        </ul>
      </div>
    </div>
  )
}

// Main Settings Section Component
export function SettingsSection() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general')

  const tabs: { id: SettingsTab; label: string }[] = [
    { id: 'general', label: 'General' },
    { id: 'alerts', label: 'Alerts' },
    { id: 'api-keys', label: 'API Keys' },
    { id: 'branding', label: 'Branding' },
  ]

  return (
    <div className="space-y-6">
      <h2 className="text-foreground text-2xl font-bold">Platform Settings</h2>

      {/* Tab Navigation */}
      <div className="border-border border-b">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`border-b-2 px-1 py-4 text-sm font-medium ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:border-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'general' && <GeneralSettings />}
        {activeTab === 'alerts' && <AlertsSettings />}
        {activeTab === 'api-keys' && <ApiKeysSettings />}
        {activeTab === 'branding' && <BrandingSettings />}
      </div>
    </div>
  )
}
