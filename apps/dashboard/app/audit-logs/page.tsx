'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@janua/ui'
import { Button } from '@janua/ui'
import { Badge } from '@janua/ui'
import { Input } from '@janua/ui'
import Link from 'next/link'
import {
  Lock,
  ArrowLeft,
  Search,
  Filter,
  RefreshCw,
  Loader2,
  AlertCircle,
  User,
  Shield,
  Key,
  Settings,
  LogIn,
  LogOut,
  UserPlus,
  UserMinus,
  FileEdit,
  Download,
} from 'lucide-react'
import { apiCall } from '../../lib/auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.janua.dev'

interface AuditLogEntry {
  id: string
  timestamp: string
  event_type: string
  actor_id?: string
  actor_email?: string
  actor_ip?: string
  target_type?: string
  target_id?: string
  action: string
  details?: Record<string, any>
  success: boolean
  organization_id?: string
}

const eventIcons: Record<string, any> = {
  login: LogIn,
  logout: LogOut,
  register: UserPlus,
  delete_user: UserMinus,
  update_user: FileEdit,
  mfa_enabled: Shield,
  mfa_disabled: Shield,
  password_change: Key,
  password_reset: Key,
  settings_change: Settings,
  default: Lock,
}

const eventLabels: Record<string, string> = {
  login: 'User Login',
  logout: 'User Logout',
  login_failed: 'Login Failed',
  register: 'User Registration',
  delete_user: 'User Deleted',
  update_user: 'User Updated',
  mfa_enabled: 'MFA Enabled',
  mfa_disabled: 'MFA Disabled',
  password_change: 'Password Changed',
  password_reset: 'Password Reset',
  settings_change: 'Settings Changed',
  token_refresh: 'Token Refreshed',
  session_created: 'Session Created',
  session_revoked: 'Session Revoked',
  api_key_created: 'API Key Created',
  api_key_revoked: 'API Key Revoked',
  invitation_sent: 'Invitation Sent',
  invitation_accepted: 'Invitation Accepted',
  sso_login: 'SSO Login',
  sso_config_updated: 'SSO Config Updated',
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [eventFilter, setEventFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)

  useEffect(() => {
    fetchLogs()
  }, [page, eventFilter])

  const fetchLogs = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams({
        page: page.toString(),
        limit: '50',
      })

      if (eventFilter !== 'all') {
        params.append('event_type', eventFilter)
      }

      const response = await apiCall(`${API_BASE_URL}/api/v1/audit-logs?${params}`)

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('You do not have permission to view audit logs')
        }
        throw new Error('Failed to fetch audit logs')
      }

      const data = await response.json()
      const logsList = Array.isArray(data) ? data : data.logs || data.items || []

      if (page === 1) {
        setLogs(logsList)
      } else {
        setLogs((prev) => [...prev, ...logsList])
      }

      setHasMore(logsList.length === 50)
    } catch (err) {
      console.error('Failed to fetch audit logs:', err)
      setError(err instanceof Error ? err.message : 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const getEventIcon = (eventType: string) => {
    const IconComponent = eventIcons[eventType] || eventIcons.default
    return <IconComponent className="h-4 w-4" />
  }

  const getEventLabel = (eventType: string) => {
    return eventLabels[eventType] || eventType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }

  const filteredLogs = logs.filter((log) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      log.actor_email?.toLowerCase().includes(query) ||
      log.event_type.toLowerCase().includes(query) ||
      log.action?.toLowerCase().includes(query) ||
      log.actor_ip?.includes(query)
    )
  })

  const handleExport = async () => {
    try {
      const response = await apiCall(`${API_BASE_URL}/api/v1/audit-logs/export`)
      if (!response.ok) throw new Error('Failed to export logs')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to export logs')
    }
  }

  const uniqueEventTypes = Array.from(new Set(logs.map((l) => l.event_type)))

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/settings" className="text-muted-foreground hover:text-foreground">
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <Lock className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold">Audit Logs</h1>
                <p className="text-sm text-muted-foreground">
                  View security events and user activity
                </p>
              </div>
            </div>
            <Badge variant="outline">Admin Only</Badge>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 space-y-6">
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                <span>{error}</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Filters */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Security Events</CardTitle>
                <CardDescription>
                  {filteredLogs.length} events found
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleExport}>
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPage(1)
                    fetchLogs()
                  }}
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row gap-4 mb-6">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by email, event type, or IP address..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <div className="flex gap-2">
                <select
                  className="h-10 px-3 border rounded-md bg-background text-sm"
                  value={eventFilter}
                  onChange={(e) => {
                    setEventFilter(e.target.value)
                    setPage(1)
                  }}
                >
                  <option value="all">All Events</option>
                  <option value="login">Logins</option>
                  <option value="login_failed">Failed Logins</option>
                  <option value="logout">Logouts</option>
                  <option value="register">Registrations</option>
                  <option value="password_change">Password Changes</option>
                  <option value="mfa_enabled">MFA Events</option>
                  <option value="settings_change">Settings Changes</option>
                </select>
              </div>
            </div>

            {loading && page === 1 ? (
              <div className="text-center py-8">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
                <p className="mt-2 text-sm text-muted-foreground">Loading audit logs...</p>
              </div>
            ) : filteredLogs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Lock className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No audit logs found</p>
                {searchQuery && (
                  <p className="text-sm mt-2">Try adjusting your search criteria</p>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {filteredLogs.map((log) => (
                  <div
                    key={log.id}
                    className={`flex items-start justify-between p-4 border rounded-lg ${
                      !log.success ? 'border-destructive/30 bg-destructive/5' : ''
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`p-2 rounded-full bg-muted ${!log.success ? 'bg-destructive/10' : ''}`}>
                        {getEventIcon(log.event_type)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{getEventLabel(log.event_type)}</span>
                          <Badge variant={log.success ? 'default' : 'destructive'}>
                            {log.success ? 'Success' : 'Failed'}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {log.actor_email && (
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {log.actor_email}
                            </span>
                          )}
                          {log.actor_ip && (
                            <span className="ml-4">IP: {log.actor_ip}</span>
                          )}
                        </div>
                        {log.action && log.action !== log.event_type && (
                          <p className="text-sm mt-1">{log.action}</p>
                        )}
                        {log.details && Object.keys(log.details).length > 0 && (
                          <details className="mt-2">
                            <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                              Show details
                            </summary>
                            <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-auto max-h-32">
                              {JSON.stringify(log.details, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground whitespace-nowrap">
                      {formatDate(log.timestamp)}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {hasMore && !loading && (
              <div className="text-center mt-6">
                <Button
                  variant="outline"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    'Load More'
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Info Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">About Audit Logs</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>
              Audit logs record all security-relevant events in your organization, including user
              authentication, settings changes, and administrative actions.
            </p>
            <p>
              Logs are retained for 90 days by default. Contact support if you need extended
              retention or compliance exports.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
