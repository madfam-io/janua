'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { adminAPI, type AdminUser } from '@/lib/admin-api'

export function UsersSection() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const data = await adminAPI.getUsers()
        setUsers(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch users')
      } finally {
        setLoading(false)
      }
    }
    fetchUsers()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <p className="text-destructive">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-foreground">User Management</h2>
        <span className="text-sm text-muted-foreground">{users.length} users</span>
      </div>

      <div className="bg-card rounded-lg border border-border">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">MFA</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Orgs</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Sessions</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Last Sign In</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-border hover:bg-muted/50">
                <td className="px-6 py-4">
                  <div>
                    <div className="text-sm font-medium text-foreground">
                      {user.first_name} {user.last_name}
                      {user.is_admin && (
                        <span className="ml-2 px-1.5 py-0.5 text-xs bg-destructive/10 text-destructive rounded">Admin</span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">{user.email}</div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    user.status === 'active' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                    user.status === 'suspended' ? 'bg-destructive/10 text-destructive' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {user.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  {user.mfa_enabled ? (
                    <span className="text-green-600 dark:text-green-400">Enabled</span>
                  ) : (
                    <span className="text-muted-foreground">Disabled</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-foreground">{user.organizations_count}</td>
                <td className="px-6 py-4 text-sm text-foreground">{user.sessions_count}</td>
                <td className="px-6 py-4 text-sm text-muted-foreground">
                  {user.last_sign_in_at ? new Date(user.last_sign_in_at).toLocaleString() : 'Never'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
