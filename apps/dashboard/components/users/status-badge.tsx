'use client'

import { CheckCircle2, Clock, XCircle } from 'lucide-react'
import { Badge } from '@janua/ui'
import type { UserStatus } from './types'

const statusConfig = {
  active: { icon: CheckCircle2, className: 'badge-active', label: 'Active' },
  inactive: { icon: Clock, className: 'badge-inactive', label: 'Inactive' },
  banned: { icon: XCircle, className: 'badge-banned', label: 'Banned' },
  pending: { icon: Clock, className: 'badge-pending', label: 'Pending' },
}

export function StatusBadge({ status }: { status: UserStatus }) {
  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <Badge variant="outline" className={config.className}>
      <Icon className="h-3 w-3 mr-1" />
      {config.label}
    </Badge>
  )
}
