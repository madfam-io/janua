'use client'

import { useState, useEffect } from 'react'
import {
  Users,
  Building2,
  Shield,
  Activity,
  CreditCard,
  RefreshCw,
  Loader2,
  AlertTriangle,
} from 'lucide-react'
import { adminAPI, type AdminStats, type SystemHealth } from '@/lib/admin-api'
import { ServiceStatus } from './service-status'

export function OverviewSection() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsData, healthData] = await Promise.all([
        adminAPI.getStats(),
        adminAPI.getHealth()
      ])
      setStats(statsData)
      setHealth(healthData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
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
        <AlertTriangle className="h-8 w-8 text-destructive mx-auto mb-2" />
        <p className="text-destructive">{error}</p>
        <button
          onClick={fetchData}
          className="mt-4 px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90"
        >
          Retry
        </button>
      </div>
    )
  }

  const statItems = stats ? [
    { label: 'Total Users', value: stats.total_users.toLocaleString(), change: `${stats.users_last_24h} new (24h)`, icon: Users },
    { label: 'Active Users', value: stats.active_users.toLocaleString(), change: `${Math.round((stats.active_users / stats.total_users) * 100)}% of total`, icon: Users },
    { label: 'Organizations', value: stats.total_organizations.toLocaleString(), change: '', icon: Building2 },
    { label: 'Active Sessions', value: stats.active_sessions.toLocaleString(), change: `${stats.sessions_last_24h} new (24h)`, icon: Activity },
    { label: 'MFA Enabled', value: stats.mfa_enabled_users.toLocaleString(), change: `${Math.round((stats.mfa_enabled_users / stats.total_users) * 100)}% of users`, icon: Shield },
    { label: 'Passkeys', value: stats.passkeys_registered.toLocaleString(), change: '', icon: CreditCard },
  ] : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-foreground">Platform Overview</h2>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground border border-border rounded-lg hover:bg-muted"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {statItems.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="bg-card p-6 rounded-lg border border-border">
              <div className="flex items-center justify-between mb-2">
                <Icon className="h-5 w-5 text-muted-foreground" />
                {stat.change && (
                  <span className="text-sm text-muted-foreground">{stat.change}</span>
                )}
              </div>
              <div className="text-2xl font-bold text-foreground">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          )
        })}
      </div>

      {/* System Health */}
      {health && (
        <div className="bg-card rounded-lg border border-border">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="text-lg font-semibold text-foreground">System Health</h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <ServiceStatus name="Database" status={health.database} />
              <ServiceStatus name="Cache (Redis)" status={health.cache} />
              <ServiceStatus name="Storage" status={health.storage} />
              <ServiceStatus name="Email" status={health.email} />
              <ServiceStatus name="Environment" status={health.environment} />
              <ServiceStatus name="Version" status={health.version} />
            </div>
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground">
                Uptime: {Math.floor(health.uptime / 3600)}h {Math.floor((health.uptime % 3600) / 60)}m
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
