'use client'

import { useState, useEffect } from 'react'
import { Activity, Database, Server, Zap, RefreshCw } from 'lucide-react'
import { Button } from '@janua/ui'

interface HealthMetrics {
  status: string
  timestamp: string
  metrics: {
    api_response_time_ms: number
    database_latency_ms: number
    redis_latency_ms: number
    cache_hit_rate_percent: number
  }
  redis_stats: {
    circuit_state: string
    total_calls: number
    successful_calls: number
    failed_calls: number
  }
}

function getStatusColor(value: number, thresholds: { good: number; warning: number }): string {
  if (value <= thresholds.good) return 'text-green-600 dark:text-green-400'
  if (value <= thresholds.warning) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-destructive'
}

function getPercentColor(value: number): string {
  if (value >= 90) return 'text-green-600 dark:text-green-400'
  if (value >= 70) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-destructive'
}

export function SystemHealth() {
  const [metrics, setMetrics] = useState<HealthMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchMetrics = async () => {
    try {
      setLoading(true)
      setError(null)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.janua.dev'
      const response = await fetch(`${apiUrl}/api/v1/health/metrics`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch metrics: ${response.status}`)
      }

      const data = await response.json()
      setMetrics(data)
      setLastUpdated(new Date())
    } catch (err) {
      console.error('Failed to fetch health metrics:', err)
      setError(err instanceof Error ? err.message : 'Failed to load metrics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()

    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !metrics) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center justify-between animate-pulse">
            <div className="h-4 bg-muted rounded w-32"></div>
            <div className="h-4 bg-muted rounded w-16"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error && !metrics) {
    return (
      <div className="space-y-4">
        <div className="text-sm text-destructive flex items-center gap-2">
          <Activity className="h-4 w-4" />
          <span>Unable to load metrics</span>
        </div>
        <Button variant="outline" size="sm" onClick={fetchMetrics}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    )
  }

  const m = metrics?.metrics

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium flex items-center gap-2">
          <Server className="h-4 w-4 text-muted-foreground" />
          API Response Time
        </span>
        <span className={`text-sm font-medium ${getStatusColor(m?.api_response_time_ms || 0, { good: 50, warning: 200 })}`}>
          {m?.api_response_time_ms?.toFixed(1) || '--'}ms
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium flex items-center gap-2">
          <Database className="h-4 w-4 text-muted-foreground" />
          Database Latency
        </span>
        <span className={`text-sm font-medium ${getStatusColor(m?.database_latency_ms || 0, { good: 10, warning: 50 })}`}>
          {m?.database_latency_ms?.toFixed(1) || '--'}ms
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium flex items-center gap-2">
          <Zap className="h-4 w-4 text-muted-foreground" />
          Redis Latency
        </span>
        <span className={`text-sm font-medium ${getStatusColor(m?.redis_latency_ms || 0, { good: 5, warning: 20 })}`}>
          {m?.redis_latency_ms?.toFixed(1) || '--'}ms
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          Cache Success Rate
        </span>
        <span className={`text-sm font-medium ${getPercentColor(m?.cache_hit_rate_percent || 0)}`}>
          {m?.cache_hit_rate_percent?.toFixed(1) || '--'}%
        </span>
      </div>

      {/* Status indicator and refresh */}
      <div className="pt-2 border-t flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${metrics?.status === 'healthy' ? 'bg-green-500 dark:bg-green-400' : 'bg-yellow-500 dark:bg-yellow-400'}`}></div>
          <span>{metrics?.status === 'healthy' ? 'All systems operational' : 'Degraded'}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchMetrics}
          disabled={loading}
          className="h-6 px-2"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>
    </div>
  )
}
