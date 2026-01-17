'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { adminAPI, type SystemHealth } from '@/lib/admin-api'
import { ServiceStatus } from './service-status'

export function InfrastructureSection() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await adminAPI.getHealth()
        setHealth(data)
      } catch (err) {
        console.error('Failed to fetch health:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchHealth()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-foreground">Infrastructure</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-card p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-4 text-foreground">Backend Services</h3>
          <div className="space-y-3">
            {health && (
              <>
                <ServiceStatus name="API Server" status={health.status} />
                <ServiceStatus name="Database" status={health.database} />
                <ServiceStatus name="Redis Cache" status={health.cache} />
                <ServiceStatus name="Storage" status={health.storage} />
                <ServiceStatus name="Email" status={health.email} />
              </>
            )}
          </div>
        </div>

        <div className="bg-card p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-4 text-foreground">Deployment Info</h3>
          <div className="space-y-2 text-sm">
            {health && (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Environment</span>
                  <span className="font-medium text-foreground">{health.environment}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Version</span>
                  <span className="font-medium text-foreground">{health.version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Uptime</span>
                  <span className="font-medium text-foreground">
                    {Math.floor(health.uptime / 3600)}h {Math.floor((health.uptime % 3600) / 60)}m
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
