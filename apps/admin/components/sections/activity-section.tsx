'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { adminAPI, type ActivityLog } from '@/lib/admin-api'

export function ActivitySection() {
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const data = await adminAPI.getActivityLogs()
        setLogs(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch activity logs')
      } finally {
        setLoading(false)
      }
    }
    fetchLogs()
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
      <h2 className="text-2xl font-bold text-foreground">Activity Logs</h2>

      <div className="bg-card rounded-lg border border-border">
        <div className="divide-y divide-border">
          {logs.map((log) => (
            <div key={log.id} className="p-4 hover:bg-muted/50">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">{log.action}</p>
                  <p className="text-xs text-muted-foreground">{log.user_email}</p>
                </div>
                <span className="text-xs text-muted-foreground">
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
              {log.ip_address && (
                <p className="mt-1 text-xs text-muted-foreground">IP: {log.ip_address}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
