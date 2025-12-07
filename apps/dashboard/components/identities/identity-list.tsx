'use client'

import { useState, useEffect } from 'react'
import { Button } from '@janua/ui'
import { MoreHorizontal, Search, Filter, Download, Loader2, AlertCircle } from 'lucide-react'
import { apiCall } from '../../lib/auth'

// API base URL for production - use public API URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.janua.dev'

interface Identity {
  id: string
  email: string
  name: string
  status: 'active' | 'inactive' | 'suspended'
  createdAt: string
  lastSignIn: string
  authMethods: string[]
}

interface ActivityLog {
  id: string
  user_id: string
  user_email: string
  action: string
  details: {
    method?: string
  }
  ip_address: string
  user_agent: string
  created_at: string
}

interface StatsResponse {
  total_users: number
  active_users: number
  suspended_users: number
}

export function IdentityList() {
  const [searchTerm, setSearchTerm] = useState('')
  const [identities, setIdentities] = useState<Identity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchIdentities()
  }, [])

  const fetchIdentities = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch activity logs to derive user information
      const activityResponse = await apiCall(`${API_BASE_URL}/api/v1/admin/activity-logs?per_page=100`)

      if (!activityResponse.ok) {
        throw new Error('Failed to fetch activity logs')
      }

      const activityLogs: ActivityLog[] = await activityResponse.json()

      // Extract unique users from activity logs
      const userMap = new Map<string, Identity>()

      for (const log of activityLogs) {
        if (!userMap.has(log.user_id)) {
          // Determine auth methods from activity logs
          const authMethods: string[] = []
          if (log.details?.method) {
            authMethods.push(log.details.method)
          }

          userMap.set(log.user_id, {
            id: log.user_id,
            email: log.user_email,
            name: log.user_email.split('@')[0] || 'Unknown',
            status: 'active',
            createdAt: log.created_at,
            lastSignIn: formatTimeAgo(log.created_at),
            authMethods: authMethods.length > 0 ? authMethods : ['password']
          })
        } else {
          // Update last sign in if this is a more recent signin action
          const existing = userMap.get(log.user_id)!
          if (log.action === 'signin' && new Date(log.created_at) > new Date(existing.createdAt)) {
            existing.lastSignIn = formatTimeAgo(log.created_at)
          }
          // Add auth methods if not already present
          if (log.details?.method && !existing.authMethods.includes(log.details.method)) {
            existing.authMethods.push(log.details.method)
          }
        }
      }

      setIdentities(Array.from(userMap.values()))
    } catch (err) {
      console.error('Failed to fetch identities:', err)
      setError(err instanceof Error ? err.message : 'Failed to load identities')
    } finally {
      setLoading(false)
    }
  }

  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    return date.toLocaleDateString()
  }

  const getStatusColor = (status: Identity['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'inactive':
        return 'bg-gray-100 text-gray-800'
      case 'suspended':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredIdentities = identities.filter(identity =>
    identity.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    identity.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading identities...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h3 className="text-lg font-semibold mb-2">Failed to Load Identities</h3>
        <p className="text-muted-foreground mb-4">{error}</p>
        <Button onClick={fetchIdentities} variant="outline">
          Try Again
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Search and Filter Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              placeholder="Search identities..."
              className="pl-8 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Button variant="outline" size="sm">
            <Filter className="h-4 w-4 mr-2" />
            Filter
          </Button>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={fetchIdentities}>
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Identity Table */}
      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-4 text-left text-sm font-medium">Identity</th>
              <th className="p-4 text-left text-sm font-medium">Status</th>
              <th className="p-4 text-left text-sm font-medium">Auth Methods</th>
              <th className="p-4 text-left text-sm font-medium">Last Sign In</th>
              <th className="p-4 text-left text-sm font-medium">User ID</th>
              <th className="p-4 text-left text-sm font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {filteredIdentities.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted-foreground">
                  {searchTerm ? 'No identities match your search' : 'No identities found'}
                </td>
              </tr>
            ) : (
              filteredIdentities.map((identity) => (
                <tr key={identity.id} className="border-b hover:bg-muted/50">
                  <td className="p-4">
                    <div>
                      <div className="font-medium">{identity.name}</div>
                      <div className="text-sm text-muted-foreground">{identity.email}</div>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(identity.status)}`}>
                      {identity.status}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex gap-1">
                      {identity.authMethods.map((method) => (
                        <span key={method} className="inline-flex items-center px-2 py-1 rounded-md bg-muted text-xs">
                          {method}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="p-4 text-sm text-muted-foreground">
                    {identity.lastSignIn}
                  </td>
                  <td className="p-4 text-sm text-muted-foreground font-mono">
                    {identity.id.slice(0, 8)}...
                  </td>
                  <td className="p-4">
                    <Button variant="ghost" size="sm">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Showing {filteredIdentities.length} of {identities.length} identities
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" size="sm" disabled>
            Previous
          </Button>
          <Button variant="outline" size="sm" disabled={identities.length < 100}>
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
