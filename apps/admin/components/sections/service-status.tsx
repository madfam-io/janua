'use client'

interface ServiceStatusProps {
  name: string
  status: string
}

export function ServiceStatus({ name, status }: ServiceStatusProps) {
  const isHealthy = status === 'healthy' || status === 'connected' || status === 'production'
  const statusColor = isHealthy
    ? 'bg-green-500/10 text-green-600 dark:text-green-400'
    : status === 'degraded'
    ? 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400'
    : 'bg-muted text-muted-foreground'

  return (
    <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
      <div className="text-sm font-medium text-foreground">{name}</div>
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColor}`}>
        {status}
      </span>
    </div>
  )
}
