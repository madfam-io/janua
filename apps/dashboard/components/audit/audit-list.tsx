'use client'

import { useState, useEffect } from 'react'
import { Button } from '@janua/ui'
import {
  Search,
  Loader2,
  AlertCircle,
  RefreshCw,
  Download,
  Filter,
  ChevronDown,
  User,
  Globe,
  Shield,
  Clock
} from 'lucide-react'
import { apiCall } from '../../lib/auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.janua.dev'

interface AuditLog {
  id: string
  action: string
  user_id: string | null
  user_email: string | null
  resource_type: string | null
  resource_id: string | null
  details: Record<string, any> | null
  ip_address: string | null
  user_agent: string | null
  timestamp: string
}

interface AuditStats {
  total_events: number
  events_by_action: Record<string, number>
  events_by_user: Array<{ user_id: string; email: string; count: number }>
  events_by_resource_type: Record<string, number>
  unique_users: number
  unique_ips: number
}

export function AuditList() {
  const [searchTerm, setSearchTerm] = useState('')
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<AuditStats | null>(null)
  const [selectedAction, setSelectedAction] = useState<string>('')
  const [showFilters, setShowFilters] = useState(false)
  const [availableActions, setAvailableActions] = useState<string[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [cursor, setCursor] = useState<string | null>(null)

  useEffect(() => {
    fetchLogs()
    fetchStats()
    fetchAvailableActions()
  }, [])

  const fetchLogs = async (append = false) => {
    try {
      if (!append) setLoading(true)
      setError(null)

      let url = `${API_BASE_URL}/api/v1/audit-logs/?limit=50`
      if (selectedAction) url += `&action=${selectedAction}`
      if (cursor && append) url += `&cursor=${cursor}`

      const response = await apiCall(url)

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required')
        }
        throw new Error('Failed to fetch audit logs')
      }

      const data = await response.json()

      if (append) {
        setLogs(prev => [...prev, ...(data.logs || [])])
      } else {
        setLogs(data.logs || [])
      }

      setHasMore(data.has_more || false)
      setCursor(data.cursor || null)
    } catch (err) {
      console.error('Failed to fetch audit logs:', err)
      setError(err instanceof Error ? err.message : 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await apiCall(`${API_BASE_URL}/api/v1/audit-logs/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch audit stats:', err)
    }
  }

  const fetchAvailableActions = async () => {
    try {
      const response = await apiCall(`${API_BASE_URL}/api/v1/audit-logs/actions/list`)
      if (response.ok) {
        const data = await response.json()
        setAvailableActions(data.actions || [])
      }
    } catch (err) {
      console.error('Failed to fetch available actions:', err)
    }
  }

  const exportLogs = async (format: 'json' | 'csv') => {
    try {
      const response = await apiCall(`${API_BASE_URL}/api/v1/audit-logs/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format })
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `audit_logs.${format}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      } else {
        alert('Failed to export audit logs')
      }
    } catch (err) {
      console.error('Failed to export logs:', err)
      alert('Failed to export audit logs')
    }
  }

  const formatDateTime = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const getActionColor = (action: string): string => {
    if (action.includes('create') || action.includes('register')) {
      return 'bg-green-100 text-green-800'
    }
    if (action.includes('delete') || action.includes('revoke')) {
      return 'bg-red-100 text-red-800'
    }
    if (action.includes('update') || action.includes('modify')) {
      return 'bg-blue-100 text-blue-800'
    }
    if (action.includes('login') || action.includes('signin')) {
      return 'bg-purple-100 text-purple-800'
    }
    if (action.includes('logout') || action.includes('signout')) {
      return 'bg-yellow-100 text-yellow-800'
    }
    return 'bg-gray-100 text-gray-800'
  }

  const filteredLogs = logs.filter(log =>
    (log.user_email?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false) ||
    log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (log.ip_address?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false) ||
    (log.resource_type?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false)
  )

  if (loading && logs.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading audit logs...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h3 className="text-lg font-semibold mb-2">Failed to Load Audit Logs</h3>
        <p className="text-muted-foreground mb-4">{error}</p>
        <Button onClick={() => fetchLogs()} variant="outline">
          Try Again
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Stats Banner */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg">
          <div>
            <div className="text-2xl font-bold">{stats.total_events}</div>
            <div className="text-sm text-muted-foreground">Total Events</div>
          </div>
          <div>
            <div className="text-2xl font-bold">{stats.unique_users}</div>
            <div className="text-sm text-muted-foreground">Unique Users</div>
          </div>
          <div>
            <div className="text-2xl font-bold">{stats.unique_ips}</div>
            <div className="text-sm text-muted-foreground">Unique IPs</div>
          </div>
          <div>
            <div className="text-2xl font-bold">
              {Object.keys(stats.events_by_action).length}
            </div>
            <div className="text-sm text-muted-foreground">Action Types</div>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            placeholder="Search by user, action, IP, or resource..."
            className="w-full pl-8 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
            <ChevronDown className={`h-4 w-4 ml-1 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </Button>
          <Button variant="outline" size="sm" onClick={() => fetchLogs()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={() => exportLogs('json')}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="p-4 bg-muted/30 rounded-lg space-y-3">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium">Action Type:</label>
            <select
              className="px-3 py-1.5 border rounded-md text-sm"
              value={selectedAction}
              onChange={(e) => {
                setSelectedAction(e.target.value)
                setCursor(null)
                fetchLogs()
              }}
            >
              <option value="">All Actions</option>
              {availableActions.map(action => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-4 text-left text-sm font-medium">Timestamp</th>
              <th className="p-4 text-left text-sm font-medium">Action</th>
              <th className="p-4 text-left text-sm font-medium">User</th>
              <th className="p-4 text-left text-sm font-medium">Resource</th>
              <th className="p-4 text-left text-sm font-medium">IP Address</th>
              <th className="p-4 text-left text-sm font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted-foreground">
                  {searchTerm ? 'No audit logs match your search' : 'No audit logs found'}
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => (
                <tr key={log.id} className="border-b hover:bg-muted/50">
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <div className="text-sm font-medium">{formatTimeAgo(log.timestamp)}</div>
                        <div className="text-xs text-muted-foreground">{formatDateTime(log.timestamp)}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${getActionColor(log.action)}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <div className="text-sm">{log.user_email || 'System'}</div>
                        {log.user_id && (
                          <div className="text-xs text-muted-foreground font-mono">
                            {log.user_id.slice(0, 8)}...
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    {log.resource_type ? (
                      <div>
                        <div className="text-sm font-medium">{log.resource_type}</div>
                        {log.resource_id && (
                          <div className="text-xs text-muted-foreground font-mono">
                            {log.resource_id.slice(0, 8)}...
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-mono">{log.ip_address || '-'}</span>
                    </div>
                  </td>
                  <td className="p-4">
                    {log.details ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => alert(JSON.stringify(log.details, null, 2))}
                        title="View details"
                      >
                        <Shield className="h-4 w-4" />
                      </Button>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Load More */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div>
          Showing {filteredLogs.length} audit log entries
        </div>
        {hasMore && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchLogs(true)}
            disabled={loading}
          >
            {loading ? (
              <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Loading...</>
            ) : (
              'Load More'
            )}
          </Button>
        )}
      </div>

      {/* Top Actions */}
      {stats && Object.keys(stats.events_by_action).length > 0 && (
        <div className="p-4 bg-muted/30 rounded-lg">
          <h4 className="text-sm font-medium mb-3">Top Actions (Last 30 Days)</h4>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(stats.events_by_action)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 8)
              .map(([action, count]) => (
                <div key={action} className="flex items-center justify-between p-2 bg-background rounded border">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getActionColor(action)}`}>
                    {action}
                  </span>
                  <span className="text-sm font-medium">{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
