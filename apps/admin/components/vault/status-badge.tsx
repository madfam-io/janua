'use client'

import { Badge } from '@/components/ui/badge'
import type { SecretStatus } from './types'

const statusConfig: Record<SecretStatus, { className: string; label: string }> = {
  active: { className: 'status-active', label: 'Active' },
  rotating: { className: 'status-rotating', label: 'Rotating' },
  expired: { className: 'status-expired', label: 'Expired' },
  revoked: { className: 'status-revoked', label: 'Revoked' },
}

export function VaultStatusBadge({ status }: { status: SecretStatus }) {
  const config = statusConfig[status]

  return (
    <Badge variant="outline" className={`${config.className} font-mono text-xs`}>
      {config.label}
    </Badge>
  )
}
