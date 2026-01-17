'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { adminAPI, type AdminOrganization } from '@/lib/admin-api'

export function TenantsSection() {
  const [orgs, setOrgs] = useState<AdminOrganization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchOrgs = async () => {
      try {
        const data = await adminAPI.getOrganizations()
        setOrgs(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch organizations')
      } finally {
        setLoading(false)
      }
    }
    fetchOrgs()
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
        <h2 className="text-2xl font-bold text-foreground">Tenant Management</h2>
        <span className="text-sm text-muted-foreground">{orgs.length} organizations</span>
      </div>

      <div className="bg-card rounded-lg border border-border">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Organization</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Plan</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Members</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Owner</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Created</th>
            </tr>
          </thead>
          <tbody>
            {orgs.map((org) => (
              <tr key={org.id} className="border-b border-border hover:bg-muted/50">
                <td className="px-6 py-4">
                  <div>
                    <div className="text-sm font-medium text-foreground">{org.name}</div>
                    <div className="text-xs text-muted-foreground">{org.slug}</div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    org.billing_plan === 'enterprise' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300' :
                    org.billing_plan === 'pro' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {org.billing_plan}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-foreground">{org.members_count}</td>
                <td className="px-6 py-4 text-sm text-muted-foreground">{org.owner_email}</td>
                <td className="px-6 py-4 text-sm text-muted-foreground">
                  {new Date(org.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
